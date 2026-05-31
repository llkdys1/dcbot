import json
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands


CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "artist_recommend_config.json"
NO_TAG_VALUE = "none"
SECTION_CHOICES = [
    app_commands.Choice(name="画师论坛", value="artist"),
    app_commands.Choice(name="gal论坛", value="gal"),
    app_commands.Choice(name="小说推荐", value="novel"),
    app_commands.Choice(name="本子推荐", value="ben"),
    app_commands.Choice(name="动漫推荐", value="anime"),
]


def load_config():
    if not CONFIG_PATH.exists():
        return {"forum_channels": {}}

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
            return json.load(config_file)
    except (json.JSONDecodeError, OSError) as error:
        print(f"Cannot load artist recommend config: {error}")
        return {"forum_channels": {}}


def get_forum_channel_id(config, section):
    value = config.get("forum_channels", {}).get(section, 0)

    try:
        return int(value)
    except (TypeError, ValueError):
        print(f"Invalid forum channel ID for {section}: {value}")
        return 0


def get_section_label(section):
    for choice in SECTION_CHOICES:
        if choice.value == section:
            return choice.name

    return section


def get_forum_tag(channel, tag_id):
    if not tag_id or tag_id == NO_TAG_VALUE:
        return None

    for tag in channel.available_tags:
        if str(tag.id) == str(tag_id):
            return tag

    return None


def format_tag_choice_name(tag):
    if tag.emoji:
        return f"{tag.emoji} {tag.name}"[:100]

    return tag.name[:100]


async def get_forum_channel(bot, channel_id):
    channel = bot.get_channel(channel_id)
    if channel is None and channel_id:
        try:
            channel = await bot.fetch_channel(channel_id)
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            return None

    if isinstance(channel, discord.ForumChannel):
        return channel

    return None


def build_recommendation_content(recommender, section_label, social_account, style_type, works_link, reason):
    recommender_text = recommender.mention if hasattr(recommender, "mention") else str(recommender)
    content_lines = [
        f"**推荐人**：{recommender_text}",
        f"**分区**：{section_label}",
        f"**社交账号**：{social_account}",
        f"**风格类型**：{style_type}",
    ]
    if works_link:
        content_lines.append(f"**作品链接**：{works_link}")

    content_lines.extend(
        [
            "",
            "**推荐理由**",
            reason,
        ]
    )
    return "\n".join(content_lines)


def parse_recommendation_content(content):
    fields = {
        "recommender": "",
        "section_label": "",
        "social_account": "",
        "style_type": "",
        "works_link": "",
        "reason": "",
    }
    lines = content.splitlines()
    reason_lines = []
    reading_reason = False

    for line in lines:
        if line.strip() == "**推荐理由**":
            reading_reason = True
            continue

        if reading_reason:
            reason_lines.append(line)
            continue

        if line.startswith("**推荐人**："):
            fields["recommender"] = line.removeprefix("**推荐人**：").strip()
        elif line.startswith("**分区**："):
            fields["section_label"] = line.removeprefix("**分区**：").strip()
        elif line.startswith("**社交账号**："):
            fields["social_account"] = line.removeprefix("**社交账号**：").strip()
        elif line.startswith("**风格类型**："):
            fields["style_type"] = line.removeprefix("**风格类型**：").strip()
        elif line.startswith("**作品链接**："):
            fields["works_link"] = line.removeprefix("**作品链接**：").strip()

    fields["reason"] = "\n".join(reason_lines).strip()
    return fields


def user_can_edit_recommendation(interaction, content):
    user_id = interaction.user.id
    if f"<@{user_id}>" in content or f"<@!{user_id}>" in content:
        return True

    permissions = getattr(interaction.user, "guild_permissions", None)
    if permissions is None:
        return False

    return permissions.administrator or permissions.manage_threads or permissions.manage_messages


async def get_thread_starter_message(thread):
    try:
        return await thread.fetch_message(thread.id)
    except discord.NotFound:
        return None


