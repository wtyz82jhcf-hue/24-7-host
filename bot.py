import os
import re
import json
import time
import random
import asyncio
from datetime import datetime

import discord
from discord.ext import commands


# ============================================================
# KONFIGURATION
# ============================================================

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

NUMBER_GAME_CHANNEL_ID = 1556308645942136872

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
EMOJI_QUIZ_PANEL_MARKER = "RLP_EMOJI_QUIZ_PANEL"
NUMBER_GAME_PANEL_MARKER = "RLP_NUMBER_GAME_PANEL"

PREFIX = "?"

BOT_START_TIME = time.time()

STATUS_TEXTS = [
    "🚔 RLP | RP-System",
    "🌐 Für eine starke & aktive Community",
    "✨ Professionell • Innovativ • Einzigartig",
    "💻 Developed by RyZe 🚀"
]


# ============================================================
# INTENTS / BOT
# ============================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None
)


# ============================================================
# DATEN
# ============================================================

DEFAULT_DATA = {
    "license_plates": {},
    "applications": {},
    "developer_tasks": {},
    "active_developer_shifts": {},
    "suggestions": {},
    "feedback": [],
    "emoji_quiz": {},
    "number_game": {
        "current_number": 1,
        "last_user_id": None,
        "wrong_attempts": {},
        "last_easter_egg": 0,
        "last_message_id": None
    }
}


def load_data():
    if not os.path.exists(DATA_FILE):
        return json.loads(json.dumps(DEFAULT_DATA))

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
    except (json.JSONDecodeError, OSError):
        loaded = {}

    data = json.loads(json.dumps(DEFAULT_DATA))

    if isinstance(loaded, dict):
        for key, value in loaded.items():
            if key in data:
                data[key] = value

    if not isinstance(data.get("license_plates"), dict):
        data["license_plates"] = {}

    if not isinstance(data.get("applications"), dict):
        data["applications"] = {}

    if not isinstance(data.get("developer_tasks"), dict):
        data["developer_tasks"] = {}

    if not isinstance(data.get("active_developer_shifts"), dict):
        data["active_developer_shifts"] = {}

    if not isinstance(data.get("suggestions"), dict):
        data["suggestions"] = {}

    if not isinstance(data.get("feedback"), list):
        data["feedback"] = []

    if not isinstance(data.get("emoji_quiz"), dict):
        data["emoji_quiz"] = {}

    if not isinstance(data.get("number_game"), dict):
        data["number_game"] = json.loads(
            json.dumps(DEFAULT_DATA["number_game"])
        )

    number_game = data["number_game"]

    if not isinstance(number_game.get("current_number"), int):
        number_game["current_number"] = 1

    if not isinstance(number_game.get("wrong_attempts"), dict):
        number_game["wrong_attempts"] = {}

    if "last_user_id" not in number_game:
        number_game["last_user_id"] = None

    if "last_easter_egg" not in number_game:
        number_game["last_easter_egg"] = 0

    if "last_message_id" not in number_game:
        number_game["last_message_id"] = None

    return data


data = load_data()


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=4
            )
    except OSError as e:
        print(f"[DATA] Fehler beim Speichern: {e}")


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def get_guild():
    return bot.get_guild(GUILD_ID)


def get_member_name(user_id):
    guild = get_guild()

    if guild:
        member = guild.get_member(int(user_id))
        if member:
            return member.display_name

    return f"User {user_id}"


async def delete_after_seconds(message, seconds=4):
    try:
        await asyncio.sleep(seconds)
        await message.delete()
    except (
        discord.NotFound,
        discord.Forbidden,
        discord.HTTPException
    ):
        pass


async def send_temp_message(channel, content=None, embed=None, seconds=4):
    try:
        message = await channel.send(
            content=content,
            embed=embed
        )
        asyncio.create_task(
            delete_after_seconds(message, seconds)
        )
        return message
    except discord.HTTPException:
        return None


def owner_check(member):
    return (
        member.guild_permissions.administrator
        or any(role.id == OWNER_ROLE_ID for role in member.roles)
    )


def normalize_text(text):
    return re.sub(
        r"\s+",
        " ",
        text.strip().lower()
    )


async def find_panel(channel, marker):
    if channel is None:
        return None

    try:
        async for message in channel.history(limit=100):
            if message.author.id != bot.user.id:
                continue

            if not message.embeds:
                continue

            for embed in message.embeds:
                footer = embed.footer.text or ""

                if marker in footer:
                    return message

    except discord.HTTPException:
        pass

    return None


async def update_or_create_panel(
    channel,
    marker,
    embed,
    view=None
):
    if channel is None:
        return None

    existing = await find_panel(channel, marker)

    if existing:
        try:
            await existing.edit(
                embed=embed,
                view=view
            )
            return existing
        except discord.HTTPException:
            pass

    try:
        return await channel.send(
            embed=embed,
            view=view
        )
    except discord.HTTPException:
        return None


# ============================================================
# NAMETAG SYSTEM
# ============================================================

async def remove_nametag(member):
    if member.nick and member.nick.startswith(NAMETAG):
        new_nick = member.nick[len(NAMETAG):].strip()

        try:
            await member.edit(
                nick=new_nick or None,
                reason="RLP Nametag entfernt"
            )
        except discord.HTTPException:
            pass


class NametagSet(discord.ui.Modal, title="Nametag setzen"):
    name = discord.ui.TextInput(
        label="Dein Name",
        placeholder="z. B. Max",
        max_length=32
    )

    async def on_submit(self, interaction: discord.Interaction):
        member = interaction.user

        new_name = self.name.value.strip()

        if not new_name:
            await interaction.response.send_message(
                "❌ Bitte gib einen Namen ein.",
                ephemeral=True
            )
            return

        if new_name.startswith(NAMETAG):
            new_name = new_name[len(NAMETAG):].strip()

        final_name = NAMETAG + new_name

        try:
            await member.edit(
                nick=final_name,
                reason="RLP Nametag gesetzt"
            )

            await interaction.response.send_message(
                f"✅ Dein Nametag wurde auf `{final_name}` gesetzt.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich kann deinen Nicknamen nicht ändern.",
                ephemeral=True
            )


class NametagRemove(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Nametag entfernen",
            emoji="🗑️",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_nametag_remove"
        )

    async def callback(self, interaction: discord.Interaction):
        await remove_nametag(interaction.user)

        await interaction.response.send_message(
            "✅ Dein Nametag wurde entfernt.",
            ephemeral=True
        )


class NametagView(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Nametag anzeigen",
            emoji="👤",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_nametag_view"
        )

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user

        if member.nick:
            name = member.nick
        else:
            name = member.display_name

        await interaction.response.send_message(
            f"👤 Dein aktueller Name: `{name}`",
            ephemeral=True
        )


class NametagSetButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Nametag setzen",
            emoji="✏️",
            style=discord.ButtonStyle.success,
            custom_id="rlp_nametag_set"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(NametagSet())


class NametagPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(NametagSetButton())
        self.add_item(NametagRemove())
        self.add_item(NametagView())


