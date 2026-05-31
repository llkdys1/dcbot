import os
import time

import discord
from discord.ext import commands


class PresenceGreeter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.target_user_ids = self._load_target_user_ids()
        self.greet_cooldown_seconds = 20 * 60
        self.last_greeted_at = {}

    def _load_target_user_ids(self):
        raw_user_ids = os.getenv("LLA_TARGET_USER_IDS") or os.getenv("LLA_TARGET_USER_ID", "")
        target_user_ids = set()

        for raw_user_id in raw_user_ids.split(","):
            raw_user_id = raw_user_id.strip()
            if not raw_user_id:
                continue

            try:
                target_user_ids.add(int(raw_user_id))
            except ValueError:
                print(f"Invalid target user ID: {raw_user_id}")

        return target_user_ids

    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        if not self.target_user_ids:
            return

        if after.id not in self.target_user_ids:
            return

        if before.status != discord.Status.offline:
            return

        if after.status == discord.Status.offline:
            return

        now = time.monotonic()
        last_greeted = self.last_greeted_at.get(after.id, 0)
        if now - last_greeted < self.greet_cooldown_seconds:
            return

        try:
            await after.send("你好，你上线啦！")
            self.last_greeted_at[after.id] = now
        except discord.Forbidden:
            print(f"Cannot send DM to user {after.id}.")


async def setup(bot):
    await bot.add_cog(PresenceGreeter(bot))
