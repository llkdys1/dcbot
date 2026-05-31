import asyncio
import json
import os
import smtplib
import time
from email.message import EmailMessage
from pathlib import Path

from discord.ext import commands


DEFAULT_SMTP_PORT = 587
DEFAULT_COOLDOWN_SECONDS = 5 * 60
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "offline_email_alert_config.json"


def load_json_config():
    if not CONFIG_PATH.exists():
        return {}

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
            return json.load(config_file)
    except (json.JSONDecodeError, OSError) as error:
        print(f"Cannot load offline email alert config: {error}")
        return {}


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


def get_config_int(config, key, env_name, default):
    value = config.get(key)
    if value in (None, ""):
        return get_env_int(env_name, default)

    try:
        return int(value)
    except (TypeError, ValueError):
        print(f"Invalid config value for {key}: {value}")
        return default


def load_email_config():
    json_config = load_json_config()
    smtp_username = str(
        json_config.get("smtp_username") or os.getenv("LLA_ALERT_SMTP_USERNAME", "")
    ).strip()
    recipients = json_config.get("email_to")
    if isinstance(recipients, str):
        recipients = [recipients]
    elif not isinstance(recipients, list):
        recipients = [
            recipient.strip()
            for recipient in os.getenv("LLA_ALERT_EMAIL_TO", "").split(",")
            if recipient.strip()
        ]

    return {
        "smtp_host": str(
            json_config.get("smtp_host") or os.getenv("LLA_ALERT_SMTP_HOST", "")
        ).strip(),
        "smtp_port": get_config_int(
            json_config, "smtp_port", "LLA_ALERT_SMTP_PORT", DEFAULT_SMTP_PORT
        ),
        "smtp_username": smtp_username,
        "smtp_password": str(
            json_config.get("smtp_password") or os.getenv("LLA_ALERT_SMTP_PASSWORD", "")
        ),
        "sender": str(
            json_config.get("email_from") or os.getenv("LLA_ALERT_EMAIL_FROM", smtp_username)
        ).strip(),
        "recipients": [str(recipient).strip() for recipient in recipients if str(recipient).strip()],
        "use_ssl": bool(
            json_config.get("smtp_ssl")
            if "smtp_ssl" in json_config
            else get_env_bool("LLA_ALERT_SMTP_SSL", False)
        ),
        "use_tls": bool(
            json_config.get("smtp_tls")
            if "smtp_tls" in json_config
            else get_env_bool("LLA_ALERT_SMTP_TLS", True)
        ),
        "cooldown_seconds": get_config_int(
            json_config,
            "cooldown_seconds",
            "LLA_ALERT_COOLDOWN_SECONDS",
            DEFAULT_COOLDOWN_SECONDS,
        ),
    }


def config_is_valid(config):
    return bool(
        config["smtp_host"]
        and config["sender"]
        and config["recipients"]
        and config["smtp_username"]
        and config["smtp_password"]
    )


def send_email(config, subject, body):
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config["sender"]
    message["To"] = ", ".join(config["recipients"])
    message.set_content(body)

    smtp_class = smtplib.SMTP_SSL if config["use_ssl"] else smtplib.SMTP

    with smtp_class(config["smtp_host"], config["smtp_port"], timeout=20) as smtp:
        if config["use_tls"] and not config["use_ssl"]:
            smtp.starttls()

        smtp.login(config["smtp_username"], config["smtp_password"])
        smtp.send_message(message)


class OfflineEmailAlert(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_email_config()
        self.last_alerted_at = 0

    @commands.Cog.listener()
    async def on_disconnect(self):
        if not config_is_valid(self.config):
            print("Offline email alert is not configured.")
            return

        now = time.monotonic()
        if now - self.last_alerted_at < self.config["cooldown_seconds"]:
            return

        self.last_alerted_at = now
        bot_name = str(self.bot.user) if self.bot.user else "Discord bot"
        subject = f"{bot_name} disconnected"
        body = (
            f"{bot_name} has disconnected from Discord.\n\n"
            "The discord.py on_disconnect event was triggered. "
            "The bot may reconnect automatically if the process is still running."
        )

        try:
            await asyncio.to_thread(send_email, self.config, subject, body)
            print("Offline email alert sent.")
        except Exception as error:
            print(f"Cannot send offline email alert: {error}")


async def setup(bot):
    await bot.add_cog(OfflineEmailAlert(bot))
