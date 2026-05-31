import asyncio
import os
import sys
from pathlib import Path

import discord
from discord.ext import commands


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANAGER_API_DIR = PROJECT_ROOT / "lla" / "manager_api"

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(PROJECT_ROOT / ".env")

token = os.getenv("LLA_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True


class LLABot(commands.Bot):
    async def setup_hook(self):
        await self.load_extension("presence_greeter")
        await self.load_extension("math_commands")
        await self.load_extension("member_gate")
        await self.load_extension("sensitive_words")
        # await self.load_extension("ai_chat")
        # await self.load_extension("offline_email_alert")
        await self.load_extension("work_recommend")
        await self.load_extension("recommend_edit")


bot = LLABot(command_prefix="!", intents=intents)


def get_env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_env_int(name, default):
    value = os.getenv(name)
    if not value:
        return default

    try:
        return int(value)
    except ValueError:
        print(f"Invalid integer for {name}: {value}")
        return default


async def start_manager_api():
    try:
        import uvicorn
    except ImportError:
        print("管理 API 未启动：缺少 uvicorn，请安装 lla/manager_api/requirements.txt。")
        return

    if str(MANAGER_API_DIR) not in sys.path:
        sys.path.insert(0, str(MANAGER_API_DIR))

    from app.main import app as manager_app

    host = os.getenv("DCBOT_MANAGER_API_HOST", "127.0.0.1")
    port = get_env_int("DCBOT_MANAGER_API_PORT", 8765)
    config = uvicorn.Config(
        manager_app,
        host=host,
        port=port,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    if token is None:
        raise RuntimeError("请先设置环境变量 LLA_BOT_TOKEN")

    tasks = [asyncio.create_task(bot.start(token), name="discord-bot")]

    if get_env_bool("DCBOT_MANAGER_API_ENABLED", True):
        tasks.append(asyncio.create_task(start_manager_api(), name="manager-api"))

    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        for task in done:
            error = task.exception()
            if error is not None:
                raise error
    finally:
        await bot.close()
        for task in tasks:
            if not task.done():
                task.cancel()


@bot.command()
@commands.has_permissions(administrator=True)
async def syncCommand(ctx):
    global_commands = list(bot.tree.get_commands(guild=None))

    if global_commands:
        bot.tree.clear_commands(guild=ctx.guild)
        for command in global_commands:
            bot.tree.add_command(command, guild=ctx.guild)

    bot.tree.clear_commands(guild=None)
    await bot.tree.sync()

    synced_commands = await bot.tree.sync(guild=ctx.guild)
    await ctx.send(f"同步完成：{len(synced_commands)} 个命令")


@bot.hybrid_command()
async def ping(ctx):
    "pingceshi"
    await ctx.send("pong")


asyncio.run(main())
