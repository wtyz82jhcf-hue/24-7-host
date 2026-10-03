import os
import json
import random
import asyncio
import time
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, ChannelSelect


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

NAMETAG_ROLE_ID = 1520102928398942348
SHIFT_PERMISSION_ROLE_ID = 1523674698574200904
DEVELOPER_SHIFT_ROLE_ID = 1527372148979798086
OWNER_ROLE_ID = 1544691379613999164

NAMETAG = "RLP | "

DATA_FILE = "bot_data.json"

NAMETAG_PANEL_MARKER = "RLP_NAMETAG_PANEL"
LICENSE_PANEL_MARKER = "RLP_LICENSE_PANEL"
SHIFT_PANEL_MARKER = "RLP_SHIFT_PANEL"
APPLICATION_PANEL_MARKER = "RLP_APPLICATION_PANEL"
DEV_TASK_PANEL_MARKER = "RLP_DEV_TASK_PANEL"
OWNER_PANEL_MARKER = "RLP_OWNER_PANEL"
COMMUNITY_PANEL_MARKER = "RLP_COMMUNITY_PANEL"


# =========================================================
# INTENTS
# =========================================================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)


# =========================================================
# DATA
# =========================================================

if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
else:
    data = {}

data.setdefault("license_plates", {})
data.setdefault("developer_tasks", {})
data.setdefault("applications", {})
data.setdefault("suggestions", {})
data.setdefault("feedback", {})
data.setdefault("bugs", {})
data.setdefault("events", {})
data.setdefault("giveaways", {})
data.setdefault("links", {
    "Website": "Noch nicht eingetragen",
    "Discord": "Dieser Server",
    "Instagram": "Noch nicht eingetragen"
})
data.setdefault("server_settings", {
    "rules": "Bitte halte dich an die Regeln des Servers.",
    "team": "Das Team wurde noch nicht eingetragen."
})


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"DATA SAVE ERROR: {e}")


# =========================================================
# HELPERS
# =========================================================

def has_role(member: discord.Member, role_id: int):
    return any(role.id == role_id for role in member.roles)


def is_owner(member: discord.Member):
    return has_role(member, OWNER_ROLE_ID)


def get_channel(channel_id: int):
    return bot.get_channel(channel_id)


def get_real_text_channel(guild: discord.Guild, selected_channel):
    """
    ChannelSelect kann AppCommandChannel zurückgeben.
    Deshalb wird der Kanal über seine ID nochmal
    als echter discord.TextChannel aus der Guild geholt.
    """

    if selected_channel is None:
        return None

    channel_id = getattr(selected_channel, "id", None)

    if channel_id is None:
        return None

    channel = guild.get_channel(channel_id)

    if isinstance(channel, discord.TextChannel):
        return channel

    return None


async def safe_delete(message):
    try:
        await message.delete()
    except Exception:
        pass


def format_duration(seconds: int):
    seconds = max(0, int(seconds))

    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = []

    if days:
        parts.append(f"{days}T")
    if hours:
        parts.append(f"{hours}Std")
    if minutes:
        parts.append(f"{minutes}Min")
    if seconds or not parts:
        parts.append(f"{seconds}Sek")

    return " ".join(parts)


def parse_duration(value: str):
    """
    Beispiele:
    30s
    10m
    2h
    1d
    """

    value = value.lower().strip()

    try:
        if value.endswith("s"):
            return int(value[:-1])

        if value.endswith("m"):
            return int(value[:-1]) * 60

        if value.endswith("h"):
            return int(value[:-1]) * 3600

        if value.endswith("d"):
            return int(value[:-1]) * 86400

        return int(value)

    except Exception:
        return None


def make_id(prefix: str):
    return f"{prefix}-{random.randint(100000, 999999)}"


# =========================================================
# NAMETAG SYSTEM
# =========================================================

class NametagResetButton(Button):

    def __init__(self):
        super().__init__(
            label="Nametag zurücksetzen",
            emoji="🔄",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_nametag_reset"
        )

    async def callback(self, interaction: discord.Interaction):

        member = interaction.user

        if not isinstance(member, discord.Member):
            await interaction.response.send_message(
                "❌ Mitglied konnte nicht erkannt werden.",
                ephemeral=True
            )
            return

        current_nick = member.nick

        if not current_nick:
            await interaction.response.send_message(
                "ℹ️ Du hast aktuell keinen Nametag.",
                ephemeral=True
            )
            return

        new_nick = current_nick
        removed = False

        prefixes = [
            NAMETAG,
            NAMETAG.replace(" ", "\u00a0")
        ]

        for prefix in prefixes:
            if new_nick.startswith(prefix):
                new_nick = new_nick[len(prefix):]
                removed = True
                break

        if not removed:
            await interaction.response.send_message(
                "ℹ️ Dein Name hat keinen RLP-Nametag.",
                ephemeral=True
            )
            return

        if not new_nick:
            new_nick = None

        try:

            await member.edit(
                nick=new_nick,
                reason="RLP Nametag zurückgesetzt"
            )

            await interaction.response.send_message(
                "✅ Dein Nametag wurde entfernt.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Ich kann deinen Nicknamen nicht ändern. "
                "Meine Bot-Rolle muss über deiner Rolle stehen.",
                ephemeral=True
            )

        except Exception as e:

            print(f"NAMETAG ERROR: {e}")

            await interaction.response.send_message(
                f"❌ Fehler: `{e}`",
                ephemeral=True
            )


