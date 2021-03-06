"""
    Copyright (c) 2018 Elliott Pardee <me [at] vypr [dot] xyz>
    This file is part of BibleBot.

    BibleBot is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    BibleBot is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with BibleBot.  If not, see <http://www.gnu.org/licenses/>.
"""

import json
import numbers
import os
import re
import sys

__dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f"{__dir_path}/../..")

import data.BGBookNames.start as bgbooknames  # noqa: E402
from data.BGBookNames.books import item_to_book  # noqa: E402
import central  # noqa: E402

books = None

try:
    books = open(f"{__dir_path}/../../data/BGBookNames/books.json")
    books = json.loads(books.read())
except FileNotFoundError:
    bgbooknames.get_books()
    books = open(f"{__dir_path}/../../data/BGBookNames/books.json")
    books = json.loads(books.read())

dashes = ["-", "—", "–"]


def list_duplicates_of(seq, item):
    start_at = -1
    locs = []

    while True:
        try:
            loc = seq.index(item, start_at + 1)
        except ValueError:
            break
        else:
            locs.append(loc)
            start_at = loc

    return locs


def purify(msg):
    msg = msg.replace("(", " ( ")
    msg = msg.replace(")", " ) ")
    msg = msg.replace("[", " [ ")
    msg = msg.replace("]", " ] ")
    msg = msg.replace("{", " { ")
    msg = msg.replace("}", " } ")
    msg = msg.replace("<", " < ")
    msg = msg.replace(">", " > ")
    msg = re.sub(r"[.,;'\"_=$#*&^%@!?]", "", msg)
    return central.capitalize_first_letter(msg)


def purge_brackets(msg):
    msg = msg.replace("(", "")
    msg = msg.replace(")", "")
    msg = msg.replace("[", "")
    msg = msg.replace("]", "")
    msg = msg.replace("{", "")
    msg = msg.replace("}", "")
    msg = msg.replace("<", "")
    msg = msg.replace(">", "")
    return msg.replace(" ", "")


def get_difference(a, b):
    i = 0
    j = 0
    result = ""

    while j < len(b):
        try:
            if a[i] != b[j] or i == len(a):
                result += b[j]
            else:
                i += 1
        except IndexError:
            result += b[j]

        j += 1

    return result.strip()


def get_books(msg):
    results = []
    existing_indices = []

    for key, value in books.items():
        for item in value:
            if item in msg:
                last_item = item.split(" ")[-1]
                msg_split = msg.split(" ")

                indices = [i for i, x in enumerate(msg_split) if x == last_item]

                for index in indices:
                    results.append((key, index))

                    if index not in existing_indices:
                        existing_indices.append(index)

    names = [i for i, j in results]
    indices = [j for i, j in results]

    numbered_overlap = ["1john", "2john", "3john", "1esdras", "2esdras"]

    try:
        for overlap in numbered_overlap:
            if overlap in names:
                name_index = names.index(overlap)
                indices_index = indices[name_index]

                for key, value in enumerate(indices):
                    if indices_index == value and names[key] != overlap:
                        results.pop(key)
    except IndexError:
        pass

    for index in existing_indices:
        dupes = list_duplicates_of(indices, index)

        if len(dupes) > 1:
            for i, j in enumerate(dupes):
                if i < len(results) - 1:
                    results.pop(i)

    return results


def create_verse_object(name, book_index, msg, available_versions, brackets):
    book_index = int(book_index)
    array = msg.split(" ")

    # find various indexes for brackets and see
    # if our verse is being surrounded by them
    bracket_indexes = []
    for i, j in enumerate(array):
        if i <= book_index:
            if brackets["first"] in j:
                is_instance = isinstance(j.index(brackets["first"]), numbers.Number)

                if is_instance:
                    bracket_indexes.append(i)

        if i > book_index:
            if brackets["second"] in j:
                is_instance = isinstance(j.index(brackets["second"]), numbers.Number)

                if is_instance:
                    bracket_indexes.append(i)

    if len(bracket_indexes) == 2:
        if bracket_indexes[0] <= book_index <= bracket_indexes[1]:
            return "invalid"

    try:
        number_split = array[book_index + 1].split(":")
    except IndexError:
        return "invalid"

    dash_split = None

    if len(number_split) > 1:
        dash_split = number_split[1].split("-")

    verse = {
        "book": name,
        "chapter": None,
        "startingVerse": None,
        "endingVerse": None
    }

    try:
        if isinstance(int(number_split[0]), numbers.Number):
            verse["chapter"] = int(number_split[0])

            if dash_split is not None:
                if isinstance(int(dash_split[0]), numbers.Number):
                    verse["startingVerse"] = int(dash_split[0])

                    if isinstance(int(dash_split[1]), numbers.Number):
                        verse["endingVerse"] = int(dash_split[1])

                        if verse["startingVerse"] > verse["endingVerse"]:
                            return "invalid"
    except (IndexError, TypeError, ValueError):
        verse = verse

    try:
        if re.sub(r"[0-9]", "", dash_split[1]) == dash_split[1]:
            if dash_split[1] == "":
                verse["endingVerse"] = "-"
    except (IndexError, TypeError):
        verse = verse

    try:
        if array[book_index + 2].upper() in available_versions:
            verse["version"] = array[book_index + 2].upper()
    except IndexError:
        verse = verse

    if verse["startingVerse"] is None:
        return

    return verse


def create_reference_string(verse):
    reference = None

    try:
        if not isinstance(int(verse["chapter"]), numbers.Number):
            return
    except (ValueError, TypeError, KeyError):
        verse = verse

    if verse is None:
        return

    if "startingVerse" in verse.keys():
        if verse["startingVerse"] is not None:
            if verse["book"] in item_to_book["ot"]:
                reference = item_to_book["ot"][verse["book"]] + "|" + \
                            str(verse["chapter"]) + ":" + str(verse["startingVerse"])
            elif verse["book"] in item_to_book["nt"]:
                reference = item_to_book["nt"][verse["book"]] + "|" + \
                            str(verse["chapter"]) + ":" + str(verse["startingVerse"])
            elif verse["book"] in item_to_book["deu"]:
                reference = item_to_book["deu"][verse["book"]] + "|" + \
                            str(verse["chapter"]) + ":" + str(verse["startingVerse"])
        else:
            if verse["book"] in item_to_book["ot"]:
                reference = item_to_book["ot"][verse["book"]] + "|" + str(verse["chapter"])
            elif verse["book"] in item_to_book["nt"]:
                reference = item_to_book["nt"][verse["book"]] + "|" + str(verse["chapter"])
            elif verse["book"] in item_to_book["deu"]:
                reference = item_to_book["deu"][verse["book"]] + "|" + str(verse["chapter"])

        if "endingVerse" in verse.keys():
            if verse["endingVerse"] is not None:
                try:
                    if verse["endingVerse"] != "-":
                        if int(verse["startingVerse"]) <= int(verse["endingVerse"]):
                            reference += "-" + str(verse["endingVerse"])
                    else:
                        reference += "-"
                except (ValueError, TypeError, KeyError):
                    reference = reference

    if "version" in verse.keys():
        reference = reference + " | v: " + verse["version"]

    return reference