class ArtistRecommendationModal(discord.ui.Modal):
    artist_name = discord.ui.TextInput(
        label="画师名字",
        placeholder="例如：某某老师 / 昵称 / 圈名",
        max_length=80,
    )
    social_account = discord.ui.TextInput(
        label="社交账号",
        placeholder="例如：Twitter/X、Pixiv、B站、微博、小红书等",
        max_length=200,
    )
    style_type = discord.ui.TextInput(
        label="风格类型",
        placeholder="例如：厚涂、赛璐璐、Q版、头像、立绘、Live2D 等",
        max_length=120,
    )
    works_link = discord.ui.TextInput(
        label="作品链接",
        placeholder="可以填写主页、作品集或接稿页面链接",
        required=False,
        max_length=300,
    )
    recommendation_reason = discord.ui.TextInput(
        label="推荐理由",
        placeholder="简单说说为什么推荐这位画师",
        style=discord.TextStyle.paragraph,
        max_length=1000,
    )

    def __init__(self, bot, section, image, tag_id=None):
        super().__init__(title="推荐画师")
        self.bot = bot
        self.section = section
        self.image = image
        self.tag_id = tag_id

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        forum_channel_id = get_forum_channel_id(config, self.section)
        channel = await get_forum_channel(self.bot, forum_channel_id)

        if channel is None:
            await interaction.response.send_message(
                "没有找到对应的论坛区块，请检查 artist_recommend_config.json。",
                ephemeral=True,
            )
            return

        tag = get_forum_tag(channel, self.tag_id)
        if self.tag_id and tag is None:
            await interaction.response.send_message(
                "找不到你选择的论坛标签，请重新选择。",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        content = build_recommendation_content(
            interaction.user,
            get_section_label(self.section),
            self.social_account.value,
            self.style_type.value,
            self.works_link.value,
            self.recommendation_reason.value,
        )

        try:
            image_file = await self.image.to_file()
            await channel.create_thread(
                name=self.artist_name.value[:100],
                content=content,
                file=image_file,
                applied_tags=[tag] if tag else [],
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "机器人没有权限在对应论坛区块发帖，请检查频道权限。",
                ephemeral=True,
            )
            return
        except discord.HTTPException as error:
            await interaction.followup.send(
                f"发布推荐帖失败：{error}",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"推荐帖已发布到 {channel.mention}。",
            ephemeral=True,
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "提交推荐时出错了，请稍后再试。",
                ephemeral=True,
            )

        print(f"Cannot submit artist recommendation: {error}")


class ArtistRecommend(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def tag_autocomplete(self, interaction, current):
        section = (
            getattr(interaction.namespace, "section", "")
            or getattr(interaction.namespace, "分区", "")
        )
        if not section:
            return [
                app_commands.Choice(name="请先选择分区", value=NO_TAG_VALUE)
            ]

        config = load_config()
        forum_channel_id = get_forum_channel_id(config, section)
        channel = await get_forum_channel(self.bot, forum_channel_id)
        if channel is None:
            return [
                app_commands.Choice(name="找不到该分区对应的论坛频道", value=NO_TAG_VALUE)
            ]

        if not channel.available_tags:
            return [
                app_commands.Choice(name="该论坛频道还没有标签", value=NO_TAG_VALUE)
            ]

        current = current.lower()
        choices = []
        if not current or current in "不添加标签".lower() or current in NO_TAG_VALUE:
            choices.append(app_commands.Choice(name="不添加标签", value=NO_TAG_VALUE))

        matched_tags = [
            tag for tag in channel.available_tags
            if current in tag.name.lower()
        ]
        choices.extend(
            app_commands.Choice(name=format_tag_choice_name(tag), value=str(tag.id))
            for tag in matched_tags
        )
        return choices[:25]

    @app_commands.command(name="作品推荐", description="填写模板并发布画师推荐到论坛区块")
    @app_commands.rename(section="分区", image="图片", tag="标签")
    @app_commands.describe(
        section="选择要发布到哪个论坛区块",
        tag="选择该论坛区块已有的标签，选择“不添加标签”则不添加标签",
        image="上传一张展示图或作品图",
    )
    @app_commands.choices(section=SECTION_CHOICES)
    @app_commands.autocomplete(tag=tag_autocomplete)
    async def artist_recommend(
        self,
        interaction: discord.Interaction,
        section: str,
        tag: str,
        image: discord.Attachment,
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "这个命令只能在服务器频道里使用。",
                ephemeral=True,
            )
            return

        if not image.content_type or not image.content_type.startswith("image/"):
            await interaction.response.send_message(
                "请上传图片文件。",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(
            ArtistRecommendationModal(self.bot, section, image, tag)
        )

async def setup(bot):
    await bot.add_cog(ArtistRecommend(bot))
