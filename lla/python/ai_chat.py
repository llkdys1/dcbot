import json
import os
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands


LLA_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = LLA_DIR / "config" / "ai_config.json"
PERSONALITY_PATH = LLA_DIR / "ai_personality.txt"
MAX_DISCORD_MESSAGE_LENGTH = 1900


def load_json_config():
    if not CONFIG_PATH.exists():
        return {"current_provider": "", "providers": {}}

    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        return json.load(config_file)


def save_json_config(config):
    with CONFIG_PATH.open("w", encoding="utf-8") as config_file:
        json.dump(config, config_file, ensure_ascii=False, indent=2)
        config_file.write("\n")


def load_personality():
    if not PERSONALITY_PATH.exists():
        return "你是一个友好、简洁的 Discord 机器人。"

    return PERSONALITY_PATH.read_text(encoding="utf-8").strip()


def split_discord_message(text):
    text = text.strip() or "我暂时没有生成回复。"
    return [
        text[index:index + MAX_DISCORD_MESSAGE_LENGTH]
        for index in range(0, len(text), MAX_DISCORD_MESSAGE_LENGTH)
    ]


class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_current_provider(self):
        config = load_json_config()
        provider_name = config.get("current_provider", "")
        provider = config.get("providers", {}).get(provider_name)
        return config, provider_name, provider

    def get_api_key(self, provider):
        api_key = provider.get("api_key", "")
        if api_key:
            return api_key

        api_key_env = provider.get("api_key_env", "")
        if api_key_env:
            return os.getenv(api_key_env, "")

        return ""

    def build_client(self, provider_name, provider):
        try:
            from openai import AsyncOpenAI
        except ImportError as error:
            raise RuntimeError("缺少 openai 库，请先运行：pip install openai") from error

        if provider.get("api_type") != "openai_compatible":
            raise RuntimeError(f"不支持的 API 类型：{provider.get('api_type')}")

        api_key = self.get_api_key(provider)
        if not api_key:
            raise RuntimeError(f"{provider_name} 没有配置 API Key。")

        return AsyncOpenAI(
            api_key=api_key,
            base_url=provider.get("base_url") or None,
        )

    async def get_provider_models(self, provider_name, provider):
        client = self.build_client(provider_name, provider)
        models = await client.models.list()
        return sorted(model.id for model in models.data)

    async def ask_model(self, prompt):
        _, provider_name, provider = self.get_current_provider()
        if provider is None:
            raise RuntimeError("当前 AI 提供商不存在，请让管理员使用 /ai_provider_select 选择。")

        client = self.build_client(provider_name, provider)
        response = await client.responses.create(
            model=provider["model"],
            instructions=load_personality(),
            input=prompt,
        )
        return response.output_text

    async def provider_autocomplete(self, interaction, current):
        config = load_json_config()
        providers = config.get("providers", {})
        names = [
            name for name in providers
            if current.lower() in name.lower()
        ]
        return [
            app_commands.Choice(name=name, value=name)
            for name in names[:25]
        ]

    async def model_autocomplete(self, interaction, current):
        _, provider_name, provider = self.get_current_provider()
        if provider is None:
            return []

        try:
            models = await self.get_provider_models(provider_name, provider)
        except RuntimeError:
            return []
        except Exception:
            return []

        matched_models = [
            model for model in models
            if current.lower() in model.lower()
        ]
        return [
            app_commands.Choice(name=model, value=model)
            for model in matched_models[:25]
        ]

    @app_commands.command(name="ai", description="和当前 AI 角色聊天")
    @app_commands.describe(message="你想对 AI 说的话")
    async def ai(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer()

        try:
            reply = await self.ask_model(message)
        except RuntimeError as error:
            await interaction.followup.send(str(error), ephemeral=True)
            return

        for chunk in split_discord_message(reply):
            await interaction.followup.send(chunk)

    @app_commands.command(name="ai_provider", description="查看当前 AI 提供商")
    async def ai_provider(self, interaction: discord.Interaction):
        _, provider_name, provider = self.get_current_provider()
        if provider is None:
            await interaction.response.send_message("当前没有可用的 AI 提供商。", ephemeral=True)
            return

        await interaction.response.send_message(
            f"当前 AI：{provider_name}\n模型：{provider.get('model', '')}\nAPI：{provider.get('base_url', '')}",
            ephemeral=True,
        )

    @app_commands.command(name="ai_provider_list", description="列出可用 AI 提供商")
    @app_commands.checks.has_permissions(administrator=True)
    async def ai_provider_list(self, interaction: discord.Interaction):
        config = load_json_config()
        current_provider = config.get("current_provider", "")
        providers = config.get("providers", {})

        if not providers:
            await interaction.response.send_message("还没有配置任何 AI 提供商。", ephemeral=True)
            return

        lines = []
        for name, provider in providers.items():
            marker = "当前" if name == current_provider else "可选"
            lines.append(f"{marker}：{name} / {provider.get('model', '')}")

        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="ai_provider_select", description="选择当前 AI 提供商")
    @app_commands.describe(provider_name="ai_config.json 里的提供商名称")
    @app_commands.autocomplete(provider_name=provider_autocomplete)
    @app_commands.checks.has_permissions(administrator=True)
    async def ai_provider_select(self, interaction: discord.Interaction, provider_name: str):
        config = load_json_config()
        providers = config.get("providers", {})

        if provider_name not in providers:
            await interaction.response.send_message(f"找不到 AI 提供商：{provider_name}", ephemeral=True)
            return

        config["current_provider"] = provider_name
        save_json_config(config)
        await interaction.response.send_message(f"已切换当前 AI 为：{provider_name}", ephemeral=True)

    @app_commands.command(name="ai_model_list", description="获取当前 AI 提供商的可用模型列表")
    @app_commands.checks.has_permissions(administrator=True)
    async def ai_model_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        _, provider_name, provider = self.get_current_provider()
        if provider is None:
            await interaction.followup.send("当前 AI 提供商不存在。", ephemeral=True)
            return

        try:
            models = await self.get_provider_models(provider_name, provider)
        except RuntimeError as error:
            await interaction.followup.send(str(error), ephemeral=True)
            return
        except Exception as error:
            await interaction.followup.send(f"获取模型列表失败：{error}", ephemeral=True)
            return

        if not models:
            await interaction.followup.send("当前提供商没有返回可用模型。", ephemeral=True)
            return

        lines = [f"当前提供商：{provider_name}", f"当前模型：{provider.get('model', '')}", ""]
        lines.extend(f"- {model}" for model in models[:80])
        if len(models) > 80:
            lines.append(f"... 还有 {len(models) - 80} 个模型未显示")

        for chunk in split_discord_message("\n".join(lines)):
            await interaction.followup.send(chunk, ephemeral=True)

    @app_commands.command(name="ai_model_select", description="选择当前 AI 提供商使用的模型")
    @app_commands.describe(model_name="当前 AI 提供商的模型名称")
    @app_commands.autocomplete(model_name=model_autocomplete)
    @app_commands.checks.has_permissions(administrator=True)
    async def ai_model_select(self, interaction: discord.Interaction, model_name: str):
        config, provider_name, provider = self.get_current_provider()
        if provider is None:
            await interaction.response.send_message("当前 AI 提供商不存在。", ephemeral=True)
            return

        provider["model"] = model_name
        config["providers"][provider_name] = provider
        save_json_config(config)
        await interaction.response.send_message(
            f"已将 {provider_name} 的当前模型切换为：{model_name}",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(AIChat(bot))
