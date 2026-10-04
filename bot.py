import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, ChannelSelect
import os
import json
import random as random_module
import asyncio
from datetime import datetime, timezone


# =========================================================
# CONFIG
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1519481018221072454

APPLICATION_CHANNEL_ID = 1541391365219295343
REVIEW_CHANNEL_ID = 1548404201493762181

NAMETAG_CHANNEL_ID = 1555684071911202836
LICENSE_PLATE_CHANNEL_ID = 1527350468832006276

DEVELOPER_TASK_CHANNEL_ID = 1540442867334385715
DEVELOPER_SHIFT_CHANNEL_ID = 1555923435056795648
SHIFT_LOG_CHANNEL_ID = 1540797414863151155

SUGGESTION_CHANNEL_ID = 1540773028642947234
FEEDBACK_CHANNEL_ID = 1556072540307333200
BUG_CHANNEL_ID = 1556072637170716732

NAMETAG_ROLE_ID = 1520102928398942348
SHIFT_PERMISSION_ROLE_ID = 1523674698574200904
DEVELOPER_SHIFT_ROLE_ID = 1527372148979798086

OWNER_ROLE_ID = 1544691379613999164
SUGGESTION_REVIEW_ROLE_ID = 1530188150456979526

NAMETAG = "RLP | "

DATA_FILE = "bot_data.json"

NAMETAG_PANEL_MARKER = "RLP_NAMETAG_PANEL"
LICENSE_PANEL_MARKER = "RLP_LICENSE_PANEL"
APPLICATION_PANEL_MARKER = "RLP_APPLICATION_PANEL"
DEV_TASK_PANEL_MARKER = "RLP_DEV_TASK_PANEL"
DEV_SHIFT_PANEL_MARKER = "RLP_DEV_SHIFT_PANEL"
COMMUNITY_PANEL_MARKER = "RLP_COMMUNITY_PANEL"
OWNER_PANEL_MARKER = "RLP_OWNER_PANEL"

PREFIX = "?"

bot_started_at = datetime.now(timezone.utc)


# =========================================================
# INTENTS / BOT
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None
)


# =========================================================
# DATA
# =========================================================

def default_data():
    return {
        "license_plates": {},
        "applications": {},
        "developer_tasks": {},
        "suggestions": {},
        "feedback": {},
        "bugs": {}
    }


def load_data():
    if not os.path.exists(DATA_FILE):
        return default_data()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        base = default_data()

        for key, value in base.items():
            if key not in data:
                data[key] = value

        return data

    except Exception as e:
        print(f"DATA LOAD ERROR: {e}")
        return default_data()


data = load_data()


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"DATA SAVE ERROR: {e}")


# =========================================================
# HELPERS
# =========================================================

def has_role(member: discord.Member, role_id: int):
    return any(role.id == role_id for role in member.roles)


def is_owner(member: discord.Member):
    return has_role(member, OWNER_ROLE_ID)


def get_guild():
    return bot.get_guild(GUILD_ID)


def get_channel(channel_id: int):
    guild = get_guild()

    if guild is None:
        return None

    return guild.get_channel(channel_id)


async def safe_delete(message):
    try:
        await message.delete()
    except Exception:
        pass


async def send_no_permission(interaction):
    message = "❌ Du hast nicht genügend Berechtigungen. Diese Funktion ist nur für Owner verfügbar."

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


def format_duration(seconds):
    seconds = int(seconds)

    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = []

    if days:
        parts.append(f"{days}T")

    if hours:
        parts.append(f"{hours}Std.")

    if minutes:
        parts.append(f"{minutes}Min.")

    parts.append(f"{seconds}Sek.")

    return " ".join(parts)


async def get_or_fetch_member(guild, user_id):
    member = guild.get_member(user_id)

    if member:
        return member

    try:
        return await guild.fetch_member(user_id)
    except Exception:
        return None


# =========================================================
# PANEL HELPERS
# =========================================================

async def delete_panel_messages(channel, marker):
    deleted = 0

    try:
        async for message in channel.history(limit=100):
            found = False

            for embed in message.embeds:
                for field in embed.fields:
                    if field.name == "Panel-ID" and field.value == marker:
                        found = True
                        break

            if found:
                try:
                    await message.delete()
                    deleted += 1
                except Exception:
                    pass

    except Exception as e:
        print(f"PANEL DELETE ERROR: {e}")

    return deleted


async def replace_panel(channel, marker, embed, view):
    await delete_panel_messages(channel, marker)

    try:
        await channel.send(embed=embed, view=view)
    except Exception as e:
        print(f"PANEL SEND ERROR: {marker}: {e}")


# =========================================================
# NAMETAG
# =========================================================

class NametagModal(Modal):
    def __init__(self):
        super().__init__(title="Nametag setzen")

        self.name_input = TextInput(
            label="Nametag",
            placeholder="Dein Discord-Name",
            required=True,
            max_length=32
        )

        self.add_item(self.name_input)

    async def on_submit(self, interaction: discord.Interaction):

        member = interaction.guild.get_member(interaction.user.id)

        if member is None:
            await interaction.response.send_message(
                "❌ Mitglied konnte nicht gefunden werden.",
                ephemeral=True
            )
            return

        if not has_role(member, NAMETAG_ROLE_ID):
            await interaction.response.send_message(
                "❌ Du hast nicht die benötigte Nametag-Rolle.",
                ephemeral=True
            )
            return

        new_name = self.name_input.value.strip()

        if not new_name:
            await interaction.response.send_message(
                "❌ Bitte gib einen Namen ein.",
                ephemeral=True
            )
            return

        if new_name.startswith(NAMETAG):
            new_name = new_name[len(NAMETAG):].strip()

        try:
            await member.edit(
                nick=f"{NAMETAG}{new_name}",
                reason="Nametag gesetzt"
            )

            await interaction.response.send_message(
                f"✅ Dein Nametag wurde auf `{NAMETAG}{new_name}` gesetzt.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Der Bot kann deinen Nicknamen nicht ändern. Prüfe die Bot-Rolle.",
                ephemeral=True
            )

        except Exception as e:
            print(f"NAMETAG ERROR: {e}")

            await interaction.response.send_message(
                "❌ Beim Setzen des Nametags ist ein Fehler aufgetreten.",
                ephemeral=True
            )


class NametagSetButton(Button):
    def __init__(self):
        super().__init__(
            label="Nametag setzen",
            emoji="🏷️",
            style=discord.ButtonStyle.primary,
            custom_id="nametag_set"
        )

    async def callback(self, interaction: discord.Interaction):

        await interaction.response.send_modal(
            NametagModal()
        )


class NametagResetButton(Button):
    def __init__(self):
        super().__init__(
            label="Nametag zurücksetzen",
            emoji="🔄",
            style=discord.ButtonStyle.secondary,
            custom_id="nametag_reset"
        )

    async def callback(self, interaction: discord.Interaction):

        member = interaction.guild.get_member(interaction.user.id)

        if member is None:
            await interaction.response.send_message(
                "❌ Mitglied konnte nicht gefunden werden.",
                ephemeral=True
            )
            return

        if not has_role(member, NAMETAG_ROLE_ID):
            await interaction.response.send_message(
                "❌ Du hast nicht die benötigte Nametag-Rolle.",
                ephemeral=True
            )
            return

        current_name = member.nick

        if not current_name:
            await interaction.response.send_message(
                "ℹ️ Du hast keinen eigenen Nicknamen.",
                ephemeral=True
            )
            return

        new_name = current_name

        if new_name.startswith(NAMETAG):
            new_name = new_name[len(NAMETAG):]

        new_name = new_name.replace("\u00a0", " ")

        if new_name.startswith(" "):
            new_name = new_name[1:]

        try:
            await member.edit(
                nick=new_name if new_name else None,
                reason="Nametag zurückgesetzt"
            )

            await interaction.response.send_message(
                "✅ Dein Nametag wurde entfernt.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Der Bot kann deinen Nicknamen nicht ändern.",
                ephemeral=True
            )

        except Exception as e:
            print(f"NAMETAG RESET ERROR: {e}")

            await interaction.response.send_message(
                "❌ Fehler beim Zurücksetzen.",
                ephemeral=True
            )


