import discord
from discord import app_commands
from discord.ext import commands

from work_recommend import (
    build_recommendation_content,
    get_thread_starter_message,
    parse_recommendation_content,
    user_can_edit_recommendation,
)


class RecommendEdit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="编辑已发布的推荐帖", description="在推荐帖内更新或修改已发布的推荐内容")
    @app_commands.rename(
        artist_name="画师名",
        social_account="社交账号",
        style_type="风格类型",
        works_link="作品链接",
        recommendation_reason="推荐理由",
    )
    @app_commands.describe(
        artist_name="新的帖子标题/画师名，不填则保持不变",
        social_account="新的社交账号，不填则保持不变",
        style_type="新的风格类型，不填则保持不变",
        works_link="新的作品链接，不填则保持不变；填 none 可清空",
        recommendation_reason="新的推荐理由，不填则保持不变",
    )
    async def artist_recommend_edit(
        self,
        interaction: discord.Interaction,
        artist_name: str | None = None,
        social_account: str | None = None,
        style_type: str | None = None,
        works_link: str | None = None,
        recommendation_reason: str | None = None,
    ):
        thread = interaction.channel
        if not isinstance(thread, discord.Thread) or not isinstance(thread.parent, discord.ForumChannel):
            await interaction.response.send_message(
                "这个命令只能在画师推荐论坛帖子里使用。",
                ephemeral=True,
            )
            return

        starter_message = await get_thread_starter_message(thread)
        if starter_message is None:
            await interaction.response.send_message(
                "找不到这个帖子的首楼内容，无法修改。",
                ephemeral=True,
            )
            return

        if starter_message.author.id != self.bot.user.id:
            await interaction.response.send_message(
                "这个帖子不是机器人发布的，不能用这个命令修改。",
                ephemeral=True,
            )
            return

        if not user_can_edit_recommendation(interaction, starter_message.content):
            await interaction.response.send_message(
                "只有原推荐人或管理员可以修改这个推荐帖。",
                ephemeral=True,
            )
            return

        fields = parse_recommendation_content(starter_message.content)
        if not fields["section_label"] and not fields["social_account"] and not fields["style_type"]:
            await interaction.response.send_message(
                "这个帖子不是新版推荐模板，无法自动识别字段。",
                ephemeral=True,
            )
            return

        if social_account is not None:
            fields["social_account"] = social_account
        if style_type is not None:
            fields["style_type"] = style_type
        if works_link is not None:
            fields["works_link"] = "" if works_link.strip().lower() == "none" else works_link
        if recommendation_reason is not None:
            fields["reason"] = recommendation_reason

        new_content = build_recommendation_content(
            fields["recommender"],
            fields["section_label"],
            fields["social_account"],
            fields["style_type"],
            fields["works_link"],
            fields["reason"],
        )

        try:
            if artist_name is not None:
                await thread.edit(name=artist_name[:100])
            await starter_message.edit(
                content=new_content,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "机器人没有权限修改这个帖子，请检查论坛权限。",
                ephemeral=True,
            )
            return
        except discord.HTTPException as error:
            await interaction.response.send_message(
                f"修改推荐帖失败：{error}",
                ephemeral=True,
            )
            return

        await interaction.response.send_message("推荐帖已修改。", ephemeral=True)


async def setup(bot):
    await bot.add_cog(RecommendEdit(bot))
