""" Lock Unlock Chat plugin. """
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

from pyrogram.types import ChatPermissions
from typing import ClassVar
from pyrogram.errors import ChatAdminRequired
from anjani_bot import listener, plugin
from anjani_bot.utils.extractor import GetChatLock


class Locks(plugin.Plugin, GetChatLock):
    name: ClassVar[str] = "Locks"
    helpable: ClassVar[bool] = True

    @listener.on("lock")
    async def lock_action(self, message):
        """ lock .. """
        chat_id = message.chat.id
        arg = message.command[0]
        lock_types = [
            "all",
            "message",
            "media",
            "animations",
            "stickers",
            "games",
            "inlinebot",
            "polls",
            "wpprev",
            "info",
            "pin",
        ]

        if not message.command or arg not in lock_types:
            return await message.reply("Use / help, rather than just trying 🙂")

        if message.command[0] not in lock_types:
            return await message.reply("Invalid lock types .. ")

        if arg == 'all':
            try:
                await self.bot.client.set_chat_permissions(chat_id, ChatPermissions())
            except ChatAdminRequired:
                return await message.reply("I'm not an admin / I don't have enough rights here..")
        if arg in lock_types:
            (
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
            ) = self.chat_lock(message, lock_types, should_lock, True)
        try:
            await self.bot.client.set_chat_permissions(
                chat_id,
                ChatPermissions(
                    can_send_messages=message,
                    can_send_media_messages=media,
                    can_send_stickers=stickers,
                    can_send_animations=animations,
                    can_send_games=games,
                    can_use_inline_bots=inlinebots,
                    can_add_web_page_previews=wepprev,
                    can_send_polls=polls,
                    can_change_info=info,
                    can_invite_users=invite,
                    can_pin_messages=pin,
                ),
            )
        except Exception:
            return await message.reply("I am not an admin / I have no right to that")
        await message.reply(f"{perm} locked for all non admin")