class NametagView(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(NametagSetButton())
        self.add_item(NametagResetButton())


def nametag_embed():
    embed = discord.Embed(
        title="🏷️ Nametag System",
        description=(
            "Hier kannst du deinen **RLP-Nametag** verwalten.\n\n"
            "🏷️ **Nametag setzen**\n"
            "Setzt deinen Namen mit dem Prefix `RLP | `.\n\n"
            "🔄 **Nametag zurücksetzen**\n"
            "Entfernt nur den `RLP | ` Prefix.\n\n"
            "Deine Rollen werden dabei **nicht verändert**."
        ),
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Panel-ID",
        value=NAMETAG_PANEL_MARKER,
        inline=False
    )

    return embed


# =========================================================
# LICENSE PLATES
# =========================================================

class LicensePlateModal(Modal):
    def __init__(self):
        super().__init__(title="Kennzeichen beantragen")

        self.plate_input = TextInput(
            label="Kennzeichen",
            placeholder="z.B. RLP 01",
            required=True,
            max_length=20
        )

        self.add_item(self.plate_input)

    async def on_submit(self, interaction: discord.Interaction):

        plate = self.plate_input.value.strip().upper()

        parts = plate.split()

        if len(parts) < 2:
            await interaction.response.send_message(
                "❌ Das Kennzeichen muss Prefix und Nummer enthalten.\nBeispiel: `RLP 01`",
                ephemeral=True
            )
            return

        number = parts[-1]

        if not number.isdigit():
            await interaction.response.send_message(
                "❌ Die letzte Kennzeichen-Komponente muss eine Zahl sein.",
                ephemeral=True
            )
            return

        for existing in data["license_plates"].values():

            if str(existing.get("number")) == str(number):
                await interaction.response.send_message(
                    "❌ Diese Nummer ist bereits vergeben.",
                    ephemeral=True
                )
                return

        user_id = str(interaction.user.id)

        data["license_plates"][user_id] = {
            "user_id": interaction.user.id,
            "plate": plate,
            "number": number
        }

        save_data()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen `{plate}` wurde gespeichert.",
            ephemeral=True
        )

        await refresh_license_panel()


class LicensePlateButton(Button):
    def __init__(self):
        super().__init__(
            label="Kennzeichen beantragen",
            emoji="🚗",
            style=discord.ButtonStyle.primary,
            custom_id="license_plate_create"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            LicensePlateModal()
        )


class LicensePlateView(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(LicensePlateButton())


async def refresh_license_panel():

    channel = get_channel(LICENSE_PLATE_CHANNEL_ID)

    if not isinstance(channel, discord.TextChannel):
        return

    await delete_panel_messages(
        channel,
        LICENSE_PANEL_MARKER
    )

    lines = []

    for entry in data["license_plates"].values():

        member = await get_or_fetch_member(
            channel.guild,
            entry["user_id"]
        )

        if member:
            name = member.display_name
        else:
            name = f"User {entry['user_id']}"

        lines.append(
            f"🚗 `{entry['plate']}` — **{name}**"
        )

    if lines:
        description = "\n".join(lines)
    else:
        description = "Noch keine Kennzeichen vergeben."

    embed = discord.Embed(
        title="🚗 Kennzeichen-System",
        description=description,
        color=discord.Color.green()
    )

    embed.add_field(
        name="Panel-ID",
        value=LICENSE_PANEL_MARKER,
        inline=False
    )

    await channel.send(
        embed=embed,
        view=LicensePlateView()
    )


# =========================================================
# APPLICATIONS
# =========================================================

class ApplicationModal(Modal):
    def __init__(self):
        super().__init__(title="Bewerbung")

        self.name_input = TextInput(
            label="Name",
            placeholder="Dein Name",
            required=True,
            max_length=100
        )

        self.age_input = TextInput(
            label="Alter",
            placeholder="Dein Alter",
            required=True,
            max_length=3
        )

        self.reason_input = TextInput(
            label="Warum möchtest du dich bewerben?",
            placeholder="Schreibe etwas über dich...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.name_input)
        self.add_item(self.age_input)
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):

        channel = get_channel(APPLICATION_CHANNEL_ID)

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Bewerbungs-Kanal wurde nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📨 Neue Bewerbung",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="👤 Benutzer",
            value=f"{interaction.user.mention}\n`{interaction.user.id}`",
            inline=False
        )

        embed.add_field(
            name="📝 Name",
            value=self.name_input.value,
            inline=True
        )

        embed.add_field(
            name="🎂 Alter",
            value=self.age_input.value,
            inline=True
        )

        embed.add_field(
            name="💬 Grund",
            value=self.reason_input.value,
            inline=False
        )

        embed.set_thumbnail(
            url=interaction.user.display_avatar.url
        )

        await channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Deine Bewerbung wurde abgeschickt.",
            ephemeral=True
        )


class ApplicationButton(Button):
    def __init__(self):
        super().__init__(
            label="Bewerben",
            emoji="📨",
            style=discord.ButtonStyle.success,
            custom_id="application_button"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            ApplicationModal()
        )


class ApplicationView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ApplicationButton())


def application_embed():

    embed = discord.Embed(
        title="📨 Bewerbung",
        description=(
            "Du möchtest dich bei uns bewerben?\n\n"
            "Klicke auf **Bewerben** und fülle das Formular aus."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Panel-ID",
        value=APPLICATION_PANEL_MARKER,
        inline=False
    )

    return embed


# =========================================================
# DEVELOPER TASKS
# =========================================================

class DeveloperTaskModal(Modal):
    def __init__(self):
        super().__init__(title="Developer Aufgabe")

        self.task_input = TextInput(
            label="Aufgabe",
            placeholder="Welche Aufgabe soll erledigt werden?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.task_input)

    async def on_submit(self, interaction: discord.Interaction):

        member = interaction.guild.get_member(interaction.user.id)

        if member is None or not has_role(
            member,
            SHIFT_PERMISSION_ROLE_ID
        ):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung dafür.",
                ephemeral=True
            )
            return

        channel = get_channel(DEVELOPER_TASK_CHANNEL_ID)

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Developer-Task-Kanal nicht gefunden.",
                ephemeral=True
            )
            return

        task_id = str(len(data["developer_tasks"]) + 1)

        data["developer_tasks"][task_id] = {
            "id": task_id,
            "author_id": interaction.user.id,
            "task": self.task_input.value,
            "created_at": discord.utils.utcnow().isoformat()
        }

        save_data()

        embed = discord.Embed(
            title=f"🛠️ Developer Aufgabe #{task_id}",
            description=self.task_input.value,
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="👤 Erstellt von",
            value=interaction.user.mention,
            inline=False
        )

        await channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Die Aufgabe wurde erstellt.",
            ephemeral=True
        )


class DeveloperTaskButton(Button):
    def __init__(self):
        super().__init__(
            label="Aufgabe erstellen",
            emoji="🛠️",
            style=discord.ButtonStyle.primary,
            custom_id="developer_task_create"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            DeveloperTaskModal()
        )


class DeveloperTaskView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(DeveloperTaskButton())


def developer_task_embed():

    embed = discord.Embed(
        title="🛠️ Developer Aufgaben",
        description=(
            "Mit dem Button kannst du eine neue Developer-Aufgabe "
            "erstellen."
        ),
        color=discord.Color.orange()
    )

    embed.add_field(
        name="Panel-ID",
        value=DEV_TASK_PANEL_MARKER,
        inline=False
    )

    return embed


# =========================================================
# DEVELOPER SHIFT
# =========================================================

