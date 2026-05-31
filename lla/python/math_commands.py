import ast
import operator

import discord
from discord import app_commands
from discord.ext import commands


OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}
EMBED_VALUE_WIDTH = 40


def normalize_expression(expression):
    return (
        expression
        .replace("×", "*")
        .replace("÷", "/")
        .replace("x", "*")
        .replace("X", "*")
    )


def calculate(node):
    if isinstance(node, ast.Expression):
        return calculate(node.body)

    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value

    if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
        left = calculate(node.left)
        right = calculate(node.right)
        return OPERATORS[type(node.op)](left, right)

    if isinstance(node, ast.UnaryOp) and type(node.op) in OPERATORS:
        return OPERATORS[type(node.op)](calculate(node.operand))

    raise ValueError("Unsupported expression")


def format_number(value):
    if isinstance(value, float) and value.is_integer():
        return str(int(value))

    return str(value)


def format_embed_value(value):
    value = str(value)
    if len(value) > EMBED_VALUE_WIDTH:
        value = value[:EMBED_VALUE_WIDTH - 3] + "..."

    return f"```{value.ljust(EMBED_VALUE_WIDTH)}```"


class MathCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="math", description="计算加减乘除")
    @app_commands.describe(expression="算式，例如 1+1 或 (2+3)*4")
    async def math(self, interaction: discord.Interaction, expression: str):
        normalized_expression = normalize_expression(expression)

        try:
            parsed_expression = ast.parse(normalized_expression, mode="eval")
            result = calculate(parsed_expression)
        except ZeroDivisionError:
            await interaction.response.send_message(
                "除数不能为 0",
                ephemeral=True,
            )
            return
        except (SyntaxError, ValueError):
            await interaction.response.send_message(
                "只支持数字、括号和 + - * / × ÷",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="计算器",
            color=discord.Color.from_rgb(255, 80, 80),
        )
        embed.add_field(
            name="计算",
            value=format_embed_value(expression),
            inline=False,
        )
        embed.add_field(
            name="结果",
            value=format_embed_value(format_number(result)),
            inline=False,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(MathCommands(bot))
