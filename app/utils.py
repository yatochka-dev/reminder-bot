import asyncio
import datetime
import re

import disnake
from dateutil.parser import parse
from fastapi import Request

from . import Embed, EmbedField
from .bot import Bot, Settings
from .loggs import logger


def convert_text_to_bold(string: str, /) -> str:
    return "\033[1m" + string + "\033[0m"


def get_member_by_id(member_id: int, /):
    member = disnake.Object(member_id)

    if not isinstance(member, disnake.Member):
        logger.warn(f"Member with id {member_id} not found, returned " f"{type(member)!r} instead")

    return member


def get_bot_from_request(request: Request) -> Bot:
    bot: Bot = request.app.state.bot

    if not bot.is_ready():
        asyncio.run(bot.wait_until_ready())

    return bot


def parse_datetime(input_string: str) -> datetime.datetime:
    logger.debug(f"Parsing datetime from {input_string}")
    # Parse the input string using a regular expression to extract the relevant information
    m = re.match(r"(?:(\d+y)?(\d+M)?(\d+w)?(\d+d)?(\d+h)?(\d+m)?(\d+s)?)", input_string)

    if m and any(item is not None for item in m.groups()):
        logger.debug(f"Matched {m.groups()}")
        years = int(m.group(1).rstrip("y")) if m.group(1) else 0
        months = int(m.group(2).rstrip("M")) if m.group(2) else 0
        weeks = int(m.group(3).rstrip("w")) if m.group(3) else 0
        days = int(m.group(4).rstrip("d")) if m.group(4) else 0
        hours = int(m.group(5).rstrip("h")) if m.group(5) else 0
        minutes = int(m.group(6).rstrip("m")) if m.group(6) else 0
        seconds = int(m.group(7).rstrip("s")) if m.group(7) else 0

        delta = datetime.timedelta(
            weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds
        )
        target_datetime = datetime.datetime.now(tz=Settings.TIMEZONE) + delta
        if years or months:
            from dateutil.relativedelta import relativedelta

            target_datetime = target_datetime + relativedelta(years=years, months=months)

    elif input_string == "tomorrow":
        logger.debug("Matched 'tomorrow'")
        target_datetime = datetime.datetime.now(tz=Settings.TIMEZONE) + datetime.timedelta(days=1)
    elif input_string == "next week":
        logger.debug("Matched 'next week'")
        target_datetime = datetime.datetime.now(tz=Settings.TIMEZONE) + datetime.timedelta(weeks=1)
    else:
        logger.debug("Matched 'parse'")
        # If the input string is not in the expected format, try parsing it using the
        # dateutil.parser module
        target_datetime = parse(input_string)

    logger.debug(f"Returning {target_datetime}")

    return target_datetime


def get_mentions_as_list(text: str) -> list[str]:
    return re.findall(r"<@!\d+>|<@&\d+>|<#\d+>|<@\d+>|@everyone|@here", text)


def get_mentions_as_string(text: str, /) -> str:
    mentions = get_mentions_as_list(text)
    return " ".join(mentions)


def create_embeds_from_fields(
    embed: Embed, fields: list[EmbedField], max_size: int = 6, emb_style: str = "default"
) -> list[Embed] | None:
    assert max_size <= 25, "Max size must be less or equal to 25"

    embeds = []

    chunks = disnake.utils.as_chunks(fields, max_size)
    emb: disnake.Embed = getattr(embed, emb_style)
    emb.clear_fields()
    for chunk in chunks:
        emb_c = emb.copy()
        for field in chunk:
            emb_c.add_field(name=field.name, value=field.value, inline=field.inline)

        embeds.append(emb_c)

    return embeds if embeds else None
