import os
import json
import random
import re
import time
import asyncio
import unicodedata

from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands, tasks
from discord.ui import (
    View,
    Button,
    Modal,
    TextInput,
    Select
)


# ============================================================
# CONFIG
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

# Zahlenspiel
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
# BOT
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
# DEFAULT DATA
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


# ============================================================
# DATA
# ============================================================

def load_data():
    if not os.path.exists(DATA_FILE):
        return json.loads(json.dumps(DEFAULT_DATA))

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = json.loads(json.dumps(DEFAULT_DATA))

    for key, default_value in DEFAULT_DATA.items():
        if key not in data:
            data[key] = json.loads(json.dumps(default_value))

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

    if not isinstance(number_game.get("last_easter_egg"), int):
        number_game["last_easter_egg"] = 0

    if "last_user_id" not in number_game:
        number_game["last_user_id"] = None

    if "last_message_id" not in number_game:
        number_game["last_message_id"] = None

    save_data(data)
    return data


def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[DATA ERROR] {e}")


data = load_data()


# ============================================================
# BASIC HELPERS
# ============================================================

def get_guild():
    return bot.get_guild(GUILD_ID)


def get_channel(channel_id):
    guild = get_guild()

    if guild:
        channel = guild.get_channel(channel_id)
        if channel:
            return channel

    return bot.get_channel(channel_id)


def member_has_role(member, role_id):
    if not member or not hasattr(member, "roles"):
        return False

    return any(role.id == role_id for role in member.roles)


def is_owner(member):
    return (
        member_has_role(member, OWNER_ROLE_ID)
        or member.guild_permissions.administrator
    )


def is_shift_manager(member):
    return (
        member_has_role(member, SHIFT_PERMISSION_ROLE_ID)
        or member_has_role(member, OWNER_ROLE_ID)
        or member.guild_permissions.administrator
    )


def current_time():
    return datetime.now(timezone.utc)


def make_embed(
    title,
    description="",
    color=discord.Color.blurple()
):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=current_time()
    )

    embed.set_footer(
        text="RLP | RP-System"
    )

    return embed