class DeveloperShiftStartButton(Button):
    def __init__(self):
        super().__init__(
            label="Schicht starten",
            emoji="🟢",
            style=discord.ButtonStyle.success,
            custom_id="developer_shift_start"
        )

    async def callback(self, interaction: discord.Interaction):

        member = interaction.guild.get_member(interaction.user.id)

        if member is None or not has_role(
            member,
            SHIFT_PERMISSION_ROLE_ID
        ):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung dafür.",
                ephemeral=True
            )
            return

        role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if role is None:
            await interaction.response.send_message(
                "❌ Developer-Schicht-Rolle wurde nicht gefunden.",
                ephemeral=True
            )
            return

        if role in member.roles:
            await interaction.response.send_message(
                "ℹ️ Du bist bereits im aktiven Dienst.",
                ephemeral=True
            )
            return

        try:
            await member.add_roles(
                role,
                reason="Developer-Schicht gestartet"
            )

            log_channel = get_channel(SHIFT_LOG_CHANNEL_ID)

            if isinstance(log_channel, discord.TextChannel):

                await log_channel.send(
                    f"🟢 **Developer-Schicht gestartet**\n"
                    f"👤 {member.mention}"
                )

            await interaction.response.send_message(
                "🟢 Deine Developer-Schicht wurde gestartet.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Der Bot kann die Schicht-Rolle nicht vergeben.",
                ephemeral=True
            )


class DeveloperShiftEndButton(Button):
    def __init__(self):
        super().__init__(
            label="Schicht beenden",
            emoji="🔴",
            style=discord.ButtonStyle.danger,
            custom_id="developer_shift_end"
        )

    async def callback(self, interaction: discord.Interaction):

        member = interaction.guild.get_member(interaction.user.id)

        if member is None or not has_role(
            member,
            SHIFT_PERMISSION_ROLE_ID
        ):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung dafür.",
                ephemeral=True
            )
            return

        role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if role is None:
            await interaction.response.send_message(
                "❌ Developer-Schicht-Rolle wurde nicht gefunden.",
                ephemeral=True
            )
            return

        if role not in member.roles:
            await interaction.response.send_message(
                "ℹ️ Du bist aktuell nicht im aktiven Dienst.",
                ephemeral=True
            )
            return

        try:
            await member.remove_roles(
                role,
                reason="Developer-Schicht beendet"
            )

            log_channel = get_channel(SHIFT_LOG_CHANNEL_ID)

            if isinstance(log_channel, discord.TextChannel):

                await log_channel.send(
                    f"🔴 **Developer-Schicht beendet**\n"
                    f"👤 {member.mention}"
                )

            await interaction.response.send_message(
                "🔴 Deine Developer-Schicht wurde beendet.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Der Bot kann die Schicht-Rolle nicht entfernen.",
                ephemeral=True
            )


class DeveloperShiftView(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(
            DeveloperShiftStartButton()
        )

        self.add_item(
            DeveloperShiftEndButton()
        )


def developer_shift_embed():

    embed = discord.Embed(
        title="🛠️ Developer-Schicht",
        description=(
            "Verwalte hier deine Developer-Schicht.\n\n"
            "🟢 **Schicht starten**\n"
            "Aktiviert deine Developer-Schicht.\n\n"
            "🔴 **Schicht beenden**\n"
            "Beendet deine Developer-Schicht."
        ),
        color=discord.Color.orange()
    )

    embed.add_field(
        name="Panel-ID",
        value=DEV_SHIFT_PANEL_MARKER,
        inline=False
    )

    return embed


# =========================================================
# SUGGESTIONS
# =========================================================

class SuggestionModal(Modal):
    def __init__(self):
        super().__init__(title="Vorschlag erstellen")

        self.suggestion_input = TextInput(
            label="Dein Vorschlag",
            placeholder="Schreibe deinen Vorschlag...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.suggestion_input)

    async def on_submit(self, interaction: discord.Interaction):

        channel = get_channel(SUGGESTION_CHANNEL_ID)

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Vorschlagskanal nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="💡 Neuer Vorschlag",
            description=self.suggestion_input.value,
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="👤 Erstellt von",
            value=interaction.user.mention,
            inline=False
        )

        embed.add_field(
            name="📊 Stimmen",
            value="🟢 Für: **0**\n🔴 Gegen: **0**",
            inline=False
        )

        embed.add_field(
            name="📌 Status",
            value="🟡 Offen",
            inline=False
        )

        message = await channel.send(
            embed=embed,
            view=SuggestionView()
        )

        data["suggestions"][str(message.id)] = {
            "author_id": interaction.user.id,
            "text": self.suggestion_input.value,
            "status": "offen",
            "for_votes": [],
            "against_votes": []
        }

        save_data()

        await interaction.response.send_message(
            f"✅ Dein Vorschlag wurde in {channel.mention} erstellt.",
            ephemeral=True
        )


class SuggestionCreateButton(Button):
    def __init__(self):
        super().__init__(
            label="Vorschlag",
            emoji="💡",
            style=discord.ButtonStyle.primary,
            custom_id="community_suggestion"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            SuggestionModal()
        )


class SuggestionVoteForButton(Button):
    def __init__(self):
        super().__init__(
            label="Für den Vorschlag",
            emoji="🟢",
            style=discord.ButtonStyle.success,
            custom_id="suggestion_vote_for"
        )

    async def callback(self, interaction: discord.Interaction):

        await handle_suggestion_vote(
            interaction,
            True
        )


class SuggestionVoteAgainstButton(Button):
    def __init__(self):
        super().__init__(
            label="Gegen den Vorschlag",
            emoji="🔴",
            style=discord.ButtonStyle.danger,
            custom_id="suggestion_vote_against"
        )

    async def callback(self, interaction: discord.Interaction):

        await handle_suggestion_vote(
            interaction,
            False
        )


class SuggestionAcceptButton(Button):
    def __init__(self):
        super().__init__(
            label="Annehmen",
            emoji="🟢",
            style=discord.ButtonStyle.success,
            custom_id="suggestion_accept"
        )

    async def callback(self, interaction: discord.Interaction):

        member = interaction.guild.get_member(
            interaction.user.id
        )

        if member is None or not has_role(
            member,
            SUGGESTION_REVIEW_ROLE_ID
        ):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung, Vorschläge zu bearbeiten.",
                ephemeral=True
            )
            return

        await set_suggestion_status(
            interaction,
            "angenommen"
        )


class SuggestionRejectButton(Button):
    def __init__(self):
        super().__init__(
            label="Ablehnen",
            emoji="🔴",
            style=discord.ButtonStyle.danger,
            custom_id="suggestion_reject"
        )

    async def callback(self, interaction: discord.Interaction):

        member = interaction.guild.get_member(
            interaction.user.id
        )

        if member is None or not has_role(
            member,
            SUGGESTION_REVIEW_ROLE_ID
        ):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung, Vorschläge zu bearbeiten.",
                ephemeral=True
            )
            return

        await set_suggestion_status(
            interaction,
            "abgelehnt"
        )


