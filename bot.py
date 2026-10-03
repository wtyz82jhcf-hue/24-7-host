import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, ChannelSelect
import os
import json
import asyncio
import random as random_module
import time
from datetime import datetime


# =========================================================
# CONFIG
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1519481018221072454

QUIZ_CHANNEL_ID = 1533409789256925185

APPLICATION_CHANNEL_ID = 1541391365219295343
REVIEW_CHANNEL_ID = 1548404201493762181

NAMETAG_CHANNEL_ID = 1555684071911202836
LICENSE_PLATE_CHANNEL_ID = 1527350468832006276

SUPPORT_VOICE_CHANNEL_ID = 1519788919254679602
SUPPORT_LOG_CHANNEL_ID = 1521439814863151155

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
SHIFT_PANEL_MARKER = "RLP_SHIFT_PANEL"
OWNER_PANEL_MARKER = "RLP_OWNER_PANEL"
COMMUNITY_PANEL_MARKER = "RLP_COMMUNITY_PANEL"


# =========================================================
# BOT
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

BOT_START_TIME = time.time()


# =========================================================
# DATA
# =========================================================

def default_data():
    return {
        "license_plates": {},
        "developer_tasks": {},
        "suggestions": {},
        "applications": {}
    }


def load_data():

    if not os.path.exists(DATA_FILE):
        return default_data()

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        defaults = default_data()

        for key, value in defaults.items():

            if key not in data:
                data[key] = value

        return data

    except Exception as e:

        print(
            f"DATA LOAD ERROR: {type(e).__name__}: {e}"
        )

        return default_data()


def save_data():

    try:

        with open(
            DATA_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

    except Exception as e:

        print(
            f"DATA SAVE ERROR: {type(e).__name__}: {e}"
        )


data = load_data()


# =========================================================
# GLOBALS
# =========================================================

quiz_message_id = None
quiz_answer = None
quiz_lock = asyncio.Lock()
quiz_starting = False

used_quiz_questions = set()

views_registered = False


# =========================================================
# QUIZ QUESTIONS
# =========================================================

QUIZ_QUESTIONS = [
    ("🇺🇸🗽", "usa"),
    ("🇩🇪🍺", "deutschland"),
    ("🇫🇷🗼", "frankreich"),
    ("🇮🇹🍕", "italien"),
    ("🇯🇵🗾", "japan"),
    ("🇬🇧👑", "uk"),
    ("🌞🌍", "sonne"),
    ("🌧️☔", "regen"),
    ("🔥💧", "wasser"),
    ("🐶", "hund"),
    ("🐱", "katze"),
    ("🦁", "löwe"),
    ("🐘", "elefant"),
    ("🍎", "apfel"),
    ("🍌", "banane"),
    ("🍕", "pizza"),
    ("🍔", "burger"),
    ("🚗", "auto"),
    ("✈️", "flugzeug"),
    ("🚲", "fahrrad"),
    ("🌙⭐", "nacht"),
    ("❄️☃️", "winter"),
    ("🌹❤️", "liebe"),
    ("⚽🥅", "fußball"),
    ("🏀⛹️", "basketball"),
]


# =========================================================
# HELPERS
# =========================================================

def get_channel(channel_id):

    return bot.get_channel(channel_id)


def has_role(member, role_id):

    if not isinstance(member, discord.Member):
        return False

    return any(
        role.id == role_id
        for role in member.roles
    )


def is_owner(member):

    return has_role(
        member,
        OWNER_ROLE_ID
    )


def is_suggestion_reviewer(member):

    return has_role(
        member,
        SUGGESTION_REVIEW_ROLE_ID
    )


def is_shift_allowed(member):

    return has_role(
        member,
        SHIFT_PERMISSION_ROLE_ID
    )


def is_developer_shift_allowed(member):

    return has_role(
        member,
        SHIFT_PERMISSION_ROLE_ID
    )


async def safe_delete(message):

    try:

        await message.delete()

    except Exception:

        pass


def uptime_string():

    seconds = int(
        time.time() - BOT_START_TIME
    )

    days = seconds // 86400
    seconds %= 86400

    hours = seconds // 3600
    seconds %= 3600

    minutes = seconds // 60
    seconds %= 60

    parts = []

    if days:
        parts.append(f"{days}d")

    if hours:
        parts.append(f"{hours}h")

    if minutes:
        parts.append(f"{minutes}m")

    parts.append(f"{seconds}s")

    return " ".join(parts)


async def delete_panel_messages(
    channel,
    marker
):

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        return

    try:

        async for message in channel.history(
            limit=100
        ):

            if message.author.id != bot.user.id:
                continue

            found = False

            if message.embeds:

                for embed in message.embeds:

                    if marker in (
                        embed.description or ""
                    ):
                        found = True

                    for field in embed.fields:

                        if marker in field.value:
                            found = True

                        if marker in field.name:
                            found = True

            if found:

                try:
                    await message.delete()
                except Exception:
                    pass

    except Exception as e:

        print(
            f"Panel Delete Fehler: {marker}: {e}"
        )


async def find_panel_message(marker):

    guild = bot.get_guild(GUILD_ID)

    if guild is None:
        return None

    for channel in guild.text_channels:

        try:

            async for message in channel.history(
                limit=100
            ):

                if message.author.id != bot.user.id:
                    continue

                for embed in message.embeds:

                    if marker in (
                        embed.description or ""
                    ):
                        return message

                    for field in embed.fields:

                        if marker in field.name:
                            return message

                        if marker in field.value:
                            return message

        except Exception:
            continue

    return None


# =========================================================
# EMOJI QUIZ
# =========================================================

async def send_quiz_question():

    global quiz_message_id
    global quiz_answer
    global quiz_starting
    global used_quiz_questions

    async with quiz_lock:

        if quiz_starting:
            return

        quiz_starting = True

        try:

            channel = get_channel(
                QUIZ_CHANNEL_ID
            )

            if not isinstance(
                channel,
                discord.TextChannel
            ):
                print(
                    "❌ Quiz-Kanal nicht gefunden:"
                    f" {QUIZ_CHANNEL_ID}"
                )
                return

            if len(used_quiz_questions) >= len(
                QUIZ_QUESTIONS
            ):
                used_quiz_questions.clear()

            available = [
                i
                for i in range(
                    len(QUIZ_QUESTIONS)
                )
                if i not in used_quiz_questions
            ]

            if not available:
                used_quiz_questions.clear()

                available = list(
                    range(
                        len(QUIZ_QUESTIONS)
                    )
                )

            index = random_module.choice(
                available
            )

            used_quiz_questions.add(index)

            emoji_text, answer = (
                QUIZ_QUESTIONS[index]
            )

            message = await channel.send(
                "🧠 **Emoji Quiz**\n\n"
                f"## {emoji_text}\n\n"
                "Schreibe deine Antwort!"
            )

            quiz_message_id = message.id
            quiz_answer = answer.lower().strip()

            print(
                f"✅ Neues Emoji Quiz: "
                f"{emoji_text} -> {answer}"
            )

        except Exception as e:

            print(
                "❌ Quiz Fehler:"
                f" {type(e).__name__}: {e}"
            )

        finally:

            quiz_starting = False


async def reset_quiz():

    global quiz_message_id
    global quiz_answer

    channel = get_channel(
        QUIZ_CHANNEL_ID
    )

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        print(
            "❌ Quiz-Kanal nicht gefunden:"
            f" {QUIZ_CHANNEL_ID}"
        )
        return

    old_id = quiz_message_id

    quiz_message_id = None
    quiz_answer = None

    if old_id:

        try:

            old_message = await channel.fetch_message(
                old_id
            )

            await old_message.delete()

        except Exception:
            pass

    # Alte Bot-Quiznachrichten suchen.
    try:

        async for message in channel.history(
            limit=50
        ):

            if message.author.id != bot.user.id:
                continue

            if message.content.startswith(
                "🧠 **Emoji Quiz**"
            ):

                try:
                    await message.delete()
                except Exception:
                    pass

    except Exception as e:

        print(
            f"Quiz Cleanup Fehler: {e}"
        )

    await send_quiz_question()


# =========================================================
# NAMETAG
# =========================================================

def remove_nametag_prefix(nickname):

    if not nickname:
        return nickname

    prefixes = [
        "RLP | ",
        "RLP |",
        "RLP\u00a0|\u00a0",
        "RLP\u00a0| ",
        "RLP | \u00a0"
    ]

    result = nickname

    for prefix in prefixes:

        if result.startswith(prefix):
            return result[len(prefix):]

    return result


class NametagAddModal(Modal):

    def __init__(self):

        super().__init__(
            title="Nametag hinzufügen"
        )

        self.name_input = TextInput(
            label="Name",
            placeholder="Dein gewünschter Name",
            required=True,
            max_length=32
        )

        self.add_item(
            self.name_input
        )

    async def on_submit(
        self,
        interaction
    ):

        if not has_role(
            interaction.user,
            NAMETAG_ROLE_ID
        ):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )

            return

        member = interaction.guild.get_member(
            interaction.user.id
        )

        if member is None:

            await interaction.response.send_message(
                "❌ Mitglied konnte nicht gefunden werden.",
                ephemeral=True
            )

            return

        nickname = (
            f"{NAMETAG}"
            f"{self.name_input.value.strip()}"
        )

        try:

            await member.edit(
                nick=nickname,
                reason="Nametag über Panel"
            )

            await interaction.response.send_message(
                f"✅ Dein Nametag wurde auf `{nickname}` gesetzt.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Der Bot kann deinen Nicknamen nicht ändern. "
                "Prüfe die Rollen-Hierarchie.",
                ephemeral=True
            )