class NametagView(View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(NametagResetButton())


async def update_nametag_panel():

    channel = get_channel(NAMETAG_CHANNEL_ID)

    if channel is None:
        return

    embed = discord.Embed(
        title="🏷️ RLP Nametag",
        description=(
            f"Der RLP-Nametag lautet:\n\n"
            f"`{NAMETAG}`\n\n"
            "Mit dem Button kannst du deinen Nametag "
            "wieder aus deinem Nicknamen entfernen."
        ),
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Panel",
        value=NAMETAG_PANEL_MARKER,
        inline=False
    )

    async for message in channel.history(limit=50):

        if message.author == bot.user and message.embeds:

            for old_embed in message.embeds:

                for field in old_embed.fields:

                    if field.value == NAMETAG_PANEL_MARKER:

                        await message.edit(
                            embed=embed,
                            view=NametagView()
                        )
                        return

    await channel.send(
        embed=embed,
        view=NametagView()
    )


# =========================================================
# LICENSE PLATE SYSTEM
# =========================================================

class LicensePlateModal(Modal):

    def __init__(self):
        super().__init__(title="Kennzeichen erstellen")

        self.plate = TextInput(
            label="Kennzeichen",
            placeholder="z.B. RLP 01",
            required=True,
            max_length=20
        )

        self.add_item(self.plate)

    async def on_submit(self, interaction):

        value = self.plate.value.strip().upper()
        parts = value.split()

        if len(parts) < 2:

            await interaction.response.send_message(
                "❌ Beispiel: `RLP 01`",
                ephemeral=True
            )
            return

        number = parts[-1]

        if not number.isdigit():

            await interaction.response.send_message(
                "❌ Der letzte Teil muss eine Zahl sein.",
                ephemeral=True
            )
            return

        user_id = str(interaction.user.id)

        if user_id in data["license_plates"]:

            await interaction.response.send_message(
                "❌ Du hast bereits ein Kennzeichen.",
                ephemeral=True
            )
            return

        for existing in data["license_plates"].values():

            existing_parts = existing["plate"].split()

            if existing_parts and existing_parts[-1] == number:

                await interaction.response.send_message(
                    f"❌ Die Nummer `{number}` ist bereits vergeben.",
                    ephemeral=True
                )
                return

        data["license_plates"][user_id] = {
            "plate": value,
            "name": interaction.user.display_name
        }

        save_data()

        await update_license_panel()

        await interaction.response.send_message(
            f"✅ Kennzeichen **{value}** wurde erstellt.",
            ephemeral=True
        )


class LicensePlateButton(Button):

    def __init__(self):
        super().__init__(
            label="Kennzeichen erstellen",
            emoji="🚗",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_license_create"
        )

    async def callback(self, interaction):

        await interaction.response.send_modal(
            LicensePlateModal()
        )


class LicensePlateView(View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(LicensePlateButton())


async def update_license_panel():

    channel = get_channel(LICENSE_PLATE_CHANNEL_ID)

    if channel is None:
        return

    embed = discord.Embed(
        title="🚗 Kennzeichen",
        description="Erstelle hier dein persönliches Kennzeichen.",
        color=discord.Color.blue()
    )

    if data["license_plates"]:

        lines = []

        for plate_data in data["license_plates"].values():

            lines.append(
                f"🚗 `{plate_data['plate']}` — "
                f"**{plate_data['name']}**"
            )

        embed.add_field(
            name="Vergebene Kennzeichen",
            value="\n".join(lines)[:1024],
            inline=False
        )

    else:

        embed.add_field(
            name="Vergebene Kennzeichen",
            value="Noch keine Kennzeichen.",
            inline=False
        )

    embed.add_field(
        name="Panel",
        value=LICENSE_PANEL_MARKER,
        inline=False
    )

    async for message in channel.history(limit=50):

        if message.author == bot.user and message.embeds:

            for old_embed in message.embeds:

                for field in old_embed.fields:

                    if field.value == LICENSE_PANEL_MARKER:

                        await message.edit(
                            embed=embed,
                            view=LicensePlateView()
                        )
                        return

    await channel.send(
        embed=embed,
        view=LicensePlateView()
    )


# =========================================================
# APPLICATION SYSTEM
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
            label="Warum möchtest du beitreten?",
            placeholder="Schreibe etwas über dich...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.name_input)
        self.add_item(self.age_input)
        self.add_item(self.reason_input)

    async def on_submit(self, interaction):

        channel = get_channel(APPLICATION_CHANNEL_ID)

        if channel is None:

            await interaction.response.send_message(
                "❌ Bewerbungs-Kanal nicht gefunden.",
                ephemeral=True
            )
            return

        application_id = make_id("APP")

        data["applications"][application_id] = {
            "user_id": interaction.user.id,
            "name": self.name_input.value,
            "age": self.age_input.value,
            "reason": self.reason_input.value,
            "status": "Offen",
            "created": int(time.time())
        }

        save_data()

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
            name="🆔 Bewerbungs-ID",
            value=application_id,
            inline=False
        )

        embed.set_footer(
            text=f"Discord: {interaction.user}"
        )

        try:

            await channel.send(embed=embed)

            await interaction.response.send_message(
                "✅ Deine Bewerbung wurde gesendet.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Der Bot kann im Bewerbungskanal nicht schreiben.",
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

    async def callback(self, interaction):

        await interaction.response.send_modal(
            ApplicationModal()
        )


class ApplicationView(View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ApplicationButton())


async def update_application_panel():

    channel = get_channel(APPLICATION_CHANNEL_ID)

    if channel is None:
        return

    embed = discord.Embed(
        title="📨 Bewerbung",
        description=(
            "Du möchtest dich bei RLP bewerben?\n\n"
            "Klicke auf **Bewerben** und fülle das Formular aus."
        ),
        color=discord.Color.green()
    )

    embed.add_field(
        name="Panel",
        value=APPLICATION_PANEL_MARKER,
        inline=False
    )

    async for message in channel.history(limit=50):

        if message.author == bot.user and message.embeds:

            for old_embed in message.embeds:

                for field in old_embed.fields:

                    if field.value == APPLICATION_PANEL_MARKER:

                        await message.edit(
                            embed=embed,
                            view=ApplicationView()
                        )
                        return

    await channel.send(
        embed=embed,
        view=ApplicationView()
    )


# =========================================================
# DEVELOPER TASK SYSTEM
# =========================================================

class DeveloperTaskModal(Modal):

    def __init__(self):
        super().__init__(title="Developer Aufgabe")

        self.task = TextInput(
            label="Aufgabe",
            placeholder="Was soll erledigt werden?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.task)

    async def on_submit(self, interaction):

        if not has_role(
            interaction.user,
            SHIFT_PERMISSION_ROLE_ID
        ):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        task_id = make_id("TASK")

        data["developer_tasks"][task_id] = {
            "task": self.task.value,
            "author": interaction.user.id,
            "completed": False,
            "created": int(time.time())
        }

        save_data()

        channel = get_channel(
            DEVELOPER_TASK_CHANNEL_ID
        )

        if channel:

            embed = discord.Embed(
                title="🛠️ Neue Developer Aufgabe",
                description=self.task.value,
                color=discord.Color.orange()
            )

            embed.add_field(
                name="Erstellt von",
                value=interaction.user.mention
            )

            embed.add_field(
                name="Task ID",
                value=task_id
            )

            await channel.send(embed=embed)

        await interaction.response.send_message(
            f"✅ Aufgabe `{task_id}` wurde erstellt.",
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

    async def callback(self, interaction):

        if not has_role(
            interaction.user,
            SHIFT_PERMISSION_ROLE_ID
        ):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            DeveloperTaskModal()
        )


class DeveloperTaskView(View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(DeveloperTaskButton())


async def update_developer_task_panel():

    channel = get_channel(
        DEVELOPER_TASK_CHANNEL_ID
    )

    if channel is None:
        return

    embed = discord.Embed(
        title="🛠️ Developer Aufgaben",
        description=(
            "Hier können berechtigte Developer "
            "neue Aufgaben erstellen."
        ),
        color=discord.Color.orange()
    )

    embed.add_field(
        name="Panel",
        value=DEV_TASK_PANEL_MARKER,
        inline=False
    )

    async for message in channel.history(limit=50):

        if message.author == bot.user and message.embeds:

            for old_embed in message.embeds:

                for field in old_embed.fields:

                    if field.value == DEV_TASK_PANEL_MARKER:

                        await message.edit(
                            embed=embed,
                            view=DeveloperTaskView()
                        )
                        return

    await channel.send(
        embed=embed,
        view=DeveloperTaskView()
    )


# =========================================================
# DEVELOPER SHIFT SYSTEM
# =========================================================

class DeveloperShiftStartButton(Button):

    def __init__(self):
        super().__init__(
            label="Schicht starten",
            emoji="🟢",
            style=discord.ButtonStyle.success,
            custom_id="rlp_shift_start"
        )

    async def callback(self, interaction):

        if not has_role(
            interaction.user,
            SHIFT_PERMISSION_ROLE_ID
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
                "❌ Schicht-Rolle nicht gefunden.",
                ephemeral=True
            )
            return

        try:

            await interaction.user.add_roles(
                role,
                reason="Developer Schicht gestartet"
            )

            log_channel = get_channel(
                SHIFT_LOG_CHANNEL_ID
            )

            if log_channel:

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
                "❌ Ich kann die Schicht-Rolle nicht vergeben.",
                ephemeral=True
            )


class DeveloperShiftEndButton(Button):

    def __init__(self):
        super().__init__(
            label="Schicht beenden",
            emoji="🔴",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_shift_end"
        )

    async def callback(self, interaction):

        if not has_role(
            interaction.user,
            SHIFT_PERMISSION_ROLE_ID
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
                "❌ Schicht-Rolle nicht gefunden.",
                ephemeral=True
            )
            return

        try:

            await interaction.user.remove_roles(
                role,
                reason="Developer Schicht beendet"
            )

            log_channel = get_channel(
                SHIFT_LOG_CHANNEL_ID
            )

            if log_channel:

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
                "❌ Ich kann die Schicht-Rolle nicht entfernen.",
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


async def update_developer_shift_panel():

    channel = get_channel(
        DEVELOPER_SHIFT_CHANNEL_ID
    )

    if channel is None:
        return

    embed = discord.Embed(
        title="🖥️ Developer Schicht",
        description=(
            "🟢 **Schicht starten**\n"
            "🔴 **Schicht beenden**"
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Panel",
        value=SHIFT_PANEL_MARKER,
        inline=False
    )

    async for message in channel.history(limit=50):

        if message.author == bot.user and message.embeds:

            for old_embed in message.embeds:

                for field in old_embed.fields:

                    if field.value == SHIFT_PANEL_MARKER:

                        await message.edit(
                            embed=embed,
                            view=DeveloperShiftView()
                        )
                        return

    await channel.send(
        embed=embed,
        view=DeveloperShiftView()
    )


# =========================================================
# QUIZ
# =========================================================

QUIZ_QUESTIONS = [
    ("🇩🇪", "deutschland"),
    ("🇺🇸🗽", "usa"),
    ("🍎", "apfel"),
    ("🍌", "banane"),
    ("🐶", "hund"),
    ("🐱", "katze"),
    ("🌞", "sonne"),
    ("🌙", "mond"),
    ("🚗", "auto"),
    ("✈️", "flugzeug"),
    ("🏠", "haus"),
    ("⚽", "fußball"),
    ("🎮", "gaming"),
    ("🍕", "pizza"),
    ("🍔", "burger"),
    ("🌳", "baum"),
    ("🌊", "meer"),
    ("❄️", "schnee"),
    ("🔥", "feuer"),
    ("❤️", "herz"),
    ("🌍", "erde"),
    ("🐼", "panda"),
    ("🦁", "löwe"),
    ("🐘", "elefant"),
    ("🍓", "erdbeere")
]

quiz_message_id = None
quiz_answer = None
quiz_lock = asyncio.Lock()
quiz_starting = False
used_quiz_questions = set()


async def send_quiz_question():

    global quiz_message_id
    global quiz_answer
    global quiz_starting

    async with quiz_lock:

        if quiz_starting:
            return

        quiz_starting = True

        try:

            channel = get_channel(
                QUIZ_CHANNEL_ID
            )

            if channel is None:
                return

            available = [
                q for q in QUIZ_QUESTIONS
                if q not in used_quiz_questions
            ]

            if not available:

                used_quiz_questions.clear()
                available = QUIZ_QUESTIONS.copy()

            question, answer = random.choice(
                available
            )

            used_quiz_questions.add(
                (question, answer)
            )

            message = await channel.send(
                f"❓ **Was bedeutet dieses Emoji?**\n\n"
                f"# {question}"
            )

            quiz_message_id = message.id
            quiz_answer = answer.lower()

        finally:

            quiz_starting = False


# =========================================================
# COMMUNITY FORMS
# =========================================================

class SuggestionModal(Modal):

    def __init__(self):
        super().__init__(title="Vorschlag")

        self.text = TextInput(
            label="Dein Vorschlag",
            placeholder="Was möchtest du am Server ändern?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.text)

    async def on_submit(self, interaction):

        suggestion_id = make_id("SUG")

        data["suggestions"][suggestion_id] = {
            "user_id": interaction.user.id,
            "text": self.text.value,
            "created": int(time.time()),
            "status": "Offen"
        }

        save_data()

        channel = get_channel(
            APPLICATION_CHANNEL_ID
        )

        if channel:

            embed = discord.Embed(
                title="💡 Neuer Vorschlag",
                description=self.text.value,
                color=discord.Color.gold()
            )

            embed.add_field(
                name="ID",
                value=suggestion_id
            )

            embed.add_field(
                name="Von",
                value=interaction.user.mention
            )

            await channel.send(
                embed=embed
            )

        await interaction.response.send_message(
            f"✅ Vorschlag `{suggestion_id}` wurde gesendet.",
            ephemeral=True
        )


class FeedbackModal(Modal):

    def __init__(self):
        super().__init__(title="Feedback")

        self.text = TextInput(
            label="Feedback",
            placeholder="Dein Feedback...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.text)

    async def on_submit(self, interaction):

        feedback_id = make_id("FDB")

        data["feedback"][feedback_id] = {
            "user_id": interaction.user.id,
            "text": self.text.value,
            "created": int(time.time())
        }

        save_data()

        channel = get_channel(
            APPLICATION_CHANNEL_ID
        )

        if channel:

            embed = discord.Embed(
                title="💬 Neues Feedback",
                description=self.text.value,
                color=discord.Color.blue()
            )

            embed.add_field(
                name="ID",
                value=feedback_id
            )

            embed.add_field(
                name="Von",
                value=interaction.user.mention
            )

            await channel.send(
                embed=embed
            )

        await interaction.response.send_message(
            "✅ Vielen Dank für dein Feedback!",
            ephemeral=True
        )


class BugModal(Modal):

    def __init__(self):
        super().__init__(title="Bug melden")

        self.text = TextInput(
            label="Bug",
            placeholder="Was funktioniert nicht?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.text)

    async def on_submit(self, interaction):

        bug_id = make_id("BUG")

        data["bugs"][bug_id] = {
            "user_id": interaction.user.id,
            "text": self.text.value,
            "created": int(time.time()),
            "status": "Offen"
        }

        save_data()

        channel = get_channel(
            DEVELOPER_TASK_CHANNEL_ID
        )

        if channel:

            embed = discord.Embed(
                title="🐛 Neuer Bug",
                description=self.text.value,
                color=discord.Color.red()
            )

            embed.add_field(
                name="Bug ID",
                value=bug_id
            )

            embed.add_field(
                name="Gemeldet von",
                value=interaction.user.mention
            )

            await channel.send(
                embed=embed
            )

        await interaction.response.send_message(
            f"🐛 Bug `{bug_id}` wurde gemeldet.",
            ephemeral=True
        )


# =========================================================
# COMMUNITY PANEL
# =========================================================

class SuggestionButton(Button):

    def __init__(self):
        super().__init__(
            label="Vorschlag",
            emoji="💡",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_community_suggestion"
        )

    async def callback(self, interaction):

        await interaction.response.send_modal(
            SuggestionModal()
        )


class FeedbackButton(Button):

    def __init__(self):
        super().__init__(
            label="Feedback",
            emoji="💬",
            style=discord.ButtonStyle.secondary,
            custom_id="rlp_community_feedback"
        )

    async def callback(self, interaction):

        await interaction.response.send_modal(
            FeedbackModal()
        )


class BugButton(Button):

    def __init__(self):
        super().__init__(
            label="Bug melden",
            emoji="🐛",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_community_bug"
        )

    async def callback(self, interaction):

        await interaction.response.send_modal(
            BugModal()
        )


class CommunityPanelView(View):

    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(SuggestionButton())
        self.add_item(FeedbackButton())
        self.add_item(BugButton())


async def send_community_panel(channel):

    embed = discord.Embed(
        title="🌟 RLP Community",
        description=(
            "Hier findest du wichtige Community-Funktionen.\n\n"
            "💡 **Vorschlag**\n"
            "Schlage neue Ideen für den Server vor.\n\n"
            "💬 **Feedback**\n"
            "Sende Feedback an das Team.\n\n"
            "🐛 **Bug melden**\n"
            "Melde einen Fehler des Servers oder Bots."
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


# =========================================================
# EVENT SYSTEM
# =========================================================

class EventJoinButton(Button):

    def __init__(self, event_id):

        super().__init__(
            label="Teilnehmen",
            emoji="🙋",
            style=discord.ButtonStyle.success,
            custom_id=f"rlp_event_join_{event_id}"
        )

        self.event_id = event_id

    async def callback(self, interaction):

        event = data["events"].get(
            self.event_id
        )

        if event is None:

            await interaction.response.send_message(
                "❌ Dieses Event existiert nicht mehr.",
                ephemeral=True
            )
            return

        if interaction.user.id in event["participants"]:

            await interaction.response.send_message(
                "ℹ️ Du nimmst bereits teil.",
                ephemeral=True
            )
            return

        event["participants"].append(
            interaction.user.id
        )

        save_data()

        await interaction.response.send_message(
            "🎉 Du nimmst jetzt am Event teil!",
            ephemeral=True
        )


class EventLeaveButton(Button):

    def __init__(self, event_id):

        super().__init__(
            label="Austragen",
            emoji="❌",
            style=discord.ButtonStyle.secondary,
            custom_id=f"rlp_event_leave_{event_id}"
        )

        self.event_id = event_id

    async def callback(self, interaction):

        event = data["events"].get(
            self.event_id
        )

        if event is None:

            await interaction.response.send_message(
                "❌ Event nicht gefunden.",
                ephemeral=True
            )
            return

        if interaction.user.id not in event["participants"]:

            await interaction.response.send_message(
                "ℹ️ Du nimmst aktuell nicht teil.",
                ephemeral=True
            )
            return

        event["participants"].remove(
            interaction.user.id
        )

        save_data()

        await interaction.response.send_message(
            "✅ Du wurdest vom Event ausgetragen.",
            ephemeral=True
        )


class EventView(View):

    def __init__(self, event_id):

        super().__init__(timeout=None)

        self.add_item(
            EventJoinButton(event_id)
        )

        self.add_item(
            EventLeaveButton(event_id)
        )


# =========================================================
# GIVEAWAY SYSTEM
# =========================================================

class GiveawayJoinButton(Button):

    def __init__(self, giveaway_id):

        super().__init__(
            label="Teilnehmen",
            emoji="🎉",
            style=discord.ButtonStyle.success,
            custom_id=f"rlp_giveaway_join_{giveaway_id}"
        )

        self.giveaway_id = giveaway_id

    async def callback(self, interaction):

        giveaway = data["giveaways"].get(
            self.giveaway_id
        )

        if giveaway is None:

            await interaction.response.send_message(
                "❌ Giveaway nicht gefunden.",
                ephemeral=True
            )
            return

        if giveaway["ended"]:

            await interaction.response.send_message(
                "❌ Dieses Giveaway ist bereits beendet.",
                ephemeral=True
            )
            return

        if interaction.user.id in giveaway["participants"]:

            await interaction.response.send_message(
                "ℹ️ Du nimmst bereits teil.",
                ephemeral=True
            )
            return

        giveaway["participants"].append(
            interaction.user.id
        )

        save_data()

        await interaction.response.send_message(
            "🎉 Du bist dabei!",
            ephemeral=True
        )


class GiveawayView(View):

    def __init__(self, giveaway_id):

        super().__init__(timeout=None)

        self.add_item(
            GiveawayJoinButton(giveaway_id)
        )


async def finish_giveaway(giveaway_id):

    giveaway = data["giveaways"].get(
        giveaway_id
    )

    if giveaway is None:
        return

    if giveaway["ended"]:
        return

    giveaway["ended"] = True

    participants = giveaway["participants"]

    winners_count = giveaway["winners"]

    channel = get_channel(
        giveaway["channel_id"]
    )

    if not participants:

        winners_text = "Niemand hat teilgenommen."

    else:

        winners = random.sample(
            participants,
            min(winners_count, len(participants))
        )

        mentions = []

        for user_id in winners:

            user = bot.get_user(user_id)

            if user:
                mentions.append(user.mention)

        winners_text = ", ".join(
            mentions
        ) if mentions else "Gewinner nicht gefunden."

    save_data()

    if channel:

        await channel.send(
            f"🎉 **Giveaway beendet!**\n\n"
            f"🎁 Preis: **{giveaway['prize']}**\n"
            f"🏆 Gewinner: {winners_text}"
        )


# =========================================================
# OWNER PANEL
# =========================================================

class AnnouncementModal(Modal):

    def __init__(self, channel):

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

    async def on_submit(self, interaction):

        if not is_owner(interaction.user):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
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
            text=f"Ankündigung von {interaction.user.display_name}"
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
                "❌ Keine Berechtigung zum Senden.",
                ephemeral=True
            )


class BotSayModal(Modal):

    def __init__(self, channel):

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

    async def on_submit(self, interaction):

        if not is_owner(interaction.user):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
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
                "❌ Keine Berechtigung zum Schreiben.",
                ephemeral=True
            )


class OwnerChannelSelectView(View):

    def __init__(self, action):

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

        self.select.callback = self.channel_selected

        self.add_item(
            self.select
        )

    async def channel_selected(self, interaction):

        if not is_owner(interaction.user):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        try:

            selected_channel = self.select.values[0]

            channel = get_real_text_channel(
                interaction.guild,
                selected_channel
            )

            if channel is None:

                await interaction.response.send_message(
                    "❌ Textkanal konnte nicht gefunden werden.",
                    ephemeral=True
                )
                return

            if self.action == "announcement":

                await interaction.response.send_modal(
                    AnnouncementModal(channel)
                )

                return

            if self.action == "say":

                await interaction.response.send_modal(
                    BotSayModal(channel)
                )

                return

            if self.action == "lock":

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

                return

            if self.action == "unlock":

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

        except discord.Forbidden:

            if interaction.response.is_done():

                await interaction.followup.send(
                    "❌ Bot hat nicht genügend Berechtigungen.",
                    ephemeral=True
                )

            else:

                await interaction.response.send_message(
                    "❌ Bot hat nicht genügend Berechtigungen.",
                    ephemeral=True
                )

        except Exception as e:

            print(
                f"OWNER SELECT ERROR: "
                f"{type(e).__name__}: {e}"
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

    async def callback(self, interaction):

        if not is_owner(interaction.user):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "📢 **Wähle den Kanal:**",
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

    async def callback(self, interaction):

        if not is_owner(interaction.user):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
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

    async def callback(self, interaction):

        if not is_owner(interaction.user):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
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

    async def callback(self, interaction):

        if not is_owner(interaction.user):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
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

    async def callback(self, interaction):

        if not is_owner(interaction.user):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
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
            custom_id="rlp_owner_server_info"
        )

    async def callback(self, interaction):

        if not is_owner(interaction.user):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        guild = interaction.guild

        embed = discord.Embed(
            title="🖥️ Server Informationen",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Server",
            value=guild.name,
            inline=True
        )

        embed.add_field(
            name="Server ID",
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

        if guild.owner:

            embed.add_field(
                name="Owner",
                value=guild.owner.mention,
                inline=True
            )

        if guild.icon:

            embed.set_thumbnail(
                url=guild.icon.url
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


async def send_owner_panel(channel):

    embed = discord.Embed(
        title="👑 RLP Owner Panel",
        description=(
            "Server- und Community-Verwaltung.\n\n"
            "📢 **Ankündigung**\n"
            "Eine Embed-Ankündigung senden.\n\n"
            "💬 **Bot Say**\n"
            "Der Bot schreibt eine Nachricht.\n\n"
            "🔒 **Channel Lock**\n"
            "Einen Kanal sperren.\n\n"
            "🔓 **Channel Unlock**\n"
            "Einen Kanal entsperren.\n\n"
            "📊 **Bot Status**\n"
            "Bot-Statistiken anzeigen.\n\n"
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


# =========================================================
# PROFILE
# =========================================================

@bot.command(name="profile")
async def profile_command(ctx, member: discord.Member = None):

    member = member or ctx.author

    embed = discord.Embed(
        title=f"👤 Profil von {member.display_name}",
        color=member.color
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.add_field(
        name="👤 Name",
        value=member.display_name,
        inline=True
    )

    embed.add_field(
        name="🆔 ID",
        value=str(member.id),
        inline=True
    )

    embed.add_field(
        name="📅 Server beigetreten",
        value=discord.utils.format_dt(
            member.joined_at,
            "D"
        ) if member.joined_at else "Unbekannt",
        inline=True
    )

    embed.add_field(
        name="📅 Account erstellt",
        value=discord.utils.format_dt(
            member.created_at,
            "D"
        ),
        inline=True
    )

    roles = [
        role.mention
        for role in member.roles
        if role != ctx.guild.default_role
    ]

    embed.add_field(
        name="🎭 Rollen",
        value=" ".join(roles[:20]) if roles else "Keine",
        inline=False
    )

    await ctx.send(
        embed=embed
    )


@bot.command(name="userinfo")
async def userinfo_command(ctx, member: discord.Member = None):

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
        value=str(member),
        inline=True
    )

    embed.add_field(
        name="Display Name",
        value=member.display_name,
        inline=True
    )

    embed.add_field(
        name="ID",
        value=str(member.id),
        inline=True
    )

    embed.add_field(
        name="Bot",
        value="Ja" if member.bot else "Nein",
        inline=True
    )

    embed.add_field(
        name="Serverbeitritt",
        value=discord.utils.format_dt(
            member.joined_at,
            "F"
        ) if member.joined_at else "Unbekannt",
        inline=False
    )

    await ctx.send(
        embed=embed
    )


@bot.command(name="avatar")
async def avatar_command(ctx, member: discord.Member = None):

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


@bot.command(name="banner")
async def banner_command(ctx, member: discord.Member = None):

    member = member or ctx.author

    user = await bot.fetch_user(
        member.id
    )

    if not user.banner:

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


@bot.command(name="roles")
async def roles_command(ctx, member: discord.Member = None):

    member = member or ctx.author

    roles = [
        role.mention
        for role in member.roles
        if role != ctx.guild.default_role
    ]

    embed = discord.Embed(
        title=f"🎭 Rollen von {member.display_name}",
        description=" ".join(roles) if roles else "Keine Rollen.",
        color=discord.Color.blurple()
    )

    await ctx.send(
        embed=embed
    )


@bot.command(name="joined")
async def joined_command(ctx, member: discord.Member = None):

    member = member or ctx.author

    if not member.joined_at:

        await ctx.send(
            "❌ Beitrittsdatum nicht verfügbar."
        )
        return

    await ctx.send(
        f"📅 **{member.display_name}** ist seit "
        f"{discord.utils.format_dt(member.joined_at, 'F')} "
        f"auf dem Server."
    )


# =========================================================
# SERVER / BOT INFO
# =========================================================

@bot.command(name="serverinfo")
async def serverinfo_command(ctx):

    guild = ctx.guild

    bots = sum(
        1
        for member in guild.members
        if member.bot
    )

    humans = guild.member_count - bots

    embed = discord.Embed(
        title=f"🖥️ {guild.name}",
        color=discord.Color.blurple()
    )

    if guild.icon:
        embed.set_thumbnail(
            url=guild.icon.url
        )

    embed.add_field(
        name="🆔 ID",
        value=str(guild.id),
        inline=True
    )

    embed.add_field(
        name="👥 Mitglieder",
        value=str(guild.member_count),
        inline=True
    )

    embed.add_field(
        name="👤 Menschen",
        value=str(humans),
        inline=True
    )

    embed.add_field(
        name="🤖 Bots",
        value=str(bots),
        inline=True
    )

    embed.add_field(
        name="💬 Textkanäle",
        value=str(
            len(guild.text_channels)
        ),
        inline=True
    )

    embed.add_field(
        name="🔊 Voice",
        value=str(
            len(guild.voice_channels)
        ),
        inline=True
    )

    embed.add_field(
        name="🎭 Rollen",
        value=str(
            len(guild.roles)
        ),
        inline=True
    )

    embed.add_field(
        name="🚀 Boosts",
        value=str(
            guild.premium_subscription_count
        ),
        inline=True
    )

    embed.add_field(
        name="📅 Erstellt",
        value=discord.utils.format_dt(
            guild.created_at,
            "D"
        ),
        inline=False
    )

    await ctx.send(
        embed=embed
    )


@bot.command(name="botinfo")
async def botinfo_command(ctx):

    embed = discord.Embed(
        title="🤖 RLP Bot",
        description="Community- und Server-Management Bot",
        color=discord.Color.blurple()
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

    embed.add_field(
        name="👥 Nutzer",
        value=str(
            sum(
                guild.member_count or 0
                for guild in bot.guilds
            )
        ),
        inline=True
    )

    embed.add_field(
        name="⚙️ Commands",
        value=str(len(bot.commands)),
        inline=True
    )

    await ctx.send(
        embed=embed
    )


@bot.command(name="status")
async def status_command(ctx):

    await ctx.send(
        f"🟢 **RLP Bot ist online!**\n"
        f"📡 Ping: `{round(bot.latency * 1000)}ms`"
    )


# =========================================================
# VOICE STATS
# =========================================================

@bot.command(name="voicestats")
async def voicestats_command(ctx):

    total = 0
    support = 0

    for voice_channel in ctx.guild.voice_channels:

        total += len(
            voice_channel.members
        )

        if voice_channel.id == SUPPORT_VOICE_CHANNEL_ID:
            support = len(
                voice_channel.members
            )

    embed = discord.Embed(
        title="🔊 Voice Statistik",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👥 Im Voice",
        value=str(total),
        inline=True
    )

    embed.add_field(
        name="🎧 Support",
        value=str(support),
        inline=True
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# COMMUNITY STATS
# =========================================================

@bot.command(name="community")
async def community_command(ctx):

    guild = ctx.guild

    online = sum(
        1
        for member in guild.members
        if member.status != discord.Status.offline
        and not member.bot
    )

    embed = discord.Embed(
        title="🌐 RLP Community",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👥 Mitglieder",
        value=str(guild.member_count),
        inline=True
    )

    embed.add_field(
        name="🟢 Online",
        value=str(online),
        inline=True
    )

    embed.add_field(
        name="🚗 Kennzeichen",
        value=str(
            len(data["license_plates"])
        ),
        inline=True
    )

    embed.add_field(
        name="📨 Bewerbungen",
        value=str(
            len(data["applications"])
        ),
        inline=True
    )

    embed.add_field(
        name="💡 Vorschläge",
        value=str(
            len(data["suggestions"])
        ),
        inline=True
    )

    embed.add_field(
        name="🐛 Bugs",
        value=str(
            len(data["bugs"])
        ),
        inline=True
    )

    embed.add_field(
        name="🎉 Events",
        value=str(
            len(data["events"])
        ),
        inline=True
    )

    embed.add_field(
        name="🎁 Giveaways",
        value=str(
            len(data["giveaways"])
        ),
        inline=True
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# LINKS
# =========================================================

@bot.command(name="links")
async def links_command(ctx):

    embed = discord.Embed(
        title="🔗 Wichtige Links",
        color=discord.Color.blurple()
    )

    for name, value in data["links"].items():

        embed.add_field(
            name=name,
            value=value,
            inline=False
        )

    await ctx.send(
        embed=embed
    )


@bot.command(name="rules")
async def rules_command(ctx):

    embed = discord.Embed(
        title="📜 Server Regeln",
        description=data["server_settings"]["rules"],
        color=discord.Color.blue()
    )

    await ctx.send(
        embed=embed
    )


@bot.command(name="team")
async def team_command(ctx):

    embed = discord.Embed(
        title="👥 RLP Team",
        description=data["server_settings"]["team"],
        color=discord.Color.blurple()
    )

    await ctx.send(
        embed=embed
    )


@bot.command(name="staff")
async def staff_command(ctx):

    team_roles = [
        OWNER_ROLE_ID,
        SHIFT_PERMISSION_ROLE_ID,
        DEVELOPER_SHIFT_ROLE_ID
    ]

    members = []

    for member in ctx.guild.members:

        if any(
            role.id in team_roles
            for role in member.roles
        ):

            members.append(
                member.mention
            )

    embed = discord.Embed(
        title="👥 Aktives Team",
        description=(
            "\n".join(members)
            if members
            else "Keine Teammitglieder gefunden."
        ),
        color=discord.Color.blurple()
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# CHANNEL / ROLE INFO
# =========================================================

@bot.command(name="channelinfo")
async def channelinfo_command(ctx):

    channel = ctx.channel

    embed = discord.Embed(
        title=f"📋 Channel Info: #{channel.name}",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🆔 ID",
        value=str(channel.id),
        inline=True
    )

    embed.add_field(
        name="Kategorie",
        value=channel.category.name
        if channel.category
        else "Keine",
        inline=True
    )

    embed.add_field(
        name="Position",
        value=str(channel.position),
        inline=True
    )

    await ctx.send(
        embed=embed
    )


@bot.command(name="roleinfo")
async def roleinfo_command(
    ctx,
    role: discord.Role
):

    embed = discord.Embed(
        title=f"🎭 Rolle: {role.name}",
        color=role.color
    )

    embed.add_field(
        name="🆔 ID",
        value=str(role.id),
        inline=True
    )

    embed.add_field(
        name="👥 Nutzer",
        value=str(len(role.members)),
        inline=True
    )

    embed.add_field(
        name="Position",
        value=str(role.position),
        inline=True
    )

    embed.add_field(
        name="Mentionable",
        value="Ja" if role.mentionable else "Nein",
        inline=True
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# EVENT COMMAND
# =========================================================

@bot.command(name="eventcreate")
async def eventcreate_command(
    ctx,
    title: str,
    date: str,
    time_text: str,
    *,
    description: str
):

    if not is_owner(ctx.author):

        await ctx.send(
            "❌ Nur Owner können Events erstellen.",
            delete_after=5
        )
        return

    event_id = make_id("EVENT")

    data["events"][event_id] = {
        "title": title,
        "date": date,
        "time": time_text,
        "description": description,
        "participants": [],
        "created_by": ctx.author.id,
        "channel_id": ctx.channel.id
    }

    save_data()

    embed = discord.Embed(
        title=f"🎉 {title}",
        description=description,
        color=discord.Color.green()
    )

    embed.add_field(
        name="📅 Datum",
        value=date,
        inline=True
    )

    embed.add_field(
        name="🕐 Uhrzeit",
        value=time_text,
        inline=True
    )

    embed.add_field(
        name="👥 Teilnehmer",
        value="0",
        inline=True
    )

    embed.set_footer(
        text=f"Event ID: {event_id}"
    )

    await ctx.send(
        embed=embed,
        view=EventView(event_id)
    )


@bot.command(name="event")
async def event_command(ctx):

    events = data["events"]

    if not events:

        await ctx.send(
            "ℹ️ Aktuell gibt es keine Events."
        )
        return

    embed = discord.Embed(
        title="🎉 Aktuelle Events",
        color=discord.Color.green()
    )

    for event_id, event in list(
        events.items()
    )[-10:]:

        embed.add_field(
            name=event["title"],
            value=(
                f"📅 {event['date']}\n"
                f"🕐 {event['time']}\n"
                f"👥 {len(event['participants'])} Teilnehmer"
            ),
            inline=False
        )

    await ctx.send(
        embed=embed
    )


# =========================================================
# GIVEAWAY COMMAND
# =========================================================

@bot.command(name="giveaway")
async def giveaway_command(
    ctx,
    duration: str,
    winners: int,
    *,
    prize: str
):

    if not is_owner(ctx.author):

        await ctx.send(
            "❌ Nur Owner können Giveaways starten.",
            delete_after=5
        )
        return

    seconds = parse_duration(
        duration
    )

    if seconds is None or seconds < 10:

        await ctx.send(
            "❌ Dauer ungültig. Beispiel: `!giveaway 1h 2 Nitro`",
            delete_after=7
        )
        return

    if winners < 1 or winners > 20:

        await ctx.send(
            "❌ Gewinner muss zwischen 1 und 20 liegen.",
            delete_after=5
        )
        return

    giveaway_id = make_id("GIVE")

    end_timestamp = int(
        time.time() + seconds
    )

    data["giveaways"][giveaway_id] = {
        "channel_id": ctx.channel.id,
        "prize": prize,
        "winners": winners,
        "participants": [],
        "ended": False,
        "end_time": end_timestamp,
        "created_by": ctx.author.id
    }

    save_data()

    embed = discord.Embed(
        title="🎁 Giveaway",
        description=(
            f"🎁 **Preis:** {prize}\n\n"
            f"🏆 **Gewinner:** {winners}\n"
            f"⏰ **Ende:** <t:{end_timestamp}:R>\n\n"
            "Klicke auf **Teilnehmen**, um mitzumachen."
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(
        text=f"Giveaway ID: {giveaway_id}"
    )

    await ctx.send(
        embed=embed,
        view=GiveawayView(giveaway_id)
    )

    await asyncio.sleep(seconds)

    await finish_giveaway(
        giveaway_id
    )


# =========================================================
# GIVEAWAY LIST
# =========================================================

@bot.command(name="giveaways")
async def giveaways_command(ctx):

    active = [
        giveaway
        for giveaway in data["giveaways"].values()
        if not giveaway["ended"]
    ]

    if not active:

        await ctx.send(
            "ℹ️ Aktuell gibt es keine aktiven Giveaways."
        )
        return

    embed = discord.Embed(
        title="🎁 Aktive Giveaways",
        color=discord.Color.gold()
    )

    for giveaway in active:

        embed.add_field(
            name=giveaway["prize"],
            value=(
                f"🏆 Gewinner: {giveaway['winners']}\n"
                f"👥 Teilnehmer: "
                f"{len(giveaway['participants'])}\n"
                f"⏰ <t:{giveaway['end_time']}:R>"
            ),
            inline=False
        )

    await ctx.send(
        embed=embed
    )


# =========================================================
# DEVELOPER COMMANDS
# =========================================================

@bot.command(name="tasks")
async def tasks_command(ctx):

    if not has_role(
        ctx.author,
        SHIFT_PERMISSION_ROLE_ID
    ):

        await ctx.send(
            "❌ Keine Berechtigung.",
            delete_after=5
        )
        return

    tasks = [
        (task_id, task)
        for task_id, task
        in data["developer_tasks"].items()
        if not task["completed"]
    ]

    if not tasks:

        await ctx.send(
            "✅ Keine offenen Developer-Aufgaben."
        )
        return

    embed = discord.Embed(
        title="🛠️ Offene Aufgaben",
        color=discord.Color.orange()
    )

    for task_id, task in tasks[-15:]:

        embed.add_field(
            name=task_id,
            value=task["task"],
            inline=False
        )

    await ctx.send(
        embed=embed
    )


@bot.command(name="taskinfo")
async def taskinfo_command(
    ctx,
    task_id: str
):

    task = data["developer_tasks"].get(
        task_id
    )

    if task is None:

        await ctx.send(
            "❌ Task nicht gefunden."
        )
        return

    embed = discord.Embed(
        title=f"🛠️ Task {task_id}",
        description=task["task"],
        color=discord.Color.orange()
    )

    embed.add_field(
        name="Status",
        value="Erledigt"
        if task["completed"]
        else "Offen"
    )

    await ctx.send(
        embed=embed
    )


@bot.command(name="taskdone")
async def taskdone_command(
    ctx,
    task_id: str
):

    if not has_role(
        ctx.author,
        SHIFT_PERMISSION_ROLE_ID
    ):

        await ctx.send(
            "❌ Keine Berechtigung.",
            delete_after=5
        )
        return

    task = data["developer_tasks"].get(
        task_id
    )

    if task is None:

        await ctx.send(
            "❌ Task nicht gefunden."
        )
        return

    task["completed"] = True
    save_data()

    await ctx.send(
        f"✅ Task `{task_id}` wurde als erledigt markiert."
    )


@bot.command(name="taskdelete")
async def taskdelete_command(
    ctx,
    task_id: str
):

    if not is_owner(ctx.author):

        await ctx.send(
            "❌ Nur Owner.",
            delete_after=5
        )
        return

    if task_id not in data["developer_tasks"]:

        await ctx.send(
            "❌ Task nicht gefunden."
        )
        return

    del data["developer_tasks"][task_id]

    save_data()

    await ctx.send(
        f"🗑️ Task `{task_id}` wurde gelöscht."
    )


# =========================================================
# DEVELOPER STATUS
# =========================================================

@bot.command(name="developers")
async def developers_command(ctx):

    role = ctx.guild.get_role(
        DEVELOPER_SHIFT_ROLE_ID
    )

    if role is None:

        await ctx.send(
            "❌ Developer-Rolle nicht gefunden."
        )
        return

    members = role.members

    embed = discord.Embed(
        title="🛠️ Aktive Developer",
        color=discord.Color.green()
    )

    if not members:

        embed.description = (
            "Aktuell ist kein Developer aktiv."
        )

    else:

        embed.description = "\n".join(
            f"🟢 {member.mention}"
            for member in members
        )

    await ctx.send(
        embed=embed
    )


@bot.command(name="devstatus")
async def devstatus_command(ctx):

    role = ctx.guild.get_role(
        DEVELOPER_SHIFT_ROLE_ID
    )

    active = len(
        role.members
    ) if role else 0

    await ctx.send(
        f"🛠️ **Developer Status**\n"
        f"🟢 Aktive Developer: `{active}`"
    )


@bot.command(name="shifts")
async def shifts_command(ctx):

    role = ctx.guild.get_role(
        DEVELOPER_SHIFT_ROLE_ID
    )

    if role is None:

        await ctx.send(
            "❌ Developer-Rolle nicht gefunden."
        )
        return

    if not role.members:

        await ctx.send(
            "🛠️ Aktuell ist niemand in einer Developer-Schicht."
        )
        return

    await ctx.send(
        "🛠️ **Aktive Schichten:**\n" +
        "\n".join(
            f"🟢 {member.mention}"
            for member in role.members
        )
    )


# =========================================================
# PLATE COMMANDS
# =========================================================

@bot.command(name="myplate")
async def myplate_command(ctx):

    plate = data["license_plates"].get(
        str(ctx.author.id)
    )

    if plate is None:

        await ctx.send(
            "🚗 Du hast noch kein Kennzeichen."
        )
        return

    await ctx.send(
        f"🚗 Dein Kennzeichen ist "
        f"**{plate['plate']}**"
    )


@bot.command(name="plateinfo")
async def plateinfo_command(
    ctx,
    member: discord.Member = None
):

    member = member or ctx.author

    plate = data["license_plates"].get(
        str(member.id)
    )

    if plate is None:

        await ctx.send(
            f"🚗 {member.mention} hat kein Kennzeichen."
        )
        return

    await ctx.send(
        f"🚗 {member.mention} hat "
        f"**{plate['plate']}**."
    )


@bot.command(name="plates")
async def plates_command(ctx):

    if not data["license_plates"]:

        await ctx.send(
            "🚗 Noch keine Kennzeichen vergeben."
        )
        return

    lines = []

    for plate in data["license_plates"].values():

        lines.append(
            f"🚗 `{plate['plate']}` — "
            f"**{plate['name']}**"
        )

    embed = discord.Embed(
        title="🚗 Kennzeichen",
        description="\n".join(lines)[:4000],
        color=discord.Color.blue()
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# NAMETAG COMMANDS
# =========================================================

@bot.command(name="nametag")
async def nametag_command(ctx):

    nick = ctx.author.nick

    if not nick:

        await ctx.send(
            "🏷️ Du hast keinen Server-Nickname."
        )
        return

    if nick.startswith(NAMETAG):

        await ctx.send(
            f"🏷️ Dein Nametag ist aktiv:\n`{nick}`"
        )

    else:

        await ctx.send(
            "🏷️ Du hast aktuell keinen RLP-Nametag."
        )


@bot.command(name="nametaginfo")
async def nametaginfo_command(ctx):

    await ctx.send(
        f"🏷️ Der aktuelle RLP-Nametag ist:\n"
        f"`{NAMETAG}`"
    )


# =========================================================
# SUGGESTIONS / FEEDBACK / BUG COMMANDS
# =========================================================

@bot.command(name="suggest")
async def suggest_command(ctx):

    await ctx.send(
        "💡 Nutze das Community-Panel, um einen Vorschlag einzureichen."
    )


@bot.command(name="suggestions")
async def suggestions_command(ctx):

    suggestions = data["suggestions"]

    if not suggestions:

        await ctx.send(
            "💡 Noch keine Vorschläge."
        )
        return

    embed = discord.Embed(
        title="💡 Vorschläge",
        color=discord.Color.gold()
    )

    for suggestion_id, suggestion in list(
        suggestions.items()
    )[-10:]:

        embed.add_field(
            name=suggestion_id,
            value=(
                f"{suggestion['text']}\n"
                f"Status: {suggestion['status']}"
            )[:1024],
            inline=False
        )

    await ctx.send(
        embed=embed
    )


@bot.command(name="feedback")
async def feedback_command(ctx):

    await ctx.send(
        "💬 Nutze das Community-Panel für Feedback."
    )


@bot.command(name="reportbug")
async def reportbug_command(ctx):

    await ctx.send(
        "🐛 Nutze das Community-Panel, um einen Bug zu melden."
    )


# =========================================================
# COMMUNITY PANEL COMMAND
# =========================================================

@bot.command(name="communitypanel")
async def communitypanel_command(ctx):

    await send_community_panel(
        ctx.channel
    )


# =========================================================
# OWNER SETTINGS COMMANDS
# =========================================================

@bot.command(name="setlink")
async def setlink_command(
    ctx,
    name: str,
    *,
    value: str
):

    if not is_owner(ctx.author):

        await ctx.send(
            "❌ Nur Owner.",
            delete_after=5
        )
        return

    data["links"][name] = value

    save_data()

    await ctx.send(
        f"🔗 Link **{name}** wurde gespeichert."
    )


@bot.command(name="setrules")
async def setrules_command(
    ctx,
    *,
    text: str
):

    if not is_owner(ctx.author):

        await ctx.send(
            "❌ Nur Owner.",
            delete_after=5
        )
        return

    data["server_settings"]["rules"] = text

    save_data()

    await ctx.send(
        "📜 Server-Regeln wurden aktualisiert."
    )


@bot.command(name="setteam")
async def setteam_command(
    ctx,
    *,
    text: str
):

    if not is_owner(ctx.author):

        await ctx.send(
            "❌ Nur Owner.",
            delete_after=5
        )
        return

    data["server_settings"]["team"] = text

    save_data()

    await ctx.send(
        "👥 Team-Information wurde aktualisiert."
    )


# =========================================================
# HELP
# =========================================================

@bot.command(name="help")
async def help_command(ctx):

    embed = discord.Embed(
        title="📚 RLP Bot Commands",
        description="Community- und Server-Funktionen",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👤 Profil",
        value=(
            "`!profile`\n"
            "`!userinfo @User`\n"
            "`!avatar @User`\n"
            "`!banner @User`\n"
            "`!roles @User`\n"
            "`!joined @User`"
        ),
        inline=False
    )

    embed.add_field(
        name="🌐 Server",
        value=(
            "`!serverinfo`\n"
            "`!community`\n"
            "`!voicestats`\n"
            "`!status`\n"
            "`!botinfo`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎉 Community",
        value=(
            "`!communitypanel`\n"
            "`!event`\n"
            "`!suggestions`\n"
            "`!giveaways`\n"
            "`!links`\n"
            "`!rules`\n"
            "`!team`\n"
            "`!staff`"
        ),
        inline=False
    )

    embed.add_field(
        name="🚗 RLP",
        value=(
            "`!myplate`\n"
            "`!plateinfo @User`\n"
            "`!plates`\n"
            "`!nametag`\n"
            "`!nametaginfo`"
        ),
        inline=False
    )

    embed.add_field(
        name="🛠️ Developer",
        value=(
            "`!developers`\n"
            "`!devstatus`\n"
            "`!shifts`\n"
            "`!tasks`\n"
            "`!taskinfo ID`\n"
            "`!taskdone ID`"
        ),
        inline=False
    )

    embed.add_field(
        name="ℹ️ Sonstiges",
        value=(
            "`!ping`\n"
            "`!help`"
        ),
        inline=False
    )

    if is_owner(ctx.author):

        embed.add_field(
            name="👑 Owner",
            value=(
                "`!ownerpanel`\n"
                "`!setlink Name Text`\n"
                "`!setrules Text`\n"
                "`!setteam Text`\n"
                "`!eventcreate Titel Datum Uhrzeit Text`\n"
                "`!giveaway 1h 1 Preis`\n"
                "`!taskdelete ID`"
            ),
            inline=False
        )

    await ctx.send(
        embed=embed
    )


# =========================================================
# PING
# =========================================================

@bot.command(name="ping")
async def ping_command(ctx):

    await ctx.send(
        f"🏓 Pong! `{round(bot.latency * 1000)}ms`"
    )


# =========================================================
# OWNER PANEL COMMANDS
# =========================================================

@bot.command(name="ownerpanel")
async def ownerpanel_command(ctx):

    if not is_owner(ctx.author):

        await ctx.send(
            "❌ Du hast keine Berechtigung.",
            delete_after=5
        )
        return

    await send_owner_panel(
        ctx.channel
    )


@bot.command(name="owner")
async def owner_command(ctx):

    if not is_owner(ctx.author):

        await ctx.send(
            "❌ Du hast keine Berechtigung.",
            delete_after=5
        )
        return

    await send_owner_panel(
        ctx.channel
    )


# =========================================================
# VOICE LOG
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

    if log_channel is None:
        return

    support_channel = get_channel(
        SUPPORT_VOICE_CHANNEL_ID
    )

    if support_channel is None:
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
# MESSAGE EVENT
# =========================================================

@bot.event
async def on_message(message):

    global quiz_message_id
    global quiz_answer

    if message.author.bot:
        return

    if message.channel.id == QUIZ_CHANNEL_ID:

        if quiz_answer is None:

            await asyncio.sleep(6)

            await safe_delete(message)

            return

        user_answer = (
            message.content
            .strip()
            .lower()
        )

        if user_answer == quiz_answer:

            current_question_id = quiz_message_id

            await safe_delete(message)

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

            success_message = await message.channel.send(
                f"✅ **Richtig!** "
                f"{message.author.mention}"
            )

            await asyncio.sleep(4)

            await safe_delete(
                success_message
            )

            await send_quiz_question()

            return

        await safe_delete(message)

        wrong_message = await message.channel.send(
            f"❌ **Falsch!** "
            f"{message.author.mention}"
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
# COMMAND ERROR
# =========================================================

@bot.event
async def on_command_error(
    ctx,
    error
):

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
            "❌ Es fehlen Argumente. Nutze `!help`.",
            delete_after=6
        )
        return

    if isinstance(
        error,
        commands.BadArgument
    ):

        await ctx.send(
            "❌ Ein Argument ist ungültig. "
            "Nutze `!help`.",
            delete_after=6
        )
        return

    print(
        f"COMMAND ERROR: "
        f"{type(error).__name__}: {error}"
    )


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    print("====================================")
    print(f"Bot online: {bot.user}")
    print(f"Guilds: {len(bot.guilds)}")
    print("====================================")

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

    try:
        await update_nametag_panel()
    except Exception as e:
        print(f"Nametag Panel Fehler: {e}")

    try:
        await update_license_panel()
    except Exception as e:
        print(f"Kennzeichen Panel Fehler: {e}")

    try:
        await update_application_panel()
    except Exception as e:
        print(f"Bewerbungs Panel Fehler: {e}")

    try:
        await update_developer_task_panel()
    except Exception as e:
        print(f"Developer Task Panel Fehler: {e}")

    try:
        await update_developer_shift_panel()
    except Exception as e:
        print(f"Developer Shift Panel Fehler: {e}")

    try:
        await send_quiz_question()
    except Exception as e:
        print(f"Quiz Fehler: {e}")


# =========================================================
# START
# =========================================================

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN wurde nicht gefunden."
    )

bot.run(TOKEN)
