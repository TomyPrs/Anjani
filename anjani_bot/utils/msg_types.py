""" Get type of each message. """
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

from enum import IntEnum, unique
from pyrogram.types import Message
from . import md_parse_button


@unique
class Types(IntEnum):
    TEXT = 0
    BUTTON_TEXT = 1
    DOCUMENT = 2
    PHOTO = 3
    VIDEO = 4
    STICKER = 5
    AUDIO = 6
    VOICE = 7
    VIDEO_NOTE = 8
    ANIMATION = 9


def get_note_type(msg: Message):
    """ Get type of notes. """
    data_type = None
    content = None
    text = ""
    raw_text = msg.text or msg.caption
    args = raw_text.split(None, 2)  # use python's maxsplit to separate cmd and args
    note_name = args[1]

    buttons = []
    # determine what the contents of the filter are - text, image, sticker, etc
    if len(args) >= 3:
        # offset = len(args[2]) - len(raw_text)  # set correct offset relative to command + notename
        text, buttons = md_parse_button(args[2])
        data_type = Types.BUTTON_TEXT if buttons else Types.TEXT
    elif msg.reply_to_message:
        msgtext = msg.reply_to_message.text or msg.reply_to_message.caption
        if len(args) >= 2 and msg.reply_to_message.text:  # not caption, text
            text, buttons = md_parse_button(msgtext)
            data_type = Types.BUTTON_TEXT if buttons else Types.TEXT
        elif msg.reply_to_message.sticker:
            content = msg.reply_to_message.sticker.file_id
            data_type = Types.STICKER

        elif msg.reply_to_message.document:
            content = msg.reply_to_message.document.file_id
            text, buttons = md_parse_button(msgtext)
            data_type = Types.DOCUMENT

        elif msg.reply_to_message.photo:
            content = msg.reply_to_message.photo[-1].file_id  # last elem = best quality
            text, buttons = md_parse_button(msgtext)
            data_type = Types.PHOTO

        elif msg.reply_to_message.audio:
            content = msg.reply_to_message.audio.file_id
            text, buttons = md_parse_button(msgtext)
            data_type = Types.AUDIO

        elif msg.reply_to_message.voice:
            content = msg.reply_to_message.voice.file_id
            text, buttons = md_parse_button(msgtext)
            data_type = Types.VOICE

        elif msg.reply_to_message.video:
            content = msg.reply_to_message.video.file_id
            text, buttons = md_parse_button(msgtext)
            data_type = Types.VIDEO

    return note_name, text, data_type, content, buttons


def get_message_type(msg):
    """ Get type message from message.text """
    if msg.text or msg.caption:
        content = None
        message_type = Types.TEXT
    elif msg.sticker:
        content = msg.sticker.file_id
        message_type = Types.STICKER

    elif msg.document:
        if msg.document.mime_type == "application/x-bad-tgsticker":
            message_type = Types.ANIMATED_STICKER
        else:
            message_type = Types.DOCUMENT
        content = msg.document.file_id

    elif msg.photo:
        content = msg.photo.file_id  # last elem = best quality
        message_type = Types.PHOTO

    elif msg.audio:
        content = msg.audio.file_id
        message_type = Types.AUDIO

    elif msg.voice:
        content = msg.voice.file_id
        message_type = Types.VOICE

    elif msg.video:
        content = msg.video.file_id
        message_type = Types.VIDEO

    elif msg.video_note:
        content = msg.video_note.file_id
        message_type = Types.VIDEO_NOTE

    elif msg.animation:
        content = msg.animation.file_id
        message_type = Types.ANIMATION
    else:
        return None, None

    return content, message_type


def get_welcome_type(msg: Message):
    """ Get welcome type. ."""
    data_type = None
    content = None
    text = ""

    args = msg.text.split(None, 1)  # use python's maxsplit to separate cmd and args

    buttons = []
    # determine what the contents of the filter are - text, image, sticker, etc
    if len(args) >= 2:
        # offset = len(args[1]) - len(msg.text)  # set correct offset relative to command + notename
        text, buttons = md_parse_button(args[1])
        data_type = Types.BUTTON_TEXT if buttons else Types.TEXT
    elif msg.reply_to_message and msg.reply_to_message.sticker:
        content = msg.reply_to_message.sticker.file_id
        text = msg.reply_to_message.caption
        data_type = Types.STICKER

    elif msg.reply_to_message and msg.reply_to_message.document:
        content = msg.reply_to_message.document.file_id
        text = msg.reply_to_message.caption
        data_type = Types.DOCUMENT

    elif msg.reply_to_message and msg.reply_to_message.photo:
        content = msg.reply_to_message.photo[-1].file_id  # last elem = best quality
        text = msg.reply_to_message.caption
        data_type = Types.PHOTO

    elif msg.reply_to_message and msg.reply_to_message.audio:
        content = msg.reply_to_message.audio.file_id
        text = msg.reply_to_message.caption
        data_type = Types.AUDIO

    elif msg.reply_to_message and msg.reply_to_message.voice:
        content = msg.reply_to_message.voice.file_id
        text = msg.reply_to_message.caption
        data_type = Types.VOICE

    elif msg.reply_to_message and msg.reply_to_message.video:
        content = msg.reply_to_message.video.file_id
        text = msg.reply_to_message.caption
        data_type = Types.VIDEO

    return text, data_type, content, buttons
