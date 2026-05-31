import json
import os
import time
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands


COOLDOWN_SECONDS = 5 * 60
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "member_gate_config.json"


def normalize_answer(answer):
    return answer.strip().lower()


def load_config():
    if not CONFIG_PATH.exists():
        return {}

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
            return json.load(config_file)
    except (json.JSONDecodeError, OSError) as error:
        print(f"Cannot load member gate config: {error}")
        return {}


def get_int_config(config, key, env_name):
    value = config.get(key) or os.getenv(env_name, "0")

    try:
        return int(value)
    except (TypeError, ValueError):
        print(f"Invalid config value for {key}: {value}")
        return 0


def load_questions(config):
    config_questions = config.get("questions", [])
    if config_questions:
        questions = []

        for item in config_questions:
            question = str(item.get("question", "")).strip()
            answer = normalize_answer(str(item.get("answer", "")))
            options = [str(option).strip() for option in item.get("options", []) if str(option).strip()]
            if question and answer and options:
                questions.append(
                    {
                        "question": question,
                        "answer": answer,
                        "options": options[:25],
                    }
                )

        return questions

    raw_questions = os.getenv("LLA_GATE_QUESTIONS", "请回答：你是否已经阅读服务器公告和规则？=是")
    questions = []

    for item in raw_questions.split(";"):
        if "=" not in item:
            continue

        question, answer = item.split("=", 1)
        question = question.strip()
        answer = normalize_answer(answer)
        if question and answer:
            questions.append(
                {
                    "question": question,
                    "answer": answer,
                    "options": ["是", "否"],
                }
            )

    return questions


