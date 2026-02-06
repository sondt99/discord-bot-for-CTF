import os

from dotenv import load_dotenv


load_dotenv()


def _get_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value


DISCORD_TOKEN = _get_env("DISCORD_TOKEN")
DISCORD_GUILD_ID = _get_env("DISCORD_GUILD_ID")
DATABASE_PATH = _get_env("DATABASE_PATH", "ctf_bot.db")
SCOREBOARD_POLL_SECONDS = int(_get_env("SCOREBOARD_POLL_SECONDS", "90"))
SCOREBOARD_TOP_N = int(_get_env("SCOREBOARD_TOP_N", "10"))

