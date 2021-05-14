""" text extractor tools """
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

from typing import Optional, Tuple, Union, Sequence

from pyrogram.types import Message, User


class ParsedChatMember:
    """Chat member attribute parser

    Attributes:
        first_name (`str`):
            User's or bot's first name.
        fullname (`str`):
            User's full name. use user first_name if not exist.
        mention (`str`):
            A text mention for this user.
        username (`str`):
            User's username.
        count (`int`, *Optional*):
            Number of members in the chat.
    """

    def __init__(self, user: User):
        self.first_name = user.first_name
        if user.last_name:
            self.fullname = self.first_name + user.last_name
        else:
            self.fullname = self.first_name
        self.mention = user.mention(style="html")
        if user.username:
            self.username = f"@{user.username}"
        else:
            self.username = self.mention
        self.count = None

    async def get_members(self, client, chat_id):
        """Count chat member"""
        self.count = await client.get_chat_members_count(chat_id)


class GetChatLock:
    def chat_lock(self, message: Message, lock_type: str, should_lock: bool) -> Sequence[str]:
        self.lock = not should_lock
        chat_perm = message.chat.permissions
        self.message = chat_perm.can_send_messages
        self.media = chat_perm.can_send_media_messages
        self.stickers = chat_perm.can_send_stickers
        self.animations = chat_perm.can_send_animations
        self.games = chat_perm.can_send_games
        self.inlinebots = chat_perm.can_use_inline_bots
        self.wpprev = chat_perm.can_add_web_page_previews
        self.polls = chat_perm.can_send_polls
        self.info = chat_perm.can_change_info
        self.invite = chat_perm.can_invite_users
        self.pin = chat_perm.can_pin_messages
        self.perm = None
        return (
            message,
            media,
            stickers,
            animations,
            games,
            inlinebots,
            wepprev,
            polls,
            info,
            invite,
            pin,
            perm,
        )


def extract_user_and_text(message: Message) -> Tuple[Union[str, int], Optional[str]]:
    """extract user and text from message.
    Prioritize user from replied message.
    Returns:
        user (None | int | str) and text (None | str).
    """
    user = None
    text = None
    if message.reply_to_message:
        user = message.reply_to_message.from_user.id
        if message.command:
            text = " ".join(message.command)
        return user, text
    if message.command:
        usr = message.command[0]
        if usr.isdigit():  # user_id
            user = int(usr)
        elif usr.startswith("@"):  # username
            user = usr
        if len(message.command) >= 2:
            text = " ".join(message.command[1:])
        if len(message.command) >= 1 and user is None:
            text = " ".join(message.command)
    return user, text


async def extract_user(client, user_ids: Union[str, int]) -> User:
    """Excract user from user id"""
    return await client.get_users(user_ids)
