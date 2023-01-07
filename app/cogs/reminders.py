import datetime

import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext.commands import Cog, slash_command, guild_only, Param, has_permissions, \
    CommandInvokeError
from disnake.ext.tasks import loop
from prisma.models import Reminder

from app import (
    Bot,
    Embed,
    parse_datetime,
    get_mentions_as_string,
    create_embeds_from_fields,
    md,
)
from app.services.ReminderService import ReminderService
from app.types import CommandInteraction
from app.views import PaginationView


class UserReminder(Cog, ReminderService):
    def __init__(self, bot: Bot):
        self.bot = bot

    @slash_command(
        name="reminder",
    )
    @guild_only()
    async def remind(self, interaction: CommandInteraction):
        pass

    @remind.sub_command(
        name="create",
    )
    async def create_reminder(
            self,
            inter: CommandInteraction,
            content: str = Param(name="content", description="The content of the reminder"),
            in_: str = Param(name="in", description="In how long should the reminder be sent"),
    ) -> None:

        assert len(in_) > 0, "You must specify a date"

        datetime_at = parse_datetime(in_)

        self.bot.logger.debug(f"Adding reminder for {inter.author} at {datetime_at}")

        assert datetime_at > self.bot.now, "You can't set a reminder in the past"

        # Add a check to see if the reminder is too far in the future 5 yrs max
        assert datetime_at < self.bot.now + datetime.timedelta(days=1825), "You can't set a reminder more than 5 years in the future"


        assert len(content) <= 1000, "Content must be less than 1000 characters"
        assert len(content) > 0, "Content must be more than 0 characters"

        assert isinstance(
            inter.channel, disnake.TextChannel
        ), "You can only set reminders in text channels"

        reminder = await self.add(
            guild=inter.guild,
            channel=inter.channel,
            member=inter.author,
            expires_at=datetime_at,
            content=content,
        )

        await self.add_task(reminder, interaction=inter)

        embed = Embed(
            description=f":alarm_clock: Reminder {md(f'#{reminder.reminder_number}'):code} "
                        f"created successfully and will be sent to this"
                        f" channel at {disnake.utils.format_dt(datetime_at, style='F')}",
            user=inter.author,
        ).success

        await inter.send(embed=embed, delete_after=30)

    @remind.sub_command_group(
        name="list",
    )
    async def list_reminders(self, inter: CommandInteraction) -> None:
        pass

    @list_reminders.sub_command(
        name="me",
    )
    async def list_my_reminders(self, inter: CommandInteraction) -> None:
        reminders = await self.get_all(member=inter.author)

        fields = [await self.create_field_from_reminder(reminder) for reminder in reminders]

        embed = Embed(
            title="Your reminders",
            description="Here are all your reminders",
            fields=fields,
            user=inter.author,
        )

        embeds = create_embeds_from_fields(embed, fields, max_size=10)

        if not embeds:
            no_reminders_embed = Embed(
                title="No reminders",
                description="You don't have any reminders",
                user=inter.author,
            ).error

            return await inter.send(embed=no_reminders_embed)

        view = PaginationView(bot=self.bot, user=inter.author, pages=embeds, timeout=60)

        await inter.send(embed=embeds[0], view=view)

    @list_reminders.sub_command(
        name="all",
    )
    @has_permissions(administrator=True)
    async def list_all_reminders(self, inter: CommandInteraction) -> None:
        reminders: list[Reminder] = (await self.get_all(guild=inter.guild)).reminders

        fields = [await self.create_field_from_reminder(reminder) for reminder in reminders]

        embed = Embed(
            title="All reminders",
            description="Here are all reminders",
            fields=fields,
            user=inter.author,
        )

        embeds = create_embeds_from_fields(embed, fields, max_size=10)

        if not embeds:
            no_reminders_embed = Embed(
                title="No reminders",
                description="There are no reminders created for this server",
                user=inter.author,
            ).error

            return await inter.send(embed=no_reminders_embed)

        view = PaginationView(bot=self.bot, user=inter.author, pages=embeds, timeout=60)

        await inter.send(embed=embeds[0], view=view)

    @remind.sub_command(
        name="delete",
    )
    async def delete_reminder(
            self,
            inter: CommandInteraction,
            reminder_number: str = Param(name="code",
                                         description="The number of the reminder you want to "
                                                     "delete: `<number>`"),
    ) -> None:
        reminder: Reminder = await self.get_by_code(inter.guild, int(reminder_number))

        assert reminder is not None, "Reminder not found"

        member = await inter.guild.getch_member(reminder.author_id)

        if member == inter.author or inter.author.guild_permissions.administrator:
            await self.remove(reminder.id)
            embed = Embed(
                description=f":alarm_clock: Reminder {md(f'#{reminder.reminder_number}'):code} "
                            f"deleted successfully",
                user=inter.author,
            ).success

            await inter.send(embed=embed, delete_after=30)
        else:
            raise AssertionError("You can't delete other people's reminders")

    @delete_reminder.autocomplete("code")
    async def delete_reminder_auto_complete(
            self, inter: CommandInteraction, reminder_number: str
    ) -> list[str]:
        if inter.author.guild_permissions.administrator:
            reminders = await self.get_all(guild=inter.guild, take=24)
            return [str(reminder.reminder_number) for reminder in reminders]
        else:
            reminders = await self.get_all(member=inter.author, take=24)
            return [str(reminder.reminder_number) for reminder in reminders]

    async def add_task(self, reminder: Reminder, interaction: CommandInteraction | None) -> None:
        time = reminder.expires_at.time()
        reminder_loop = loop(time=time)(self.remind_task)

        reminder_loop.start(reminder_id=reminder.id, interaction=interaction)

    async def remind_task(self, reminder_id: int, interaction: CommandInteraction | None) -> None:
        reminder = await self.get(reminder_id)

        if reminder is None:
            return

        channel = self.bot.get_channel(reminder.channel_id)
        member = self.bot.get_user(reminder.author_id)

        mentions = get_mentions_as_string(reminder.content)

        reminder_embed = Embed(
            title=f"Reminder {md(f'#{reminder.reminder_number}')}: ",
            description=reminder.content,
            user=member,
        ).info

        allowed_mentions = disnake.AllowedMentions(
            everyone=False,
            users=True,
            roles=False,
        )

        async def send_in_channel():
            await channel.send(
                f"{member.mention} {mentions}",
                embed=reminder_embed,
                allowed_mentions=allowed_mentions,
            )

        if not interaction:
            await send_in_channel()
        else:
            try:
                await interaction.followup.send(
                    f"{member.mention} {mentions}",
                    embed=reminder_embed,
                    allowed_mentions=allowed_mentions,
                )
            except disnake.HTTPException:
                await send_in_channel()

        await self.remove(reminder.id)

    async def cog_slash_command_error(
            self, inter: ApplicationCommandInteraction, error: Exception
    ) -> None:
        self.bot.logger.error(f"Error in remind command {type(error)}")
        if isinstance(error, CommandInvokeError):
            embed = Embed(
                title="Error",
                description=error.args[0],
                user=inter.author,
            ).error

            await inter.send(embed=embed)
        elif isinstance(error, disnake.HTTPException):
            embed = Embed(
                title="Error",
                description="I couldn't send the reminder in the channel",
                user=inter.author,
            ).error

            await inter.send(embed=embed)

        elif isinstance(error, disnake.errors.Forbidden):
            embed = Embed(
                title="Error",
                description="I don't have permissions to send messages in that channel",
                user=inter.author,
            ).error

            await inter.send(embed=embed)

        elif isinstance(error, disnake.ext.commands.MissingPermissions):
            embed = Embed(
                title="Error",
                description="You don't have permissions to use this command",
                user=inter.author,
            ).error

            await inter.send(embed=embed)

        else:
            raise error


def setup(bot: Bot):
    cog = UserReminder(bot)

    bot.add_cog(cog)

    @bot.listen("on_ready")
    async def ready():
        reminders_deleted = await cog.remove_expired_reminders()

        bot.logger.warn(f"Removed {reminders_deleted} expired reminders")

        reminders = await cog.get_all()

        bot.logger.debug(f"Found {reminders} reminders")

        for reminder in reminders:
            await cog.add_task(reminder, interaction=None)
