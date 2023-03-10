import datetime
from pathlib import Path

import disnake.mixins
import pydantic.main
from disnake.ext.commands import InteractionBot
from pydantic import BaseSettings

from .db import prisma
from .loggs import logger, prisma_logger, disnake_logger

__all__ = ["Bot", "Settings"]

from .types import SupportsIntCast


class AppSettings(BaseSettings):
    TESTING: bool = True
    TIMEZONE = datetime.timezone(
        offset=datetime.timedelta(hours=2), name="UTC"
    )

    github_link = "https://github.com/yatochka-dev/discord-bot-boilerplate"

    # EMBED SETTINGS
    RGB_DEFAULT_COLOR: disnake.Color = disnake.Color.from_rgb(255, 255, 255)
    RGB_ERROR_COLOR: disnake.Color = disnake.Color.from_rgb(255, 0, 0)
    RGB_SUCCESS_COLOR: disnake.Color = disnake.Color.from_rgb(0, 255, 0)
    RGB_WARNING_COLOR: disnake.Color = disnake.Color.from_rgb(255, 255, 0)
    RGB_INFO_COLOR: disnake.Color = disnake.Color.from_rgb(0, 255, 255)

    # if none - won't be added
    AUTHOR_DISPLAY_NAME: str | None = None
    ICON_URL: str | None = None


Settings = AppSettings()


@property
def snowflake(self):
    return str(self.id)


@property
def id_(self) -> int | None:
    if hasattr(self, "snowflake"):
        snowflake_ = self.snowflake
        if isinstance(snowflake_, SupportsIntCast):
            return int(snowflake_)

    if hasattr(self, "id"):
        return self.id

    return None


class Bot(InteractionBot):
    def __init__(self, *args, **kwargs):
        intents = disnake.Intents.default()
        intents.members = True
        self.APP_SETTINGS = AppSettings()
        self.BASE_DIR = Path(__file__).resolve().parent.parent
        self.logger = logger
        self.prisma = prisma
        self.disnake_logger = disnake_logger
        self.prisma_logger = prisma_logger

        disnake.mixins.Hashable.snowflake = snowflake  # noqa
        pydantic.main.BaseModel.id_ = id_  # noqa

        super().__init__(*args, **kwargs, intents=intents)

    @property
    def now(self):
        return datetime.datetime.now(tz=self.APP_SETTINGS.TIMEZONE)
