import json
import sqlite3
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands


LLA_DIR = Path(__file__).resolve().parent.parent
DB_PATH = LLA_DIR / "data" / "bot_data.db"
LEGACY_CONFIG_PATH = LLA_DIR / "config" / "sensitive_words_config.json"


def normalize_text(text):
    return text.casefold()


class SensitiveWordsStore:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()

    def connect(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sensitive_words (
                    guild_id INTEGER NOT NULL,
                    word TEXT NOT NULL,
                    normalized_word TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (guild_id, normalized_word)
                )
                """
            )
        self.migrate_legacy_json()

    def migrate_legacy_json(self):
        if not LEGACY_CONFIG_PATH.exists():
            return

        try:
            with LEGACY_CONFIG_PATH.open("r", encoding="utf-8") as config_file:
                data = json.load(config_file)
        except (json.JSONDecodeError, OSError) as error:
            print(f"Cannot migrate sensitive words config: {error}")
            return

        guild_id = data.get("guild_id")
        words = data.get("words", [])
        if not guild_id or not words:
            return

        for word in words:
            word = str(word).strip()
            if word:
                self.add_word(int(guild_id), word)

    def add_word(self, guild_id, word):
        normalized_word = normalize_text(word)

        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO sensitive_words (guild_id, word, normalized_word)
                VALUES (?, ?, ?)
                """,
                (guild_id, word, normalized_word),
            )
            return cursor.rowcount > 0

    def remove_word(self, guild_id, word):
        normalized_word = normalize_text(word)

        with self.connect() as conn:
            cursor = conn.execute(
                """
                DELETE FROM sensitive_words
                WHERE guild_id = ? AND normalized_word = ?
                """,
                (guild_id, normalized_word),
            )
            return cursor.rowcount > 0

    def list_words(self, guild_id):
        with self.connect() as conn:
            cursor = conn.execute(
                """
                SELECT word
                FROM sensitive_words
                WHERE guild_id = ?
                ORDER BY word
                """,
                (guild_id,),
            )
            return [row[0] for row in cursor.fetchall()]

    def find_blocked_word(self, guild_id, content):
        normalized_content = normalize_text(content)

        for word in self.list_words(guild_id):
            if normalize_text(word) in normalized_content:
                return word

        return None


class SensitiveWords(commands.Cog):
    sensitive_words = app_commands.Group(name="敏感词", description="管理服务器敏感词")

    def __init__(self, bot):
        self.bot = bot
        self.store = SensitiveWordsStore(DB_PATH)

    async def owner_only(self, interaction):
        if interaction.guild is None:
            await interaction.response.send_message("这个命令只能在服务器里使用。", ephemeral=True)
            return False

        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("只有服务器所有者可以管理敏感词。", ephemeral=True)
            return False

        return True

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None or message.author.bot:
            return

        blocked_word = self.store.find_blocked_word(message.guild.id, message.content)
        if blocked_word is None:
            return

        try:
            await message.delete()
        except discord.Forbidden:
            print("机器人没有权限删除包含敏感词的消息。")
            return
        except discord.NotFound:
            return

        await message.channel.send(
            f"{message.author.mention}，你的消息包含敏感词，已被删除。",
            delete_after=8,
            allowed_mentions=discord.AllowedMentions(users=True),
        )
        print(f"Deleted message with sensitive word: {blocked_word}")

    @sensitive_words.command(name="添加", description="添加一个敏感词，仅服务器所有者可用")
    @app_commands.describe(word="要添加的敏感词")
    async def add_word(self, interaction: discord.Interaction, word: str):
        if not await self.owner_only(interaction):
            return

        word = word.strip()
        if not word:
            await interaction.response.send_message("敏感词不能为空。", ephemeral=True)
            return

        if self.store.add_word(interaction.guild.id, word):
            await interaction.response.send_message(f"已添加敏感词：{word}", ephemeral=True)
            return

        await interaction.response.send_message("这个敏感词已经存在。", ephemeral=True)

    @sensitive_words.command(name="删除", description="删除一个敏感词，仅服务器所有者可用")
    @app_commands.describe(word="要删除的敏感词")
    async def remove_word(self, interaction: discord.Interaction, word: str):
        if not await self.owner_only(interaction):
            return

        word = word.strip()
        if self.store.remove_word(interaction.guild.id, word):
            await interaction.response.send_message(f"已删除敏感词：{word}", ephemeral=True)
            return

        await interaction.response.send_message("没有找到这个敏感词。", ephemeral=True)

    @sensitive_words.command(name="列表", description="查看当前敏感词，仅服务器所有者可用")
    async def list_words(self, interaction: discord.Interaction):
        if not await self.owner_only(interaction):
            return

        words = self.store.list_words(interaction.guild.id)
        if not words:
            await interaction.response.send_message("当前没有敏感词。", ephemeral=True)
            return

        content = "、".join(words)
        if len(content) > 1800:
            content = content[:1800] + "..."

        await interaction.response.send_message(f"当前敏感词：{content}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(SensitiveWords(bot))
