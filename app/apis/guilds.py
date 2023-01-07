import disnake
from fastapi import APIRouter, Depends

from app import parse_datetime
from app.services.GuildService import GuildService
from app.services.ReminderService import ReminderService

router = APIRouter()


@router.get("/guilds/")
async def getGuilds(service: GuildService = Depends(GuildService)):
    return await service.get_all()


@router.get("/guilds/{guild_id}")
async def is_guild_exists(
        guild_id: int, service: GuildService = Depends(GuildService)
):
    return await service.exists(guild_id)


@router.get("/guilds/{guild_id}/")
async def get_guild_by_id(
        guild_id: int, service: GuildService = Depends(GuildService)
):
    return await service.get(guild_id)


@router.get("/test/{input}")
async def test(input: str):
    return parse_datetime(input)

@router.get("/guilds/{guild_id}/reminders/{code}")
async def get_guild_reminders(
        guild_id: int, code: int, service: ReminderService = Depends(ReminderService)
):
    return await service.get_by_code(disnake.Object(guild_id), code)