class GateQuestionSelect(discord.ui.Select):
    def __init__(self, gate, question_index, question):
        options = [
            discord.SelectOption(label=option, value=option)
            for option in question["options"]
        ]
        super().__init__(
            placeholder=f"请选择问题 {question_index + 1} 的答案",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.gate = gate
        self.question_index = question_index

    async def callback(self, interaction):
        self.gate.selected_answers[interaction.user.id][self.question_index] = self.values[0]
        await interaction.response.defer(ephemeral=True)


class GateAnswerView(discord.ui.View):
    def __init__(self, gate, member, gate_message=None):
        super().__init__(timeout=300)
        self.gate = gate
        self.member = member
        self.gate_message = gate_message
        gate.selected_answers[member.id] = {}

        for index, question in enumerate(gate.questions):
            self.add_item(GateQuestionSelect(gate, index, question))

    @discord.ui.button(label="提交答案", style=discord.ButtonStyle.success)
    async def submit_answers(self, interaction, button):
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("这个验证不是给你的。", ephemeral=True)
            return

        selected_answers = self.gate.selected_answers.get(interaction.user.id, {})
        if len(selected_answers) != len(self.gate.questions):
            await interaction.response.send_message("请先完成所有选择题。", ephemeral=True)
            return

        if not self.gate.answers_are_correct(selected_answers):
            self.gate.cooldowns[interaction.user.id] = time.monotonic()
            self.gate.selected_answers.pop(interaction.user.id, None)
            await interaction.response.send_message("答案不正确，请 5 分钟后再试。", ephemeral=True)
            await self.delete_gate_message()
            return

        role = interaction.guild.get_role(self.gate.verified_role_id)
        if role is None:
            await interaction.response.send_message("验证配置有误，请联系管理员。", ephemeral=True)
            await self.delete_gate_message()
            return

        try:
            await self.member.add_roles(role, reason="Passed server rules gate")
        except discord.Forbidden:
            await interaction.response.send_message(
                "机器人没有权限添加身份组，请联系管理员。",
                ephemeral=True,
            )
            await self.delete_gate_message()
            return

        self.gate.pending_members.pop(interaction.user.id, None)
        self.gate.cooldowns.pop(interaction.user.id, None)
        self.gate.selected_answers.pop(interaction.user.id, None)
        await interaction.response.send_message(
            "验证通过，欢迎加入！现在你可以在服务器发言了。",
            ephemeral=True,
        )
        await self.delete_gate_message()

    async def delete_gate_message(self):
        if self.gate_message is None:
            return

        try:
            await self.gate_message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass


class GateView(discord.ui.View):
    def __init__(self, gate, member):
        super().__init__(timeout=None)
        self.gate = gate
        self.member = member
        self.gate_message = None

    @discord.ui.button(label="开始验证", style=discord.ButtonStyle.primary)
    async def start_gate(self, interaction, button):
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("这个验证不是给你的。", ephemeral=True)
            return

        remaining_seconds = self.gate.get_cooldown_remaining(interaction.user.id)
        if remaining_seconds > 0:
            minutes = max(1, int(remaining_seconds // 60))
            await interaction.response.send_message(
                f"答案不正确，请 {minutes} 分钟后再试。",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="新人验证题目",
            description="请阅读下面的题目，在下拉菜单中选择答案，然后点击提交答案。",
            color=discord.Color.from_rgb(255, 120, 180),
        )
        for index, question in enumerate(self.gate.questions, start=1):
            embed.add_field(
                name=f"问题 {index}",
                value=question["question"],
                inline=False,
            )

        await interaction.response.send_message(
            embed=embed,
            view=GateAnswerView(self.gate, self.member, self.gate_message),
            ephemeral=True,
        )


class MemberGate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        config = load_config()
        self.rules_channel_id = get_int_config(config, "rules_channel_id", "LLA_RULES_CHANNEL_ID")
        self.verified_role_id = get_int_config(config, "verified_role_id", "LLA_VERIFIED_ROLE_ID")
        self.questions = load_questions(config)
        self.pending_members = {}
        self.cooldowns = {}
        self.selected_answers = {}

    def is_configured(self):
        return self.rules_channel_id != 0 and self.verified_role_id != 0 and bool(self.questions)

    def get_rules_channel(self, guild):
        channel = guild.get_channel(self.rules_channel_id)
        if isinstance(channel, discord.TextChannel):
            return channel

        return None

    def answers_are_correct(self, selected_answers):
        for index, question in enumerate(self.questions):
            if normalize_answer(selected_answers.get(index, "")) != question["answer"]:
                return False

        return True

    def get_cooldown_remaining(self, user_id):
        failed_at = self.cooldowns.get(user_id)
        if failed_at is None:
            return 0

        elapsed_seconds = time.monotonic() - failed_at
        return max(0, COOLDOWN_SECONDS - elapsed_seconds)

    async def send_gate_question(self, member):
        self.pending_members[member.id] = member.guild.id
        channel = self.get_rules_channel(member.guild)
        if channel is None:
            print(f"Rules channel {self.rules_channel_id} was not found.")
            return

        embed = discord.Embed(
            title="新人验证",
            description=(
                f"{member.mention}\n\n"
                "欢迎加入服务器！请先阅读本频道的公告和规则。\n\n"
                "阅读完毕后点击下方按钮回答验证问题。"
            ),
            color=discord.Color.from_rgb(255, 120, 180),
        )
        view = GateView(self, member)
        message = await channel.send(member.mention, embed=embed, view=view)
        view.gate_message = message

    @app_commands.command(name="qa", description="测试新人验证流程")
    async def qa(self, interaction):
        if interaction.guild is None:
            await interaction.response.send_message("这个命令只能在服务器里使用。", ephemeral=True)
            return

        if not self.is_configured():
            await interaction.response.send_message(
                "验证配置还没完成，请检查 member_gate_config.json。",
                ephemeral=True,
            )
            return

        member = interaction.guild.get_member(interaction.user.id)
        if member is None:
            await interaction.response.send_message("找不到你的成员信息。", ephemeral=True)
            return

        self.pending_members[member.id] = member.guild.id
        embed = discord.Embed(
            title="新人验证测试",
            description=(
                f"{member.mention}\n\n"
                "这是测试验证入口。点击下方按钮回答验证问题。"
            ),
            color=discord.Color.from_rgb(255, 120, 180),
        )
        view = GateView(self, member)
        message = await interaction.channel.send(member.mention, embed=embed, view=view)
        view.gate_message = message
        await interaction.response.send_message("测试验证入口已发送。", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot or not self.is_configured():
            return

        await self.send_gate_question(member)


async def setup(bot):
    await bot.add_cog(MemberGate(bot))