class NametagResetButton(Button):

    def __init__(self):

        super().__init__(
            label="Nametag entfernen",
            emoji="🗑️",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_nametag_reset"
        )

    async def callback(
        self,
        interaction
    ):

        member = interaction.guild.get_member(
            interaction.user.id
        )

        if member is None:

            await interaction.response.send_message(
                "❌ Mitglied nicht gefunden.",
                ephemeral=True
            )

            return

        if not member.nick:

            await interaction.response.send_message(
                "ℹ️ Du hast keinen gesetzten Nicknamen.",
                ephemeral=True
            )

            return

        new_nick = remove_nametag_prefix(
            member.nick
        )

        if new_nick == member.nick:

            await interaction.response.send_message(
                "ℹ️ Dein Nickname enthält keinen RLP-Nametag.",
                ephemeral=True
            )

            return

        try:

            await member.edit(
                nick=new_nick,
                reason="Nametag entfernt"
            )

            await interaction.response.send_message(
                "✅ Der RLP-Nametag wurde entfernt.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Der Bot kann deinen Nicknamen nicht ändern.",
                ephemeral=True
            )


class NametagButton(Button):

    def __init__(self):

        super().__init__(
            label="Nametag setzen",
            emoji="🏷️",
            style=discord.ButtonStyle.success,
            custom_id="rlp_nametag_add"
        )

    async def callback(
        self,
        interaction
    ):

        if not has_role(
            interaction.user,
            NAMETAG_ROLE_ID
        ):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            NametagAddModal()
        )


class NametagView(View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        self.add_item(
            NametagButton()
        )

        self.add_item(
            NametagResetButton()
        )


async def update_nametag_panel():

    channel = get_channel(
        NAMETAG_CHANNEL_ID
    )

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        return

    # WICHTIG:
    # Nametags werden hier NICHT verändert.
    # Das Panel wird nur erstellt, wenn noch keines existiert.

    existing = None

    try:

        async for message in channel.history(
            limit=100
        ):

            if message.author.id != bot.user.id:
                continue

            for embed in message.embeds:

                if NAMETAG_PANEL_MARKER in (
                    embed.description or ""
                ):
                    existing = message
                    break

            if existing:
                break

    except Exception:
        pass

    if existing:
        return

    embed = discord.Embed(
        title="🏷️ Nametag System",
        description=(
            "Hier kannst du deinen RLP-Nametag verwalten.\n\n"
            "🏷️ **Nametag setzen**\n"
            "Setzt `RLP | ` vor deinen Namen.\n\n"
            "🗑️ **Nametag entfernen**\n"
            "Entfernt nur den RLP-Präfix."
        ),
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Panel",
        value=NAMETAG_PANEL_MARKER,
        inline=False
    )

    await channel.send(
        embed=embed,
        view=NametagView()
    )


# =========================================================
# KENNZEICHEN
# =========================================================

class LicensePlateModal(Modal):

    def __init__(self):

        super().__init__(
            title="Kennzeichen erstellen"
        )

        self.plate_input = TextInput(
            label="Kennzeichen",
            placeholder="z.B. RLP 01",
            required=True,
            max_length=20
        )

        self.add_item(
            self.plate_input
        )

    async def on_submit(
        self,
        interaction
    ):

        value = (
            self.plate_input.value
            .strip()
            .upper()
        )

        parts = value.split()

        if len(parts) < 2:

            await interaction.response.send_message(
                "❌ Bitte Prefix und Nummer angeben. "
                "Beispiel: `RLP 01`",
                ephemeral=True
            )

            return

        numeric = parts[-1]

        if not numeric.isdigit():

            await interaction.response.send_message(
                "❌ Die letzte Kennzeichen-Gruppe muss eine Zahl sein.",
                ephemeral=True
            )

            return

        # Genau eine Nummer pro Nutzer
        user_id = str(
            interaction.user.id
        )

        for owner_id, plate in data[
            "license_plates"
        ].items():

            if owner_id == user_id:

                await interaction.response.send_message(
                    "❌ Du hast bereits ein Kennzeichen.",
                    ephemeral=True
                )

                return

            existing_parts = plate.split()

            if existing_parts:

                existing_number = (
                    existing_parts[-1]
                )

                # Globale Nummernsperre
                if existing_number == numeric:

                    await interaction.response.send_message(
                        "❌ Diese Nummer wird bereits verwendet.",
                        ephemeral=True
                    )

                    return

        data["license_plates"][
            user_id
        ] = value

        save_data()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen `{value}` wurde erstellt.",
            ephemeral=True
        )

        await update_license_panel()


class LicensePlateButton(Button):

    def __init__(self):

        super().__init__(
            label="Kennzeichen erstellen",
            emoji="🚗",
            style=discord.ButtonStyle.success,
            custom_id="rlp_license_create"
        )

    async def callback(
        self,
        interaction
    ):

        await interaction.response.send_modal(
            LicensePlateModal()
        )