class SuggestionView(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(SuggestionVoteForButton())
        self.add_item(SuggestionVoteAgainstButton())
        self.add_item(SuggestionAcceptButton())
        self.add_item(SuggestionRejectButton())


async def handle_suggestion_vote(
    interaction: discord.Interaction,
    vote_for: bool
):

    message_id = str(interaction.message.id)

    suggestion = data["suggestions"].get(message_id)

    if suggestion is None:
        await interaction.response.send_message(
            "❌ Dieser Vorschlag wurde nicht gefunden.",
            ephemeral=True
        )
        return

    user_id = interaction.user.id

    for_votes = suggestion.setdefault(
        "for_votes",
        []
    )

    against_votes = suggestion.setdefault(
        "against_votes",
        []
    )

    # =====================================================
    # WICHTIG:
    # Jeder kann seine Stimme ändern.
    # Es kommt NICHT "du hast schon abgestimmt".
    # =====================================================

    if vote_for:

        if user_id in against_votes:
            against_votes.remove(user_id)

        if user_id not in for_votes:
            for_votes.append(user_id)

    else:

        if user_id in for_votes:
            for_votes.remove(user_id)

        if user_id not in against_votes:
            against_votes.append(user_id)

    save_data()

    await update_suggestion_message(
        interaction.message,
        suggestion
    )

    if vote_for:
        text = "🟢 Deine Stimme ist jetzt **für den Vorschlag**."
    else:
        text = "🔴 Deine Stimme ist jetzt **gegen den Vorschlag**."

    await interaction.response.send_message(
        text,
        ephemeral=True
    )


async def set_suggestion_status(
    interaction,
    status
):

    message_id = str(interaction.message.id)

    suggestion = data["suggestions"].get(message_id)

    if suggestion is None:
        await interaction.response.send_message(
            "❌ Dieser Vorschlag wurde nicht gefunden.",
            ephemeral=True
        )
        return

    suggestion["status"] = status

    save_data()

    await update_suggestion_message(
        interaction.message,
        suggestion
    )

    if status == "angenommen":
        text = "🟢 Der Vorschlag wurde angenommen."
    else:
        text = "🔴 Der Vorschlag wurde abgelehnt."

    await interaction.response.send_message(
        text,
        ephemeral=True
    )


async def update_suggestion_message(
    message,
    suggestion
):

    status = suggestion.get(
        "status",
        "offen"
    )

    if status == "angenommen":
        status_text = "🟢 Angenommen"
        color = discord.Color.green()

    elif status == "abgelehnt":
        status_text = "🔴 Abgelehnt"
        color = discord.Color.red()

    else:
        status_text = "🟡 Offen"
        color = discord.Color.blurple()

    for_count = len(
        suggestion.get("for_votes", [])
    )

    against_count = len(
        suggestion.get("against_votes", [])
    )

    embed = discord.Embed(
        title="💡 Neuer Vorschlag",
        description=suggestion.get("text", ""),
        color=color
    )

    author_id = suggestion.get("author_id")

    if author_id:
        member = message.guild.get_member(
            author_id
        )

        if member:
            author_text = member.mention
        else:
            author_text = f"<@{author_id}>"

        embed.add_field(
            name="👤 Erstellt von",
            value=author_text,
            inline=False
        )

    embed.add_field(
        name="📊 Stimmen",
        value=(
            f"🟢 Für: **{for_count}**\n"
            f"🔴 Gegen: **{against_count}**"
        ),
        inline=False
    )

    embed.add_field(
        name="📌 Status",
        value=status_text,
        inline=False
    )

    try:
        await message.edit(
            embed=embed,
            view=SuggestionView()
        )
    except Exception as e:
        print(f"SUGGESTION UPDATE ERROR: {e}")


# =========================================================
# COMMUNITY PANEL
# =========================================================

class FeedbackModal(Modal):
    def __init__(self):
        super().__init__(title="Feedback")

        self.feedback_input = TextInput(
            label="Dein Feedback",
            placeholder="Was möchtest du uns mitteilen?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.feedback_input)

    async def on_submit(self, interaction):

        channel = get_channel(
            FEEDBACK_CHANNEL_ID
        )

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Feedback-Kanal nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="💬 Neues Feedback",
            description=self.feedback_input.value,
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="👤 Von",
            value=interaction.user.mention,
            inline=False
        )

        await channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Dein Feedback wurde gesendet.",
            ephemeral=True
        )


class BugModal(Modal):
    def __init__(self):
        super().__init__(title="Bug melden")

        self.bug_input = TextInput(
            label="Bug",
            placeholder="Beschreibe den Fehler...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.bug_input)

    async def on_submit(self, interaction):

        channel = get_channel(
            BUG_CHANNEL_ID
        )

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Bug-Kanal nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🐞 Neuer Bug",
            description=self.bug_input.value,
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="👤 Gemeldet von",
            value=interaction.user.mention,
            inline=False
        )

        await channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Der Bug wurde gemeldet.",
            ephemeral=True
        )


class FeedbackButton(Button):
    def __init__(self):
        super().__init__(
            label="Feedback",
            emoji="💬",
            style=discord.ButtonStyle.secondary,
            custom_id="community_feedback"
        )

    async def callback(self, interaction):
        await interaction.response.send_modal(
            FeedbackModal()
        )


class BugButton(Button):
    def __init__(self):
        super().__init__(
            label="Bug melden",
            emoji="🐞",
            style=discord.ButtonStyle.danger,
            custom_id="community_bug"
        )

    async def callback(self, interaction):
        await interaction.response.send_modal(
            BugModal()
        )


class CommunityPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(SuggestionCreateButton())
        self.add_item(FeedbackButton())
        self.add_item(BugButton())


