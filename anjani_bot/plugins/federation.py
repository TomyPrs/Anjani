"""Bot Federation Tools"""
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

import asyncio
import logging
import os
import time
from datetime import datetime
from typing import Union

from motor.motor_asyncio import AsyncIOMotorCursor
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from anjani_bot import listener, plugin
from anjani_bot.utils import (
    ParsedChatMember,
    extract_user,
    extract_user_and_text,
    rand_key,
)

LOGGER = logging.getLogger(__name__)


class FedBase(plugin.Plugin):
    # declaring collection as a class member cause used by other.
    feds_db = listener.__bot__.get_collection("FEDERATIONS")

    async def __on_load__(self):
        self.lock = asyncio.Lock()

    async def __migrate__(self, old_chat_id, new_chat_id):
        async with self.lock:
            await self.feds_db.update_one(
                {"chats": old_chat_id}, {"$set": {"chats.$": new_chat_id}}
            )

    @staticmethod
    def is_fed_admin(fed_data: dict, user_id) -> bool:
        """Check federation admin"""
        return user_id == fed_data["owner"] or user_id in fed_data.get("admins", [])

    @classmethod
    async def get_fed_bychat(cls, chat_id):
        """Get fed data from chat id"""
        return await cls.feds_db.find_one({"chats": chat_id})

    async def get_fed(self, fid):
        """Get fed data"""
        return await self.feds_db.find_one({"_id": fid})

    async def fban_user(self, fid, user_id, fullname=None, reason=None, ban: bool = True):
        """Remove or Add banned user"""
        if ban:
            action = "$set"
            data = {"name": fullname, "reason": reason, "time": time.time()}
        else:
            action = "$unset"
            data = 1
        async with self.lock:
            await self.feds_db.update_one(
                {"_id": fid}, {action: {f"banned.{int(user_id)}": data}}, upsert=True
            )

    async def check_fban(self, user_id) -> Union[AsyncIOMotorCursor, bool]:
        """Check user banned list"""
        doc = await self.feds_db.count_documents({f"banned.{user_id}": {"$exists": True}})
        return (
            self.feds_db.find(
                {f"banned.{user_id}": {"$exists": True}},
                projection={f"banned.{user_id}": 1, "name": 1, "chats": 1},
            )
            if doc
            else False
        )

    @staticmethod
    def parse_date(timestamp: float) -> str:
        """get a date format from a timestamp"""
        return datetime.fromtimestamp(timestamp).strftime("%Y %b %d %H:%M UTC")