class LicensePlateView(View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        self.add_item(
            LicensePlateButton()
        )


async def update_license_panel():

    channel = get_channel(
        LICENSE_PLATE_CHANNEL_ID
    )

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        return

    await delete_panel_messages(
        channel,
        LICENSE_PANEL_MARKER
    )

    embed = discord.Embed(
        title="🚗 Kennzeichen",
        description=(
            "Hier kannst du dein Kennzeichen erstellen.\n\n"
            "⚠️ Jeder Nutzer kann nur **ein Kennzeichen** besitzen.\n"
            "⚠️ Die Nummer am Ende darf serverweit nicht doppelt vorkommen."
        ),
        color=discord.Color.blue()
    )

    if data["license_plates"]:

        lines = []

        for user_id, plate in data[
            "license_plates"
        ].items():

            member = channel.guild.get_member(
                int(user_id)
            )

            if member:

                name = member.display_name

            else:

                name = f"User {user_id}"

            lines.append(
                f"🚗 `{plate}` — **{name}**"
            )

        embed.add_field(
            name="Aktuelle Kennzeichen",
            value="\n".join(lines),
            inline=False
        )

    else:

        embed.add_field(
            name="Aktuelle Kennzeichen",
            value="Noch keine Kennzeichen.",
            inline=False
        )

    embed.add_field(
        name="Panel",
        value=LICENSE_PANEL_MARKER,
        inline=False
    )

    await channel.send(
        embed=embed,
        view=LicensePlateView()
    )


# =========================================================
# BEWERBUNG
# =========================================================

class ApplicationModal(Modal):

    def __init__(self):

        super().__init__(
            title="Bewerbung"
        )

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
            label="Warum möchtest du ins Team?",
            placeholder="Schreibe etwas über dich...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(
            self.name_input
        )

        self.add_item(
            self.age_input
        )

        self.add_item(
            self.reason_input
        )

    async def on_submit(
        self,
        interaction
    ):

        channel = get_channel(
            APPLICATION_CHANNEL_ID
        )

        if not isinstance(
            channel,
            discord.TextChannel
        ):

            await interaction.response.send_message(
                "❌ Bewerbungskanal nicht gefunden.",
                ephemeral=True
            )

            return

        embed = discord.Embed(
            title="📨 Neue Bewerbung",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="👤 Name",
            value=self.name_input.value,
            inline=True
        )

        embed.add_field(
            name="🎂 Alter",
            value=self.age_input.value,
            inline=True
        )

        embed.add_field(
            name="📝 Grund",
            value=self.reason_input.value,
            inline=False
        )

        embed.add_field(
            name="Discord",
            value=interaction.user.mention,
            inline=False
        )

        await channel.send(
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Deine Bewerbung wurde gesendet.",
            ephemeral=True
        )


class ApplicationButton(Button):

    def __init__(self):

        super().__init__(
            label="Bewerben",
            emoji="📨",
            style=discord.ButtonStyle.success,
            custom_id="rlp_application_button"
        )

    async def callback(
        self,
        interaction
    ):

        await interaction.response.send_modal(
            ApplicationModal()
        )