def community_embed():

    embed = discord.Embed(
        title="🌐 Community",
        description=(
            "Hier findest du unsere Community-Funktionen.\n\n"
            "💡 **Vorschlag**\n"
            "Sende uns einen neuen Vorschlag.\n\n"
            "💬 **Feedback**\n"
            "Teile uns deine Meinung mit.\n\n"
            "🐞 **Bug melden**\n"
            "Melde einen Fehler beim Team."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Panel-ID",
        value=COMMUNITY_PANEL_MARKER,
        inline=False
    )

    return embed


# =========================================================
# OWNER PANEL
# =========================================================

class OwnerChannelSelectView(View):
    def __init__(self, action):
        super().__init__(timeout=180)

        self.action = action

        self.select = ChannelSelect(
            placeholder="Wähle einen Textkanal...",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1
        )

        self.select.callback = self.channel_selected

        self.add_item(self.select)

    async def channel_selected(self, interaction):

        if not is_owner(interaction.user):
            await send_no_permission(interaction)
            return

        selected = self.select.values[0]

        channel = interaction.guild.get_channel(
            selected.id
        )

        if not isinstance(
            channel,
            discord.TextChannel
        ):
            await interaction.response.send_message(
                "❌ Dieser Kanal ist kein Textkanal.",
                ephemeral=True
            )
            return

        try:

            if self.action == "announcement":

                await interaction.response.send_modal(
                    AnnouncementModal(channel)
                )

            elif self.action == "say":

                await interaction.response.send_modal(
                    BotSayModal(channel)
                )

            elif self.action == "lock":

                await interaction.response.defer(
                    ephemeral=True
                )

                overwrite = channel.overwrites_for(
                    interaction.guild.default_role
                )

                overwrite.send_messages = False

                await channel.set_permissions(
                    interaction.guild.default_role,
                    overwrite=overwrite,
                    reason=f"Owner Lock durch {interaction.user}"
                )

                await interaction.followup.send(
                    f"🔒 {channel.mention} wurde gesperrt.",
                    ephemeral=True
                )

            elif self.action == "unlock":

                await interaction.response.defer(
                    ephemeral=True
                )

                overwrite = channel.overwrites_for(
                    interaction.guild.default_role
                )

                overwrite.send_messages = None

                await channel.set_permissions(
                    interaction.guild.default_role,
                    overwrite=overwrite,
                    reason=f"Owner Unlock durch {interaction.user}"
                )

                await interaction.followup.send(
                    f"🔓 {channel.mention} wurde entsperrt.",
                    ephemeral=True
                )

            elif self.action == "clear":

                await interaction.response.defer(
                    ephemeral=True
                )

                deleted = await channel.purge(
                    limit=100
                )

                await interaction.followup.send(
                    f"🧹 Es wurden **{len(deleted)} Nachrichten** gelöscht.",
                    ephemeral=True
                )

            elif self.action == "giveaway":

                await interaction.response.send_modal(
                    GiveawayModal(channel)
                )

        except discord.Forbidden:

            if interaction.response.is_done():
                await interaction.followup.send(
                    "❌ Der Bot hat nicht genügend Berechtigungen.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "❌ Der Bot hat nicht genügend Berechtigungen.",
                    ephemeral=True
                )

        except Exception as e:

            print(
                f"OWNER CHANNEL ERROR: "
                f"{type(e).__name__}: {e}"
            )

            if interaction.response.is_done():
                await interaction.followup.send(
                    "❌ Es ist ein Fehler aufgetreten.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "❌ Es ist ein Fehler aufgetreten.",
                    ephemeral=True
                )


class AnnouncementModal(Modal):
    def __init__(self, channel):
        super().__init__(title="Ankündigung")

        self.channel = channel

        self.title_input = TextInput(
            label="Titel",
            placeholder="Titel der Ankündigung",
            required=True,
            max_length=256
        )

        self.message_input = TextInput(
            label="Nachricht",
            placeholder="Text der Ankündigung...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=4000
        )

        self.add_item(self.title_input)
        self.add_item(self.message_input)

    async def on_submit(self, interaction):

        if not is_owner(interaction.user):
            await send_no_permission(interaction)
            return

        embed = discord.Embed(
            title=f"📢 {self.title_input.value}",
            description=self.message_input.value,
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )

        embed.set_footer(
            text=f"Ankündigung von {interaction.user.display_name}"
        )

        try:

            await self.channel.send(
                embed=embed
            )

            await interaction.response.send_message(
                f"✅ Ankündigung wurde in {self.channel.mention} gesendet.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Der Bot kann dort keine Nachricht senden.",
                ephemeral=True
            )


class BotSayModal(Modal):
    def __init__(self, channel):
        super().__init__(title="Bot Say")

        self.channel = channel

        self.message_input = TextInput(
            label="Nachricht",
            placeholder="Was soll der Bot schreiben?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=4000
        )

        self.add_item(self.message_input)

    async def on_submit(self, interaction):

        if not is_owner(interaction.user):
            await send_no_permission(interaction)
            return

        try:

            await self.channel.send(
                self.message_input.value
            )

            await interaction.response.send_message(
                f"✅ Nachricht wurde in {self.channel.mention} gesendet.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Der Bot kann dort nicht schreiben.",
                ephemeral=True
            )


class GiveawayModal(Modal):
    def __init__(self, channel):
        super().__init__(title="Giveaway starten")

        self.channel = channel

        self.prize_input = TextInput(
            label="Gewinn",
            placeholder="z.B. Nitro",
            required=True,
            max_length=256
        )

        self.duration_input = TextInput(
            label="Dauer in Minuten",
            placeholder="z.B. 60",
            required=True,
            max_length=6
        )

        self.winner_input = TextInput(
            label="Anzahl Gewinner",
            placeholder="z.B. 1",
            required=True,
            max_length=3
        )

        self.add_item(self.prize_input)
        self.add_item(self.duration_input)
        self.add_item(self.winner_input)

    async def on_submit(self, interaction):

        if not is_owner(interaction.user):
            await send_no_permission(interaction)
            return

        try:
            minutes = int(
                self.duration_input.value
            )

            winners = int(
                self.winner_input.value
            )

            if minutes <= 0 or winners <= 0:
                raise ValueError

        except ValueError:

            await interaction.response.send_message(
                "❌ Dauer und Gewinner müssen positive Zahlen sein.",
                ephemeral=True
            )
            return

        end_time = discord.utils.utcnow().timestamp() + (
            minutes * 60
        )

        embed = discord.Embed(
            title="🎁 Giveaway",
            description=(
                f"🎁 **Gewinn:** {self.prize_input.value}\n\n"
                f"🏆 **Gewinner:** {winners}\n"
                f"⏱️ **Dauer:** {minutes} Minuten\n\n"
                "Reagiere mit 🎉 um teilzunehmen!"
            ),
            color=discord.Color.gold()
        )

        embed.set_footer(
            text=f"Gestartet von {interaction.user.display_name}"
        )

        message = await self.channel.send(
            embed=embed
        )

        await message.add_reaction("🎉")

        await interaction.response.send_message(
            f"✅ Giveaway wurde in {self.channel.mention} gestartet.",
            ephemeral=True
        )

        await asyncio.sleep(
            minutes * 60
        )

        try:

            message = await self.channel.fetch_message(
                message.id
            )

            reaction = discord.utils.get(
                message.reactions,
                emoji="🎉"
            )

            if reaction is None:
                participants = []
            else:
                participants = []

                async for user in reaction.users():

                    if user.bot:
                        continue

                    participants.append(user)

            if participants:

                winners_selected = random_module.sample(
                    participants,
                    min(winners, len(participants))
                )

                winner_mentions = ", ".join(
                    user.mention
                    for user in winners_selected
                )

                await self.channel.send(
                    f"🎉 **Giveaway beendet!**\n"
                    f"Gewinn: **{self.prize_input.value}**\n"
                    f"Gewinner: {winner_mentions}"
                )

            else:

                await self.channel.send(
                    f"🎁 Das Giveaway für **{self.prize_input.value}** "
                    "ist beendet, aber es gab keine Teilnehmer."
                )

        except Exception as e:
            print(f"GIVEAWAY END ERROR: {e}")


# =========================================================
# OWNER BUTTONS
# =========================================================

class OwnerAnnouncementButton(Button):
    def __init__(self):
        super().__init__(
            label="Ankündigung",
            emoji="📢",
            style=discord.ButtonStyle.primary,
            custom_id="owner_announcement"
        )

    async def callback(self, interaction):

        if not is_owner(interaction.user):
            await send_no_permission(interaction)
            return

        await interaction.response.send_message(
            "📢 Wähle den Kanal für die Ankündigung:",
            view=OwnerChannelSelectView("announcement"),
            ephemeral=True
        )


class OwnerSayButton(Button):
    def __init__(self):
        super().__init__(
            label="Bot Say",
            emoji="💬",
            style=discord.ButtonStyle.primary,
            custom_id="owner_say"
        )

    async def callback(self, interaction):

        if not is_owner(interaction.user):
            await send_no_permission(interaction)
            return

        await interaction.response.send_message(
            "💬 Wähle den Kanal:",
            view=OwnerChannelSelectView("say"),
            ephemeral=True
        )


class OwnerLockButton(Button):
    def __init__(self):
        super().__init__(
            label="Channel Lock",
            emoji="🔒",
            style=discord.ButtonStyle.danger,
            custom_id="owner_lock"
        )

    async def callback(self, interaction):

        if not is_owner(interaction.user):
            await send_no_permission(interaction)
            return

        await interaction.response.send_message(
            "🔒 Wähle den Kanal:",
            view=OwnerChannelSelectView("lock"),
            ephemeral=True
        )


class OwnerUnlockButton(Button):
    def __init__(self):
        super().__init__(
            label="Channel Unlock",
            emoji="🔓",
            style=discord.ButtonStyle.success,
            custom_id="owner_unlock"
        )

    async def callback(self, interaction):

        if not is_owner(interaction.user):
            await send_no_permission(interaction)
            return

        await interaction.response.send_message(
            "🔓 Wähle den Kanal:",
            view=OwnerChannelSelectView("unlock"),
            ephemeral=True
        )


class OwnerGiveawayButton(Button):
    def __init__(self):
        super().__init__(
            label="Giveaway starten",
            emoji="🎁",
            style=discord.ButtonStyle.success,
            custom_id="owner_giveaway"
        )

    async def callback(self, interaction):

        if not is_owner(interaction.user):
            await send_no_permission(interaction)
            return

        await interaction.response.send_message(
            "🎁 Wähle den Kanal für das Giveaway:",
            view=OwnerChannelSelectView("giveaway"),
            ephemeral=True
        )


class OwnerClearButton(Button):
    def __init__(self):
        super().__init__(
            label="Nachrichten löschen",
            emoji="🧹",
            style=discord.ButtonStyle.danger,
            custom_id="owner_clear"
        )

    async def callback(self, interaction):

        if not is_owner(interaction.user):
            await send_no_permission(interaction)
            return

        await interaction.response.send_message(
            "🧹 Wähle den Kanal:",
            view=OwnerChannelSelectView("clear"),
            ephemeral=True
        )


class OwnerStatusButton(Button):
    def __init__(self):
        super().__init__(
            label="Bot Status",
            emoji="📊",
            style=discord.ButtonStyle.secondary,
            custom_id="owner_status"
        )

    async def callback(self, interaction):

        if not is_owner(interaction.user):
            await send_no_permission(interaction)
            return

        latency = round(
            bot.latency * 1000
        )

        uptime = format_duration(
            (
                datetime.now(timezone.utc)
                - bot_started_at
            ).total_seconds()
        )

        embed = discord.Embed(
            title="📊 Bot Status",
            color=discord.Color.green()
        )

        embed.add_field(
            name="🟢 Status",
            value="Online",
            inline=True
        )

        embed.add_field(
            name="📡 Ping",
            value=f"{latency} ms",
            inline=True
        )

        embed.add_field(
            name="⏱️ Uptime",
            value=uptime,
            inline=False
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


class OwnerServerInfoButton(Button):
    def __init__(self):
        super().__init__(
            label="Server Info",
            emoji="🖥️",
            style=discord.ButtonStyle.secondary,
            custom_id="owner_serverinfo"
        )

    async def callback(self, interaction):

        if not is_owner(interaction.user):
            await send_no_permission(interaction)
            return

        guild = interaction.guild

        embed = discord.Embed(
            title="🖥️ Server Info",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="📛 Server",
            value=guild.name,
            inline=True
        )

        embed.add_field(
            name="👥 Mitglieder",
            value=str(guild.member_count),
            inline=True
        )

        embed.add_field(
            name="📁 Kanäle",
            value=str(len(guild.channels)),
            inline=True
        )

        embed.add_field(
            name="🎭 Rollen",
            value=str(len(guild.roles)),
            inline=True
        )

        embed.add_field(
            name="🆔 Server ID",
            value=str(guild.id),
            inline=False
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


class OwnerUserInfoButton(Button):
    def __init__(self):
        super().__init__(
            label="User Info",
            emoji="👤",
            style=discord.ButtonStyle.secondary,
            custom_id="owner_userinfo"
        )

    async def callback(self, interaction):

        if not is_owner(interaction.user):
            await send_no_permission(interaction)
            return

        embed = discord.Embed(
            title="👤 Deine User Info",
            color=discord.Color.blurple()
        )

        embed.set_thumbnail(
            url=interaction.user.display_avatar.url
        )

        embed.add_field(
            name="Name",
            value=interaction.user.display_name,
            inline=True
        )

        embed.add_field(
            name="ID",
            value=str(interaction.user.id),
            inline=True
        )

        embed.add_field(
            name="Account erstellt",
            value=discord.utils.format_dt(
                interaction.user.created_at,
                style="F"
            ),
            inline=False
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


class OwnerRoleButton(Button):
    def __init__(self):
        super().__init__(
            label="Rollen Info",
            emoji="🎭",
            style=discord.ButtonStyle.secondary,
            custom_id="owner_roleinfo"
        )

    async def callback(self, interaction):

        if not is_owner(interaction.user):
            await send_no_permission(interaction)
            return

        roles = [
            role.mention
            for role in interaction.guild.roles
            if role != interaction.guild.default_role
        ]

        text = "\n".join(roles)

        if len(text) > 3900:
            text = text[:3900] + "\n..."

        embed = discord.Embed(
            title="🎭 Server-Rollen",
            description=text or "Keine Rollen vorhanden.",
            color=discord.Color.blurple()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


class OwnerPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(
            OwnerAnnouncementButton()
        )

        self.add_item(
            OwnerSayButton()
        )

        self.add_item(
            OwnerLockButton()
        )

        self.add_item(
            OwnerUnlockButton()
        )

        self.add_item(
            OwnerGiveawayButton()
        )

        self.add_item(
            OwnerClearButton()
        )

        self.add_item(
            OwnerStatusButton()
        )

        self.add_item(
            OwnerServerInfoButton()
        )

        self.add_item(
            OwnerUserInfoButton()
        )

        self.add_item(
            OwnerRoleButton()
        )


def owner_embed():

    embed = discord.Embed(
        title="👑 Owner Panel",
        description=(
            "Hier kannst du den Server und Bot verwalten.\n\n"
            "📢 **Ankündigung** — Embed-Ankündigung senden\n"
            "💬 **Bot Say** — Bot-Nachricht senden\n"
            "🔒 **Channel Lock** — Kanal sperren\n"
            "🔓 **Channel Unlock** — Kanal entsperren\n"
            "🎁 **Giveaway starten** — Giveaway starten\n"
            "🧹 **Nachrichten löschen** — bis zu 100 Nachrichten löschen\n"
            "📊 **Bot Status** — Status und Uptime\n"
            "🖥️ **Server Info** — Serverinformationen\n"
            "👤 **User Info** — eigene Userinformationen\n"
            "🎭 **Rollen Info** — Serverrollen anzeigen"
        ),
        color=discord.Color.gold()
    )

    embed.add_field(
        name="🔐 Berechtigung",
        value=f"Nur <@&{OWNER_ROLE_ID}> darf die Buttons benutzen.",
        inline=False
    )

    embed.add_field(
        name="Panel-ID",
        value=OWNER_PANEL_MARKER,
        inline=False
    )

    return embed


async def send_owner_panel(channel):

    await channel.send(
        embed=owner_embed(),
        view=OwnerPanelView()
    )


# =========================================================
# COMMAND CHECK
# =========================================================

def owner_command():
    async def predicate(ctx):

        if not isinstance(ctx.author, discord.Member):
            return False

        if not is_owner(ctx.author):
            await ctx.send(
                "❌ Du hast nicht genügend Berechtigungen."
            )
            return False

        return True

    return commands.check(predicate)


# =========================================================
# BASIC COMMANDS
# =========================================================

@bot.command(name="ping")
async def ping(ctx):

    await ctx.send(
        f"🏓 Pong! `{round(bot.latency * 1000)} ms`"
    )


@bot.command(name="uptime")
async def uptime(ctx):

    seconds = (
        datetime.now(timezone.utc)
        - bot_started_at
    ).total_seconds()

    await ctx.send(
        f"⏱️ Bot-Uptime: **{format_duration(seconds)}**"
    )


@bot.command(name="botinfo")
async def botinfo(ctx):

    embed = discord.Embed(
        title="🤖 Bot Info",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Name",
        value=bot.user.name if bot.user else "Unbekannt",
        inline=True
    )

    embed.add_field(
        name="ID",
        value=str(bot.user.id) if bot.user else "Unbekannt",
        inline=True
    )

    embed.add_field(
        name="Ping",
        value=f"{round(bot.latency * 1000)} ms",
        inline=True
    )

    await ctx.send(embed=embed)


@bot.command(name="status")
async def status(ctx):

    await ctx.send(
        f"🟢 **Online**\n"
        f"📡 Ping: `{round(bot.latency * 1000)} ms`"
    )


@bot.command(name="membercount")
async def membercount(ctx):

    await ctx.send(
        f"👥 Mitglieder: **{ctx.guild.member_count}**"
    )


@bot.command(name="member")
async def member(ctx):

    await ctx.send(
        f"👤 Du bist **{ctx.author.display_name}**."
    )


# =========================================================
# SERVER COMMANDS
# =========================================================

@bot.command(name="serverinfo")
async def serverinfo(ctx):

    guild = ctx.guild

    embed = discord.Embed(
        title="🖥️ Server Info",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="📛 Name",
        value=guild.name,
        inline=True
    )

    embed.add_field(
        name="👥 Mitglieder",
        value=str(guild.member_count),
        inline=True
    )

    embed.add_field(
        name="📁 Kanäle",
        value=str(len(guild.channels)),
        inline=True
    )

    embed.add_field(
        name="🎭 Rollen",
        value=str(len(guild.roles)),
        inline=True
    )

    embed.add_field(
        name="📅 Erstellt",
        value=discord.utils.format_dt(
            guild.created_at,
            style="F"
        ),
        inline=False
    )

    await ctx.send(embed=embed)


@bot.command(name="serverage")
async def serverage(ctx):

    seconds = (
        datetime.now(timezone.utc)
        - ctx.guild.created_at
    ).total_seconds()

    await ctx.send(
        f"📅 Der Server existiert seit **{format_duration(seconds)}**."
    )


@bot.command(name="rolelist")
async def rolelist(ctx):

    roles = [
        role.mention
        for role in reversed(ctx.guild.roles)
        if role != ctx.guild.default_role
    ]

    if not roles:
        await ctx.send("🎭 Keine Rollen vorhanden.")
        return

    chunks = []
    current = ""

    for role in roles:

        if len(current) + len(role) + 1 > 1900:
            chunks.append(current)
            current = ""

        current += role + "\n"

    if current:
        chunks.append(current)

    for chunk in chunks:
        await ctx.send(
            f"🎭 **Rollen**\n{chunk}"
        )


@bot.command(name="channellist")
async def channellist(ctx):

    channels = []

    for channel in ctx.guild.channels:

        channels.append(
            f"{channel.mention} — `{channel.id}`"
        )

    text = "\n".join(channels)

    if len(text) > 3900:
        text = text[:3900] + "\n..."

    embed = discord.Embed(
        title="📁 Kanäle",
        description=text,
        color=discord.Color.blurple()
    )

    await ctx.send(embed=embed)


@bot.command(name="channelinfo")
async def channelinfo(ctx, channel: discord.TextChannel = None):

    channel = channel or ctx.channel

    embed = discord.Embed(
        title="📁 Channel Info",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Name",
        value=channel.name,
        inline=True
    )

    embed.add_field(
        name="ID",
        value=str(channel.id),
        inline=True
    )

    embed.add_field(
        name="Kategorie",
        value=channel.category.name if channel.category else "Keine",
        inline=True
    )

    await ctx.send(embed=embed)


@bot.command(name="roleinfo")
async def roleinfo(ctx, role: discord.Role):

    embed = discord.Embed(
        title="🎭 Rollen Info",
        color=role.color
    )

    embed.add_field(
        name="Name",
        value=role.name,
        inline=True
    )

    embed.add_field(
        name="ID",
        value=str(role.id),
        inline=True
    )

    embed.add_field(
        name="Mitglieder",
        value=str(len(role.members)),
        inline=True
    )

    await ctx.send(embed=embed)


# =========================================================
# USER COMMANDS
# =========================================================

@bot.command(name="userinfo")
async def userinfo(ctx, member: discord.Member = None):

    member = member or ctx.author

    embed = discord.Embed(
        title="👤 User Info",
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.add_field(
        name="Name",
        value=member.display_name,
        inline=True
    )

    embed.add_field(
        name="ID",
        value=str(member.id),
        inline=True
    )

    embed.add_field(
        name="Account erstellt",
        value=discord.utils.format_dt(
            member.created_at,
            style="F"
        ),
        inline=False
    )

    embed.add_field(
        name="Server beigetreten",
        value=discord.utils.format_dt(
            member.joined_at,
            style="F"
        ) if member.joined_at else "Unbekannt",
        inline=False
    )

    await ctx.send(embed=embed)


@bot.command(name="avatar")
async def avatar(ctx, member: discord.Member = None):

    member = member or ctx.author

    embed = discord.Embed(
        title=f"🖼️ Avatar von {member.display_name}",
        color=discord.Color.blurple()
    )

    embed.set_image(
        url=member.display_avatar.url
    )

    await ctx.send(embed=embed)


@bot.command(name="banner")
async def banner(ctx, member: discord.Member = None):

    member = member or ctx.author

    try:
        user = await bot.fetch_user(
            member.id
        )

        if user.banner is None:
            await ctx.send(
                "❌ Dieser Nutzer hat keinen Banner."
            )
            return

        embed = discord.Embed(
            title=f"🖼️ Banner von {member.display_name}",
            color=discord.Color.blurple()
        )

        embed.set_image(
            url=user.banner.url
        )

        await ctx.send(embed=embed)

    except Exception:
        await ctx.send(
            "❌ Banner konnte nicht geladen werden."
        )


# =========================================================
# COMMUNITY COMMANDS
# =========================================================

@bot.command(name="suggest")
async def suggest(ctx):

    await ctx.send(
        f"💡 Nutze das Community-Panel für Vorschläge "
        f"oder schreibe deinen Vorschlag in {ctx.guild.get_channel(SUGGESTION_CHANNEL_ID).mention if ctx.guild.get_channel(SUGGESTION_CHANNEL_ID) else 'den Vorschlagskanal'}."
    )


@bot.command(name="feedback")
async def feedback(ctx):

    await ctx.send(
        "💬 Nutze das Community-Panel für Feedback."
    )


@bot.command(name="bug")
async def bug(ctx):

    await ctx.send(
        "🐞 Nutze das Community-Panel, um einen Bug zu melden."
    )


@bot.command(name="report")
async def report(ctx, *, text=None):

    if not text:
        await ctx.send(
            f"❌ Nutzung: `{PREFIX}report <Meldung>`"
        )
        return

    channel = get_channel(
        BUG_CHANNEL_ID
    )

    if not isinstance(channel, discord.TextChannel):
        await ctx.send(
            "❌ Meldekanal nicht gefunden."
        )
        return

    embed = discord.Embed(
        title="🚨 Meldung",
        description=text,
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow()
    )

    embed.add_field(
        name="Gemeldet von",
        value=ctx.author.mention,
        inline=False
    )

    await channel.send(
        embed=embed
    )

    await ctx.send(
        "✅ Deine Meldung wurde weitergeleitet."
    )


@bot.command(name="apply")
async def apply(ctx):

    channel = get_channel(
        APPLICATION_CHANNEL_ID
    )

    if isinstance(channel, discord.TextChannel):

        await ctx.send(
            f"📨 Bewerbungen kannst du über das Bewerbungs-Panel "
            f"in {channel.mention} starten."
        )

    else:

        await ctx.send(
            "📨 Nutze das Bewerbungs-Panel."
        )


@bot.command(name="support")
async def support(ctx):

    await ctx.send(
        "🛠️ Bei Problemen kannst du das Team über die Community-Funktionen kontaktieren."
    )


@bot.command(name="supportinfo")
async def supportinfo(ctx):

    await ctx.send(
        "🛠️ **Support**\n"
        "Nutze `?suggest`, `?feedback` oder `?bug` für die entsprechenden Bereiche."
    )


@bot.command(name="rules")
async def rules(ctx):

    await ctx.send(
        "📜 Bitte halte dich an die Serverregeln und behandle andere Mitglieder respektvoll."
    )


@bot.command(name="team")
async def team(ctx):

    await ctx.send(
        "👥 Das Team findest du über die auf dem Server vergebenen Team-Rollen."
    )


@bot.command(name="website")
async def website(ctx):

    await ctx.send(
        "🌐 Eine Website ist aktuell nicht hinterlegt."
    )


@bot.command(name="socials")
async def socials(ctx):

    await ctx.send(
        "📱 Social Media ist aktuell nicht hinterlegt."
    )


@bot.command(name="invite")
async def invite(ctx):

    if bot.user is None:
        return

    permissions = discord.Permissions(
        administrator=True
    )

    url = discord.utils.oauth_url(
        bot.user.id,
        permissions=permissions
    )

    await ctx.send(
        f"🤖 **Bot einladen:**\n{url}"
    )


# =========================================================
# FUN COMMANDS
# =========================================================

@bot.command(name="8ball")
async def eightball(ctx, *, question=None):

    if not question:
        await ctx.send(
            f"❓ Nutzung: `{PREFIX}8ball <Frage>`"
        )
        return

    answers = [
        "Ja.",
        "Nein.",
        "Vielleicht.",
        "Sehr wahrscheinlich.",
        "Eher nicht.",
        "Definitiv.",
        "Das kann niemand sicher sagen.",
        "Frag später nochmal."
    ]

    await ctx.send(
        f"🎱 {random_module.choice(answers)}"
    )


@bot.command(name="coinflip")
async def coinflip(ctx):

    result = random_module.choice(
        ["Kopf", "Zahl"]
    )

    await ctx.send(
        f"🪙 **{result}**"
    )


@bot.command(name="dice")
async def dice(ctx):

    number = random_module.randint(
        1,
        6
    )

    await ctx.send(
        f"🎲 Du hast eine **{number}** gewürfelt."
    )


@bot.command(name="choose")
async def choose(ctx, *, choices=None):

    if not choices:
        await ctx.send(
            f"❌ Nutzung: `{PREFIX}choose A | B | C`"
        )
        return

    options = [
        x.strip()
        for x in choices.split("|")
        if x.strip()
    ]

    if len(options) < 2:
        await ctx.send(
            "❌ Du brauchst mindestens zwei Optionen."
        )
        return

    await ctx.send(
        f"🎯 Ich wähle: **{random_module.choice(options)}**"
    )


@bot.command(name="random")
async def random_number(ctx, minimum: int = None, maximum: int = None):

    if minimum is None or maximum is None:

        await ctx.send(
            f"❌ Nutzung: `{PREFIX}random <min> <max>`"
        )

        return

    if minimum > maximum:
        minimum, maximum = maximum, minimum

    number = random_module.randint(
        minimum,
        maximum
    )

    await ctx.send(
        f"🎲 Zufallszahl: **{number}**"
    )


# =========================================================
# OWNER COMMANDS
# =========================================================

@bot.command(name="ownerpanel", aliases=["owner"])
@owner_command()
async def ownerpanel(ctx):

    await send_owner_panel(
        ctx.channel
    )

    await ctx.send(
        "👑 Owner Panel wurde erstellt."
    )


@bot.command(name="communitypanel")
@owner_command()
async def communitypanel(ctx):

    await ctx.send(
        embed=community_embed(),
        view=CommunityPanelView()
    )


@bot.command(name="panel")
@owner_command()
async def panel(ctx):

    await ctx.send(
        "📋 Verfügbare Panels:\n"
        f"• `{PREFIX}ownerpanel` — Owner Panel\n"
        f"• `{PREFIX}communitypanel` — Community Panel"
    )


# =========================================================
# HELP
# =========================================================

@bot.command(name="help")
async def help_command(ctx):

    embed = discord.Embed(
        title="📚 Bot Commands",
        description=f"Prefix: `{PREFIX}`",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🤖 Bot",
        value=(
            f"`{PREFIX}ping`\n"
            f"`{PREFIX}uptime`\n"
            f"`{PREFIX}botinfo`\n"
            f"`{PREFIX}status`\n"
            f"`{PREFIX}invite`"
        ),
        inline=True
    )

    embed.add_field(
        name="🖥️ Server",
        value=(
            f"`{PREFIX}serverinfo`\n"
            f"`{PREFIX}serverage`\n"
            f"`{PREFIX}membercount`\n"
            f"`{PREFIX}rolelist`\n"
            f"`{PREFIX}channellist`\n"
            f"`{PREFIX}channelinfo`\n"
            f"`{PREFIX}roleinfo`"
        ),
        inline=True
    )

    embed.add_field(
        name="👤 User",
        value=(
            f"`{PREFIX}userinfo`\n"
            f"`{PREFIX}member`\n"
            f"`{PREFIX}avatar`\n"
            f"`{PREFIX}banner`"
        ),
        inline=True
    )

    embed.add_field(
        name="🌐 Community",
        value=(
            f"`{PREFIX}suggest`\n"
            f"`{PREFIX}feedback`\n"
            f"`{PREFIX}bug`\n"
            f"`{PREFIX}report`\n"
            f"`{PREFIX}apply`\n"
            f"`{PREFIX}support`"
        ),
        inline=True
    )

    embed.add_field(
        name="🎮 Fun",
        value=(
            f"`{PREFIX}8ball`\n"
            f"`{PREFIX}coinflip`\n"
            f"`{PREFIX}dice`\n"
            f"`{PREFIX}choose`\n"
            f"`{PREFIX}random`"
        ),
        inline=True
    )

    embed.add_field(
        name="👑 Owner",
        value=(
            f"`{PREFIX}ownerpanel`\n"
            f"`{PREFIX}owner`\n"
            f"`{PREFIX}communitypanel`"
        ),
        inline=True
    )

    await ctx.send(embed=embed)


# =========================================================
# ERROR HANDLER
# =========================================================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(
        error,
        commands.CommandNotFound
    ):
        return

    if isinstance(
        error,
        commands.MissingRequiredArgument
    ):
        await ctx.send(
            f"❌ Es fehlt ein Argument. Nutze `{PREFIX}help`."
        )
        return

    if isinstance(
        error,
        commands.MemberNotFound
    ):
        await ctx.send(
            "❌ Dieser Benutzer wurde nicht gefunden."
        )
        return

    if isinstance(
        error,
        commands.RoleNotFound
    ):
        await ctx.send(
            "❌ Diese Rolle wurde nicht gefunden."
        )
        return

    if isinstance(
        error,
        commands.MissingPermissions
    ):
        await ctx.send(
            "❌ Du hast nicht genügend Berechtigungen."
        )
        return

    if isinstance(
        error,
        commands.CheckFailure
    ):
        return

    print(
        f"COMMAND ERROR in {ctx.command}: "
        f"{type(error).__name__}: {error}"
    )


# =========================================================
# MESSAGE EVENT
# =========================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    await bot.process_commands(message)


# =========================================================
# READY / STARTUP
# =========================================================

startup_done = False


@bot.event
async def on_ready():

    global startup_done

    print("=" * 60)
    print(f"BOT ONLINE: {bot.user}")
    print(f"PREFIX: {PREFIX}")
    print("=" * 60)

    if startup_done:
        return

    startup_done = True

    guild = bot.get_guild(
        GUILD_ID
    )

    if guild is None:
        print("❌ GUILD NICHT GEFUNDEN")
        return

    print(
        f"✅ Server gefunden: {guild.name}"
    )

    # -----------------------------------------------------
    # Nametag Panel
    # WICHTIG:
    # Hier werden KEINE Nicknames verändert.
    # -----------------------------------------------------

    nametag_channel = guild.get_channel(
        NAMETAG_CHANNEL_ID
    )

    if isinstance(
        nametag_channel,
        discord.TextChannel
    ):

        await replace_panel(
            nametag_channel,
            NAMETAG_PANEL_MARKER,
            nametag_embed(),
            NametagView()
        )

    # -----------------------------------------------------
    # License Panel
    # -----------------------------------------------------

    await refresh_license_panel()

    # -----------------------------------------------------
    # Application Panel
    # -----------------------------------------------------

    application_channel = guild.get_channel(
        APPLICATION_CHANNEL_ID
    )

    if isinstance(
        application_channel,
        discord.TextChannel
    ):

        await replace_panel(
            application_channel,
            APPLICATION_PANEL_MARKER,
            application_embed(),
            ApplicationView()
        )

    # -----------------------------------------------------
    # Developer Task Panel
    # -----------------------------------------------------

    developer_task_channel = guild.get_channel(
        DEVELOPER_TASK_CHANNEL_ID
    )

    if isinstance(
        developer_task_channel,
        discord.TextChannel
    ):

        await replace_panel(
            developer_task_channel,
            DEV_TASK_PANEL_MARKER,
            developer_task_embed(),
            DeveloperTaskView()
        )

    # -----------------------------------------------------
    # Developer Shift Panel
    # -----------------------------------------------------

    developer_shift_channel = guild.get_channel(
        DEVELOPER_SHIFT_CHANNEL_ID
    )

    if isinstance(
        developer_shift_channel,
        discord.TextChannel
    ):

        await replace_panel(
            developer_shift_channel,
            DEV_SHIFT_PANEL_MARKER,
            developer_shift_embed(),
            DeveloperShiftView()
        )

    print("✅ Panels aktualisiert")
    print("❌ Emoji Quiz: ENTFERNT")
    print("❌ Support Voice System: ENTFERNT")
    print("✅ Owner Panel Berechtigungsprüfung aktiv")
    print("✅ Suggestion Voting mit Stimmenwechsel aktiv")


# =========================================================
# SETUP HOOK
# =========================================================

async def setup_hook():

    # Persistent Views
    bot.add_view(
        NametagView()
    )

    bot.add_view(
        LicensePlateView()
    )

    bot.add_view(
        ApplicationView()
    )

    bot.add_view(
        DeveloperTaskView()
    )

    bot.add_view(
        DeveloperShiftView()
    )

    bot.add_view(
        CommunityPanelView()
    )

    bot.add_view(
        SuggestionView()
    )

    bot.add_view(
        OwnerPanelView()
    )

    # Keine Slash Commands.
    # Der Bot arbeitet ausschließlich mit ? Commands.

    print("✅ Persistent Views geladen")


bot.setup_hook = setup_hook


# =========================================================
# START
# =========================================================

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN wurde nicht gefunden."
    )


bot.run(TOKEN)