class Federation(FedBase):
    name = "Federations"
    helpable = True

    @listener.on("newfed")
    async def new_fed(self, message):
        """Create a new federations"""
        chat_id = message.chat.id
        if message.chat.type != "private":
            return await message.reply_text(await self.bot.text(chat_id, "error-chat-not-private"))

        if message.command:
            fed_name = (" ".join(message.command)).strip()
            fed_id = rand_key()
            owner_id = message.from_user.id

            check = await self.feds_db.find_one({"owner": owner_id})
            if check:
                return await message.reply_text("You can only own 1 federation")

            async with self.lock:
                await self.feds_db.insert_one({"_id": fed_id, "name": fed_name, "owner": owner_id})
            await asyncio.gather(
                message.reply_text(
                    "**New federation have been created**\n"
                    f"**Name:** {fed_name}\n"
                    f"**Fed ID:** {fed_id}\n\n"
                    f"Use this command on group to join the federations\n"
                    f"`/joinfed {fed_id}`",
                    parse_mode="markdown",
                ),
                self.bot.channel_log(
                    f"Created new federation **{fed_name}** with ID: **{fed_id}**"
                ),
            )
        else:
            await message.reply_text("Please write the federation name too!")

    @listener.on("delfed")
    async def del_fed(self, message):
        """Delete federations"""
        chat_id = message.chat.id
        if message.chat.type != "private":
            return await message.reply_text(await self.bot.text(chat_id, "error-chat-not-private"))

        if message.command:
            to_del_fed = message.command[0]
            user_id = message.from_user.id
            feds = await self.get_fed(to_del_fed)
            if not feds:
                return await message.reply_text("No federation found with that ID!")
            # if not (feds["owner"] == user_id or user_id == self.bot.staff["owner"]):
            if user_id not in (feds["owner"], self.bot.staff["owner"]):
                return await message.reply_text("Only federation owner can delete!")

            await message.reply_text(
                "Are you sure you want to delete this federation? "
                "This action cannot be undone! "
                "You will loose your entire ban list and your federation "
                "will be permanently lost!"
                f"\nConfirm deletion of **{feds['name']}**",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Confirm Deletion",
                                callback_data=f"rmfed_{to_del_fed}",
                            )
                        ],
                        [InlineKeyboardButton(text="Abort", callback_data="rmfed_abort")],
                    ]
                ),
            )
        else:
            await message.reply_text("Specified the feds ID you want to delete.")

    @listener.on(filters=filters.regex(r"rmfed_(.*?)"), update="callbackquery")
    async def del_fed_query(self, query):
        """Delete federation button listener"""
        fed_id = query.data.split("_")[1]
        if fed_id == "abort":
            return await query.message.edit_text("Federation deletion canceled")
        async with self.lock:
            data = await self.feds_db.find_one_and_delete({"_id": fed_id})
        await query.message.edit_text(
            "You have removed your Federation!\n"
            f"All groups data that connect to **{data['name']}** are now removed."
        )

    @listener.on("joinfed", admin_only=True)
    async def join_fed(self, message):
        """Join a federation in chats"""
        chat_id = message.chat.id
        user_id = message.from_user.id
        admins = await message.chat.get_member(user_id)
        if not (admins.status == "creator" or user_id == self.bot.staff["owner"]):
            return await message.reply_text("Only group creator can use this command!")

        if message.command:
            if await self.get_fed_bychat(chat_id):
                return await message.reply_text("You cannot join two federations from one chat!")
            fid = message.command[0]
            check = await self.get_fed(fid)
            if not check:
                return await message.reply_text("Please enter a valid federation ID")
            if chat_id in check.get("chats", []):
                return await message.reply_text(
                    "This group is already connected to that federation"
                )

            async with self.lock:
                await self.feds_db.update_one({"_id": fid}, {"$push": {"chats": chat_id}})
            await message.reply_text(f"Chat joined to **{check['name']}** Federation!")

    @listener.on("leavefed", admin_only=True)
    async def leave_fed(self, message):
        """Leave a federation in chats"""
        chat_id = message.chat.id
        user_id = message.from_user.id
        admins = await message.chat.get_member(user_id)
        if not (admins.status == "creator" or user_id == self.bot.staff["owner"]):
            return await message.reply_text("Only group creator can use this command!")

        if message.command:
            fid = message.command[0]
            check = await self.get_fed(fid)
            if not check:
                return await message.reply_text("Please enter a valid federation ID")
            if chat_id not in check.get("chats"):
                return await message.reply_text("This chat isn't connected to that federation!")

            async with self.lock:
                await self.feds_db.update_one({"_id": fid}, {"$pull": {"chats": chat_id}})
            await message.reply_text(f"This chat has left the **{check['name']}** Federation!")

    @listener.on(["fpromote", "fedpromote"])
    async def promote_fadmin(self, message):
        """Promote user to fed admin"""
        if message.chat.type == "private":
            return await message.reply_text("This command is specific to the group, not to the PM!")

        chat_id = message.chat.id
        user_id = message.from_user.id
        to_promote, _ = extract_user_and_text(message)
        if not to_promote:
            return await message.reply_text("Who should I promote?\nGive me some user!")
        if isinstance(to_promote, str):
            to_promote = (await extract_user(self.bot.client, to_promote)).id
        fed_data = await self.get_fed_bychat(chat_id)
        if not fed_data:
            return await message.reply_text("Chat not connected to any Federation")
        if user_id != fed_data["owner"]:
            return await message.reply_text("Only federation owner can promote new admin!")
        if to_promote == fed_data["owner"]:
            return await message.reply_text("You are the owner of this Feds!")
        if to_promote in fed_data.get("admins", []):
            return await message.reply_text("User already an admin in this feds")

        async with self.lock:
            await self.feds_db.update_one(
                {"_id": fed_data["_id"]}, {"$push": {"admins": to_promote}}
            )
        await message.reply_text("succesfully fpromoted!")

    @listener.on(["fdemote", "feddemote"])
    async def demote_fadmin(self, message):
        """Demote user to fed admin"""
        if message.chat.type == "private":
            return await message.reply_text("This command is specific to the group, not to the PM!")

        chat_id = message.chat.id
        user_id = message.from_user.id
        to_demote, _ = extract_user_and_text(message)
        if not to_demote:
            return await message.reply_text("Who should I demote?\nGive me some user!")
        if isinstance(to_demote, str):
            to_demote = (await extract_user(self.bot.client, to_demote)).id
        fed_data = await self.get_fed_bychat(chat_id)
        if not fed_data:
            return await message.reply_text("Chat not connected to any Federation")
        if user_id != fed_data["owner"]:
            return await message.reply_text("Only federation owner can demote admin!")
        if to_demote == fed_data["owner"]:
            return await message.reply_text("You are the owner of this Feds!")
        if to_demote not in fed_data.get("admins", []):
            return await message.reply_text("User isn't an admin in this federation!")

        async with self.lock:
            await self.feds_db.update_one(
                {"_id": fed_data["_id"]}, {"$pull": {"admins": to_demote}}
            )
        await message.reply_text("succesfully fdemoted!")

    @listener.on("fedinfo")
    async def fed_info(self, message):
        """Fetch federation info"""
        chat_id = message.chat.id
        if message.command:
            fdata = await self.get_fed(message.command[0])
            text = "Can't find federation with that ID"
        elif message.chat.type != "private":
            fdata = await self.get_fed_bychat(chat_id)
            text = "This chat is not in any federation!"
        else:
            fdata = None
            text = "Please specified a federation ID"

        if not fdata:
            return await message.reply_text(text)

        owner = await extract_user(self.bot.client, fdata["owner"])

        text = "**Federation Information:**\n"
        text += f"**Fed ID: **` {fdata['_id']}`\n"
        text += f"**Name: **`{fdata['name']}`\n"
        text += f"**Creator: **{owner.mention}\n"
        text += f"**Total Admins: ** `{len(fdata.get('admins', []))}`\n"
        text += f"**Total banned user: ** `{len(fdata.get('banned', []))}`\n"
        text += f"**Total groups connected: ** `{len(fdata.get('chats', []))}`"
        await message.reply_text(text)

    @listener.on("fadmins")
    async def fed_admins(self, message):
        """Fetch federation admins"""
        chat_id = message.chat.id
        if message.command:
            fdata = await self.get_fed(message.command[0])
            text = "Can't find federation with that ID"
        else:
            fdata = await self.get_fed_bychat(chat_id)
            text = "This chat is not in any federation!"

        if not fdata:
            return await message.reply_text(text)
        user_id = message.from_user.id
        if not self.is_fed_admin(fdata, user_id):
            return await message.reply_text("Only federation admin can do this")

        owner = await extract_user(self.bot.client, fdata["owner"])

        text = f"**{fdata['name']}** admins:\n"
        text += f"👑 Owner: {owner.mention}\n"
        if len(fdata.get("admins", [])) != 0:
            text += "Admins:\n"
            for admin in fdata["admins"]:
                user = await extract_user(self.bot.client, admin)
                text += f" • {user.mention}\n"
        else:
            text += "There are no admin in this federation"
        await message.reply_text(text)

    @listener.on("fban")
    async def fed_ban(self, message):
        """Fed ban a user"""
        if message.chat.type == "private":
            return await message.reply_text("This command is specific to the group, not to the PM!")

        chat_id = message.chat.id
        banner = message.from_user
        fed_data = await self.get_fed_bychat(chat_id)
        if not fed_data:
            return await message.reply_text("This chat is not in any federation!")

        if not self.is_fed_admin(fed_data, banner.id):
            return await message.reply_text("Only federation admin can do this")

        to_ban, reason = extract_user_and_text(message)
        if not to_ban:
            return await message.reply_text("You don't seem to be referring to a user")

        user = await extract_user(self.bot.client, to_ban)
        user_id = user.id
        if user_id == self.bot.identifier:
            return await message.reply_text("Please... i'm not that dumb!")
        if self.is_fed_admin(fed_data, user_id):
            return await message.reply_text("He is a federation admin, I can't fban him.")
        if user_id in self.bot.staff_id or user_id in (777000, 1087968824):
            return await message.reply_text("I won't fban this user!")

        if not reason:
            reason = "No reason given."
        update = False
        if str(user_id) in fed_data.get("banned", {}).keys():
            update = True

        banned_user = ParsedChatMember(user)
        await self.fban_user(fed_data["_id"], user_id, banned_user.fullname, reason, True)
        if update:
            text = (
                "**New Federation Ban**\n"
                f"**Federation: **{fed_data['name']}\n"
                f"**Federation admin: **{banner.mention}\n"
                f"**User: ** {banned_user.mention}\n"
                f"**User ID: ** {user_id}\n"
                f"**Old reason**: {fed_data['banned'][str(user_id)]['reason']}\n"
                f"**New reason**: {reason}"
            )
        else:
            text = (
                "**New Federation Ban**\n"
                f"**Federation: **{fed_data['name']}\n"
                f"**Federation admin: **{banner.mention}\n"
                f"**User: ** {banned_user.mention}\n"
                f"**User ID: ** {user_id}\n"
                f"**Reason**: {reason}"
            )

        await message.reply_text(text, disable_web_page_preview=True)
        for chats in fed_data["chats"]:
            await self.bot.client.kick_chat_member(chats, user_id)

    @listener.on("unfban")
    async def unfban_user(self, message):
        """Unban a user on federation"""
        if message.chat.type == "private":
            return await message.reply_text("This command is specific to the group, not to the PM!")

        chat_id = message.chat.id
        banner = message.from_user
        fed_data = await self.get_fed_bychat(chat_id)
        if not fed_data:
            return await message.reply_text("This chat is not in any federation!")

        if not self.is_fed_admin(fed_data, banner.id):
            return await message.reply_text("Only federation admin can do this")

        to_unban, _ = extract_user_and_text(message)
        if not to_unban:
            return await message.reply_text("You don't seem to be referring to a user")

        user = await extract_user(self.bot.client, to_unban)
        if str(user.id) not in fed_data.get("banned").keys():
            return await message.reply_text("This user is not fbanned!")

        await self.fban_user(fed_data["_id"], user.id, ParsedChatMember(user).fullname, ban=False)

        text = (
            "**Un-FedBan**\n"
            f"**Federation : **{str(fed_data['name'])}\n"
            f"**Federation admin: **{banner.mention}\n"
            f"**User: **{user.mention}\n"
            f"**User ID: **`{user.id}`"
        )
        await message.reply_text(text)
        for chats in fed_data["chats"]:
            await self.bot.client.unban_chat_member(chats, user.id)

    @listener.on(["fedstats", "fstats"])
    async def fed_stats(self, message):
        """Get user status"""
        # chat_id = message.chat.id
        user_id, _ = extract_user_and_text(message)
        if isinstance(user_id, str):
            user_id = (await extract_user(self.bot.client, user_id)).id
        if not user_id:
            user_id = message.from_user.id

        # <user_Id> <fed_id>
        if len(message.command) == 2 and message.command[0].isdigit():
            fid = message.command[1]
            data = await self.get_fed(fid)
            if not data:
                return await message.reply_text("Can't find federation with that ID")
            if message.command[0] in data.get("banned", {}):
                res = data["banned"][str(message.command[0])]
                await message.reply_text(
                    "User is banned in that federation\n"
                    f"**Reason: **{res['reason']}\n"
                    f"**Banned on: **{self.parse_date(res['time'])}"
                )
            else:
                return await message.reply_text("User is not banned in that federation!")

        # <user_Id>
        else:
            data = await self.check_fban(user_id)
            if data:
                text = "This user has been banned in this federations\n"
                async for bans in data:
                    text += f" -  **{bans['name']}**(`{bans['_id']}`)\n"
                    text += f"    **Reason: **{bans['banned'][str(user_id)]['reason']}\n"
            else:
                text = "This user is not banned in any federation!"
            await message.reply_text(text)

    @listener.on("fbackup", filters.private)
    async def backup_fedband(self, message):
        """Backup federation ban list"""
        if not message.command:
            return await message.reply_text("Give me a Fed ID to backup")

        data = await self.get_fed(message.command[0])
        if not data:
            return await message.reply_text("Invalid Fed ID!")
        if message.from_user.id != data["owner"]:
            return await message.reply_text("Only federation owner can do this!")

        banned_list = data["banned"]
        file_name = f"{self.bot.get_config.download_path}{data['name']}.csv"
        print(file_name)
        with open(file_name, "w") as file:
            for user in banned_list:
                ban_data = banned_list[str(user)]
                file.writelines(
                    f"{user},{ban_data['name']},{ban_data['reason']},{ban_data['time']}"
                )

        await message.reply_document(file_name)
        os.remove(file_name)

    @listener.on("fexport", filters.private)
    async def restore_fban(self, message):
        """Restore a backup bans"""
        chat_id = message.chat.id
        if not (message.reply_to_message and message.reply_to_message.document):
            return await message.reply_text(await self.bot.text(chat_id, "no-backup-file"))
        if not message.command:
            return await message.reply_text("Give me a Fed ID to backup")
        fid = message.command[0]
        data = await self.get_fed(fid)
        if not data:
            return await message.reply_text("Invalid Fed ID!")

        file = await message.reply_to_message.download(self.bot.get_config.download_path)
        with open(file, "r") as buff:
            for line in buff:
                data = line.split(",")
                await self.fban_user(fid, data[0], data[1], data[2], True)
        await message.reply_text("Restore done")
        os.remove(file)