async def error_response(interaction, text):
    embed = make_embed(
        "❌ Fehler",
        text,
        discord.Color.red()
    )

    if interaction.response.is_done():
        await interaction.followup.send(
            embed=embed,
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


# ============================================================
# PANEL HELPERS
# ============================================================

async def find_panel(channel, marker):
    if not channel:
        return None

    try:
        async for message in channel.history(limit=100):
            if (
                message.author.id == bot.user.id
                and message.embeds
                and message.embeds[0].footer
                and message.embeds[0].footer.text
                and marker in message.embeds[0].footer.text
            ):
                return message
    except Exception as e:
        print(f"[PANEL SEARCH] {e}")

    return None


async def update_panel(
    channel_id,
    marker,
    embed,
    view=None
):
    channel = get_channel(channel_id)

    if not channel:
        print(f"[PANEL] Channel {channel_id} nicht gefunden.")
        return None

    try:
        message = await find_panel(channel, marker)

        if message:
            await message.edit(
                embed=embed,
                view=view
            )
            return message

        return await channel.send(
            embed=embed,
            view=view
        )

    except Exception as e:
        print(f"[PANEL ERROR] {marker}: {e}")
        return None


# ============================================================
# NAMETAG SYSTEM
# ============================================================

async def remove_nametag(member):
    try:
        if member.nick and member.nick.startswith(NAMETAG):
            new_nick = member.nick[len(NAMETAG):].strip()

            if not new_nick:
                new_nick = None

            await member.edit(
                nick=new_nick,
                reason="RLP Nametag entfernt"
            )
    except Exception as e:
        print(f"[NAMETAG REMOVE] {e}")


def nametag_panel():
    embed = make_embed(
        "🏷️ Nametag System",
        (
            "Hier kannst du deinen persönlichen **RLP-Nametag** verwalten.\n\n"
            "### Funktionen\n"
            "🏷️ **Nametag setzen**\n"
            "Entfernt deinen bisherigen Namen und setzt den RLP-Nametag.\n\n"
            "🗑️ **Nametag entfernen**\n"
            "Entfernt den RLP-Nametag wieder.\n\n"
            "👀 **Nametag anzeigen**\n"
            "Zeigt dir deinen aktuellen Nametag."
        ),
        discord.Color.blue()
    )

    embed.set_footer(
        text=f"{NAMETAG_PANEL_MARKER} • RLP | RP-System"
    )

    return embed


class NametagSet(Modal, title="🏷️ Nametag setzen"):

    name = TextInput(
        label="Dein Name",
        placeholder="z. B. Max Mustermann",
        max_length=32
    )

    async def on_submit(self, interaction):
        member = interaction.guild.get_member(interaction.user.id)

        if not member:
            return await error_response(
                interaction,
                "Mitglied konnte nicht gefunden werden."
            )

        if not member_has_role(member, NAMETAG_ROLE_ID):
            return await error_response(
                interaction,
                "Du hast keine Berechtigung für das Nametag-System."
            )

        try:
            await member.edit(
                nick=f"{NAMETAG}{self.name.value}",
                reason="RLP Nametag gesetzt"
            )

            embed = make_embed(
                "✅ Nametag gesetzt",
                f"Dein Nametag wurde auf **{NAMETAG}{self.name.value}** gesetzt.",
                discord.Color.green()
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

        except discord.Forbidden:
            await error_response(
                interaction,
                "Ich kann deinen Nicknamen nicht ändern. Prüfe meine Rollenposition."
            )


class NametagRemove(Button):
    def __init__(self):
        super().__init__(
            label="Nametag entfernen",
            emoji="🗑️",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_nametag_remove"
        )

    async def callback(self, interaction):
        member = interaction.guild.get_member(interaction.user.id)

        if not member_has_role(member, NAMETAG_ROLE_ID):
            return await error_response(
                interaction,
                "Du hast keine Berechtigung."
            )

        await remove_nametag(member)

        await interaction.response.send_message(
            embed=make_embed(
                "✅ Nametag entfernt",
                "Dein RLP-Nametag wurde entfernt.",
                discord.Color.green()
            ),
            ephemeral=True
        )


class NametagView(View):
    def __init__(self):
        super().__init__(timeout=None)

        set_button = Button(
            label="Nametag setzen",
            emoji="🏷️",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_nametag_set"
        )

        set_button.callback = self.set_callback

        view_button = Button(
            label="Nametag anzeigen",
            emoji="👀",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_nametag_view"
        )

        view_button.callback = self.view_callback

        self.add_item(set_button)
        self.add_item(NametagRemove())
        self.add_item(set_button)
        self.remove_item(set_button)
        self.add_item(set_button)
        self.add_item(view_button)

    async def set_callback(self, interaction):
        await interaction.response.send_modal(NametagSet())

    async def view_callback(self, interaction):
        member = interaction.guild.get_member(interaction.user.id)

        if not member:
            return await error_response(
                interaction,
                "Mitglied nicht gefunden."
            )

        current = member.nick or member.name

        await interaction.response.send_message(
            embed=make_embed(
                "👀 Dein Nametag",
                f"Dein aktueller Name ist:\n**{current}**",
                discord.Color.blurple()
            ),
            ephemeral=True
        )


# ============================================================
# LICENSE PLATES
# ============================================================

def normalize_plate(text):
    return re.sub(
        r"[^A-Z0-9]",
        "",
        text.upper()
    )


def extract_plate_number(text):
    match = re.search(
        r"(\d{1,5})$",
        text
    )

    if not match:
        return None

    return int(match.group(1))


def license_panel():
    embed = make_embed(
        "🚘 Kennzeichen-System",
        (
            "Verwalte hier dein persönliches Kennzeichen.\n\n"
            "🔢 **Kennzeichen beantragen**\n"
            "Wähle ein gewünschtes Kennzeichen.\n\n"
            "👀 **Eigenes Kennzeichen anzeigen**\n"
            "Zeigt dein aktuell gespeichertes Kennzeichen.\n\n"
            "⚠️ Bereits vergebene Nummern können nicht erneut verwendet werden."
        ),
        discord.Color.blue()
    )

    embed.set_footer(
        text=f"{LICENSE_PANEL_MARKER} • RLP | RP-System"
    )

    return embed


class PlateModal(Modal, title="🚘 Kennzeichen beantragen"):

    plate = TextInput(
        label="Kennzeichen",
        placeholder="z. B. RLP 123",
        max_length=12
    )

    async def on_submit(self, interaction):
        member = interaction.guild.get_member(interaction.user.id)

        if not member:
            return await error_response(
                interaction,
                "Mitglied nicht gefunden."
            )

        plate = normalize_plate(self.plate.value)

        if not plate:
            return await error_response(
                interaction,
                "Ungültiges Kennzeichen."
            )

        number = extract_plate_number(plate)

        if number is None:
            return await error_response(
                interaction,
                "Das Kennzeichen muss mit einer Nummer enden."
            )

        for uid, saved_plate in data["license_plates"].items():
            if uid != str(member.id):
                if normalize_plate(saved_plate) == plate:
                    return await error_response(
                        interaction,
                        "Dieses Kennzeichen ist bereits vergeben."
                    )

        data["license_plates"][str(member.id)] = plate
        save_data(data)

        await interaction.response.send_message(
            embed=make_embed(
                "✅ Kennzeichen gespeichert",
                f"Dein Kennzeichen lautet jetzt:\n**{plate}**",
                discord.Color.green()
            ),
            ephemeral=True
        )


class PlateButton(Button):
    def __init__(self):
        super().__init__(
            label="Kennzeichen beantragen",
            emoji="🚘",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_plate_request"
        )

    async def callback(self, interaction):
        await interaction.response.send_modal(PlateModal())


class PlateView(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(PlateButton())

        button = Button(
            label="Kennzeichen anzeigen",
            emoji="👀",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_plate_view"
        )

        button.callback = self.view_plate

        self.add_item(button)

    async def view_plate(self, interaction):
        plate = data["license_plates"].get(
            str(interaction.user.id)
        )

        if not plate:
            return await error_response(
                interaction,
                "Du hast noch kein Kennzeichen."
            )

        await interaction.response.send_message(
            embed=make_embed(
                "🚘 Dein Kennzeichen",
                f"Dein Kennzeichen:\n**{plate}**",
                discord.Color.blurple()
            ),
            ephemeral=True
        )


async def refresh_license_panel():
    await update_panel(
        LICENSE_PLATE_CHANNEL_ID,
        LICENSE_PANEL_MARKER,
        license_panel(),
        PlateView()
    )


# ============================================================
# APPLICATION SYSTEM
# ============================================================

class ApplicationModal(Modal, title="📋 Bewerbung"):

    name = TextInput(
        label="Name",
        placeholder="Dein Name",
        max_length=100
    )

    age = TextInput(
        label="Alter",
        placeholder="Dein Alter",
        max_length=3
    )

    experience = TextInput(
        label="RP-Erfahrung",
        placeholder="Wie viel RP-Erfahrung hast du?",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    reason = TextInput(
        label="Warum möchtest du beitreten?",
        placeholder="Erkläre deine Motivation.",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    async def on_submit(self, interaction):
        channel = get_channel(APPLICATION_CHANNEL_ID)

        if not channel:
            return await error_response(
                interaction,
                "Bewerbungskanal nicht gefunden."
            )

        review_channel = get_channel(REVIEW_CHANNEL_ID)

        embed = make_embed(
            "📋 Neue Bewerbung",
            (
                f"**Bewerber:** {interaction.user.mention}\n"
                f"**Name:** {self.name.value}\n"
                f"**Alter:** {self.age.value}\n\n"
                f"**RP-Erfahrung:**\n{self.experience.value}\n\n"
                f"**Motivation:**\n{self.reason.value}"
            ),
            discord.Color.orange()
        )

        target = review_channel or channel

        await target.send(embed=embed)

        await interaction.response.send_message(
            embed=make_embed(
                "✅ Bewerbung abgeschickt",
                "Deine Bewerbung wurde erfolgreich eingereicht.",
                discord.Color.green()
            ),
            ephemeral=True
        )


class ApplicationButton(Button):
    def __init__(self):
        super().__init__(
            label="Bewerben",
            emoji="📋",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_application_start"
        )

    async def callback(self, interaction):
        await interaction.response.send_modal(ApplicationModal())


class ApplicationView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ApplicationButton())


def application_panel():
    embed = make_embed(
        "📋 Bewerbung",
        (
            "Du möchtest Teil unseres Teams werden?\n\n"
            "Klicke auf **Bewerben** und fülle das Formular vollständig aus.\n\n"
            "Bitte beantworte alle Fragen ehrlich und ausführlich."
        ),
        discord.Color.blue()
    )

    embed.set_footer(
        text=f"{APPLICATION_PANEL_MARKER} • RLP | RP-System"
    )

    return embed


# ============================================================
# DEVELOPER TASK SYSTEM
# ============================================================

class DeveloperTaskModal(Modal, title="💻 Developer Aufgabe"):

    task = TextInput(
        label="Aufgabe",
        placeholder="Welche Aufgabe soll erledigt werden?",
        style=discord.TextStyle.paragraph,
        max_length=2000
    )

    priority = TextInput(
        label="Priorität",
        placeholder="Niedrig / Mittel / Hoch",
        max_length=20
    )

    async def on_submit(self, interaction):
        task_id = str(int(time.time() * 1000))

        data["developer_tasks"][task_id] = {
            "creator": interaction.user.id,
            "task": self.task.value,
            "priority": self.priority.value,
            "created_at": time.time(),
            "completed": False
        }

        save_data(data)

        channel = get_channel(DEVELOPER_TASK_CHANNEL_ID)

        if channel:
            embed = make_embed(
                "💻 Neue Developer-Aufgabe",
                (
                    f"**Aufgabe:**\n{self.task.value}\n\n"
                    f"**Priorität:** {self.priority.value}\n"
                    f"**Erstellt von:** {interaction.user.mention}"
                ),
                discord.Color.purple()
            )

            await channel.send(embed=embed)

        await interaction.response.send_message(
            embed=make_embed(
                "✅ Aufgabe erstellt",
                "Die Developer-Aufgabe wurde erstellt.",
                discord.Color.green()
            ),
            ephemeral=True
        )


class DeveloperTaskButton(Button):
    def __init__(self):
        super().__init__(
            label="Aufgabe erstellen",
            emoji="💻",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_dev_task_create"
        )

    async def callback(self, interaction):
        await interaction.response.send_modal(
            DeveloperTaskModal()
        )


class DeveloperTaskView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(DeveloperTaskButton())


def developer_task_panel():
    embed = make_embed(
        "💻 Developer Aufgaben",
        (
            "Hier können neue Aufgaben für das Developer-Team erstellt werden.\n\n"
            "📝 Aufgabe erstellen\n"
            "Erstelle eine neue Aufgabe inklusive Priorität."
        ),
        discord.Color.purple()
    )

    embed.set_footer(
        text=f"{DEV_TASK_PANEL_MARKER} • RLP | RP-System"
    )

    return embed


# ============================================================
# DEVELOPER SHIFT
# ============================================================

def shift_panel():
    embed = make_embed(
        "💻 Developer Schicht",
        (
            "Verwalte hier deine Developer-Schicht.\n\n"
            "🟢 **Schicht starten**\n"
            "Starte deine Arbeitszeit.\n\n"
            "🔴 **Schicht beenden**\n"
            "Beende deine aktuelle Arbeitszeit.\n\n"
            "Nur berechtigte Teammitglieder können eine Schicht starten."
        ),
        discord.Color.green()
    )

    embed.set_footer(
        text=f"{DEV_SHIFT_PANEL_MARKER} • RLP | RP-System"
    )

    return embed


class ShiftStart(Button):
    def __init__(self):
        super().__init__(
            label="Schicht starten",
            emoji="🟢",
            style=discord.ButtonStyle.success,
            custom_id="rlp_shift_start"
        )

    async def callback(self, interaction):
        member = interaction.guild.get_member(interaction.user.id)

        if not is_shift_manager(member):
            return await error_response(
                interaction,
                "Du hast keine Berechtigung, eine Developer-Schicht zu starten."
            )

        uid = str(member.id)

        if uid in data["active_developer_shifts"]:
            return await error_response(
                interaction,
                "Du bist bereits im Dienst."
            )

        data["active_developer_shifts"][uid] = {
            "started_at": time.time()
        }

        save_data(data)

        await shift_log(
            f"🟢 {member.mention} hat eine Developer-Schicht gestartet."
        )

        await interaction.response.send_message(
            embed=make_embed(
                "🟢 Schicht gestartet",
                "Deine Developer-Schicht wurde gestartet.",
                discord.Color.green()
            ),
            ephemeral=True
        )


class ShiftEnd(Button):
    def __init__(self):
        super().__init__(
            label="Schicht beenden",
            emoji="🔴",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_shift_end"
        )

    async def callback(self, interaction):
        member = interaction.guild.get_member(interaction.user.id)

        if not member:
            return await error_response(
                interaction,
                "Mitglied nicht gefunden."
            )

        uid = str(member.id)

        shift = data["active_developer_shifts"].get(uid)

        if not shift:
            return await error_response(
                interaction,
                "Du hast aktuell keine aktive Schicht."
            )

        duration = int(time.time() - shift["started_at"])

        del data["active_developer_shifts"][uid]
        save_data(data)

        hours = duration // 3600
        minutes = (duration % 3600) // 60

        await shift_log(
            f"🔴 {member.mention} hat die Developer-Schicht beendet.\n"
            f"Dauer: **{hours}h {minutes}min**"
        )

        await interaction.response.send_message(
            embed=make_embed(
                "🔴 Schicht beendet",
                f"Schichtdauer: **{hours}h {minutes}min**",
                discord.Color.red()
            ),
            ephemeral=True
        )


class ShiftView(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(ShiftStart())
        self.add_item(ShiftEnd())


async def shift_log(text):
    channel = get_channel(SHIFT_LOG_CHANNEL_ID)

    if channel:
        try:
            await channel.send(
                embed=make_embed(
                    "💻 Developer Schicht",
                    text,
                    discord.Color.blurple()
                )
            )
        except Exception as e:
            print(f"[SHIFT LOG] {e}")


async def refresh_shift_panel():
    await update_panel(
        DEVELOPER_SHIFT_CHANNEL_ID,
        DEV_SHIFT_PANEL_MARKER,
        shift_panel(),
        ShiftView()
    )


# ============================================================
# COMMUNITY
# ============================================================

class SuggestionModal(Modal, title="💡 Vorschlag erstellen"):

    suggestion = TextInput(
        label="Dein Vorschlag",
        placeholder="Was möchtest du verbessern?",
        style=discord.TextStyle.paragraph,
        max_length=2000
    )

    async def on_submit(self, interaction):
        channel = get_channel(SUGGESTION_CHANNEL_ID)

        if not channel:
            return await error_response(
                interaction,
                "Vorschlagskanal wurde nicht gefunden."
            )

        suggestion_id = str(int(time.time() * 1000))

        data["suggestions"][suggestion_id] = {
            "author": interaction.user.id,
            "text": self.suggestion.value,
            "for": 0,
            "against": 0,
            "accepted": False,
            "rejected": False,
            "voters": []
        }

        save_data(data)

        message = await channel.send(
            embed=suggestion_embed(suggestion_id),
            view=SuggestionView(suggestion_id)
        )

        data["suggestions"][suggestion_id]["message_id"] = message.id
        save_data(data)

        await interaction.response.send_message(
            embed=make_embed(
                "✅ Vorschlag eingereicht",
                "Dein Vorschlag wurde erfolgreich eingereicht.",
                discord.Color.green()
            ),
            ephemeral=True
        )


class FeedbackModal(Modal, title="📝 Feedback geben"):

    feedback = TextInput(
        label="Feedback",
        placeholder="Dein Feedback...",
        style=discord.TextStyle.paragraph,
        max_length=2000
    )

    async def on_submit(self, interaction):
        channel = get_channel(FEEDBACK_CHANNEL_ID)

        if not channel:
            return await error_response(
                interaction,
                "Feedbackkanal nicht gefunden."
            )

        data["feedback"].append({
            "author": interaction.user.id,
            "text": self.feedback.value,
            "created_at": time.time()
        })

        save_data(data)

        await channel.send(
            embed=make_embed(
                "📝 Neues Feedback",
                (
                    f"**Von:** {interaction.user.mention}\n\n"
                    f"{self.feedback.value}"
                ),
                discord.Color.blurple()
            )
        )

        await interaction.response.send_message(
            embed=make_embed(
                "✅ Feedback gesendet",
                "Danke für dein Feedback!",
                discord.Color.green()
            ),
            ephemeral=True
        )


class CommunitySuggestion(Button):
    def __init__(self):
        super().__init__(
            label="Vorschlag einreichen",
            emoji="💡",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_community_suggestion"
        )

    async def callback(self, interaction):
        await interaction.response.send_modal(
            SuggestionModal()
        )


class CommunityFeedback(Button):
    def __init__(self):
        super().__init__(
            label="Feedback",
            emoji="📝",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_community_feedback"
        )

    async def callback(self, interaction):
        await interaction.response.send_modal(
            FeedbackModal()
        )


class CommunityView(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(CommunitySuggestion())
        self.add_item(CommunityFeedback())


def community_panel():
    embed = make_embed(
        "🌐 Community",
        (
            "Willkommen im Community-Bereich!\n\n"
            "💡 **Vorschlag einreichen**\n"
            "Du hast eine Idee für den Server? Teile sie mit uns.\n\n"
            "📝 **Feedback**\n"
            "Sende uns dein Feedback zur Community oder zum Server."
        ),
        discord.Color.blue()
    )

    embed.set_footer(
        text=f"{COMMUNITY_PANEL_MARKER} • RLP | RP-System"
    )

    return embed


def suggestion_embed(suggestion_id):
    suggestion = data["suggestions"].get(suggestion_id)

    if not suggestion:
        return make_embed(
            "❌ Vorschlag nicht gefunden",
            "Dieser Vorschlag existiert nicht mehr.",
            discord.Color.red()
        )

    status = "🟡 Offen"

    if suggestion.get("accepted"):
        status = "🟢 Angenommen"

    if suggestion.get("rejected"):
        status = "🔴 Abgelehnt"

    embed = make_embed(
        "💡 Community-Vorschlag",
        (
            f"**Vorschlag von:** <@{suggestion['author']}>\n\n"
            f"{suggestion['text']}\n\n"
            f"**Status:** {status}\n\n"
            f"👍 Dafür: **{suggestion.get('for', 0)}**\n"
            f"👎 Dagegen: **{suggestion.get('against', 0)}**"
        ),
        discord.Color.blurple()
    )

    embed.set_footer(
        text=f"Suggestion ID: {suggestion_id}"
    )

    return embed


async def update_suggestion(suggestion_id):
    suggestion = data["suggestions"].get(suggestion_id)

    if not suggestion:
        return

    channel = get_channel(SUGGESTION_CHANNEL_ID)

    if not channel:
        return

    message_id = suggestion.get("message_id")

    if not message_id:
        return

    try:
        message = await channel.fetch_message(message_id)

        await message.edit(
            embed=suggestion_embed(suggestion_id),
            view=SuggestionView(suggestion_id)
        )

    except Exception as e:
        print(f"[SUGGESTION UPDATE] {e}")


class SuggestionFor(Button):
    def __init__(self, suggestion_id):
        super().__init__(
            label="Dafür",
            emoji="👍",
            style=discord.ButtonStyle.success,
            custom_id=f"rlp_suggestion_for:{suggestion_id}"
        )

        self.suggestion_id = suggestion_id

    async def callback(self, interaction):
        suggestion = data["suggestions"].get(
            self.suggestion_id
        )

        if not suggestion:
            return await error_response(
                interaction,
                "Vorschlag nicht gefunden."
            )

        uid = str(interaction.user.id)

        if uid in suggestion["voters"]:
            return await error_response(
                interaction,
                "Du hast bereits abgestimmt."
            )

        suggestion["voters"].append(uid)
        suggestion["for"] += 1

        save_data(data)

        await update_suggestion(
            self.suggestion_id
        )

        await interaction.response.send_message(
            "👍 Deine Stimme wurde gespeichert.",
            ephemeral=True
        )


class SuggestionAgainst(Button):
    def __init__(self, suggestion_id):
        super().__init__(
            label="Dagegen",
            emoji="👎",
            style=discord.ButtonStyle.danger,
            custom_id=f"rlp_suggestion_against:{suggestion_id}"
        )

        self.suggestion_id = suggestion_id

    async def callback(self, interaction):
        suggestion = data["suggestions"].get(
            self.suggestion_id
        )

        if not suggestion:
            return await error_response(
                interaction,
                "Vorschlag nicht gefunden."
            )

        uid = str(interaction.user.id)

        if uid in suggestion["voters"]:
            return await error_response(
                interaction,
                "Du hast bereits abgestimmt."
            )

        suggestion["voters"].append(uid)
        suggestion["against"] += 1

        save_data(data)

        await update_suggestion(
            self.suggestion_id
        )

        await interaction.response.send_message(
            "👎 Deine Stimme wurde gespeichert.",
            ephemeral=True
        )


class SuggestionAccept(Button):
    def __init__(self, suggestion_id):
        super().__init__(
            label="Annehmen",
            emoji="✅",
            style=discord.ButtonStyle.success,
            custom_id=f"rlp_suggestion_accept:{suggestion_id}"
        )

        self.suggestion_id = suggestion_id

    async def callback(self, interaction):
        member = interaction.guild.get_member(
            interaction.user.id
        )

        if not member_has_role(
            member,
            SUGGESTION_REVIEW_ROLE_ID
        ) and not is_owner(member):
            return await error_response(
                interaction,
                "Du hast keine Berechtigung."
            )

        suggestion = data["suggestions"].get(
            self.suggestion_id
        )

        if not suggestion:
            return await error_response(
                interaction,
                "Vorschlag nicht gefunden."
            )

        suggestion["accepted"] = True
        suggestion["rejected"] = False

        save_data(data)

        await update_suggestion(
            self.suggestion_id
        )

        await interaction.response.send_message(
            "✅ Vorschlag wurde angenommen.",
            ephemeral=True
        )


class SuggestionReject(Button):
    def __init__(self, suggestion_id):
        super().__init__(
            label="Ablehnen",
            emoji="❌",
            style=discord.ButtonStyle.danger,
            custom_id=f"rlp_suggestion_reject:{suggestion_id}"
        )

        self.suggestion_id = suggestion_id

    async def callback(self, interaction):
        member = interaction.guild.get_member(
            interaction.user.id
        )

        if not member_has_role(
            member,
            SUGGESTION_REVIEW_ROLE_ID
        ) and not is_owner(member):
            return await error_response(
                interaction,
                "Du hast keine Berechtigung."
            )

        suggestion = data["suggestions"].get(
            self.suggestion_id
        )

        if not suggestion:
            return await error_response(
                interaction,
                "Vorschlag nicht gefunden."
            )

        suggestion["rejected"] = True
        suggestion["accepted"] = False

        save_data(data)

        await update_suggestion(
            self.suggestion_id
        )

        await interaction.response.send_message(
            "❌ Vorschlag wurde abgelehnt.",
            ephemeral=True
        )


class SuggestionView(View):
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
    ("🍕", "pizza", "Essen", "Rundes Gericht", "Oft mit Käse"),
    ("🚗", "auto", "Fahrzeug", "Hat meistens vier Räder", "Fährt auf Straßen"),
    ("🐶", "hund", "Tier", "Beliebtes Haustier", "Macht oft Wau"),
    ("🐱", "katze", "Tier", "Beliebtes Haustier", "Macht oft Miau"),
    ("🌈", "regenbogen", "Natur", "Mehrere Farben", "Nach Regen am Himmel"),
    ("⚽", "fußball", "Sport", "Mannschaftssport", "Rundes Spielgerät"),
    ("🏀", "basketball", "Sport", "Mannschaftssport", "Ball und Korb"),
    ("🍔", "burger", "Essen", "Fast Food", "Brot mit Füllung"),
    ("🍎", "apfel", "Obst", "Lebensmittel", "Kann rot oder grün sein"),
    ("☀️", "sonne", "Natur", "Am Himmel", "Bringt Licht und Wärme"),
    ("🌙", "mond", "Weltraum", "Am Himmel", "Sieht man nachts"),
    ("🚑", "rettungswagen", "Fahrzeug", "Blaulicht", "Hilft bei Notfällen"),
    ("🚒", "feuerwehr", "Einsatz", "Blaulicht", "Löscht Brände"),
    ("🚓", "polizei", "Einsatz", "Blaulicht", "Sorgt für Sicherheit"),
    ("✈️", "flugzeug", "Fahrzeug", "Kann fliegen", "Startet von einem Flughafen"),
    ("🚢", "schiff", "Fahrzeug", "Auf dem Wasser", "Kann sehr groß sein"),
    ("🏠", "haus", "Gebäude", "Wohnort", "Hat meistens Türen und Fenster"),
    ("📱", "handy", "Technik", "Elektronisches Gerät", "Kann telefonieren"),
    ("💻", "computer", "Technik", "Elektronisches Gerät", "Wird oft zum Arbeiten genutzt"),
    ("🎸", "gitarre", "Musik", "Instrument", "Hat Saiten"),
    ("🎹", "klavier", "Musik", "Instrument", "Hat viele Tasten"),
    ("📚", "bücher", "Bildung", "Lernmaterial", "Bestehen aus vielen Seiten"),
    ("🎂", "kuchen", "Essen", "Geburtstag", "Oft mit Kerzen"),
    ("❄️", "schnee", "Natur", "Kalt", "Fällt im Winter"),
    ("🔥", "feuer", "Natur", "Sehr heiß", "Kann brennen"),
    ("🌊", "welle", "Natur", "Wasser", "Findet man im Meer")
]


def ensure_emoji_user(user_id):
    uid = str(user_id)
    now = time.time()

    state = data["emoji_quiz"].get(uid)

    if not isinstance(state, dict):
        state = {
            "active": False,
            "question": None,
            "question_index": None,
            "answer": "",
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

        data["emoji_quiz"][uid] = state

    if now >= state.get("usage_reset_at", 0):
        state["tips_used"] = 0
        state["letters_used"] = 0
        state["skips_used"] = 0
        state["usage_reset_at"] = now + 7200

    save_data(data)

    return state


def choose_emoji_question(state):
    old_index = state.get("question_index")

    possible = list(range(len(EMOJI_QUESTIONS)))

    if len(possible) > 1 and old_index in possible:
        possible.remove(old_index)

    index = random.choice(possible)

    emoji, answer, hint1, hint2, hint3 = EMOJI_QUESTIONS[index]

    state["question_index"] = index
    state["question"] = emoji
    state["answer"] = answer
    state["hints"] = [hint1, hint2, hint3]
    state["active"] = True

    return emoji, answer


def emoji_quiz_panel():
    embed = make_embed(
        "🎯 Emoji Quiz",
        (
            "Errate Begriffe anhand von Emojis.\n\n"
            "▶️ **Neues Quiz** – startet eine neue Aufgabe\n"
            "💡 **Tipp anfordern** – bis zu 3 Tipps\n"
            "🔤 **Anfangsbuchstaben** – bis zu 3 Anfragen\n"
            "⏭️ **Aufgabe überspringen** – bis zu 3 Anfragen\n"
            "🏆 **Bestenliste** – persönliche Statistik + Rangliste\n\n"
            "### Wichtig\n"
            "Die Limits gelten **pro Benutzer** und unabhängig vom Quiz.\n"
            "Alle drei Limits werden automatisch alle **2 Stunden** zurückgesetzt."
        ),
        discord.Color.gold()
    )

    embed.set_footer(
        text=f"{EMOJI_QUIZ_PANEL_MARKER} • RLP | RP-System"
    )

    return embed


class EmojiQuizNew(Button):
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

        now = time.time()

        if now - state.get("last_action", 0) < 1.5:
            return await error_response(
                interaction,
                "Bitte warte kurz, bevor du die nächste Aktion ausführst."
            )

        state["last_action"] = now
        state["quiz_channel_id"] = interaction.channel.id

        emoji, answer = choose_emoji_question(state)

        save_data(data)

        embed = make_embed(
            "🎯 Neue Emoji-Aufgabe",
            (
                f"# {emoji}\n\n"
                "Schreibe deine Antwort direkt in diesen Kanal.\n\n"
                "💡 Du kannst bei Bedarf einen Tipp anfordern."
            ),
            discord.Color.gold()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


class EmojiQuizHint(Button):
    def __init__(self):
        super().__init__(
            label="Tipp anfordern",
            emoji="💡",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_emoji_hint"
        )

    async def callback(self, interaction):
        state = ensure_emoji_user(
            interaction.user.id
        )

        if not state.get("active"):
            return await error_response(
                interaction,
                "Starte zuerst mit ▶️ ein neues Quiz."
            )

        if state["tips_used"] >= 3:
            return await error_response(
                interaction,
                "💡 **Tipp-Limit erreicht**\n\n"
                "Du hast bereits **3/3 Tipp-Anfragen** verwendet.\n"
                "Das Tipp-Limit wird automatisch alle **2 Stunden** zurückgesetzt."
            )

        state["tips_used"] += 1

        index = state["tips_used"] - 1
        hint = state["hints"][index]

        save_data(data)

        await interaction.response.send_message(
            embed=make_embed(
                f"💡 Tipp {state['tips_used']}/3",
                hint,
                discord.Color.blue()
            ),
            ephemeral=True
        )


class EmojiQuizLetters(Button):
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

        if not state.get("active"):
            return await error_response(
                interaction,
                "Starte zuerst mit ▶️ ein neues Quiz."
            )

        if state["letters_used"] >= 3:
            return await error_response(
                interaction,
                "🔤 **Anfangsbuchstaben-Limit erreicht**\n\n"
                "Du hast bereits **3/3 Anfangsbuchstaben-Anfragen** verwendet.\n"
                "Das Limit wird automatisch alle **2 Stunden** zurückgesetzt."
            )

        state["letters_used"] += 1

        count = state["letters_used"]

        letters = state["answer"][:count]

        save_data(data)

        await interaction.response.send_message(
            embed=make_embed(
                f"🔤 Anfangsbuchstaben {count}/3",
                f"Die bisher bekannten Buchstaben:\n**{letters.upper()}**",
                discord.Color.blurple()
            ),
            ephemeral=True
        )


class EmojiQuizSkip(Button):
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

        if not state.get("active"):
            return await error_response(
                interaction,
                "Du hast aktuell keine aktive Aufgabe."
            )

        if state["skips_used"] >= 3:
            return await error_response(
                interaction,
                "⏭️ **Überspringen-Limit erreicht**\n\n"
                "Du hast bereits **3/3 Überspringen-Anfragen** verwendet.\n"
                "Das Limit wird automatisch alle **2 Stunden** zurückgesetzt."
            )

        state["skips_used"] += 1
        state["skipped"] += 1
        state["total"] += 1

        old_answer = state["answer"]

        emoji, answer = choose_emoji_question(state)

        save_data(data)

        await interaction.response.send_message(
            embed=make_embed(
                "⏭️ Aufgabe übersprungen",
                (
                    f"Die richtige Antwort war **{old_answer}**.\n\n"
                    f"### Neue Aufgabe\n"
                    f"# {emoji}\n\n"
                    "Antworte direkt im Kanal."
                ),
                discord.Color.orange()
            ),
            ephemeral=True
        )


class EmojiQuizLeaderboard(Button):
    def __init__(self):
        super().__init__(
            label="Bestenliste",
            emoji="🏆",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_emoji_leaderboard"
        )

    async def callback(self, interaction):
        state = ensure_emoji_user(
            interaction.user.id
        )

        entries = []

        for uid, user_state in data["emoji_quiz"].items():
            entries.append(
                (
                    int(user_state.get("score", 0)),
                    int(user_state.get("solved", 0)),
                    uid
                )
            )

        entries.sort(
            key=lambda x: (x[0], x[1]),
            reverse=True
        )

        lines = []

        for position, entry in enumerate(entries[:10], 1):
            score, solved, uid = entry

            member = interaction.guild.get_member(uid)

            if member:
                name = member.display_name
            else:
                name = f"User {uid}"

            lines.append(
                f"**{position}.** {name} — "
                f"🏆 {score} Punkte • ✅ {solved}"
            )

        if not lines:
            lines.append("Noch keine Einträge.")

        reset_at = state["usage_reset_at"]

        reset_text = discord.utils.format_dt(
            datetime.fromtimestamp(
                reset_at,
                tz=timezone.utc
            ),
            style="R"
        )

        embed = make_embed(
            "🏆 Emoji-Quiz Bestenliste",
            (
                "\n".join(lines)
                + "\n\n"
                "### Deine Statistik\n"
                f"🏆 Punkte: **{state['score']}**\n"
                f"✅ Gelöst: **{state['solved']}**\n"
                f"⏭️ Übersprungen: **{state['skipped']}**\n\n"
                f"💡 Tipps: **{state['tips_used']}/3**\n"
                f"🔤 Buchstaben: **{state['letters_used']}/3**\n"
                f"⏭️ Überspringen: **{state['skips_used']}/3**\n\n"
                f"🔄 Reset: {reset_text}"
            ),
            discord.Color.gold()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


class EmojiQuizView(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(EmojiQuizNew())
        self.add_item(EmojiQuizHint())
        self.add_item(EmojiQuizLetters())
        self.add_item(EmojiQuizSkip())
        self.add_item(EmojiQuizLeaderboard())


# ============================================================
# OWNER PANEL
# ============================================================

def owner_check(member):
    return is_owner(member)


def owner_panel():
    embed = make_embed(
        "👑 Owner Panel",
        (
            "Willkommen im **Owner Control Center**.\n\n"
            "Hier stehen dir die wichtigsten Serververwaltungs-Funktionen zur Verfügung.\n\n"
            "### 📢 Kommunikation\n"
            "📢 **Ankündigung senden**\n"
            "💬 **Bot-Nachricht senden**\n\n"
            "### 🔒 Moderation\n"
            "🔒 **Kanal sperren**\n"
            "🔓 **Kanal entsperren**\n"
            "🧹 **Nachrichten löschen**\n\n"
            "### 🛠️ Server\n"
            "📊 **Bot-Status**\n"
            "🖥️ **Server-Info**\n"
            "👤 **User-Info**\n"
            "🎭 **Rollen-Info**\n\n"
            "### 🎉 Events\n"
            "🎁 **Giveaway starten**\n\n"
            "Alle Aktionen werden über das Panel ausgeführt."
        ),
        discord.Color.gold()
    )

    embed.set_footer(
        text=f"{OWNER_PANEL_MARKER} • RLP | Owner System"
    )

    return embed


# ============================================================
# OWNER CHANNEL SELECT
# ============================================================

class OwnerChannelSelect(Select):
    def __init__(self, action):
        self.action = action

        options = []

        for channel in get_guild().text_channels[:25]:
            options.append(
                discord.SelectOption(
                    label=channel.name[:100],
                    value=str(channel.id),
                    description=f"#{channel.name}"[:100]
                )
            )

        super().__init__(
            placeholder="Kanal auswählen...",
            options=options,
            custom_id=f"rlp_owner_channel_{action}"
        )

    async def callback(self, interaction):
        if not owner_check(interaction.user):
            return await error_response(
                interaction,
                "Du hast keine Owner-Berechtigung."
            )

        channel_id = int(self.values[0])
        channel = get_channel(channel_id)

        if not channel:
            return await error_response(
                interaction,
                "Kanal nicht gefunden."
            )

        if self.action == "announcement":
            await interaction.response.send_modal(
                AnnouncementModal(channel)
            )

        elif self.action == "say":
            await interaction.response.send_modal(
                BotSayModal(channel)
            )


# ============================================================
# ANNOUNCEMENT
# ============================================================

class AnnouncementModal(Modal, title="📢 Ankündigung"):

    title_input = TextInput(
        label="Titel",
        placeholder="Titel der Ankündigung",
        max_length=256
    )

    message = TextInput(
        label="Nachricht",
        placeholder="Deine Ankündigung...",
        style=discord.TextStyle.paragraph,
        max_length=4000
    )

    async def on_submit(self, interaction):
        await interaction.response.defer(
            ephemeral=True
        )

        channel = self.channel

        embed = make_embed(
            self.title_input.value,
            self.message.value,
            discord.Color.gold()
        )

        embed.set_author(
            name=f"Ankündigung von {interaction.user.display_name}"
        )

        await channel.send(
            embed=embed
        )

        await interaction.followup.send(
            embed=make_embed(
                "✅ Ankündigung gesendet",
                f"Die Ankündigung wurde in {channel.mention} gesendet.",
                discord.Color.green()
            ),
            ephemeral=True
        )

    def __init__(self, channel):
        super().__init__()
        self.channel = channel


# ============================================================
# BOT SAY
# ============================================================

class BotSayModal(Modal, title="💬 Bot Nachricht"):

    message = TextInput(
        label="Nachricht",
        placeholder="Was soll der Bot schreiben?",
        style=discord.TextStyle.paragraph,
        max_length=4000
    )

    async def on_submit(self, interaction):
        await interaction.response.defer(
            ephemeral=True
        )

        await self.channel.send(
            self.message.value
        )

        await interaction.followup.send(
            embed=make_embed(
                "✅ Nachricht gesendet",
                f"Die Nachricht wurde in {self.channel.mention} gesendet.",
                discord.Color.green()
            ),
            ephemeral=True
        )

    def __init__(self, channel):
        super().__init__()
        self.channel = channel


# ============================================================
# LOCK / UNLOCK
# ============================================================

async def lock_channel(channel):
    guild = channel.guild

    overwrite = channel.overwrites_for(
        guild.default_role
    )

    overwrite.send_messages = False

    await channel.set_permissions(
        guild.default_role,
        overwrite=overwrite,
        reason="Owner Panel – Kanal gesperrt"
    )


async def unlock_channel(channel):
    guild = channel.guild

    overwrite = channel.overwrites_for(
        guild.default_role
    )

    overwrite.send_messages = None

    await channel.set_permissions(
        guild.default_role,
        overwrite=overwrite,
        reason="Owner Panel – Kanal entsperrt"
    )


# ============================================================
# OWNER BUTTONS
# ============================================================

class AnnouncementButton(Button):
    def __init__(self):
        super().__init__(
            label="Ankündigung",
            emoji="📢",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_owner_announcement"
        )

    async def callback(self, interaction):
        if not owner_check(interaction.user):
            return await error_response(
                interaction,
                "Du hast keine Owner-Berechtigung."
            )

        view = View(timeout=60)
        view.add_item(
            OwnerChannelSelect("announcement")
        )

        await interaction.response.send_message(
            embed=make_embed(
                "📢 Ankündigung",
                "Wähle den Kanal, in dem die Ankündigung gesendet werden soll.",
                discord.Color.gold()
            ),
            view=view,
            ephemeral=True
        )


class SayButton(Button):
    def __init__(self):
        super().__init__(
            label="Bot Nachricht",
            emoji="💬",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_owner_say"
        )

    async def callback(self, interaction):
        if not owner_check(interaction.user):
            return await error_response(
                interaction,
                "Du hast keine Owner-Berechtigung."
            )

        view = View(timeout=60)
        view.add_item(
            OwnerChannelSelect("say")
        )

        await interaction.response.send_message(
            embed=make_embed(
                "💬 Bot Nachricht",
                "Wähle den Zielkanal.",
                discord.Color.blurple()
            ),
            view=view,
            ephemeral=True
        )


class LockButton(Button):
    def __init__(self):
        super().__init__(
            label="Kanal sperren",
            emoji="🔒",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_owner_lock"
        )

    async def callback(self, interaction):
        if not owner_check(interaction.user):
            return await error_response(
                interaction,
                "Du hast keine Owner-Berechtigung."
            )

        try:
            await lock_channel(
                interaction.channel
            )

            await interaction.response.send_message(
                embed=make_embed(
                    "🔒 Kanal gesperrt",
                    f"{interaction.channel.mention} wurde gesperrt.",
                    discord.Color.red()
                )
            )

        except discord.Forbidden:
            await error_response(
                interaction,
                "Ich habe keine Berechtigung, diesen Kanal zu sperren."
            )


class UnlockButton(Button):
    def __init__(self):
        super().__init__(
            label="Kanal entsperren",
            emoji="🔓",
            style=discord.ButtonStyle.success,
            custom_id="rlp_owner_unlock"
        )

    async def callback(self, interaction):
        if not owner_check(interaction.user):
            return await error_response(
                interaction,
                "Du hast keine Owner-Berechtigung."
            )

        try:
            await unlock_channel(
                interaction.channel
            )

            await interaction.response.send_message(
                embed=make_embed(
                    "🔓 Kanal entsperrt",
                    f"{interaction.channel.mention} wurde entsperrt.",
                    discord.Color.green()
                )
            )

        except discord.Forbidden:
            await error_response(
                interaction,
                "Ich habe keine Berechtigung, diesen Kanal zu entsperren."
            )


class StatusButton(Button):
    def __init__(self):
        super().__init__(
            label="Bot Status",
            emoji="📊",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_status"
        )

    async def callback(self, interaction):
        if not owner_check(interaction.user):
            return await error_response(
                interaction,
                "Du hast keine Owner-Berechtigung."
            )

        uptime = int(time.time() - BOT_START_TIME)

        days = uptime // 86400
        hours = (uptime % 86400) // 3600
        minutes = (uptime % 3600) // 60

        embed = make_embed(
            "📊 Bot Status",
            (
                f"🟢 **Online:** Ja\n"
                f"⏱️ **Uptime:** {days}d {hours}h {minutes}min\n"
                f"🌐 **Server:** {len(bot.guilds)}\n"
                f"👥 **User:** {len(bot.users)}\n"
                f"📡 **Latency:** {round(bot.latency * 1000)}ms"
            ),
            discord.Color.green()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


class ServerInfoButton(Button):
    def __init__(self):
        super().__init__(
            label="Server Info",
            emoji="🖥️",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_server_info"
        )

    async def callback(self, interaction):
        if not owner_check(interaction.user):
            return await error_response(
                interaction,
                "Du hast keine Owner-Berechtigung."
            )

        guild = interaction.guild

        embed = make_embed(
            "🖥️ Server Informationen",
            (
                f"**Name:** {guild.name}\n"
                f"**ID:** `{guild.id}`\n"
                f"**Owner:** <@{guild.owner_id}>\n"
                f"**Mitglieder:** {guild.member_count}\n"
                f"**Kanäle:** {len(guild.channels)}\n"
                f"**Rollen:** {len(guild.roles)}\n"
                f"**Erstellt:** {discord.utils.format_dt(guild.created_at, 'F')}"
            ),
            discord.Color.blurple()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


class UserInfoButton(Button):
    def __init__(self):
        super().__init__(
            label="User Info",
            emoji="👤",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_user_info"
        )

    async def callback(self, interaction):
        if not owner_check(interaction.user):
            return await error_response(
                interaction,
                "Du hast keine Owner-Berechtigung."
            )

        await interaction.response.send_message(
            embed=make_embed(
                "👤 User Info",
                "Wähle unten einen User aus.",
                discord.Color.blurple()
            ),
            view=UserInfoView(),
            ephemeral=True
        )


class RolesInfoButton(Button):
    def __init__(self):
        super().__init__(
            label="Rollen Info",
            emoji="🎭",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_roles_info"
        )

    async def callback(self, interaction):
        if not owner_check(interaction.user):
            return await error_response(
                interaction,
                "Du hast keine Owner-Berechtigung."
            )

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
            text = text[:3900] + "\n..."

        await interaction.response.send_message(
            embed=make_embed(
                "🎭 Server Rollen",
                text or "Keine Rollen vorhanden.",
                discord.Color.blurple()
            ),
            ephemeral=True
        )


# ============================================================
# USER INFO
# ============================================================

class UserInfoSelect(Select):
    def __init__(self):
        guild = get_guild()

        options = []

        for member in guild.members[:25]:
            options.append(
                discord.SelectOption(
                    label=member.display_name[:100],
                    value=str(member.id),
                    description=f"ID: {member.id}"[:100]
                )
            )

        if not options:
            options.append(
                discord.SelectOption(
                    label="Keine User gefunden",
                    value="none"
                )
            )

        super().__init__(
            placeholder="User auswählen...",
            options=options,
            custom_id="rlp_owner_user_select"
        )

    async def callback(self, interaction):
        if self.values[0] == "none":
            return await error_response(
                interaction,
                "Kein User verfügbar."
            )

        member = interaction.guild.get_member(
            int(self.values[0])
        )

        if not member:
            return await error_response(
                interaction,
                "User nicht gefunden."
            )

        roles = [
            role.mention
            for role in member.roles
            if not role.is_default()
        ]

        embed = make_embed(
            "👤 User Informationen",
            (
                f"**Name:** {member}\n"
                f"**Display Name:** {member.display_name}\n"
                f"**ID:** `{member.id}`\n"
                f"**Bot:** {'Ja' if member.bot else 'Nein'}\n"
                f"**Account erstellt:** {discord.utils.format_dt(member.created_at, 'F')}\n"
                f"**Serverbeitritt:** {discord.utils.format_dt(member.joined_at, 'F') if member.joined_at else 'Unbekannt'}\n\n"
                f"**Rollen:**\n"
                + (
                    "\n".join(roles)
                    if roles
                    else "Keine zusätzlichen Rollen."
                )
            ),
            discord.Color.blurple()
        )

        if member.avatar:
            embed.set_thumbnail(
                url=member.avatar.url
            )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


class UserInfoView(View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(UserInfoSelect())


# ============================================================
# CLEAR MESSAGES
# ============================================================

class ClearMessagesModal(Modal, title="🧹 Nachrichten löschen"):

    amount = TextInput(
        label="Anzahl",
        placeholder="z. B. 20",
        max_length=4
    )

    async def on_submit(self, interaction):
        try:
            amount = int(self.amount.value)
        except ValueError:
            return await error_response(
                interaction,
                "Bitte gib eine gültige Zahl ein."
            )

        if amount < 1 or amount > 100:
            return await error_response(
                interaction,
                "Du kannst zwischen 1 und 100 Nachrichten löschen."
            )

        await interaction.response.defer(
            ephemeral=True
        )

        try:
            deleted = await interaction.channel.purge(
                limit=amount
            )

            await interaction.followup.send(
                embed=make_embed(
                    "🧹 Nachrichten gelöscht",
                    f"Es wurden **{len(deleted)}** Nachrichten gelöscht.",
                    discord.Color.green()
                ),
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.followup.send(
                embed=make_embed(
                    "❌ Keine Berechtigung",
                    "Ich darf hier keine Nachrichten löschen.",
                    discord.Color.red()
                ),
                ephemeral=True
            )


async def clear_channel(channel, amount):
    return await channel.purge(
        limit=amount
    )


class ClearButton(Button):
    def __init__(self):
        super().__init__(
            label="Nachrichten löschen",
            emoji="🧹",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_owner_clear"
        )

    async def callback(self, interaction):
        if not owner_check(interaction.user):
            return await error_response(
                interaction,
                "Du hast keine Owner-Berechtigung."
            )

        await interaction.response.send_modal(
            ClearMessagesModal()
        )


# ============================================================
# GIVEAWAY
# ============================================================

class GiveawayModal(Modal, title="🎁 Giveaway starten"):

    prize = TextInput(
        label="Gewinn",
        placeholder="z. B. 10.000$",
        max_length=200
    )

    duration = TextInput(
        label="Dauer in Minuten",
        placeholder="z. B. 60",
        max_length=5
    )

    winners = TextInput(
        label="Anzahl Gewinner",
        placeholder="z. B. 1",
        max_length=3
    )

    async def on_submit(self, interaction):
        try:
            duration = int(self.duration.value)
            winners = int(self.winners.value)
        except ValueError:
            return await error_response(
                interaction,
                "Dauer und Gewinner müssen Zahlen sein."
            )

        if duration < 1:
            return await error_response(
                interaction,
                "Die Giveaway-Dauer muss mindestens 1 Minute betragen."
            )

        if duration > 10080:
            return await error_response(
                interaction,
                "Die maximale Giveaway-Dauer beträgt 7 Tage."
            )

        if winners < 1 or winners > 50:
            return await error_response(
                interaction,
                "Die Gewinneranzahl muss zwischen 1 und 50 liegen."
            )

        end_time = time.time() + duration * 60

        embed = make_embed(
            "🎁 GIVEAWAY",
            (
                f"## 🎉 {self.prize.value}\n\n"
                f"🏆 **Gewinner:** {winners}\n"
                f"⏰ **Endet:** <t:{int(end_time)}:R>\n\n"
                "Klicke auf 🎉, um teilzunehmen!\n\n"
                f"**Gestartet von:** {interaction.user.mention}"
            ),
            discord.Color.gold()
        )

        embed.set_footer(
            text="RLP | Giveaway"
        )

        message = await interaction.channel.send(
            embed=embed
        )

        await message.add_reaction("🎉")

        asyncio.create_task(
            finish_giveaway(
                channel_id=interaction.channel.id,
                message_id=message.id,
                prize=self.prize.value,
                winners_count=winners,
                end_time=end_time
            )
        )

        await interaction.response.send_message(
            embed=make_embed(
                "✅ Giveaway gestartet",
                (
                    f"Das Giveaway für **{self.prize.value}** wurde gestartet.\n"
                    f"Ende: <t:{int(end_time)}:R>"
                ),
                discord.Color.green()
            ),
            ephemeral=True
        )


async def finish_giveaway(
    channel_id,
    message_id,
    prize,
    winners_count,
    end_time
):
    wait_time = max(
        0,
        end_time - time.time()
    )

    await asyncio.sleep(wait_time)

    channel = get_channel(channel_id)

    if not channel:
        return

    try:
        message = await channel.fetch_message(
            message_id
        )
    except Exception:
        return

    users = []

    for reaction in message.reactions:
        if str(reaction.emoji) == "🎉":
            try:
                async for user in reaction.users():
                    if user.bot:
                        continue

                    users.append(user)

            except Exception as e:
                print(f"[GIVEAWAY USERS] {e}")

    unique_users = list(
        {
            user.id: user
            for user in users
        }.values()
    )

    if not unique_users:
        await channel.send(
            embed=make_embed(
                "🎁 Giveaway beendet",
                (
                    f"Das Giveaway für **{prize}** ist beendet.\n\n"
                    "Leider gab es keine Teilnehmer."
                ),
                discord.Color.red()
            )
        )
        return

    winners = random.sample(
        unique_users,
        min(winners_count, len(unique_users))
    )

    winner_mentions = ", ".join(
        user.mention
        for user in winners
    )

    embed = make_embed(
        "🎉 Giveaway beendet",
        (
            f"**Gewinn:** {prize}\n\n"
            f"🏆 **Gewinner:**\n{winner_mentions}\n\n"
            "Herzlichen Glückwunsch!"
        ),
        discord.Color.green()
    )

    await channel.send(
        content=winner_mentions,
        embed=embed
    )


class GiveawayStartButton(Button):
    def __init__(self):
        super().__init__(
            label="Giveaway starten",
            emoji="🎁",
            style=discord.ButtonStyle.success,
            custom_id="rlp_owner_giveaway"
        )

    async def callback(self, interaction):
        if not owner_check(interaction.user):
            return await error_response(
                interaction,
                "Du hast keine Owner-Berechtigung."
            )

        await interaction.response.send_modal(
            GiveawayModal()
        )


# ============================================================
# OWNER VIEW
# ============================================================

class OwnerView(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(AnnouncementButton())
        self.add_item(SayButton())
        self.add_item(LockButton())
        self.add_item(UnlockButton())

        self.add_item(StatusButton())
        self.add_item(ServerInfoButton())
        self.add_item(UserInfoButton())
        self.add_item(RolesInfoButton())

        self.add_item(ClearButton())
        self.add_item(GiveawayStartButton())


# ============================================================
# NUMBER GAME
# ============================================================

def number_game_panel():
    current = data["number_game"]["current_number"]

    embed = make_embed(
        "🔢 Zahlenspiel",
        (
            "# 1 → ∞\n\n"
            "Zählt gemeinsam von **1 bis unendlich**.\n\n"
            f"🔢 **Aktuell erwartet:** `{current}`\n\n"
            "### Regeln\n"
            "✅ Schreibe immer die nächste richtige Zahl.\n"
            "❌ Eine falsche Zahl setzt das Spiel sofort wieder auf **1**.\n"
            "👥 Eine Person darf **nicht zweimal hintereinander** eine richtige Zahl schreiben.\n"
            "⚠️ Falsche Eingaben führen bei wiederholten Verstößen zu steigenden Timeouts.\n"
            "🎉 Bei **100, 200, 300, ...** gibt es ein Easter Egg."
        ),
        discord.Color.blue()
    )

    embed.set_footer(
        text=f"{NUMBER_GAME_PANEL_MARKER} • RLP | Zahlenspiel"
    )

    return embed


def wrong_timeout_minutes(wrong_count):
    if wrong_count < 4:
        return 0

    # 4 Fehler = 5 Minuten
    # Danach alle weiteren 10 Fehler +5 Minuten
    level = 1 + ((wrong_count - 4) // 10)

    minutes = 5 * level

    return min(minutes, 24 * 60)


async def apply_number_timeout(member, wrong_count):
    minutes = wrong_timeout_minutes(
        wrong_count
    )

    if minutes <= 0:
        return False, minutes

    if not member.guild.me.guild_permissions.moderate_members:
        return False, minutes

    try:
        await member.timeout(
            timedelta(minutes=minutes),
            reason=f"Zahlenspiel: {wrong_count} falsche Eingaben"
        )

        return True, minutes

    except discord.Forbidden:
        return False, minutes

    except Exception as e:
        print(f"[NUMBER TIMEOUT] {e}")
        return False, minutes


async def refresh_number_game_panel():
    await update_panel(
        NUMBER_GAME_CHANNEL_ID,
        NUMBER_GAME_PANEL_MARKER,
        number_game_panel(),
        None
    )


# ============================================================
# COMMANDS
# ============================================================

@bot.command(name="nametagpanel")
@commands.guild_only()
async def nametagpanel_command(ctx):
    if not is_owner(ctx.author):
        return

    await update_panel(
        NAMETAG_CHANNEL_ID,
        NAMETAG_PANEL_MARKER,
        nametag_panel(),
        NametagView()
    )

    await ctx.send(
        "✅ Nametag Panel aktualisiert.",
        delete_after=5
    )


@bot.command(name="licensepanel")
@commands.guild_only()
async def licensepanel_command(ctx):
    if not is_owner(ctx.author):
        return

    await refresh_license_panel()

    await ctx.send(
        "✅ Kennzeichen Panel aktualisiert.",
        delete_after=5
    )


@bot.command(name="bewerbungpanel")
@commands.guild_only()
async def bewerbungpanel_command(ctx):
    if not is_owner(ctx.author):
        return

    await update_panel(
        APPLICATION_CHANNEL_ID,
        APPLICATION_PANEL_MARKER,
        application_panel(),
        ApplicationView()
    )

    await ctx.send(
        "✅ Bewerbungs-Panel aktualisiert.",
        delete_after=5
    )


@bot.command(name="devtaskpanel")
@commands.guild_only()
async def devtaskpanel_command(ctx):
    if not is_owner(ctx.author):
        return

    await update_panel(
        DEVELOPER_TASK_CHANNEL_ID,
        DEV_TASK_PANEL_MARKER,
        developer_task_panel(),
        DeveloperTaskView()
    )

    await ctx.send(
        "✅ Developer-Task-Panel aktualisiert.",
        delete_after=5
    )


@bot.command(name="devshiftpanel")
@commands.guild_only()
async def devshiftpanel_command(ctx):
    if not is_owner(ctx.author):
        return

    await refresh_shift_panel()

    await ctx.send(
        "✅ Developer-Shift-Panel aktualisiert.",
        delete_after=5
    )


@bot.command(name="communitypanel")
@commands.guild_only()
async def communitypanel_command(ctx):
    if not is_owner(ctx.author):
        return

    # WICHTIG:
    # Community Panel kommt genau in den Kanal,
    # in dem ?communitypanel ausgeführt wurde.
    await update_panel(
        ctx.channel.id,
        COMMUNITY_PANEL_MARKER,
        community_panel(),
        CommunityView()
    )

    await ctx.send(
        "✅ Community Panel wurde in diesem Kanal aktualisiert.",
        delete_after=5
    )


@bot.command(
    name="ownerpanel",
    aliases=["owner"]
)
@commands.guild_only()
async def ownerpanel_command(ctx):
    if not owner_check(ctx.author):
        await ctx.send(
            "❌ Du hast keine Owner-Berechtigung.",
            delete_after=5
        )
        return

    # WICHTIG:
    # Owner Panel kommt IMMER in den aktuellen Command-Kanal.
    panel = await update_panel(
        ctx.channel.id,
        OWNER_PANEL_MARKER,
        owner_panel(),
        OwnerView()
    )

    if panel:
        await ctx.send(
            "✅ Owner Panel wurde hier aktualisiert.",
            delete_after=5
        )
    else:
        await ctx.send(
            "❌ Das Owner Panel konnte nicht gesendet werden. "
            "Prüfe die Bot-Berechtigungen für diesen Kanal.",
            delete_after=8
        )


@bot.command(
    name="emojiquizpanel",
    aliases=["emojiquiz"]
)
@commands.guild_only()
async def emojiquizpanel_command(ctx):
    if not is_owner(ctx.author):
        return

    await update_panel(
        ctx.channel.id,
        EMOJI_QUIZ_PANEL_MARKER,
        emoji_quiz_panel(),
        EmojiQuizView()
    )

    await ctx.send(
        "✅ Emoji-Quiz Panel wurde hier aktualisiert.",
        delete_after=5
    )


@bot.command(
    name="zahlenspiel",
    aliases=["numbergame"]
)
@commands.guild_only()
async def numbergame_command(ctx):
    if not is_owner(ctx.author):
        return

    await refresh_number_game_panel()

    await ctx.send(
        "✅ Zahlenspiel-Panel aktualisiert.",
        delete_after=5
    )


# ============================================================
# HELP
# ============================================================

@bot.command(name="help")
@commands.guild_only()
async def help_command(ctx):
    embed = make_embed(
        "📚 RLP Bot Hilfe",
        (
            "### 👥 Allgemein\n"
            "`?help` – Diese Hilfe\n\n"
            "### 🏷️ Systeme\n"
            "`?nametagpanel`\n"
            "`?licensepanel`\n"
            "`?bewerbungpanel`\n"
            "`?devtaskpanel`\n"
            "`?devshiftpanel`\n"
            "`?communitypanel`\n"
            "`?emojiquizpanel`\n"
            "`?zahlenspiel`\n\n"
            "### 👑 Owner\n"
            "`?ownerpanel`\n"
            "`?owner`"
        ),
        discord.Color.blurple()
    )

    if is_owner(ctx.author):
        embed.add_field(
            name="👑 Owner-Funktionen",
            value=(
                "📢 Ankündigungen\n"
                "💬 Bot-Nachrichten\n"
                "🔒 Kanäle sperren\n"
                "🔓 Kanäle entsperren\n"
                "🧹 Nachrichten löschen\n"
                "📊 Bot Status\n"
                "🖥️ Server Info\n"
                "👤 User Info\n"
                "🎭 Rollen Info\n"
                "🎁 Giveaways"
            ),
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
        commands.MissingRequiredArgument
    ):
        await ctx.send(
            "❌ Es fehlen erforderliche Argumente.",
            delete_after=5
        )
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

    print(
        f"[COMMAND ERROR] {ctx.command}: {error}"
    )


# ============================================================
# STATUS
# ============================================================

@tasks.loop(seconds=15)
async def rotate_bot_status():
    if not bot.user:
        return

    text = random.choice(
        STATUS_TEXTS
    )

    try:
        await bot.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=text
            )
        )
    except Exception as e:
        print(f"[STATUS] {e}")


# ============================================================
# READY
# ============================================================

startup_done = False


@bot.event
async def on_ready():
    global startup_done

    print(
        f"✅ Eingeloggt als {bot.user} "
        f"({bot.user.id})"
    )

    if not startup_done:
        startup_done = True

        # Persistent Views
        bot.add_view(NametagView())
        bot.add_view(PlateView())
        bot.add_view(ApplicationView())
        bot.add_view(DeveloperTaskView())
        bot.add_view(ShiftView())
        bot.add_view(CommunityView())
        bot.add_view(OwnerView())
        bot.add_view(EmojiQuizView())

        # Feste Panels aktualisieren
        await update_panel(
            NAMETAG_CHANNEL_ID,
            NAMETAG_PANEL_MARKER,
            nametag_panel(),
            NametagView()
        )

        await refresh_license_panel()

        await update_panel(
            APPLICATION_CHANNEL_ID,
            APPLICATION_PANEL_MARKER,
            application_panel(),
            ApplicationView()
        )

        await update_panel(
            DEVELOPER_TASK_CHANNEL_ID,
            DEV_TASK_PANEL_MARKER,
            developer_task_panel(),
            DeveloperTaskView()
        )

        await refresh_shift_panel()

        # Zahlenspiel bleibt im festen Zahlenspiel-Kanal.
        await refresh_number_game_panel()

        # WICHTIG:
        # Community Panel und Owner Panel werden hier NICHT
        # automatisch irgendwo erstellt.
        #
        # Sie werden ausschließlich dort erstellt/aktualisiert,
        # wo ?communitypanel bzw. ?ownerpanel ausgeführt werden.

    if not rotate_bot_status.is_running():
        rotate_bot_status.start()


# ============================================================
# MESSAGE HANDLER
# ============================================================

def normalize_answer(text):
    text = text.casefold()
    text = unicodedata.normalize(
        "NFKD",
        text
    )

    text = "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )

    text = re.sub(
        r"[^a-z0-9äöüß ]",
        "",
        text
    )

    return " ".join(
        text.split()
    )


async def handle_emoji_answer(message):
    uid = str(message.author.id)

    state = data["emoji_quiz"].get(uid)

    if not state:
        return False

    if not state.get("active"):
        return False

    if state.get("quiz_channel_id") != message.channel.id:
        return False

    if message.content.startswith(PREFIX):
        return False

    answer = normalize_answer(
        message.content
    )

    correct = normalize_answer(
        state.get("answer", "")
    )

    if answer != correct:
        return False

    solved_answer = state["answer"]

    state["active"] = False
    state["score"] = state.get("score", 0) + 1
    state["solved"] = state.get("solved", 0) + 1
    state["total"] = state.get("total", 0) + 1

    save_data(data)

    await message.reply(
        embed=make_embed(
            "🎉 Richtig!",
            (
                f"Glückwunsch {message.author.mention}!\n\n"
                f"Die Antwort war **{solved_answer}**.\n"
                f"🏆 Punkte: **{state['score']}**"
            ),
            discord.Color.green()
        ),
        mention_author=False
    )

    return True


async def handle_number_game(message):
    if message.author.bot:
        return

    if message.channel.id != NUMBER_GAME_CHANNEL_ID:
        return

    # Nur reine Ganzzahlen zählen als Eingabe.
    if not re.fullmatch(
        r"\d+",
        message.content.strip()
    ):
        return

    try:
        number = int(
            message.content.strip()
        )
    except ValueError:
        return

    game = data["number_game"]

    expected = game["current_number"]
    last_user_id = game.get("last_user_id")

    # --------------------------------------------------------
    # RICHTIGE ZAHL
    # --------------------------------------------------------

    if number == expected:

        # Gleiche Person darf nicht zweimal nacheinander.
        if last_user_id == message.author.id:
            await message.reply(
                embed=make_embed(
                    "⚠️ Andere Person erforderlich",
                    (
                        "Du hast gerade die letzte richtige Zahl gesetzt.\n\n"
                        "Die nächste Zahl muss von **einer anderen Person** "
                        "geschrieben werden.\n\n"
                        f"🔢 Die erwartete Zahl bleibt **{expected}**."
                    ),
                    discord.Color.orange()
                ),
                mention_author=False
            )

            return

        game["current_number"] += 1
        game["last_user_id"] = message.author.id

        save_data(data)

        await message.reply(
            embed=make_embed(
                "✅ Richtig!",
                (
                    f"{message.author.mention} hat **{number}** korrekt gesetzt.\n\n"
                    f"➡️ Als Nächstes wird **{game['current_number']}** erwartet."
                ),
                discord.Color.green()
            ),
            mention_author=False
        )

        # Easter Egg bei 100, 200, 300...
        if number >= 100 and number % 100 == 0:
            if game.get("last_easter_egg", 0) != number:
                game["last_easter_egg"] = number
                save_data(data)

                easter_messages = [
                    f"🎉 **{number}!** Ihr habt einen weiteren Meilenstein erreicht!",
                    f"🚀 **{number} erreicht!** Die Community zieht durch!",
                    f"🏆 **{number}!** Starkes Teamwork!",
                    f"✨ **{number}** — nächster Meilenstein wartet!"
                ]

                await message.channel.send(
                    embed=make_embed(
                        "🎉 EASTER EGG",
                        random.choice(easter_messages),
                        discord.Color.gold()
                    )
                )

        return

    # --------------------------------------------------------
    # FALSCHE ZAHL
    # --------------------------------------------------------

    wrong_attempts = game.get(
        "wrong_attempts",
        {}
    )

    uid = str(message.author.id)

    wrong_attempts[uid] = (
        int(wrong_attempts.get(uid, 0)) + 1
    )

    game["wrong_attempts"] = wrong_attempts

    old_expected = expected

    game["current_number"] = 1
    game["last_user_id"] = None

    save_data(data)

    wrong_count = wrong_attempts[uid]

    timeout_applied, timeout_minutes = (
        await apply_number_timeout(
            message.author,
            wrong_count
        )
    )

    description = (
        f"{message.author.mention} hat **{number}** geschrieben.\n\n"
        f"❌ Erwartet wurde **{old_expected}**.\n\n"
        "🔄 Das Zahlenspiel wurde auf **1** zurückgesetzt.\n\n"
        f"⚠️ Deine falschen Eingaben: **{wrong_count}**"
    )

    if timeout_applied:
        description += (
            f"\n\n⏱️ Aufgrund der Anzahl falscher Eingaben "
            f"wurde eine **{timeout_minutes}-minütige Auszeit** verhängt."
        )
    elif wrong_timeout_minutes(wrong_count) > 0:
        description += (
            "\n\n⚠️ Das nächste Timeout-Level wäre erreicht, "
            "aber der Bot konnte keine Auszeit setzen."
        )

    await message.reply(
        embed=make_embed(
            "❌ Falsche Zahl",
            description,
            discord.Color.red()
        ),
        mention_author=False
    )


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Zahlenspiel
    await handle_number_game(
        message
    )

    # Emoji Quiz
    await handle_emoji_answer(
        message
    )

    # Commands
    await bot.process_commands(
        message
    )


# ============================================================
# START
# ============================================================

def start_bot():
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN wurde nicht gefunden."
        )

    bot.run(TOKEN)


if __name__ == "__main__":
    start_bot()
