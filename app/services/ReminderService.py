import datetime
from typing import overload

import disnake
from prisma import models
from prisma.models import Reminder

from .index import CRUDXService
from .. import EmbedField


class ReminderService(CRUDXService):
    async def add(
            self,
            guild: disnake.Guild,
            channel: disnake.TextChannel,
            member: disnake.Member,
            expires_at: datetime.datetime,
            content: str,
    ) -> Reminder:
        current_count = (await self.bot.prisma.guild.find_first(
            where={
                "snowflake": guild.snowflake,
            },
        )).reminders_count

        # reminder = await self.bot.prisma.reminder.create(
        #     data={
        #         "content": content,
        #         "channel_id": channel.id,
        #         "author_id": member.id,
        #         "expires_at": expires_at,
        #         "reminder_number": current_count + 1,
        #         "guild": {
        #             "connect": {
        #                 "snowflake": guild.snowflake,
        #             },
        #         },
        #     }
        # )

        upd = await self.bot.prisma.guild.update(
            where={
                "snowflake": guild.snowflake,
            },
            data={
                "reminders_count": current_count + 1,
                "reminders": {
                    "create": {
                        "content": content,
                        "channel_id": channel.id,
                        "author_id": member.id,
                        "expires_at": expires_at,
                        "reminder_number": current_count + 1,
                    },
                },
            },
            include={
                "reminders": True,
            },
        )
        # print upd
        self.bot.logger.debug(str(upd))

        return upd.reminders[-1]

    async def get(self, reminder_id: int, /, include_guild=True) -> Reminder | None:
        return await self.bot.prisma.reminder.find_unique(
            where={
                "id": reminder_id,
            },
            include={
                "guild": include_guild,
            },
        )

    async def get_by_code(self, guild: disnake.Guild, code: int) -> Reminder | None:
        return await self.bot.prisma.reminder.find_first(
            where={
                "reminder_number": int(code),
                "guild": {
                    "snowflake": guild.snowflake,
                }
            }
        )

    async def remove(self, reminder_id: int) -> Reminder | None:
        return await self.bot.prisma.reminder.delete(
            where={
                "id": reminder_id,
            }
        )

    async def remove_expired_reminders(self) -> int:
        """
        Removes all expired reminders from the database.
        returns the number of deleted reminders.
        """

        return await self.bot.prisma.reminder.delete_many(
            where={
                "expires_at": {
                    "lte": self.bot.now,
                }
            }
        )

    @overload
    async def get_all(self, guild: disnake.Guild) -> models.Guild:
        ...

    @overload
    async def get_all(self, guild: disnake.Guild, take: int) -> list[models.Reminder]:
        ...

    @overload
    async def get_all(self, member: disnake.Member, take: int) -> list[models.Reminder]:
        ...

    @overload
    async def get_all(self) -> list[models.Reminder]:
        ...

    @overload
    async def get_all(self, member: disnake.Member) -> list[models.Reminder]:
        ...

    async def get_all(
            self, guild: disnake.Guild = None, member: disnake.Member = None, take: int = None
    ) -> list[models.Reminder] | models.Guild:

        if guild and not take:

            return await self.bot.prisma.guild.find_unique(
                where={
                    "snowflake": guild.snowflake,
                },
                include={
                    "reminders": True,
                },
            )

        elif guild and take:
            return await self.bot.prisma.reminder.find_many(
                where={
                    "guild": {
                        "snowflake": guild.snowflake,
                    }
                },
                take=take,
            )
        elif member:
            return await self.bot.prisma.reminder.find_many(
                where={
                    "author_id": member.id,
                    "guild": {
                        "snowflake": member.guild.snowflake,
                    },
                },
                take=take,
            )

        else:
            return await self.bot.prisma.reminder.find_many(
                take=take,
            )

    async def create_field_from_reminder(self, reminder: Reminder) -> EmbedField:
        return EmbedField(
            name=f"#{reminder.reminder_number}. "
                 f"{disnake.utils.format_dt(reminder.expires_at, style='f')} "
                 f"| {await self.bot.getch_user(reminder.author_id)}",
            value=f"{reminder.content}",
        )
