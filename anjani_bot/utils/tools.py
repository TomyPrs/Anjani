"""Bot tools"""
# Copyright (C) 2020 - 2021  UserbotIndo Team, <https://github.com/userbotindo.git>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import time
from random import choice
from typing import Union
from uuid import uuid4
from re import compile as compilere

from pyrogram.types import InlineKeyboardButton

# Regex for button parser
BTN_URL_REGEX = compilere(r"(\[([^\[]+?)\]\(buttonurl:(?:/{0,2})(.+?)(:same)?\))")

def get_readable_time(seconds: int) -> str:
    """get human readable time from seconds."""
    up_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]

    for count in range(1, 4):
        if count < 3:
            remainder, result = divmod(seconds, 60)
        else:
            remainder, result = divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)

    for index in enumerate(time_list):
        time_list[index[0]] = str(
            time_list[index[0]]) + time_suffix_list[index[0]]
    if len(time_list) == 4:
        up_time += time_list.pop() + ", "

    time_list.reverse()
    up_time += ":".join(time_list)

    return up_time


async def extract_time(time_text) -> Union[int, bool]:
    """ Extract time from time flags """
    if any(time_text.endswith(unit) for unit in ("m", "h", "d")):
        unit = time_text[-1]
        time_num = time_text[:-1]
        if not time_num.isdigit():
            return False

        if unit == "m":
            bantime = int(time.time() + int(time_num) * 60)
        elif unit == "h":
            bantime = int(time.time() + int(time_num) * 60 * 60)
        elif unit == "d":
            bantime = int(time.time() + int(time_num) * 24 * 60 * 60)
        return bantime
    return False


async def nekobin(client, data: str) -> str:
    """ return the nekobin pasted key """
    async with client.http.post(
            "https://nekobin.com/api/documents",
            json={"content": data},
    ) as resp:
        if resp.status != 200:
            response = await resp.json()
            key = response['result']['key']
            return key
    return None


async def remove_escapes(text: str) -> str:
    """Remove escaped in msg.text  """
    counter = 0
    res = ""
    is_escaped = False
    while counter < len(text):
        if is_escaped:
            res += text[counter]
            is_escaped = False
        elif text[counter] == "\\":
            is_escaped = True
        else:
            res += text[counter]
        counter += 1
    return res


async def md_parse_button(text):
    """ Parse button from matched msg.text. """
    markdown_parser = text
    prev = 0
    parser_data = ""
    buttons = []
    for match in BTN_URL_REGEX.finditer(markdown_parser):
        # escape check
        md_escaped = 0
        to_check = match.start(1) - 1
        while to_check > 0 and markdown_parser[to_check] == "\\":
            md_escapes += 1
            to_check -= 1

        # if != "escaped" -> Create button: btn
        if md_escaped % 2 == 0:
            # create a thruple with button label, url, and newline status
            buttons.append((match.group(2), match.group(3), bool(match.group(4))))
            parser_data += markdown_parser[prev : match.start(1)]
            prev = match.end(1)
        # if odd, escaped -> move along
        else:
            parser_data += markdown_parser[prev:to_check]
            prev = match.start(1) - 1

    parser_data += markdown_parser[prev:]

    return parser_data, buttons


async def build_keyboard(buttons):
    """Build keyboards from provided buttons."""
    keyb = []
    for btn in buttons:
        if btn[-1] and keyb:
            keyb[-1].append(InlineKeyboardButton(btn[0], url=btn[1]))
        else:
            keyb.append([InlineKeyboardButton(btn[0], url=btn[1])])

    return keyb


def format_integer(number, thousand_separator="."):
    """ make an integer easy to read """
    def _reverse(string):
        string = "".join(reversed(string))
        return string

    string = _reverse(str(number))
    count = 0
    result = ""
    for char in string:
        count += 1
        if count % 3 == 0:
            if len(string) == count:
                result = char + result
            else:
                result = thousand_separator + char + result
        else:
            result = char + result
    return result


async def extrack_text(message):
    """ extrack msg.text ["Caption", "Text", "None=Sticker"] """
    return message.text or message.caption or (message.sticker.emoji if message.sticker else None)


def rand_array(array: list):
    """pick an item randomly from list"""
    return choice(array)


def rand_key():
    """generates a random key"""
    return str(uuid4())[:8]