def nametag_embed():
    embed = discord.Embed(
        title="🏷️ RLP Nametag-System",
        description=(
            "Hier kannst du deinen persönlichen RLP-Nametag verwalten.\n\n"
            "✏️ **Nametag setzen**\n"
            "Setze deinen gewünschten Namen.\n\n"
            "🗑️ **Nametag entfernen**\n"
            "Entfernt den RLP-Nametag.\n\n"
            "👤 **Nametag anzeigen**\n"
            "Zeigt deinen aktuellen Namen."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(text=NAMETAG_PANEL_MARKER)

    return embed


@bot.command(name="nametagpanel")
@commands.has_permissions(administrator=True)
async def nametag_panel(ctx):
    channel = bot.get_channel(NAMETAG_CHANNEL_ID)

    if channel is None:
        await ctx.send("❌ Nametag-Kanal wurde nicht gefunden.")
        return

    await update_or_create_panel(
        channel,
        NAMETAG_PANEL_MARKER,
        nametag_embed(),
        NametagPanelView()
    )

    await ctx.send("✅ Nametag-Panel aktualisiert.")


# ============================================================
# KENNZEICHEN SYSTEM
# ============================================================

def normalize_plate_number(value):
    """
    Macht aus:
    01   -> 1
    001  -> 1
    0001 -> 1

    Dadurch zählen RLP 01 und RLP 001
    als dieselbe Nummer.
    """

    value = str(value).strip()

    if not value.isdigit():
        return None

    number = int(value)

    if number < 1:
        return None

    return number


def format_plate(number):
    number = normalize_plate_number(number)

    if number is None:
        return None

    return f"RLP {number:02d}"


def plate_number_is_taken(number, ignore_user_id=None):
    number = normalize_plate_number(number)

    if number is None:
        return True

    for user_id, plate_data in data["license_plates"].items():
        if ignore_user_id is not None and str(user_id) == str(ignore_user_id):
            continue

        if isinstance(plate_data, dict):
            stored_number = plate_data.get("number")

            if normalize_plate_number(stored_number) == number:
                return True

        else:
            # Falls alte Daten nur als String gespeichert wurden
            old_number = str(plate_data)

            match = re.search(
                r"(\d+)",
                old_number
            )

            if match:
                if normalize_plate_number(match.group(1)) == number:
                    return True

    return False


def get_user_plate(user_id):
    plate_data = data["license_plates"].get(str(user_id))

    if not plate_data:
        return None

    if isinstance(plate_data, dict):
        number = normalize_plate_number(
            plate_data.get("number")
        )

        if number is None:
            return None

        return format_plate(number)

    match = re.search(
        r"(\d+)",
        str(plate_data)
    )

    if not match:
        return None

    number = normalize_plate_number(match.group(1))

    if number is None:
        return None

    return format_plate(number)


def get_all_plates_text():
    plates = []

    for user_id, plate_data in data["license_plates"].items():

        number = None

        if isinstance(plate_data, dict):
            number = normalize_plate_number(
                plate_data.get("number")
            )
        else:
            match = re.search(
                r"(\d+)",
                str(plate_data)
            )

            if match:
                number = normalize_plate_number(
                    match.group(1)
                )

        if number is None:
            continue

        plate = format_plate(number)
        owner = get_member_name(user_id)

        plates.append(
            (
                number,
                plate,
                owner
            )
        )

    plates.sort(key=lambda x: x[0])

    if not plates:
        return "Noch keine Kennzeichen vergeben."

    lines = []

    for _, plate, owner in plates:
        lines.append(
            f"`{plate}` — **{owner}**"
        )

    result = "\n".join(lines)

    # Discord Embed Description Limit
    if len(result) > 3900:
        result = result[:3850]
        result += "\n… weitere Kennzeichen vorhanden."

    return result


class PlateModal(discord.ui.Modal, title="Kennzeichen beantragen"):
    number = discord.ui.TextInput(
        label="Kennzeichennummer",
        placeholder="z. B. 01, 02, 123",
        min_length=1,
        max_length=6
    )

    async def on_submit(self, interaction: discord.Interaction):

        number = normalize_plate_number(
            self.number.value
        )

        if number is None:
            await interaction.response.send_message(
                "❌ Bitte gib eine gültige positive Nummer ein.",
                ephemeral=True
            )
            return

        # Eindeutigkeitsprüfung
        if plate_number_is_taken(number):
            existing_plate = format_plate(number)

            await interaction.response.send_message(
                f"❌ Das Kennzeichen `{existing_plate}` ist bereits vergeben.\n"
                f"`RLP 01` und `RLP 001` zählen dabei als dieselbe Nummer.",
                ephemeral=True
            )
            return

        user_id = str(interaction.user.id)

        # Vorhandenes Kennzeichen dieses Users ersetzen
        data["license_plates"][user_id] = {
            "number": number,
            "plate": format_plate(number),
            "user_id": interaction.user.id,
            "username": interaction.user.display_name,
            "created_at": int(time.time())
        }

        save_data()

        await refresh_license_panel()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen `{format_plate(number)}` wurde vergeben.",
            ephemeral=True
        )


class PlateButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Kennzeichen beantragen",
            emoji="🚘",
            style=discord.ButtonStyle.success,
            custom_id="rlp_plate_request"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(PlateModal())


class PlateRemoveButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Kennzeichen entfernen",
            emoji="🗑️",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_plate_remove"
        )

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)

        if user_id not in data["license_plates"]:
            await interaction.response.send_message(
                "❌ Du hast kein Kennzeichen.",
                ephemeral=True
            )
            return

        old_plate = get_user_plate(user_id)

        del data["license_plates"][user_id]
        save_data()

        await refresh_license_panel()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen `{old_plate}` wurde entfernt.",
            ephemeral=True
        )


class PlateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(PlateButton())
        self.add_item(PlateRemoveButton())


def license_embed():
    embed = discord.Embed(
        title="🚘 RLP Kennzeichen-System",
        description=(
            "Hier kannst du ein Kennzeichen beantragen.\n\n"
            "**Regeln:**\n"
            "• Jede Nummer darf nur einmal vergeben werden.\n"
            "• `RLP 01` und `RLP 001` gelten als dieselbe Nummer.\n"
            "• Bereits vergebene Nummern können nicht erneut verwendet werden.\n"
            "• Deine Kennzeichen-Daten bleiben auch nach einem Bot-Neustart erhalten."
        ),
        color=discord.Color.blue()
    )

    embed.add_field(
        name="🚘 Aktuell vergebene Kennzeichen",
        value=get_all_plates_text(),
        inline=False
    )

    embed.set_footer(text=LICENSE_PANEL_MARKER)

    return embed


async def refresh_license_panel():
    channel = bot.get_channel(
        LICENSE_PLATE_CHANNEL_ID
    )

    if channel is None:
        return

    await update_or_create_panel(
        channel,
        LICENSE_PANEL_MARKER,
        license_embed(),
        PlateView()
    )


@bot.command(name="licensepanel")
@commands.has_permissions(administrator=True)
async def license_panel(ctx):
    await refresh_license_panel()

    await ctx.send(
        "✅ Kennzeichen-Panel aktualisiert."
    )


# ============================================================
# BEWERBUNGEN
# ============================================================

class ApplicationModal(discord.ui.Modal, title="Bewerbung"):
    name = discord.ui.TextInput(
        label="Name",
        max_length=50
    )

    age = discord.ui.TextInput(
        label="Alter",
        max_length=3
    )

    experience = discord.ui.TextInput(
        label="RP-Erfahrung",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    motivation = discord.ui.TextInput(
        label="Warum möchtest du beitreten?",
        style=discord.TextStyle.paragraph,
        max_length=1500
    )

    async def on_submit(self, interaction: discord.Interaction):

        channel = bot.get_channel(
            REVIEW_CHANNEL_ID
        )

        if channel is None:
            await interaction.response.send_message(
                "❌ Bewerbungs-Kanal wurde nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📨 Neue Bewerbung",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )

        embed.add_field(
            name="👤 Bewerber",
            value=interaction.user.mention,
            inline=False
        )

        embed.add_field(
            name="Name",
            value=self.name.value,
            inline=True
        )

        embed.add_field(
            name="Alter",
            value=self.age.value,
            inline=True
        )

        embed.add_field(
            name="RP-Erfahrung",
            value=self.experience.value,
            inline=False
        )

        embed.add_field(
            name="Motivation",
            value=self.motivation.value,
            inline=False
        )

        await channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Deine Bewerbung wurde erfolgreich eingereicht.",
            ephemeral=True
        )


class ApplicationButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Bewerben",
            emoji="📨",
            style=discord.ButtonStyle.success,
            custom_id="rlp_application_button"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            ApplicationModal()
        )


class ApplicationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ApplicationButton())


def application_embed():
    embed = discord.Embed(
        title="📨 RLP Bewerbung",
        description=(
            "Du möchtest Teil unseres Teams werden?\n\n"
            "Klicke auf den Button und fülle die Bewerbung aus."
        ),
        color=discord.Color.green()
    )

    embed.set_footer(
        text=APPLICATION_PANEL_MARKER
    )

    return embed


async def refresh_application_panel():
    channel = bot.get_channel(
        APPLICATION_CHANNEL_ID
    )

    if channel:
        await update_or_create_panel(
            channel,
            APPLICATION_PANEL_MARKER,
            application_embed(),
            ApplicationView()
        )


@bot.command(name="bewerbungpanel")
@commands.has_permissions(administrator=True)
async def application_panel(ctx):
    await refresh_application_panel()
    await ctx.send("✅ Bewerbungs-Panel aktualisiert.")


# ============================================================
# DEVELOPER TASKS
# ============================================================

class DeveloperTaskModal(
    discord.ui.Modal,
    title="Developer-Aufgabe"
):
    task = discord.ui.TextInput(
        label="Aufgabe",
        style=discord.TextStyle.paragraph,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):

        task_id = str(
            int(time.time() * 1000)
        )

        data["developer_tasks"][task_id] = {
            "task": self.task.value,
            "author_id": interaction.user.id,
            "created_at": int(time.time()),
            "completed": False
        }

        save_data()

        channel = bot.get_channel(
            DEVELOPER_TASK_CHANNEL_ID
        )

        if channel:
            embed = discord.Embed(
                title="💻 Neue Developer-Aufgabe",
                description=self.task.value,
                color=discord.Color.blurple()
            )

            embed.add_field(
                name="Erstellt von",
                value=interaction.user.mention
            )

            await channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Developer-Aufgabe wurde erstellt.",
            ephemeral=True
        )


class DeveloperTaskButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Aufgabe erstellen",
            emoji="💻",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_dev_task_button"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            DeveloperTaskModal()
        )


class DeveloperTaskView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(DeveloperTaskButton())


def developer_task_embed():
    embed = discord.Embed(
        title="💻 Developer-System",
        description=(
            "Hier können neue Developer-Aufgaben erstellt werden."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=DEV_TASK_PANEL_MARKER
    )

    return embed


async def refresh_developer_task_panel():
    channel = bot.get_channel(
        DEVELOPER_TASK_CHANNEL_ID
    )

    if channel:
        await update_or_create_panel(
            channel,
            DEV_TASK_PANEL_MARKER,
            developer_task_embed(),
            DeveloperTaskView()
        )


@bot.command(name="devtaskpanel")
@commands.has_permissions(administrator=True)
async def developer_task_panel(ctx):
    await refresh_developer_task_panel()
    await ctx.send("✅ Developer-Task-Panel aktualisiert.")


# ============================================================
# DEVELOPER SCHICHT
# ============================================================

def has_shift_permission(member):
    return (
        member.guild_permissions.administrator
        or any(
            role.id == SHIFT_PERMISSION_ROLE_ID
            for role in member.roles
        )
    )


class ShiftStart(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Schicht starten",
            emoji="🟢",
            style=discord.ButtonStyle.success,
            custom_id="rlp_shift_start"
        )

    async def callback(self, interaction: discord.Interaction):

        if not has_shift_permission(interaction.user):
            await interaction.response.send_message(
                "❌ Du darfst keine Developer-Schicht starten.",
                ephemeral=True
            )
            return

        user_id = str(interaction.user.id)

        if user_id in data["active_developer_shifts"]:
            await interaction.response.send_message(
                "⚠️ Du bist bereits im Dienst.",
                ephemeral=True
            )
            return

        data["active_developer_shifts"][user_id] = {
            "started": time.time()
        }

        save_data()

        await shift_log(
            interaction.user,
            "🟢 Schicht gestartet"
        )

        await interaction.response.send_message(
            "🟢 Deine Developer-Schicht wurde gestartet.",
            ephemeral=True
        )


class ShiftEnd(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Schicht beenden",
            emoji="🔴",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_shift_end"
        )

    async def callback(self, interaction: discord.Interaction):

        if not has_shift_permission(interaction.user):
            await interaction.response.send_message(
                "❌ Du darfst keine Developer-Schicht beenden.",
                ephemeral=True
            )
            return

        user_id = str(interaction.user.id)

        shift = data["active_developer_shifts"].get(user_id)

        if not shift:
            await interaction.response.send_message(
                "⚠️ Du hast keine aktive Schicht.",
                ephemeral=True
            )
            return

        duration = int(
            time.time() - shift["started"]
        )

        del data["active_developer_shifts"][user_id]

        save_data()

        minutes = duration // 60
        seconds = duration % 60

        await shift_log(
            interaction.user,
            f"🔴 Schicht beendet — {minutes}m {seconds}s"
        )

        await interaction.response.send_message(
            f"🔴 Schicht beendet.\n"
            f"⏱️ Dauer: `{minutes}m {seconds}s`",
            ephemeral=True
        )


class ShiftView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(ShiftStart())
        self.add_item(ShiftEnd())


async def shift_log(member, text):
    channel = bot.get_channel(
        SHIFT_LOG_CHANNEL_ID
    )

    if channel is None:
        return

    embed = discord.Embed(
        title="🛠️ Developer-Schicht",
        description=text,
        color=discord.Color.blurple(),
        timestamp=datetime.now()
    )

    embed.add_field(
        name="Developer",
        value=member.mention
    )

    await channel.send(embed=embed)


def shift_embed():
    active = data["active_developer_shifts"]

    lines = []

    for user_id, shift in active.items():
        duration = int(
            time.time() - shift["started"]
        )

        minutes = duration // 60
        seconds = duration % 60

        lines.append(
            f"🟢 **{get_member_name(user_id)}** "
            f"— `{minutes}m {seconds}s`"
        )

    if not lines:
        active_text = "Aktuell ist niemand im Developer-Dienst."
    else:
        active_text = "\n".join(lines)

    embed = discord.Embed(
        title="🛠️ Developer-Schichtsystem",
        description=(
            "Verwalte hier deine Developer-Schicht.\n\n"
            f"{active_text}"
        ),
        color=discord.Color.green()
    )

    embed.set_footer(
        text=DEV_SHIFT_PANEL_MARKER
    )

    return embed


async def refresh_shift_panel():
    channel = bot.get_channel(
        DEVELOPER_SHIFT_CHANNEL_ID
    )

    if channel:
        await update_or_create_panel(
            channel,
            DEV_SHIFT_PANEL_MARKER,
            shift_embed(),
            ShiftView()
        )


@bot.command(name="devshiftpanel")
@commands.has_permissions(administrator=True)
async def developer_shift_panel(ctx):
    await refresh_shift_panel()
    await ctx.send("✅ Developer-Schicht-Panel aktualisiert.")


# ============================================================
# COMMUNITY
# ============================================================

class SuggestionModal(
    discord.ui.Modal,
    title="Vorschlag einreichen"
):
    suggestion = discord.ui.TextInput(
        label="Dein Vorschlag",
        style=discord.TextStyle.paragraph,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):

        suggestion_id = str(
            int(time.time() * 1000)
        )

        data["suggestions"][suggestion_id] = {
            "author_id": interaction.user.id,
            "text": self.suggestion.value,
            "for": [],
            "against": [],
            "accepted": False,
            "rejected": False,
            "created_at": int(time.time())
        }

        save_data()

        channel = bot.get_channel(
            SUGGESTION_CHANNEL_ID
        )

        if channel:
            await channel.send(
                embed=suggestion_embed(suggestion_id),
                view=SuggestionView(suggestion_id)
            )

        await interaction.response.send_message(
            "✅ Dein Vorschlag wurde eingereicht.",
            ephemeral=True
        )


class FeedbackModal(
    discord.ui.Modal,
    title="Feedback geben"
):
    feedback = discord.ui.TextInput(
        label="Feedback",
        style=discord.TextStyle.paragraph,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):

        data["feedback"].append({
            "user_id": interaction.user.id,
            "text": self.feedback.value,
            "created_at": int(time.time())
        })

        save_data()

        channel = bot.get_channel(
            FEEDBACK_CHANNEL_ID
        )

        if channel:
            embed = discord.Embed(
                title="💬 Neues Feedback",
                description=self.feedback.value,
                color=discord.Color.gold()
            )

            embed.add_field(
                name="Von",
                value=interaction.user.mention
            )

            await channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Vielen Dank für dein Feedback!",
            ephemeral=True
        )