class ApplicationView(View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        self.add_item(
            ApplicationButton()
        )


async def update_application_panel():

    channel = get_channel(
        APPLICATION_CHANNEL_ID
    )

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        return

    await delete_panel_messages(
        channel,
        APPLICATION_PANEL_MARKER
    )

    embed = discord.Embed(
        title="📨 Bewerbung",
        description=(
            "Du möchtest Teil des Teams werden?\n\n"
            "Klicke auf **Bewerben** und fülle das Formular aus."
        ),
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Panel",
        value=APPLICATION_PANEL_MARKER,
        inline=False
    )

    await channel.send(
        embed=embed,
        view=ApplicationView()
    )


# =========================================================
# SUGGESTIONS
# =========================================================

def build_suggestion_embed(
    suggestion
):

    status = suggestion.get(
        "status",
        "offen"
    )

    status_text = {
        "offen": "🟡 Offen",
        "angenommen": "🟢 Angenommen",
        "abgelehnt": "🔴 Abgelehnt"
    }.get(
        status,
        "🟡 Offen"
    )

    author_id = suggestion.get(
        "author_id"
    )

    author = (
        f"<@{author_id}>"
        if author_id
        else "Unbekannt"
    )

    for_votes = len(
        suggestion.get(
            "for_votes",
            []
        )
    )

    against_votes = len(
        suggestion.get(
            "against_votes",
            []
        )
    )

    embed = discord.Embed(
        title="💡 Vorschlag",
        description=suggestion.get(
            "text",
            "Kein Text"
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👤 Eingereicht von",
        value=author,
        inline=False
    )

    embed.add_field(
        name="📊 Status",
        value=status_text,
        inline=True
    )

    embed.add_field(
        name="🟢 Dafür",
        value=str(for_votes),
        inline=True
    )

    embed.add_field(
        name="🔴 Dagegen",
        value=str(against_votes),
        inline=True
    )

    embed.set_footer(
        text=f"Vorschlag-ID: {suggestion.get('id', 'unbekannt')}"
    )

    return embed


class SuggestionModal(Modal):

    def __init__(self):

        super().__init__(
            title="Vorschlag einreichen"
        )

        self.suggestion_input = TextInput(
            label="Dein Vorschlag",
            placeholder="Was möchtest du verbessern?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(
            self.suggestion_input
        )

    async def on_submit(
        self,
        interaction
    ):

        channel = get_channel(
            SUGGESTION_CHANNEL_ID
        )

        if not isinstance(
            channel,
            discord.TextChannel
        ):

            await interaction.response.send_message(
                "❌ Vorschlagskanal nicht gefunden.",
                ephemeral=True
            )

            return

        suggestion_id = str(
            int(time.time() * 1000)
        )

        suggestion = {
            "id": suggestion_id,
            "author_id": interaction.user.id,
            "text": self.suggestion_input.value,
            "status": "offen",
            "for_votes": [],
            "against_votes": []
        }

        message = await channel.send(
            embed=build_suggestion_embed(
                suggestion
            ),
            view=SuggestionView()
        )

        data["suggestions"][
            str(message.id)
        ] = suggestion

        save_data()

        await interaction.response.send_message(
            f"✅ Dein Vorschlag wurde in {channel.mention} eingereicht.",
            ephemeral=True
        )


class SuggestionAcceptButton(Button):

    def __init__(self):

        super().__init__(
            label="Annehmen",
            emoji="🟢",
            style=discord.ButtonStyle.success,
            custom_id="rlp_suggestion_accept"
        )

    async def callback(
        self,
        interaction
    ):

        if not is_suggestion_reviewer(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Du hast dafür keine Berechtigung.",
                ephemeral=True
            )

            return

        suggestion = data[
            "suggestions"
        ].get(
            str(interaction.message.id)
        )

        if not suggestion:

            await interaction.response.send_message(
                "❌ Dieser Vorschlag wurde nicht gefunden.",
                ephemeral=True
            )

            return

        suggestion["status"] = "angenommen"

        save_data()

        await interaction.message.edit(
            embed=build_suggestion_embed(
                suggestion
            ),
            view=SuggestionView()
        )

        await interaction.response.send_message(
            "🟢 Der Vorschlag wurde angenommen.",
            ephemeral=True
        )


class SuggestionRejectButton(Button):

    def __init__(self):

        super().__init__(
            label="Ablehnen",
            emoji="🔴",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_suggestion_reject"
        )

    async def callback(
        self,
        interaction
    ):

        if not is_suggestion_reviewer(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Du hast dafür keine Berechtigung.",
                ephemeral=True
            )

            return

        suggestion = data[
            "suggestions"
        ].get(
            str(interaction.message.id)
        )

        if not suggestion:

            await interaction.response.send_message(
                "❌ Dieser Vorschlag wurde nicht gefunden.",
                ephemeral=True
            )

            return

        suggestion["status"] = "abgelehnt"

        save_data()

        await interaction.message.edit(
            embed=build_suggestion_embed(
                suggestion
            ),
            view=SuggestionView()
        )

        await interaction.response.send_message(
            "🔴 Der Vorschlag wurde abgelehnt.",
            ephemeral=True
        )


class SuggestionForButton(Button):

    def __init__(self):

        super().__init__(
            label="Für den Vorschlag",
            emoji="🟢",
            style=discord.ButtonStyle.success,
            custom_id="rlp_suggestion_for"
        )

    async def callback(
        self,
        interaction
    ):

        suggestion = data[
            "suggestions"
        ].get(
            str(interaction.message.id)
        )

        if not suggestion:

            await interaction.response.send_message(
                "❌ Vorschlag nicht gefunden.",
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

        # WICHTIG:
        # Wenn vorher dagegen gewählt wurde,
        # wird diese Stimme entfernt.
        if user_id in against_votes:

            against_votes.remove(
                user_id
            )

        # Wenn bereits dafür gewählt wurde,
        # bleibt die Stimme einfach bestehen.
        if user_id not in for_votes:

            for_votes.append(
                user_id
            )

        save_data()

        await interaction.message.edit(
            embed=build_suggestion_embed(
                suggestion
            ),
            view=SuggestionView()
        )

        await interaction.response.send_message(
            "🟢 Deine Stimme ist jetzt **dafür**.",
            ephemeral=True
        )


class SuggestionAgainstButton(Button):

    def __init__(self):

        super().__init__(
            label="Gegen den Vorschlag",
            emoji="🔴",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_suggestion_against"
        )

    async def callback(
        self,
        interaction
    ):

        suggestion = data[
            "suggestions"
        ].get(
            str(interaction.message.id)
        )

        if not suggestion:

            await interaction.response.send_message(
                "❌ Vorschlag nicht gefunden.",
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

        # WICHTIG:
        # Vorherige Dafür-Stimme entfernen.
        if user_id in for_votes:

            for_votes.remove(
                user_id
            )

        # Danach Dagegen setzen.
        if user_id not in against_votes:

            against_votes.append(
                user_id
            )

        save_data()

        await interaction.message.edit(
            embed=build_suggestion_embed(
                suggestion
            ),
            view=SuggestionView()
        )

        await interaction.response.send_message(
            "🔴 Deine Stimme ist jetzt **dagegen**.",
            ephemeral=True
        )


class SuggestionView(View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        self.add_item(
            SuggestionAcceptButton()
        )

        self.add_item(
            SuggestionRejectButton()
        )

        self.add_item(
            SuggestionForButton()
        )

        self.add_item(
            SuggestionAgainstButton()
        )


# =========================================================
# FEEDBACK
# =========================================================

class FeedbackModal(Modal):

    def __init__(self):

        super().__init__(
            title="Feedback senden"
        )

        self.feedback_input = TextInput(
            label="Feedback",
            placeholder="Dein Feedback...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(
            self.feedback_input
        )

    async def on_submit(
        self,
        interaction
    ):

        channel = get_channel(
            FEEDBACK_CHANNEL_ID
        )

        if not isinstance(
            channel,
            discord.TextChannel
        ):

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

        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url
        )

        await channel.send(
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Dein Feedback wurde gesendet.",
            ephemeral=True
        )


# =========================================================
# BUG
# =========================================================

class BugModal(Modal):

    def __init__(self):

        super().__init__(
            title="Bug melden"
        )

        self.bug_input = TextInput(
            label="Bug",
            placeholder="Beschreibe den Fehler...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(
            self.bug_input
        )

    async def on_submit(
        self,
        interaction
    ):

        channel = get_channel(
            BUG_CHANNEL_ID
        )

        if not isinstance(
            channel,
            discord.TextChannel
        ):

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

        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url
        )

        await channel.send(
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Der Bug wurde gemeldet.",
            ephemeral=True
        )


# =========================================================
# COMMUNITY PANEL
# =========================================================

class CommunitySuggestionButton(Button):

    def __init__(self):

        super().__init__(
            label="Vorschlag",
            emoji="💡",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_community_suggestion"
        )

    async def callback(
        self,
        interaction
    ):

        await interaction.response.send_modal(
            SuggestionModal()
        )


class CommunityFeedbackButton(Button):

    def __init__(self):

        super().__init__(
            label="Feedback",
            emoji="💬",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_community_feedback"
        )

    async def callback(
        self,
        interaction
    ):

        await interaction.response.send_modal(
            FeedbackModal()
        )


class CommunityBugButton(Button):

    def __init__(self):

        super().__init__(
            label="Bug melden",
            emoji="🐞",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_community_bug"
        )

    async def callback(
        self,
        interaction
    ):

        await interaction.response.send_modal(
            BugModal()
        )


class CommunityPanelView(View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        self.add_item(
            CommunitySuggestionButton()
        )

        self.add_item(
            CommunityFeedbackButton()
        )

        self.add_item(
            CommunityBugButton()
        )


async def send_community_panel(
    channel
):

    embed = discord.Embed(
        title="🌐 Community",
        description=(
            "Du hast Feedback, einen Vorschlag oder einen Bug?\n\n"
            "💡 **Vorschlag**\n"
            "Reiche einen neuen Vorschlag ein.\n\n"
            "💬 **Feedback**\n"
            "Schicke uns dein Feedback.\n\n"
            "🐞 **Bug melden**\n"
            "Melde einen Fehler."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Panel",
        value=COMMUNITY_PANEL_MARKER,
        inline=False
    )

    await channel.send(
        embed=embed,
        view=CommunityPanelView()
    )


async def update_community_panel():

    message = await find_panel_message(
        COMMUNITY_PANEL_MARKER
    )

    if message is None:
        return

    channel = message.channel

    try:
        await message.delete()
    except Exception:
        pass

    await send_community_panel(
        channel
    )


# =========================================================
# DEVELOPER TASKS
# =========================================================

class DeveloperTaskModal(Modal):

    def __init__(self):

        super().__init__(
            title="Developer Aufgabe"
        )

        self.task_input = TextInput(
            label="Aufgabe",
            placeholder="Was soll erledigt werden?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(
            self.task_input
        )

    async def on_submit(
        self,
        interaction
    ):

        if not is_shift_allowed(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )

            return

        channel = get_channel(
            DEVELOPER_TASK_CHANNEL_ID
        )

        if not isinstance(
            channel,
            discord.TextChannel
        ):

            await interaction.response.send_message(
                "❌ Developer-Kanal nicht gefunden.",
                ephemeral=True
            )

            return

        task_id = str(
            int(time.time() * 1000)
        )

        data["developer_tasks"][
            task_id
        ] = {
            "author_id": interaction.user.id,
            "task": self.task_input.value,
            "created_at": datetime.utcnow().isoformat()
        }

        save_data()

        embed = discord.Embed(
            title="🛠️ Neue Developer-Aufgabe",
            description=self.task_input.value,
            color=discord.Color.orange()
        )

        embed.add_field(
            name="👤 Erstellt von",
            value=interaction.user.mention,
            inline=False
        )

        await channel.send(
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Aufgabe erstellt.",
            ephemeral=True
        )


class DeveloperTaskButton(Button):

    def __init__(self):

        super().__init__(
            label="Aufgabe erstellen",
            emoji="🛠️",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_dev_task_create"
        )

    async def callback(
        self,
        interaction
    ):

        await interaction.response.send_modal(
            DeveloperTaskModal()
        )


class DeveloperTaskView(View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        self.add_item(
            DeveloperTaskButton()
        )


async def update_developer_task_panel():

    channel = get_channel(
        DEVELOPER_TASK_CHANNEL_ID
    )

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        return

    await delete_panel_messages(
        channel,
        DEV_TASK_PANEL_MARKER
    )

    embed = discord.Embed(
        title="🛠️ Developer Aufgaben",
        description=(
            "Hier können berechtigte Mitglieder neue "
            "Developer-Aufgaben erstellen."
        ),
        color=discord.Color.orange()
    )

    embed.add_field(
        name="Panel",
        value=DEV_TASK_PANEL_MARKER,
        inline=False
    )

    await channel.send(
        embed=embed,
        view=DeveloperTaskView()
    )


# =========================================================
# DEVELOPER SHIFT
# =========================================================

class DeveloperShiftStartButton(Button):

    def __init__(self):

        super().__init__(
            label="Schicht starten",
            emoji="🟢",
            style=discord.ButtonStyle.success,
            custom_id="rlp_dev_shift_start"
        )

    async def callback(
        self,
        interaction
    ):

        if not is_developer_shift_allowed(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )

            return

        role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if role is None:

            await interaction.response.send_message(
                "❌ Developer-Schicht-Rolle nicht gefunden.",
                ephemeral=True
            )

            return

        if role in interaction.user.roles:

            await interaction.response.send_message(
                "ℹ️ Du bist bereits in der Developer-Schicht.",
                ephemeral=True
            )

            return

        try:

            await interaction.user.add_roles(
                role,
                reason="Developer-Schicht gestartet"
            )

            log_channel = get_channel(
                SHIFT_LOG_CHANNEL_ID
            )

            if isinstance(
                log_channel,
                discord.TextChannel
            ):

                await log_channel.send(
                    f"🟢 **Developer-Schicht gestartet**\n"
                    f"👤 {interaction.user.mention}"
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
            custom_id="rlp_dev_shift_end"
        )

    async def callback(
        self,
        interaction
    ):

        if not is_developer_shift_allowed(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )

            return

        role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if role is None:

            await interaction.response.send_message(
                "❌ Developer-Schicht-Rolle nicht gefunden.",
                ephemeral=True
            )

            return

        if role not in interaction.user.roles:

            await interaction.response.send_message(
                "ℹ️ Du bist aktuell nicht in der Developer-Schicht.",
                ephemeral=True
            )

            return

        try:

            await interaction.user.remove_roles(
                role,
                reason="Developer-Schicht beendet"
            )

            log_channel = get_channel(
                SHIFT_LOG_CHANNEL_ID
            )

            if isinstance(
                log_channel,
                discord.TextChannel
            ):

                await log_channel.send(
                    f"🔴 **Developer-Schicht beendet**\n"
                    f"👤 {interaction.user.mention}"
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

        super().__init__(
            timeout=None
        )

        self.add_item(
            DeveloperShiftStartButton()
        )

        self.add_item(
            DeveloperShiftEndButton()
        )


async def update_developer_shift_panel():

    channel = get_channel(
        DEVELOPER_SHIFT_CHANNEL_ID
    )

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        return

    await delete_panel_messages(
        channel,
        SHIFT_PANEL_MARKER
    )

    embed = discord.Embed(
        title="💻 Developer-Schicht",
        description=(
            "Verwalte hier deine Developer-Schicht.\n\n"
            "🟢 Schicht starten\n"
            "🔴 Schicht beenden"
        ),
        color=discord.Color.green()
    )

    embed.add_field(
        name="Panel",
        value=SHIFT_PANEL_MARKER,
        inline=False
    )

    await channel.send(
        embed=embed,
        view=DeveloperShiftView()
    )


# =========================================================
# OWNER PANEL
# =========================================================

class AnnouncementModal(Modal):

    def __init__(
        self,
        channel
    ):

        super().__init__(
            title="Ankündigung"
        )

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

        self.add_item(
            self.title_input
        )

        self.add_item(
            self.message_input
        )

    async def on_submit(
        self,
        interaction
    ):

        if not is_owner(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )

            return

        embed = discord.Embed(
            title=f"📢 {self.title_input.value}",
            description=self.message_input.value,
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )

        embed.set_footer(
            text=(
                f"Ankündigung von "
                f"{interaction.user.display_name}"
            )
        )

        try:

            await self.channel.send(
                embed=embed
            )

            await interaction.response.send_message(
                f"✅ Ankündigung wurde in "
                f"{self.channel.mention} gesendet.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Der Bot kann dort nicht schreiben.",
                ephemeral=True
            )


class BotSayModal(Modal):

    def __init__(
        self,
        channel
    ):

        super().__init__(
            title="Bot Say"
        )

        self.channel = channel

        self.message_input = TextInput(
            label="Nachricht",
            placeholder="Was soll der Bot schreiben?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=4000
        )

        self.add_item(
            self.message_input
        )

    async def on_submit(
        self,
        interaction
    ):

        if not is_owner(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )

            return

        try:

            await self.channel.send(
                self.message_input.value
            )

            await interaction.response.send_message(
                f"✅ Nachricht wurde in "
                f"{self.channel.mention} gesendet.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Der Bot kann dort nicht schreiben.",
                ephemeral=True
            )


class OwnerChannelSelectView(View):

    def __init__(
        self,
        action
    ):

        super().__init__(
            timeout=180
        )

        self.action = action

        self.select = ChannelSelect(
            placeholder="Wähle einen Textkanal...",
            channel_types=[
                discord.ChannelType.text
            ],
            min_values=1,
            max_values=1
        )

        self.select.callback = (
            self.channel_selected
        )

        self.add_item(
            self.select
        )

    async def channel_selected(
        self,
        interaction
    ):

        if not is_owner(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )

            return

        try:

            selected = self.select.values[0]

            channel = (
                interaction.guild.get_channel(
                    selected.id
                )
            )

            if not isinstance(
                channel,
                discord.TextChannel
            ):

                await interaction.response.send_message(
                    "❌ Kein Textkanal.",
                    ephemeral=True
                )

                return

            if self.action == "announcement":

                await interaction.response.send_modal(
                    AnnouncementModal(
                        channel
                    )
                )

                return

            if self.action == "say":

                await interaction.response.send_modal(
                    BotSayModal(
                        channel
                    )
                )

                return

            if self.action == "lock":

                await interaction.response.defer(
                    ephemeral=True
                )

                overwrite = (
                    channel.overwrites_for(
                        interaction.guild.default_role
                    )
                )

                overwrite.send_messages = False

                await channel.set_permissions(
                    interaction.guild.default_role,
                    overwrite=overwrite,
                    reason=(
                        f"Channel Lock durch "
                        f"{interaction.user}"
                    )
                )

                await interaction.followup.send(
                    f"🔒 {channel.mention} wurde gesperrt.",
                    ephemeral=True
                )

                return

            if self.action == "unlock":

                await interaction.response.defer(
                    ephemeral=True
                )

                overwrite = (
                    channel.overwrites_for(
                        interaction.guild.default_role
                    )
                )

                overwrite.send_messages = None

                await channel.set_permissions(
                    interaction.guild.default_role,
                    overwrite=overwrite,
                    reason=(
                        f"Channel Unlock durch "
                        f"{interaction.user}"
                    )
                )

                await interaction.followup.send(
                    f"🔓 {channel.mention} wurde entsperrt.",
                    ephemeral=True
                )

                return

        except discord.Forbidden:

            if interaction.response.is_done():

                await interaction.followup.send(
                    "❌ Der Bot hat nicht genügend Rechte.",
                    ephemeral=True
                )

            else:

                await interaction.response.send_message(
                    "❌ Der Bot hat nicht genügend Rechte.",
                    ephemeral=True
                )

        except Exception as e:

            print(
                f"OWNER SELECT ERROR: {e}"
            )

            if interaction.response.is_done():

                await interaction.followup.send(
                    f"❌ Fehler: `{e}`",
                    ephemeral=True
                )

            else:

                await interaction.response.send_message(
                    f"❌ Fehler: `{e}`",
                    ephemeral=True
                )


class OwnerAnnouncementButton(Button):

    def __init__(self):

        super().__init__(
            label="Ankündigung",
            emoji="📢",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_owner_announcement"
        )

    async def callback(
        self,
        interaction
    ):

        if not is_owner(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "📢 **Wähle den Kanal für die Ankündigung:**",
            view=OwnerChannelSelectView(
                "announcement"
            ),
            ephemeral=True
        )


class OwnerSayButton(Button):

    def __init__(self):

        super().__init__(
            label="Bot Say",
            emoji="💬",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_owner_say"
        )

    async def callback(
        self,
        interaction
    ):

        if not is_owner(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "💬 **Wähle den Kanal:**",
            view=OwnerChannelSelectView(
                "say"
            ),
            ephemeral=True
        )


class OwnerLockButton(Button):

    def __init__(self):

        super().__init__(
            label="Channel Lock",
            emoji="🔒",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_owner_lock"
        )

    async def callback(
        self,
        interaction
    ):

        if not is_owner(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "🔒 **Wähle den Kanal:**",
            view=OwnerChannelSelectView(
                "lock"
            ),
            ephemeral=True
        )


class OwnerUnlockButton(Button):

    def __init__(self):

        super().__init__(
            label="Channel Unlock",
            emoji="🔓",
            style=discord.ButtonStyle.success,
            custom_id="rlp_owner_unlock"
        )

    async def callback(
        self,
        interaction
    ):

        if not is_owner(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "🔓 **Wähle den Kanal:**",
            view=OwnerChannelSelectView(
                "unlock"
            ),
            ephemeral=True
        )


class OwnerStatusButton(Button):

    def __init__(self):

        super().__init__(
            label="Bot Status",
            emoji="📊",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_owner_status"
        )

    async def callback(
        self,
        interaction
    ):

        if not is_owner(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )

            return

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
            value=f"{round(bot.latency * 1000)} ms",
            inline=True
        )

        embed.add_field(
            name="🌐 Server",
            value=str(len(bot.guilds)),
            inline=True
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
            custom_id="rlp_owner_serverinfo"
        )

    async def callback(
        self,
        interaction
    ):

        if not is_owner(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )

            return

        guild = interaction.guild

        embed = discord.Embed(
            title="🖥️ Server Info",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="Server",
            value=guild.name,
            inline=True
        )

        embed.add_field(
            name="Server-ID",
            value=str(guild.id),
            inline=True
        )

        embed.add_field(
            name="Mitglieder",
            value=str(guild.member_count),
            inline=True
        )

        embed.add_field(
            name="Kanäle",
            value=str(len(guild.channels)),
            inline=True
        )

        embed.add_field(
            name="Rollen",
            value=str(len(guild.roles)),
            inline=True
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


class OwnerPanelView(View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

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
            OwnerStatusButton()
        )

        self.add_item(
            OwnerServerInfoButton()
        )


async def send_owner_panel(
    channel
):

    embed = discord.Embed(
        title="👑 Owner Panel",
        description=(
            "Hier kannst du Server- und Bot-Funktionen verwalten.\n\n"
            "📢 **Ankündigung**\n"
            "Kanal auswählen und Nachricht erstellen.\n\n"
            "💬 **Bot Say**\n"
            "Der Bot schreibt eine Nachricht.\n\n"
            "🔒 **Channel Lock**\n"
            "Kanal sperren.\n\n"
            "🔓 **Channel Unlock**\n"
            "Kanal entsperren.\n\n"
            "📊 **Bot Status**\n"
            "Bot-Informationen anzeigen.\n\n"
            "🖥️ **Server Info**\n"
            "Serverinformationen anzeigen."
        ),
        color=discord.Color.gold()
    )

    embed.add_field(
        name="Panel",
        value=OWNER_PANEL_MARKER,
        inline=False
    )

    await channel.send(
        embed=embed,
        view=OwnerPanelView()
    )


async def update_owner_panel():

    message = await find_panel_message(
        OWNER_PANEL_MARKER
    )

    if message is None:
        return

    channel = message.channel

    try:
        await message.delete()
    except Exception:
        pass

    await send_owner_panel(
        channel
    )


# =========================================================
# GENERAL COMMANDS
# =========================================================

@bot.command()
async def ping(ctx):

    await ctx.send(
        f"🏓 Pong! `{round(bot.latency * 1000)}ms`"
    )


@bot.command()
async def ownerpanel(ctx):

    if not is_owner(ctx.author):

        await ctx.send(
            "❌ Du hast keine Berechtigung.",
            delete_after=5
        )

        return

    await send_owner_panel(
        ctx.channel
    )


@bot.command()
async def owner(ctx):

    if not is_owner(ctx.author):

        await ctx.send(
            "❌ Du hast keine Berechtigung.",
            delete_after=5
        )

        return

    await send_owner_panel(
        ctx.channel
    )


@bot.command()
async def serverinfo(ctx):

    guild = ctx.guild

    embed = discord.Embed(
        title="🖥️ Server Info",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Name",
        value=guild.name,
        inline=True
    )

    embed.add_field(
        name="Mitglieder",
        value=str(guild.member_count),
        inline=True
    )

    embed.add_field(
        name="Kanäle",
        value=str(len(guild.channels)),
        inline=True
    )

    embed.add_field(
        name="Rollen",
        value=str(len(guild.roles)),
        inline=True
    )

    await ctx.send(
        embed=embed
    )


@bot.command()
async def botinfo(ctx):

    embed = discord.Embed(
        title="🤖 Bot Info",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Bot",
        value=str(bot.user),
        inline=True
    )

    embed.add_field(
        name="Ping",
        value=f"{round(bot.latency * 1000)} ms",
        inline=True
    )

    embed.add_field(
        name="Uptime",
        value=uptime_string(),
        inline=True
    )

    embed.add_field(
        name="Server",
        value=str(len(bot.guilds)),
        inline=True
    )

    await ctx.send(
        embed=embed
    )


@bot.command()
async def userinfo(
    ctx,
    member: discord.Member = None
):

    member = member or ctx.author

    embed = discord.Embed(
        title="👤 User Info",
        color=member.color
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
            "D"
        ),
        inline=False
    )

    await ctx.send(
        embed=embed
    )


@bot.command()
async def roleinfo(
    ctx,
    role: discord.Role
):

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

    await ctx.send(
        embed=embed
    )


@bot.command()
async def channelinfo(
    ctx,
    channel: discord.TextChannel = None
):

    channel = channel or ctx.channel

    embed = discord.Embed(
        title="📺 Channel Info",
        color=discord.Color.blue()
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
        value=(
            channel.category.name
            if channel.category
            else "Keine"
        ),
        inline=True
    )

    await ctx.send(
        embed=embed
    )


@bot.command()
async def avatar(
    ctx,
    member: discord.Member = None
):

    member = member or ctx.author

    embed = discord.Embed(
        title=f"🖼️ Avatar von {member.display_name}"
    )

    embed.set_image(
        url=member.display_avatar.url
    )

    await ctx.send(
        embed=embed
    )


@bot.command()
async def banner(
    ctx,
    member: discord.Member = None
):

    member = member or ctx.author

    user = await bot.fetch_user(
        member.id
    )

    if user.banner is None:

        await ctx.send(
            "ℹ️ Dieser Nutzer hat keinen Banner."
        )

        return

    embed = discord.Embed(
        title=f"🖼️ Banner von {member.display_name}"
    )

    embed.set_image(
        url=user.banner.url
    )

    await ctx.send(
        embed=embed
    )


@bot.command()
async def membercount(ctx):

    await ctx.send(
        f"👥 Aktuelle Mitglieder: **{ctx.guild.member_count}**"
    )


@bot.command()
async def rolelist(ctx):

    roles = [
        role.mention
        for role in ctx.guild.roles
        if role.name != "@everyone"
    ]

    if not roles:

        await ctx.send(
            "Keine Rollen gefunden."
        )

        return

    text = "\n".join(
        roles[:100]
    )

    await ctx.send(
        f"🎭 **Rollen:**\n{text}"
    )


@bot.command()
async def channellist(ctx):

    channels = []

    for channel in ctx.guild.channels:

        channels.append(
            f"{channel.mention} — `{channel.id}`"
        )

    await ctx.send(
        "📺 **Kanäle:**\n"
        + "\n".join(
            channels[:100]
        )
    )


# =========================================================
# COMMUNITY COMMANDS
# =========================================================

@bot.command()
async def suggest(
    ctx,
    *,
    text=None
):

    if not text:

        await ctx.send(
            "❌ Nutze: `!suggest Dein Vorschlag`",
            delete_after=8
        )

        return

    channel = get_channel(
        SUGGESTION_CHANNEL_ID
    )

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        return

    suggestion = {
        "id": str(
            int(time.time() * 1000)
        ),
        "author_id": ctx.author.id,
        "text": text,
        "status": "offen",
        "for_votes": [],
        "against_votes": []
    }

    message = await channel.send(
        embed=build_suggestion_embed(
            suggestion
        ),
        view=SuggestionView()
    )

    data["suggestions"][
        str(message.id)
    ] = suggestion

    save_data()

    await ctx.send(
        f"✅ Dein Vorschlag wurde in {channel.mention} gesendet.",
        delete_after=5
    )


@bot.command()
async def feedback(
    ctx,
    *,
    text=None
):

    if not text:

        await ctx.send(
            "❌ Nutze: `!feedback Dein Feedback`",
            delete_after=8
        )

        return

    channel = get_channel(
        FEEDBACK_CHANNEL_ID
    )

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        return

    embed = discord.Embed(
        title="💬 Neues Feedback",
        description=text,
        color=discord.Color.blue()
    )

    embed.set_author(
        name=ctx.author.display_name,
        icon_url=ctx.author.display_avatar.url
    )

    await channel.send(
        embed=embed
    )

    await ctx.send(
        "✅ Feedback gesendet.",
        delete_after=5
    )


@bot.command()
async def bug(
    ctx,
    *,
    text=None
):

    if not text:

        await ctx.send(
            "❌ Nutze: `!bug Beschreibung`",
            delete_after=8
        )

        return

    channel = get_channel(
        BUG_CHANNEL_ID
    )

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        return

    embed = discord.Embed(
        title="🐞 Neuer Bug",
        description=text,
        color=discord.Color.red()
    )

    embed.set_author(
        name=ctx.author.display_name,
        icon_url=ctx.author.display_avatar.url
    )

    await channel.send(
        embed=embed
    )

    await ctx.send(
        "✅ Bug gemeldet.",
        delete_after=5
    )


@bot.command()
async def apply(ctx):

    await ctx.send(
        "📨 Nutze das Bewerbungs-Panel im Bewerbungs-Kanal."
    )


@bot.command()
async def support(ctx):

    channel = get_channel(
        SUPPORT_VOICE_CHANNEL_ID
    )

    if channel:

        await ctx.send(
            f"🔊 Support: {channel.mention}"
        )

    else:

        await ctx.send(
            "🔊 Support-Kanal nicht gefunden."
        )


@bot.command()
async def supportinfo(ctx):

    await ctx.send(
        "🔊 Bei Fragen oder Problemen kannst du "
        "unseren Support nutzen."
    )


# =========================================================
# FUN COMMANDS
# =========================================================

@bot.command(name="8ball")
async def eightball(
    ctx,
    *,
    question=None
):

    if not question:

        await ctx.send(
            "❌ Stelle eine Frage."
        )

        return

    answers = [
        "Ja.",
        "Nein.",
        "Vielleicht.",
        "Sehr wahrscheinlich.",
        "Eher nicht.",
        "Sieht gut aus.",
        "Ich weiß es nicht."
    ]

    await ctx.send(
        f"🎱 {random_module.choice(answers)}"
    )


@bot.command()
async def coinflip(ctx):

    result = random_module.choice(
        ["Kopf", "Zahl"]
    )

    await ctx.send(
        f"🪙 **{result}**"
    )


@bot.command()
async def dice(ctx):

    await ctx.send(
        f"🎲 Du hast eine **{random_module.randint(1, 6)}** gewürfelt."
    )


@bot.command()
async def choose(
    ctx,
    *,
    options=None
):

    if not options:

        await ctx.send(
            "❌ Beispiel: `!choose A | B | C`"
        )

        return

    choices = [
        x.strip()
        for x in options.split("|")
        if x.strip()
    ]

    if len(choices) < 2:

        await ctx.send(
            "❌ Du brauchst mindestens zwei Möglichkeiten."
        )

        return

    await ctx.send(
        f"🤔 Ich wähle: **{random_module.choice(choices)}**"
    )


@bot.command(name="random")
async def random_number(
    ctx,
    minimum: int = None,
    maximum: int = None
):

    if minimum is None or maximum is None:

        await ctx.send(
            "❌ Beispiel: `!random 1 100`"
        )

        return

    if minimum > maximum:

        minimum, maximum = maximum, minimum

    await ctx.send(
        f"🎲 Zufallszahl: **{random_module.randint(minimum, maximum)}**"
    )


@bot.command()
async def serverage(ctx):

    created = ctx.guild.created_at

    await ctx.send(
        f"📅 Der Server wurde am "
        f"{discord.utils.format_dt(created, 'D')} erstellt."
    )


@bot.command()
async def member(ctx):

    await ctx.send(
        f"👤 Du bist **{ctx.author.display_name}**."
    )


# =========================================================
# INFO COMMANDS
# =========================================================

@bot.command()
async def uptime(ctx):

    await ctx.send(
        f"⏱️ Uptime: `{uptime_string()}`"
    )


@bot.command()
async def status(ctx):

    await ctx.send(
        "🟢 **Online**"
    )


@bot.command()
async def website(ctx):

    await ctx.send(
        "🌐 Die Website ist derzeit nicht hinterlegt."
    )


@bot.command()
async def socials(ctx):

    await ctx.send(
        "📱 Unsere Socials sind derzeit nicht hinterlegt."
    )


@bot.command()
async def team(ctx):

    await ctx.send(
        "👥 Unser Team findest du auf dem Server."
    )


@bot.command()
async def rules(ctx):

    await ctx.send(
        "📜 Bitte beachte die Regeln des Servers."
    )


@bot.command()
async def invite(ctx):

    permissions = discord.Permissions(
        view_channel=True,
        send_messages=True,
        embed_links=True,
        read_message_history=True
    )

    url = discord.utils.oauth_url(
        bot.user.id,
        permissions=permissions,
        scopes=("bot",)
    )

    await ctx.send(
        f"🤖 Bot einladen:\n{url}"
    )


# =========================================================
# HELP
# =========================================================

@bot.command()
async def help(ctx):

    embed = discord.Embed(
        title="📚 RLP Bot Hilfe",
        description=(
            "**Allgemeine Befehle**\n"
            "`!ping` `!uptime` `!status` `!help`\n"
            "`!invite` `!rules` `!team` `!website` `!socials`\n\n"

            "**Server / Info**\n"
            "`!serverinfo` `!botinfo` `!userinfo`\n"
            "`!roleinfo` `!channelinfo` `!avatar` `!banner`\n"
            "`!membercount` `!rolelist` `!channellist`\n\n"

            "**Community**\n"
            "`!suggest` `!feedback` `!bug`\n"
            "`!apply` `!support` `!supportinfo`\n\n"

            "**Fun**\n"
            "`!8ball` `!coinflip` `!dice`\n"
            "`!choose` `!random` `!serverage` `!member`\n\n"

            "**Owner**\n"
            "`!ownerpanel` `!owner`"
        ),
        color=discord.Color.blurple()
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# VOICE SUPPORT LOG
# =========================================================

@bot.event
async def on_voice_state_update(
    member,
    before,
    after
):

    log_channel = get_channel(
        SUPPORT_LOG_CHANNEL_ID
    )

    support_channel = get_channel(
        SUPPORT_VOICE_CHANNEL_ID
    )

    if not isinstance(
        log_channel,
        discord.TextChannel
    ):
        return

    if not isinstance(
        support_channel,
        discord.VoiceChannel
    ):
        return

    if (
        before.channel != support_channel
        and after.channel == support_channel
    ):

        await log_channel.send(
            f"🔊 **Support beigetreten**\n"
            f"👤 {member.mention}\n"
            f"📍 {support_channel.mention}"
        )

    elif (
        before.channel == support_channel
        and after.channel != support_channel
    ):

        await log_channel.send(
            f"🔇 **Support verlassen**\n"
            f"👤 {member.mention}"
        )


# =========================================================
# MESSAGE HANDLER
# =========================================================

@bot.event
async def on_message(
    message
):

    global quiz_message_id
    global quiz_answer

    if message.author.bot:
        return

    # =====================================================
    # QUIZ
    # =====================================================

    if message.channel.id == QUIZ_CHANNEL_ID:

        if quiz_answer is None:

            await asyncio.sleep(6)

            await safe_delete(
                message
            )

            return

        user_answer = (
            message.content
            .strip()
            .lower()
        )

        # RICHTIG
        if user_answer == quiz_answer:

            current_question_id = (
                quiz_message_id
            )

            await safe_delete(
                message
            )

            if current_question_id:

                try:

                    question_message = (
                        await message.channel.fetch_message(
                            current_question_id
                        )
                    )

                    await safe_delete(
                        question_message
                    )

                except Exception:
                    pass

            quiz_message_id = None
            quiz_answer = None

            success_message = (
                await message.channel.send(
                    f"✅ **Richtig!** "
                    f"{message.author.mention}"
                )
            )

            await asyncio.sleep(4)

            await safe_delete(
                success_message
            )

            await send_quiz_question()

            return

        # FALSCH
        await safe_delete(
            message
        )

        wrong_message = (
            await message.channel.send(
                f"❌ **Falsch!** "
                f"{message.author.mention}"
            )
        )

        await asyncio.sleep(4)

        await safe_delete(
            wrong_message
        )

        return

    await bot.process_commands(
        message
    )


# =========================================================
# SETUP HOOK
# =========================================================

@bot.event
async def setup_hook():

    global views_registered

    if views_registered:
        return

    views_registered = True

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
        OwnerPanelView()
    )

    bot.add_view(
        CommunityPanelView()
    )

    bot.add_view(
        SuggestionView()
    )

    # Alte Slash Commands entfernen
    try:

        guild_obj = discord.Object(
            id=GUILD_ID
        )

        bot.tree.clear_commands(
            guild=guild_obj
        )

        await bot.tree.sync(
            guild=guild_obj
        )

        bot.tree.clear_commands(
            guild=None
        )

        await bot.tree.sync()

        print(
            "✅ Alte Slash Commands entfernt."
        )

    except Exception as e:

        print(
            f"Slash-Command Cleanup Fehler: {e}"
        )


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    print(
        "===================================="
    )

    print(
        f"Bot online: {bot.user}"
    )

    print(
        f"Guilds: {len(bot.guilds)}"
    )

    print(
        "===================================="
    )

    # Panels aktualisieren
    try:

        await update_nametag_panel()

    except Exception as e:

        print(
            f"Nametag Panel Fehler: {e}"
        )

    try:

        await update_license_panel()

    except Exception as e:

        print(
            f"Kennzeichen Panel Fehler: {e}"
        )

    try:

        await update_application_panel()

    except Exception as e:

        print(
            f"Bewerbungs Panel Fehler: {e}"
        )

    try:

        await update_developer_task_panel()

    except Exception as e:

        print(
            f"Developer Task Panel Fehler: {e}"
        )

    try:

        await update_developer_shift_panel()

    except Exception as e:

        print(
            f"Developer Shift Panel Fehler: {e}"
        )

    try:

        await update_owner_panel()

    except Exception as e:

        print(
            f"Owner Panel Fehler: {e}"
        )

    try:

        await update_community_panel()

    except Exception as e:

        print(
            f"Community Panel Fehler: {e}"
        )

    # Emoji Quiz aktualisieren
    try:

        await reset_quiz()

    except Exception as e:

        print(
            f"Emoji Quiz Fehler: {e}"
        )


# =========================================================
# RUN
# =========================================================

if not TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN wurde nicht gefunden."
    )


bot.run(TOKEN)