class CommunitySuggestion(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Vorschlag",
            emoji="💡",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_community_suggestion"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            SuggestionModal()
        )


class CommunityFeedback(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Feedback",
            emoji="💬",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_community_feedback"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            FeedbackModal()
        )


class CommunityView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(CommunitySuggestion())
        self.add_item(CommunityFeedback())


def community_embed():
    embed = discord.Embed(
        title="🌐 Community",
        description=(
            "Hier kannst du dich aktiv an der Community beteiligen.\n\n"
            "💡 **Vorschlag**\n"
            "Reiche einen neuen Vorschlag ein.\n\n"
            "💬 **Feedback**\n"
            "Sende uns dein Feedback."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=COMMUNITY_PANEL_MARKER
    )

    return embed


@bot.command(name="communitypanel")
async def community_panel(ctx):
    await update_or_create_panel(
        ctx.channel,
        COMMUNITY_PANEL_MARKER,
        community_embed(),
        CommunityView()
    )

    await ctx.send(
        "✅ Community-Panel wurde in diesem Kanal aktualisiert."
    )


def suggestion_embed(suggestion_id):
    suggestion = data["suggestions"].get(
        suggestion_id
    )

    if not suggestion:
        return discord.Embed(
            title="❌ Vorschlag nicht gefunden."
        )

    author_id = suggestion["author_id"]

    accepted = suggestion.get("accepted", False)
    rejected = suggestion.get("rejected", False)

    if accepted:
        status = "🟢 Angenommen"
    elif rejected:
        status = "🔴 Abgelehnt"
    else:
        status = "🟡 Offen"

    embed = discord.Embed(
        title="💡 Community-Vorschlag",
        description=suggestion["text"],
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👤 Autor",
        value=f"<@{author_id}>",
        inline=True
    )

    embed.add_field(
        name="📊 Status",
        value=status,
        inline=True
    )

    embed.add_field(
        name="👍 Dafür",
        value=str(
            len(suggestion.get("for", []))
        ),
        inline=True
    )

    embed.add_field(
        name="👎 Dagegen",
        value=str(
            len(suggestion.get("against", []))
        ),
        inline=True
    )

    return embed


async def update_suggestion(
    interaction,
    suggestion_id
):
    suggestion = data["suggestions"].get(
        suggestion_id
    )

    if not suggestion:
        return

    await interaction.message.edit(
        embed=suggestion_embed(suggestion_id),
        view=SuggestionView(suggestion_id)
    )


class SuggestionFor(discord.ui.Button):
    def __init__(self, suggestion_id):
        super().__init__(
            label="Dafür",
            emoji="👍",
            style=discord.ButtonStyle.success,
            custom_id=f"rlp_suggestion_for_{suggestion_id}"
        )

        self.suggestion_id = suggestion_id

    async def callback(self, interaction):
        suggestion = data["suggestions"].get(
            self.suggestion_id
        )

        if not suggestion:
            await interaction.response.send_message(
                "❌ Vorschlag nicht gefunden.",
                ephemeral=True
            )
            return

        user_id = interaction.user.id

        if user_id in suggestion["against"]:
            suggestion["against"].remove(user_id)

        if user_id not in suggestion["for"]:
            suggestion["for"].append(user_id)

        save_data()

        await update_suggestion(
            interaction,
            self.suggestion_id
        )

        await interaction.response.send_message(
            "👍 Stimme gespeichert.",
            ephemeral=True
        )


class SuggestionAgainst(discord.ui.Button):
    def __init__(self, suggestion_id):
        super().__init__(
            label="Dagegen",
            emoji="👎",
            style=discord.ButtonStyle.danger,
            custom_id=f"rlp_suggestion_against_{suggestion_id}"
        )

        self.suggestion_id = suggestion_id

    async def callback(self, interaction):
        suggestion = data["suggestions"].get(
            self.suggestion_id
        )

        if not suggestion:
            await interaction.response.send_message(
                "❌ Vorschlag nicht gefunden.",
                ephemeral=True
            )
            return

        user_id = interaction.user.id

        if user_id in suggestion["for"]:
            suggestion["for"].remove(user_id)

        if user_id not in suggestion["against"]:
            suggestion["against"].append(user_id)

        save_data()

        await update_suggestion(
            interaction,
            self.suggestion_id
        )

        await interaction.response.send_message(
            "👎 Stimme gespeichert.",
            ephemeral=True
        )


class SuggestionAccept(discord.ui.Button):
    def __init__(self, suggestion_id):
        super().__init__(
            label="Annehmen",
            emoji="✅",
            style=discord.ButtonStyle.success,
            custom_id=f"rlp_suggestion_accept_{suggestion_id}"
        )

        self.suggestion_id = suggestion_id

    async def callback(self, interaction):

        if not (
            interaction.user.guild_permissions.administrator
            or any(
                role.id == SUGGESTION_REVIEW_ROLE_ID
                for role in interaction.user.roles
            )
        ):
            await interaction.response.send_message(
                "❌ Du darfst Vorschläge nicht verwalten.",
                ephemeral=True
            )
            return

        suggestion = data["suggestions"].get(
            self.suggestion_id
        )

        if not suggestion:
            await interaction.response.send_message(
                "❌ Vorschlag nicht gefunden.",
                ephemeral=True
            )
            return

        suggestion["accepted"] = True
        suggestion["rejected"] = False

        save_data()

        await update_suggestion(
            interaction,
            self.suggestion_id
        )

        await interaction.response.send_message(
            "✅ Vorschlag angenommen.",
            ephemeral=True
        )


class SuggestionReject(discord.ui.Button):
    def __init__(self, suggestion_id):
        super().__init__(
            label="Ablehnen",
            emoji="❌",
            style=discord.ButtonStyle.danger,
            custom_id=f"rlp_suggestion_reject_{suggestion_id}"
        )

        self.suggestion_id = suggestion_id

    async def callback(self, interaction):

        if not (
            interaction.user.guild_permissions.administrator
            or any(
                role.id == SUGGESTION_REVIEW_ROLE_ID
                for role in interaction.user.roles
            )
        ):
            await interaction.response.send_message(
                "❌ Du darfst Vorschläge nicht verwalten.",
                ephemeral=True
            )
            return

        suggestion = data["suggestions"].get(
            self.suggestion_id
        )

        if not suggestion:
            await interaction.response.send_message(
                "❌ Vorschlag nicht gefunden.",
                ephemeral=True
            )
            return

        suggestion["rejected"] = True
        suggestion["accepted"] = False

        save_data()

        await update_suggestion(
            interaction,
            self.suggestion_id
        )

        await interaction.response.send_message(
            "❌ Vorschlag abgelehnt.",
            ephemeral=True
        )


class SuggestionView(discord.ui.View):
    def __init__(self, suggestion_id):
        super().__init__(timeout=None)

        self.add_item(
            SuggestionFor(suggestion_id)
        )

        self.add_item(
            SuggestionAgainst(suggestion_id)
        )

        self.add_item(
            SuggestionAccept(suggestion_id)
        )

        self.add_item(
            SuggestionReject(suggestion_id)
        )


# ============================================================
# EMOJI QUIZ
# ============================================================

EMOJI_QUESTIONS = [
    {
        "emojis": "🍕",
        "answer": "pizza",
        "hint": "Ein beliebtes italienisches Essen."
    },
    {
        "emojis": "🐶",
        "answer": "hund",
        "hint": "Ein sehr beliebtes Haustier."
    },
    {
        "emojis": "🐱",
        "answer": "katze",
        "hint": "Ein Haustier, das gerne klettert."
    },
    {
        "emojis": "🌈",
        "answer": "regenbogen",
        "hint": "Entsteht oft nach Regen und Sonne."
    },
    {
        "emojis": "⚽",
        "answer": "fußball",
        "hint": "Ein sehr beliebter Mannschaftssport."
    },
    {
        "emojis": "🚗",
        "answer": "auto",
        "hint": "Damit kann man fahren."
    },
    {
        "emojis": "🍎",
        "answer": "apfel",
        "hint": "Eine beliebte Frucht."
    },
    {
        "emojis": "☀️",
        "answer": "sonne",
        "hint": "Sie scheint am Himmel."
    },
    {
        "emojis": "🌙",
        "answer": "mond",
        "hint": "Man sieht ihn nachts am Himmel."
    },
    {
        "emojis": "🚔",
        "answer": "polizei",
        "hint": "Sie sorgt für Sicherheit."
    }
]


def ensure_emoji_user(user_id):
    user_id = str(user_id)

    now = time.time()

    state = data["emoji_quiz"].get(user_id)

    if not isinstance(state, dict):
        state = {
            "active": False,
            "question": None,
            "question_index": None,
            "answer": "",
            "hints": [],
            "tips_used": 0,
            "letters_used": 0,
            "skips_used": 0,
            "usage_reset_at": now + 7200,
            "score": 0,
            "solved": 0,
            "skipped": 0,
            "total": 0,
            "last_action": 0,
            "quiz_channel_id": None
        }

        data["emoji_quiz"][user_id] = state

    if now >= state.get("usage_reset_at", 0):
        state["tips_used"] = 0
        state["letters_used"] = 0
        state["skips_used"] = 0
        state["usage_reset_at"] = now + 7200

    return state


def emoji_new_question(state):
    index = random.randrange(
        len(EMOJI_QUESTIONS)
    )

    question = EMOJI_QUESTIONS[index]

    state["active"] = True
    state["question"] = question["emojis"]
    state["question_index"] = index
    state["answer"] = question["answer"]
    state["hints"] = []
    state["last_action"] = time.time()
    state["total"] += 1

    return question


class EmojiNewQuiz(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Neues Quiz",
            emoji="▶️",
            style=discord.ButtonStyle.success,
            custom_id="rlp_emoji_new"
        )

    async def callback(self, interaction):

        state = ensure_emoji_user(
            interaction.user.id
        )

        question = emoji_new_question(state)

        save_data()

        await interaction.response.send_message(
            f"🎯 **Emoji-Quiz**\n\n"
            f"{question['emojis']}\n\n"
            f"Schreibe deine Antwort hier in den Chat.",
            ephemeral=True
        )


class EmojiHint(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Tipp anfordern",
            emoji="💡",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_emoji_hint"
        )

    async def callback(self, interaction):

        state = ensure_emoji_user(
            interaction.user.id
        )

        if state["tips_used"] >= 3:
            reset_time = int(
                max(
                    0,
                    state["usage_reset_at"] - time.time()
                ) / 60
            )

            await interaction.response.send_message(
                f"❌ Deine **Tipp-Nutzung** ist bereits bei 3/3.\n"
                f"🔄 Zurückgesetzt in ca. {reset_time} Minuten.",
                ephemeral=True
            )
            return

        if not state["active"]:
            await interaction.response.send_message(
                "❌ Du hast aktuell kein aktives Quiz.",
                ephemeral=True
            )
            return

        question = EMOJI_QUESTIONS[
            state["question_index"]
        ]

        state["tips_used"] += 1

        save_data()

        await interaction.response.send_message(
            f"💡 Tipp: {question['hint']}\n\n"
            f"Nutzung: `{state['tips_used']}/3`",
            ephemeral=True
        )


class EmojiLetters(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Anfangsbuchstaben",
            emoji="🔤",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_emoji_letters"
        )

    async def callback(self, interaction):

        state = ensure_emoji_user(
            interaction.user.id
        )

        if state["letters_used"] >= 3:
            reset_time = int(
                max(
                    0,
                    state["usage_reset_at"] - time.time()
                ) / 60
            )

            await interaction.response.send_message(
                f"❌ Deine **Anfangsbuchstaben-Nutzung** ist 3/3.\n"
                f"🔄 Zurückgesetzt in ca. {reset_time} Minuten.",
                ephemeral=True
            )
            return

        if not state["active"]:
            await interaction.response.send_message(
                "❌ Du hast aktuell kein aktives Quiz.",
                ephemeral=True
            )
            return

        answer = state["answer"]

        letters = " ".join(
            word[0].upper()
            for word in answer.split()
            if word
        )

        state["letters_used"] += 1

        save_data()

        await interaction.response.send_message(
            f"🔤 Anfangsbuchstaben: `{letters}`\n\n"
            f"Nutzung: `{state['letters_used']}/3`",
            ephemeral=True
        )


class EmojiSkip(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Aufgabe überspringen",
            emoji="⏭️",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_emoji_skip"
        )

    async def callback(self, interaction):

        state = ensure_emoji_user(
            interaction.user.id
        )

        if state["skips_used"] >= 3:
            reset_time = int(
                max(
                    0,
                    state["usage_reset_at"] - time.time()
                ) / 60
            )

            await interaction.response.send_message(
                f"❌ Deine **Skip-Nutzung** ist 3/3.\n"
                f"🔄 Zurückgesetzt in ca. {reset_time} Minuten.",
                ephemeral=True
            )
            return

        if not state["active"]:
            await interaction.response.send_message(
                "❌ Du hast aktuell kein aktives Quiz.",
                ephemeral=True
            )
            return

        state["skips_used"] += 1
        state["skipped"] += 1

        question = emoji_new_question(state)

        save_data()

        await interaction.response.send_message(
            f"⏭️ Neue Aufgabe:\n\n"
            f"{question['emojis']}",
            ephemeral=True
        )


class EmojiLeaderboard(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Bestenliste",
            emoji="🏆",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_emoji_leaderboard"
        )

    async def callback(self, interaction):

        entries = []

        for user_id, state in data["emoji_quiz"].items():
            if not isinstance(state, dict):
                continue

            entries.append(
                (
                    int(state.get("score", 0)),
                    int(state.get("solved", 0)),
                    user_id
                )
            )

        entries.sort(
            key=lambda x: (
                x[0],
                x[1]
            ),
            reverse=True
        )

        lines = []

        for position, (score, solved, user_id) in enumerate(
            entries[:10],
            start=1
        ):
            name = get_member_name(user_id)

            lines.append(
                f"**{position}.** {name} — "
                f"🏆 `{score}` Punkte | ✅ `{solved}` gelöst"
            )

        if not lines:
            lines.append(
                "Noch keine Ergebnisse."
            )

        state = ensure_emoji_user(
            interaction.user.id
        )

        await interaction.response.send_message(
            "🏆 **Emoji-Quiz Bestenliste**\n\n"
            + "\n".join(lines)
            + "\n\n"
            f"Dein Score: `{state['score']}`\n"
            f"Gelöst: `{state['solved']}`\n"
            f"Übersprungen: `{state['skipped']}`",
            ephemeral=True
        )


class EmojiQuizView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(EmojiNewQuiz())
        self.add_item(EmojiHint())
        self.add_item(EmojiLetters())
        self.add_item(EmojiSkip())
        self.add_item(EmojiLeaderboard())


def emoji_quiz_embed():
    embed = discord.Embed(
        title="🎯 Emoji-Quiz",
        description=(
            "Teste dein Wissen anhand von Emojis.\n\n"
            "▶️ **Neues Quiz**\n"
            "Startet eine neue Aufgabe.\n\n"
            "💡 **Tipp** — 3 Nutzungen / 2 Stunden\n"
            "🔤 **Anfangsbuchstaben** — 3 Nutzungen / 2 Stunden\n"
            "⏭️ **Überspringen** — 3 Nutzungen / 2 Stunden\n"
            "🏆 **Bestenliste**\n\n"
            "Die Nutzungen sind **global pro Benutzer** und werden "
            "alle 2 Stunden zurückgesetzt."
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(
        text=EMOJI_QUIZ_PANEL_MARKER
    )

    return embed


@bot.command(
    name="emojiquizpanel",
    aliases=["emojiquiz"]
)
async def emojiquiz_panel(ctx):
    await update_or_create_panel(
        ctx.channel,
        EMOJI_QUIZ_PANEL_MARKER,
        emoji_quiz_embed(),
        EmojiQuizView()
    )

    await ctx.send(
        "✅ Emoji-Quiz-Panel aktualisiert."
    )


# ============================================================
# ZAHLENSPIEL
# ============================================================

def wrong_timeout_minutes(wrong_count):
    if wrong_count < 4:
        return 0

    level = 1 + ((wrong_count - 4) // 10)

    minutes = 5 * level

    return min(minutes, 24 * 60)


async def handle_number_game(message):

    if message.channel.id != NUMBER_GAME_CHANNEL_ID:
        return False

    if message.author.bot:
        return False

    content = message.content.strip()

    if not re.fullmatch(r"\d+", content):
        return False

    number = int(content)

    number_game = data["number_game"]

    expected = int(
        number_game.get(
            "current_number",
            1
        )
    )

    last_user_id = number_game.get(
        "last_user_id"
    )

    user_id = str(
        message.author.id
    )

    # --------------------------------------------------------
    # RICHTIGE ZAHL
    # --------------------------------------------------------

    if number == expected:

        # Gleicher User darf nicht zweimal hintereinander
        if last_user_id == message.author.id:

            warning = await message.channel.send(
                f"⚠️ **Nicht möglich!**\n"
                f"Die Zahl `{expected}` muss von einer "
                f"anderen Person geschrieben werden.\n"
                f"Die Zahl bleibt bei `{expected}`."
            )

            asyncio.create_task(
                delete_after_seconds(
                    warning,
                    4
                )
            )

            return True

        number_game["current_number"] = expected + 1
        number_game["last_user_id"] = message.author.id
        number_game["last_message_id"] = message.id

        save_data()

        check_message = await message.channel.send(
            f"✅ `{number}` — korrekt!"
        )

        asyncio.create_task(
            delete_after_seconds(
                check_message,
                4
            )
        )

        # Easter Egg bei 100, 200, 300 ...
        if number % 100 == 0:
            if number_game.get("last_easter_egg", 0) != number:

                number_game["last_easter_egg"] = number

                save_data()

                easter_egg = await message.channel.send(
                    f"🎉 **{number} erreicht!**\n"
                    f"Starke Leistung — weiter geht's mit "
                    f"`{number + 1}`!"
                )

                asyncio.create_task(
                    delete_after_seconds(
                        easter_egg,
                        4
                    )
                )

        return True

    # --------------------------------------------------------
    # FALSCHE ZAHL
    # --------------------------------------------------------

    wrong_attempts = number_game.setdefault(
        "wrong_attempts",
        {}
    )

    wrong_attempts[user_id] = (
        int(wrong_attempts.get(user_id, 0)) + 1
    )

    wrong_count = wrong_attempts[user_id]

    number_game["current_number"] = 1
    number_game["last_user_id"] = None
    number_game["last_message_id"] = message.id

    save_data()

    timeout_minutes = wrong_timeout_minutes(
        wrong_count
    )

    if timeout_minutes > 0:

        timeout_text = (
            f"\n⏱️ Du hast insgesamt **{wrong_count} Fehlversuche**."
            f"\n🔒 Dafür erhältst du einen Timeout von "
            f"**{timeout_minutes} Minuten**."
        )

        bot_message = await message.channel.send(
            f"❌ **Falsche Zahl!**\n"
            f"Du hast `{number}` geschrieben, erwartet wurde "
            f"`{expected}`.\n\n"
            f"🔄 Das Zahlenspiel wurde auf `{1}` zurückgesetzt."
            f"{timeout_text}"
        )

        asyncio.create_task(
            delete_after_seconds(
                bot_message,
                4
            )
        )

        try:
            until = discord.utils.utcnow() + discord.timedelta(
                minutes=timeout_minutes
            )

            await message.author.timeout(
                until,
                reason="RLP Zahlenspiel – zu viele Fehlversuche"
            )

        except AttributeError:
            try:
                duration = datetime.now().timestamp() + (
                    timeout_minutes * 60
                )

                await message.author.timeout(
                    discord.utils.utcnow() + __import__(
                        "datetime"
                    ).timedelta(
                        minutes=timeout_minutes
                    ),
                    reason="RLP Zahlenspiel – zu viele Fehlversuche"
                )

            except (
                discord.Forbidden,
                discord.HTTPException,
                Exception
            ):
                pass

        except (
            discord.Forbidden,
            discord.HTTPException
        ):
            pass

    else:

        bot_message = await message.channel.send(
            f"❌ **Falsche Zahl!**\n"
            f"Du hast `{number}` geschrieben, erwartet wurde "
            f"`{expected}`.\n\n"
            f"🔄 Das Zahlenspiel wurde auf `{1}` zurückgesetzt."
        )

        asyncio.create_task(
            delete_after_seconds(
                bot_message,
                4
            )
        )

    # Falsche Nachricht des Users ebenfalls nach 4 Sekunden löschen
    asyncio.create_task(
        delete_after_seconds(
            message,
            4
        )
    )

    return True


def number_game_embed():
    number_game = data["number_game"]

    current = number_game.get(
        "current_number",
        1
    )

    embed = discord.Embed(
        title="🔢 RLP Zahlenspiel",
        description=(
            "Hier zählt die Community gemeinsam von "
            "**1 bis unendlich**.\n\n"
            "📌 **Regeln:**\n"
            "• Es muss immer die nächste Zahl geschrieben werden.\n"
            "• Nach einer richtigen Zahl muss eine andere Person "
            "die nächste Zahl schreiben.\n"
            "• Eine falsche Zahl setzt das Spiel wieder auf **1**.\n"
            "• Fehlversuche werden gezählt.\n"
            "• Ab 4 Fehlversuchen gibt es einen Timeout.\n"
            "• Alle korrekten Bot-Bestätigungen verschwinden nach "
            "**4 Sekunden**.\n"
            "• Falsche Zahlennachrichten werden ebenfalls nach "
            "**4 Sekunden** gelöscht.\n\n"
            f"🎯 **Aktuell erwartet:** `{current}`"
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=NUMBER_GAME_PANEL_MARKER
    )

    return embed


async def refresh_number_game_panel():
    channel = bot.get_channel(
        NUMBER_GAME_CHANNEL_ID
    )

    if channel:
        await update_or_create_panel(
            channel,
            NUMBER_GAME_PANEL_MARKER,
            number_game_embed(),
            None
        )


@bot.command(
    name="zahlenspiel",
    aliases=["numbergame"]
)
async def number_game_panel(ctx):

    if not owner_check(ctx.author):
        await ctx.send(
            "❌ Du darfst dieses Panel nicht verwalten."
        )
        return

    await refresh_number_game_panel()

    await ctx.send(
        "✅ Zahlenspiel-Panel aktualisiert."
    )


# ============================================================
# OWNER PANEL
# ============================================================

class OwnerChannelSelect(
    discord.ui.ChannelSelect
):
    def __init__(self):
        super().__init__(
            placeholder="Kanal auswählen",
            custom_id="rlp_owner_channel_select",
            channel_types=[
                discord.ChannelType.text
            ]
        )

    async def callback(self, interaction):

        if not owner_check(interaction.user):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        channel = self.values[0]

        await interaction.response.send_message(
            f"📌 Ausgewählter Kanal: {channel.mention}",
            ephemeral=True
        )


class AnnouncementModal(
    discord.ui.Modal,
    title="Ankündigung"
):
    text = discord.ui.TextInput(
        label="Ankündigung",
        style=discord.TextStyle.paragraph,
        max_length=4000
    )

    async def on_submit(self, interaction):

        if not owner_check(interaction.user):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📢 Ankündigung",
            description=self.text.value,
            color=discord.Color.red()
        )

        embed.set_footer(
            text=f"Von {interaction.user.display_name}"
        )

        await interaction.channel.send(
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Ankündigung gesendet.",
            ephemeral=True
        )


class BotSayModal(
    discord.ui.Modal,
    title="Bot-Nachricht"
):
    text = discord.ui.TextInput(
        label="Nachricht",
        style=discord.TextStyle.paragraph,
        max_length=4000
    )

    async def on_submit(self, interaction):

        if not owner_check(interaction.user):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.channel.send(
            self.text.value
        )

        await interaction.response.send_message(
            "✅ Bot-Nachricht gesendet.",
            ephemeral=True
        )


class OwnerAnnouncement(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Ankündigung",
            emoji="📢",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_owner_announcement"
        )

    async def callback(self, interaction):
        await interaction.response.send_modal(
            AnnouncementModal()
        )


class OwnerBotSay(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Bot-Nachricht",
            emoji="💬",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_botsay"
        )

    async def callback(self, interaction):
        await interaction.response.send_modal(
            BotSayModal()
        )


class OwnerLock(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Kanal sperren",
            emoji="🔒",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_owner_lock"
        )

    async def callback(self, interaction):

        if not owner_check(interaction.user):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        overwrite = interaction.channel.overwrites_for(
            interaction.guild.default_role
        )

        overwrite.send_messages = False

        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            overwrite=overwrite
        )

        await interaction.response.send_message(
            "🔒 Kanal wurde gesperrt.",
            ephemeral=True
        )


class OwnerUnlock(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Kanal entsperren",
            emoji="🔓",
            style=discord.ButtonStyle.success,
            custom_id="rlp_owner_unlock"
        )

    async def callback(self, interaction):

        if not owner_check(interaction.user):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        overwrite = interaction.channel.overwrites_for(
            interaction.guild.default_role
        )

        overwrite.send_messages = None

        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            overwrite=overwrite
        )

        await interaction.response.send_message(
            "🔓 Kanal wurde entsperrt.",
            ephemeral=True
        )


class OwnerStatus(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Bot Status",
            emoji="📊",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_status"
        )

    async def callback(self, interaction):

        uptime = int(
            time.time() - BOT_START_TIME
        )

        hours = uptime // 3600
        minutes = (uptime % 3600) // 60
        seconds = uptime % 60

        embed = discord.Embed(
            title="📊 Bot Status",
            color=discord.Color.green()
        )

        embed.add_field(
            name="Status",
            value="🟢 Online"
        )

        embed.add_field(
            name="Ping",
            value=f"`{round(bot.latency * 1000)} ms`"
        )

        embed.add_field(
            name="Uptime",
            value=f"`{hours}h {minutes}m {seconds}s`"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


class OwnerServerInfo(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Server Info",
            emoji="🖥️",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_serverinfo"
        )

    async def callback(self, interaction):

        guild = interaction.guild

        embed = discord.Embed(
            title="🖥️ Server-Informationen",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Server",
            value=guild.name
        )

        embed.add_field(
            name="Mitglieder",
            value=str(guild.member_count)
        )

        embed.add_field(
            name="Kanäle",
            value=str(len(guild.channels))
        )

        embed.add_field(
            name="Rollen",
            value=str(len(guild.roles))
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


class OwnerUserInfo(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="User Info",
            emoji="👤",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_userinfo"
        )

    async def callback(self, interaction):

        member = interaction.user

        embed = discord.Embed(
            title="👤 User-Informationen",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Name",
            value=member.display_name
        )

        embed.add_field(
            name="ID",
            value=str(member.id)
        )

        embed.add_field(
            name="Rollen",
            value=", ".join(
                role.mention
                for role in member.roles[1:]
            ) or "Keine"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


class OwnerRolesInfo(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Rollen Info",
            emoji="🎭",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_roles"
        )

    async def callback(self, interaction):

        roles = interaction.guild.roles

        lines = []

        for role in reversed(roles):
            if role.is_default():
                continue

            lines.append(
                f"{role.mention} — `{role.id}`"
            )

        text = "\n".join(lines)

        if len(text) > 3900:
            text = text[:3850] + "\n…"

        embed = discord.Embed(
            title="🎭 Server-Rollen",
            description=text or "Keine Rollen.",
            color=discord.Color.blurple()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


class ClearMessagesModal(
    discord.ui.Modal,
    title="Nachrichten löschen"
):
    amount = discord.ui.TextInput(
        label="Anzahl",
        placeholder="z. B. 10",
        max_length=4
    )

    async def on_submit(self, interaction):

        if not owner_check(interaction.user):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        try:
            amount = int(
                self.amount.value
            )
        except ValueError:
            await interaction.response.send_message(
                "❌ Ungültige Anzahl.",
                ephemeral=True
            )
            return

        amount = max(
            1,
            min(
                amount,
                100
            )
        )

        deleted = await interaction.channel.purge(
            limit=amount
        )

        await interaction.response.send_message(
            f"🧹 `{len(deleted)}` Nachrichten gelöscht.",
            ephemeral=True
        )


class ClearButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Clear Messages",
            emoji="🧹",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_owner_clear"
        )

    async def callback(self, interaction):
        await interaction.response.send_modal(
            ClearMessagesModal()
        )


class GiveawayModal(
    discord.ui.Modal,
    title="Giveaway starten"
):
    prize = discord.ui.TextInput(
        label="Preis",
        max_length=200
    )

    duration = discord.ui.TextInput(
        label="Dauer in Sekunden",
        placeholder="z. B. 60",
        max_length=6
    )

    async def on_submit(self, interaction):

        if not owner_check(interaction.user):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        try:
            duration = int(
                self.duration.value
            )
        except ValueError:
            await interaction.response.send_message(
                "❌ Ungültige Dauer.",
                ephemeral=True
            )
            return

        duration = max(
            5,
            min(duration, 86400)
        )

        embed = discord.Embed(
            title="🎁 GIVEAWAY",
            description=(
                f"🎁 Preis: **{self.prize.value}**\n\n"
                "Klicke auf 🎉, um teilzunehmen!\n\n"
                f"⏱️ Ende in **{duration} Sekunden**."
            ),
            color=discord.Color.gold()
        )

        message = await interaction.channel.send(
            embed=embed
        )

        await message.add_reaction("🎉")

        await interaction.response.send_message(
            "✅ Giveaway gestartet.",
            ephemeral=True
        )

        asyncio.create_task(
            finish_giveaway(
                interaction.channel,
                message.id,
                self.prize.value,
                duration
            )
        )


async def finish_giveaway(
    channel,
    message_id,
    prize,
    duration
):

    await asyncio.sleep(duration)

    try:
        message = await channel.fetch_message(
            message_id
        )
    except discord.HTTPException:
        return

    reaction = None

    for r in message.reactions:
        if str(r.emoji) == "🎉":
            reaction = r
            break

    if reaction is None:
        await channel.send(
            "🎁 Giveaway beendet — keine Teilnehmer."
        )
        return

    users = []

    try:
        async for user in reaction.users():
            if not user.bot:
                users.append(user)
    except discord.HTTPException:
        return

    if not users:
        await channel.send(
            "🎁 Giveaway beendet — keine Teilnehmer."
        )
        return

    winner = random.choice(users)

    await channel.send(
        f"🎉 **Giveaway beendet!**\n"
        f"Gewonnen hat {winner.mention}!\n"
        f"🎁 Preis: **{prize}**"
    )


class GiveawayStartButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Giveaway starten",
            emoji="🎁",
            style=discord.ButtonStyle.success,
            custom_id="rlp_owner_giveaway"
        )

    async def callback(self, interaction):
        await interaction.response.send_modal(
            GiveawayModal()
        )


class OwnerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(OwnerAnnouncement())
        self.add_item(OwnerBotSay())
        self.add_item(OwnerLock())
        self.add_item(OwnerUnlock())
        self.add_item(OwnerStatus())
        self.add_item(OwnerServerInfo())
        self.add_item(OwnerUserInfo())
        self.add_item(OwnerRolesInfo())
        self.add_item(ClearButton())
        self.add_item(GiveawayStartButton())


def owner_embed():
    embed = discord.Embed(
        title="👑 RLP Owner Panel",
        description=(
            "Willkommen im Owner Panel.\n\n"
            "📢 **Ankündigung**\n"
            "💬 **Bot-Nachricht**\n"
            "🔒 **Kanal sperren**\n"
            "🔓 **Kanal entsperren**\n"
            "📊 **Bot Status**\n"
            "🖥️ **Server Info**\n"
            "👤 **User Info**\n"
            "🎭 **Rollen Info**\n"
            "🧹 **Nachrichten löschen**\n"
            "🎁 **Giveaway starten**"
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(
        text=OWNER_PANEL_MARKER
    )

    return embed


@bot.command(
    name="ownerpanel",
    aliases=["owner"]
)
async def owner_panel(ctx):

    if not owner_check(ctx.author):
        await ctx.send(
            "❌ Du hast keine Berechtigung für das Owner Panel."
        )
        return

    await update_or_create_panel(
        ctx.channel,
        OWNER_PANEL_MARKER,
        owner_embed(),
        OwnerView()
    )

    await ctx.send(
        "✅ Owner Panel aktualisiert."
    )


# ============================================================
# HELP
# ============================================================

@bot.command(name="help")
async def help_command(ctx):

    embed = discord.Embed(
        title="📚 RLP Bot Hilfe",
        description="Verfügbare Befehle:",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🔧 Administration",
        value=(
            "`?nametagpanel`\n"
            "`?licensepanel`\n"
            "`?bewerbungpanel`\n"
            "`?devtaskpanel`\n"
            "`?devshiftpanel`\n"
            "`?zahlenspiel`\n"
            "`?ownerpanel` / `?owner`"
        ),
        inline=False
    )

    embed.add_field(
        name="🌐 Community",
        value="`?communitypanel`",
        inline=False
    )

    embed.add_field(
        name="🎯 Quiz",
        value="`?emojiquizpanel` / `?emojiquiz`",
        inline=False
    )

    await ctx.send(
        embed=embed
    )


# ============================================================
# COMMAND ERROR
# ============================================================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(
        error,
        commands.CommandNotFound
    ):
        return

    if isinstance(
        error,
        commands.MissingPermissions
    ):
        await ctx.send(
            "❌ Du hast dafür keine Berechtigung.",
            delete_after=5
        )
        return

    if isinstance(
        error,
        commands.MissingRequiredArgument
    ):
        await ctx.send(
            "❌ Es fehlt ein benötigtes Argument.",
            delete_after=5
        )
        return

    print(
        f"[COMMAND ERROR] {repr(error)}"
    )


# ============================================================
# READY
# ============================================================

@bot.event
async def on_ready():

    print(
        f"✅ Eingeloggt als {bot.user} "
        f"(ID: {bot.user.id})"
    )

    # Persistent Views
    bot.add_view(
        NametagPanelView()
    )

    bot.add_view(
        PlateView()
    )

    bot.add_view(
        ApplicationView()
    )

    bot.add_view(
        DeveloperTaskView()
    )

    bot.add_view(
        ShiftView()
    )

    bot.add_view(
        CommunityView()
    )

    bot.add_view(
        EmojiQuizView()
    )

    bot.add_view(
        OwnerView()
    )

    # --------------------------------------------------------
    # WICHTIG:
    # License Plates werden hier NICHT gelöscht!
    # --------------------------------------------------------

    await refresh_license_panel()
    await refresh_application_panel()
    await refresh_developer_task_panel()
    await refresh_shift_panel()
    await refresh_number_game_panel()

    # Community / Owner / Emoji Quiz NICHT automatisch
    # irgendwo erstellen.
    #
    # Diese Panels werden nur über ihre Commands
    # im jeweiligen aktuellen Kanal erstellt.

    try:
        await bot.change_presence(
            activity=discord.Game(
                name=STATUS_TEXTS[0]
            )
        )
    except discord.HTTPException:
        pass


# ============================================================
# MESSAGE HANDLER
# ============================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # Zahlenspiel zuerst bearbeiten
    handled = await handle_number_game(
        message
    )

    if handled:
        return

    # Emoji Quiz
    user_id = str(
        message.author.id
    )

    quiz_state = data["emoji_quiz"].get(
        user_id
    )

    if isinstance(quiz_state, dict):

        now = time.time()

        if now >= quiz_state.get(
            "usage_reset_at",
            0
        ):
            ensure_emoji_user(
                message.author.id
            )
            save_data()

        if (
            quiz_state.get("active")
            and quiz_state.get("quiz_channel_id") is not None
        ):

            if (
                message.channel.id
                == quiz_state.get("quiz_channel_id")
            ):

                answer = normalize_text(
                    message.content
                )

                expected_answer = normalize_text(
                    quiz_state.get(
                        "answer",
                        ""
                    )
                )

                if answer == expected_answer:

                    quiz_state["active"] = False
                    quiz_state["solved"] += 1
                    quiz_state["score"] += 1

                    save_data()

                    await message.channel.send(
                        f"✅ **Richtig, {message.author.display_name}!** "
                        f"+1 Punkt."
                    )

                    return

    await bot.process_commands(message)


# ============================================================
# START
# ============================================================

def start_bot():
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN wurde nicht gesetzt."
        )

    bot.run(TOKEN)


if __name__ == "__main__":
    start_bot()
