import os
import json
import asyncio
import random
import time
import platform
from datetime import datetime, timezone

import discord
from discord.ext import commands


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

# Community
SUGGESTION_CHANNEL_ID = 1540773028642947234
FEEDBACK_CHANNEL_ID = 1556072540307333200
BUG_CHANNEL_ID = 1556072637170716732

# Rollen
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

BOT_START_TIME = time.time()


# =========================================================
# INTENTS
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.voice_states = True


bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)


# =========================================================
# DATA
# =========================================================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "license_plates": {},
            "developer_tasks": {},
            "used_license_numbers": []
        }

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        data.setdefault("license_plates", {})
        data.setdefault("developer_tasks", {})
        data.setdefault("used_license_numbers", [])

        return data

    except Exception:
        return {
            "license_plates": {},
            "developer_tasks": {},
            "used_license_numbers": []
        }


data = load_data()


def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# =========================================================
# HELPER
# =========================================================

def get_guild():
    return bot.get_guild(GUILD_ID)


def get_channel(channel_id):
    channel = bot.get_channel(channel_id)

    if channel is not None:
        return channel

    guild = get_guild()

    if guild is None:
        return None

    return guild.get_channel(channel_id)


def has_role(member, role_id):
    return isinstance(member, discord.Member) and any(
        role.id == role_id for role in member.roles
    )


def is_owner(member):
    return has_role(member, OWNER_ROLE_ID)


async def safe_delete(message):
    try:
        await message.delete()
    except Exception:
        pass


def clean_nametag(nickname):
    if nickname is None:
        return None

    result = nickname

    prefixes = [
        NAMETAG,
        NAMETAG.replace(" ", "\u00a0")
    ]

    for prefix in prefixes:
        if result.startswith(prefix):
            result = result[len(prefix):]
            break

    return result


def format_uptime(seconds):
    seconds = int(seconds)

    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = []

    if days:
        parts.append(f"{days}d")

    if hours:
        parts.append(f"{hours}h")

    if minutes:
        parts.append(f"{minutes}m")

    parts.append(f"{seconds}s")

    return " ".join(parts)


# =========================================================
# QUIZ
# =========================================================

QUIZ_QUESTIONS = [
    ("🇺🇸🗽", "usa"),
    ("🇩🇪🥨", "deutschland"),
    ("🍎📱", "apple"),
    ("🌙⭐", "nacht"),
    ("☀️🌡️", "sommer"),
    ("🐶", "hund"),
    ("🐱", "katze"),
    ("🍕", "pizza"),
    ("⚽🏆", "fußball"),
    ("🚗", "auto"),
    ("🎮", "gaming"),
    ("🍔", "burger"),
    ("🌊🏖️", "strand"),
    ("❄️⛄", "winter"),
    ("🎃", "halloween"),
    ("🎄🎁", "weihnachten"),
    ("❤️", "herz"),
    ("🚀🌌", "weltraum"),
    ("🐼", "panda"),
    ("🦁", "löwe")
]

used_quiz_questions = set()

quiz_message_id = None
quiz_answer = None
quiz_lock = asyncio.Lock()
quiz_starting = False


async def send_quiz_question():
    global quiz_message_id
    global quiz_answer
    global quiz_starting

    async with quiz_lock:
        if quiz_starting:
            return

        if quiz_answer is not None:
            return

        quiz_starting = True

        try:
            channel = get_channel(QUIZ_CHANNEL_ID)

            if channel is None:
                return

            available = [
                q for q in QUIZ_QUESTIONS
                if q[0] not in used_quiz_questions
            ]

            if not available:
                used_quiz_questions.clear()
                available = QUIZ_QUESTIONS.copy()

            question, answer = random.choice(available)

            used_quiz_questions.add(question)

            message = await channel.send(
                f"🧠 **Quiz**\n\n"
                f"Was ist das?\n\n"
                f"# {question}\n\n"
                f"> Schreibe deine Antwort in den Chat!"
            )

            quiz_message_id = message.id
            quiz_answer = answer.lower().strip()

        finally:
            quiz_starting = False


# =========================================================
# NAMETAG
# =========================================================

class NametagResetButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Nametag entfernen",
            emoji="🔄",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_nametag_reset"
        )

    async def callback(self, interaction: discord.Interaction):

        member = interaction.user

        if not isinstance(member, discord.Member):
            await interaction.response.send_message(
                "❌ Dieser Button funktioniert nur auf dem Server.",
                ephemeral=True
            )
            return

        if member.nick is None:
            await interaction.response.send_message(
                "❌ Du hast aktuell keinen Nametag.",
                ephemeral=True
            )
            return

        old_nick = member.nick
        new_nick = clean_nametag(old_nick)

        if new_nick == old_nick:
            await interaction.response.send_message(
                "❌ Dein Nickname enthält keinen RLP-Nametag.",
                ephemeral=True
            )
            return

        try:
            await member.edit(
                nick=new_nick,
                reason="RLP Nametag zurückgesetzt"
            )

            await interaction.response.send_message(
                f"✅ Dein Nametag wurde entfernt.\n"
                f"Neuer Name: **{new_nick}**",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich kann deinen Nickname nicht ändern. "
                "Überprüfe die Bot-Rolle und deren Position.",
                ephemeral=True
            )

        except Exception as e:
            print(f"Nametag Error: {e}")

            await interaction.response.send_message(
                "❌ Beim Entfernen des Nametags ist ein Fehler aufgetreten.",
                ephemeral=True
            )


class NametagView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(NametagResetButton())


async def update_nametag_panel():

    channel = get_channel(NAMETAG_CHANNEL_ID)

    if channel is None:
        return

    embed = discord.Embed(
        title="🏷️ Nametag-System",
        description=(
            "Hier kannst du deinen **RLP-Nametag** verwalten.\n\n"
            f"**Nametag:** `{NAMETAG}`\n\n"
            "Wenn du deinen Nametag entfernen möchtest, "
            "klicke auf den Button unten."
        ),
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Panel",
        value=NAMETAG_PANEL_MARKER,
        inline=False
    )

    found = False

    async for message in channel.history(limit=50):

        if message.author != bot.user:
            continue

        if not message.embeds:
            continue

        if NAMETAG_PANEL_MARKER in message.embeds[0].description if message.embeds[0].description else False:
            found = True
            break

        for field in message.embeds[0].fields:
            if field.value == NAMETAG_PANEL_MARKER:
                found = True
                break

        if found:
            break

    if not found:
        await channel.send(
            embed=embed,
            view=NametagView()
        )


# =========================================================
# KENNZEICHEN
# =========================================================

class LicensePlateModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Kennzeichen erstellen")

        self.plate = discord.ui.TextInput(
            label="Kennzeichen",
            placeholder="z.B. RLP 01 oder RY ZE 25",
            required=True,
            max_length=20
        )

        self.add_item(self.plate)

    async def on_submit(self, interaction):

        user_id = str(interaction.user.id)

        plate = self.plate.value.strip().upper()

        parts = plate.split()

        if len(parts) < 2:
            await interaction.response.send_message(
                "❌ Das Kennzeichen muss aus Prefix + Nummer bestehen.",
                ephemeral=True
            )
            return

        numeric_part = parts[-1]

        if not numeric_part.isdigit():
            await interaction.response.send_message(
                "❌ Die letzte Kennzeichen-Komponente muss eine Zahl sein.",
                ephemeral=True
            )
            return

        number = int(numeric_part)

        if number in data["used_license_numbers"]:
            await interaction.response.send_message(
                "❌ Diese Nummer wird bereits verwendet.",
                ephemeral=True
            )
            return

        if user_id in data["license_plates"]:
            await interaction.response.send_message(
                "❌ Du besitzt bereits ein Kennzeichen.",
                ephemeral=True
            )
            return

        data["license_plates"][user_id] = {
            "plate": plate,
            "number": number,
            "name": interaction.user.display_name
        }

        data["used_license_numbers"].append(number)

        save_data()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen **{plate}** wurde erstellt.",
            ephemeral=True
        )

        await update_license_panel()


class LicensePlateButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Kennzeichen erstellen",
            emoji="🚗",
            style=discord.ButtonStyle.success,
            custom_id="rlp_license_create"
        )

    async def callback(self, interaction):
        await interaction.response.send_modal(
            LicensePlateModal()
        )


class LicensePlateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(LicensePlateButton())


async def update_license_panel():

    channel = get_channel(LICENSE_PLATE_CHANNEL_ID)

    if channel is None:
        return

    embed = discord.Embed(
        title="🚗 Kennzeichen-System",
        description=(
            "Erstelle hier dein persönliches Kennzeichen.\n\n"
            "⚠️ Die **Nummer am Ende** muss serverweit einzigartig sein.\n"
            "Der Prefix darf von mehreren Personen verwendet werden."
        ),
        color=discord.Color.orange()
    )

    if data["license_plates"]:

        lines = []

        for user_id, info in data["license_plates"].items():

            member = channel.guild.get_member(int(user_id))

            if member:
                name = member.display_name
            else:
                name = info.get("name", "Unbekannt")

            lines.append(
                f"» **{info['plate']}** — {name}"
            )

        text = "\n".join(lines)

        if len(text) > 3900:
            text = text[:3900] + "\n..."

        embed.add_field(
            name="Aktuelle Kennzeichen",
            value=text,
            inline=False
        )

    else:

        embed.add_field(
            name="Aktuelle Kennzeichen",
            value="Noch keine Kennzeichen vergeben.",
            inline=False
        )

    embed.add_field(
        name="Panel",
        value=LICENSE_PANEL_MARKER,
        inline=False
    )

    found = False

    async for message in channel.history(limit=50):

        if message.author != bot.user:
            continue

        if not message.embeds:
            continue

        for field in message.embeds[0].fields:
            if field.value == LICENSE_PANEL_MARKER:
                found = True
                break

        if found:
            try:
                await message.edit(
                    embed=embed,
                    view=LicensePlateView()
                )
            except Exception:
                pass

            return

    await channel.send(
        embed=embed,
        view=LicensePlateView()
    )


# =========================================================
# BEWERBUNGEN
# =========================================================

class ApplicationModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Bewerbung")

        self.name_input = discord.ui.TextInput(
            label="Name",
            placeholder="Wie heißt du?",
            required=True,
            max_length=100
        )

        self.age_input = discord.ui.TextInput(
            label="Alter",
            placeholder="Wie alt bist du?",
            required=True,
            max_length=3
        )

        self.reason_input = discord.ui.TextInput(
            label="Warum möchtest du ins Team?",
            placeholder="Erzähle uns etwas über dich...",
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
                "❌ Bewerbungskanal nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📝 Neue Bewerbung",
            color=discord.Color.blurple(),
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
            name="💬 Warum Team?",
            value=self.reason_input.value,
            inline=False
        )

        embed.add_field(
            name="Discord",
            value=f"{interaction.user.mention}\n`{interaction.user.id}`",
            inline=False
        )

        await channel.send(
            content="📥 **Neue Bewerbung eingegangen!**",
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Deine Bewerbung wurde erfolgreich abgeschickt!",
            ephemeral=True
        )


class ApplicationButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Bewerben",
            emoji="📝",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_application_button"
        )

    async def callback(self, interaction):
        await interaction.response.send_modal(
            ApplicationModal()
        )


class ApplicationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ApplicationButton())


async def update_application_panel():

    channel = get_channel(APPLICATION_CHANNEL_ID)

    if channel is None:
        return

    embed = discord.Embed(
        title="📝 Bewerbungen",
        description=(
            "Du möchtest Teil unseres Teams werden?\n\n"
            "Dann klicke auf **Bewerben** und fülle das Formular aus."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Panel",
        value=APPLICATION_PANEL_MARKER,
        inline=False
    )

    found = False

    async for message in channel.history(limit=50):

        if message.author != bot.user:
            continue

        if not message.embeds:
            continue

        for field in message.embeds[0].fields:
            if field.value == APPLICATION_PANEL_MARKER:
                found = True
                break

        if found:
            try:
                await message.edit(
                    embed=embed,
                    view=ApplicationView()
                )
            except Exception:
                pass

            return

    await channel.send(
        embed=embed,
        view=ApplicationView()
    )


# =========================================================
# DEVELOPER TASKS
# =========================================================

class DeveloperTaskModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Developer Aufgabe")

        self.task_input = discord.ui.TextInput(
            label="Aufgabe",
            placeholder="Was soll erledigt werden?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.task_input)

    async def on_submit(self, interaction):

        if not has_role(interaction.user, SHIFT_PERMISSION_ROLE_ID):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung dafür.",
                ephemeral=True
            )
            return

        task_id = str(int(time.time() * 1000))

        data["developer_tasks"][task_id] = {
            "task": self.task_input.value,
            "creator": interaction.user.id,
            "created": datetime.now(timezone.utc).isoformat()
        }

        save_data()

        channel = get_channel(DEVELOPER_TASK_CHANNEL_ID)

        if channel:

            embed = discord.Embed(
                title="👨‍💻 Neue Developer-Aufgabe",
                description=self.task_input.value,
                color=discord.Color.blurple(),
                timestamp=discord.utils.utcnow()
            )

            embed.add_field(
                name="Erstellt von",
                value=interaction.user.mention,
                inline=True
            )

            embed.add_field(
                name="Task ID",
                value=task_id,
                inline=True
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
            emoji="➕",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_dev_task_create"
        )

    async def callback(self, interaction):
        if not has_role(interaction.user, SHIFT_PERMISSION_ROLE_ID):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            DeveloperTaskModal()
        )


class DeveloperTaskView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(DeveloperTaskButton())


async def update_developer_task_panel():

    channel = get_channel(DEVELOPER_TASK_CHANNEL_ID)

    if channel is None:
        return

    embed = discord.Embed(
        title="👨‍💻 Developer Aufgaben",
        description=(
            "Hier können berechtigte Mitglieder neue "
            "Developer-Aufgaben erstellen."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Panel",
        value=DEV_TASK_PANEL_MARKER,
        inline=False
    )

    found = False

    async for message in channel.history(limit=50):

        if message.author != bot.user:
            continue

        if not message.embeds:
            continue

        for field in message.embeds[0].fields:
            if field.value == DEV_TASK_PANEL_MARKER:
                found = True
                break

        if found:
            try:
                await message.edit(
                    embed=embed,
                    view=DeveloperTaskView()
                )
            except Exception:
                pass

            return

    await channel.send(
        embed=embed,
        view=DeveloperTaskView()
    )


# =========================================================
# DEVELOPER SHIFT
# =========================================================

class DeveloperShiftStartButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Schicht starten",
            emoji="🟢",
            style=discord.ButtonStyle.success,
            custom_id="rlp_dev_shift_start"
        )

    async def callback(self, interaction):

        if not has_role(interaction.user, SHIFT_PERMISSION_ROLE_ID):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung für Developer-Schichten.",
                ephemeral=True
            )
            return

        role = interaction.guild.get_role(DEVELOPER_SHIFT_ROLE_ID)

        if role is None:
            await interaction.response.send_message(
                "❌ Developer-Schicht-Rolle wurde nicht gefunden.",
                ephemeral=True
            )
            return

        if role in interaction.user.roles:
            await interaction.response.send_message(
                "⚠️ Du bist bereits in einer Developer-Schicht.",
                ephemeral=True
            )
            return

        try:
            await interaction.user.add_roles(
                role,
                reason="Developer-Schicht gestartet"
            )

            log_channel = get_channel(SHIFT_LOG_CHANNEL_ID)

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


class DeveloperShiftEndButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Schicht beenden",
            emoji="🔴",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_dev_shift_end"
        )

    async def callback(self, interaction):

        if not has_role(interaction.user, SHIFT_PERMISSION_ROLE_ID):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        role = interaction.guild.get_role(DEVELOPER_SHIFT_ROLE_ID)

        if role is None:
            await interaction.response.send_message(
                "❌ Developer-Schicht-Rolle wurde nicht gefunden.",
                ephemeral=True
            )
            return

        if role not in interaction.user.roles:
            await interaction.response.send_message(
                "⚠️ Du bist aktuell nicht in einer Developer-Schicht.",
                ephemeral=True
            )
            return

        try:
            await interaction.user.remove_roles(
                role,
                reason="Developer-Schicht beendet"
            )

            log_channel = get_channel(SHIFT_LOG_CHANNEL_ID)

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


class DeveloperShiftView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(DeveloperShiftStartButton())
        self.add_item(DeveloperShiftEndButton())


async def update_developer_shift_panel():

    channel = get_channel(DEVELOPER_SHIFT_CHANNEL_ID)

    if channel is None:
        return

    embed = discord.Embed(
        title="👨‍💻 Developer-Schicht",
        description=(
            "Hier kannst du deine Developer-Schicht verwalten.\n\n"
            "🟢 **Schicht starten**\n"
            "🔴 **Schicht beenden**"
        ),
        color=discord.Color.green()
    )

    embed.add_field(
        name="Panel",
        value=SHIFT_PANEL_MARKER,
        inline=False
    )

    found = False

    async for message in channel.history(limit=50):

        if message.author != bot.user:
            continue

        if not message.embeds:
            continue

        for field in message.embeds[0].fields:
            if field.value == SHIFT_PANEL_MARKER:
                found = True
                break

        if found:
            try:
                await message.edit(
                    embed=embed,
                    view=DeveloperShiftView()
                )
            except Exception:
                pass

            return

    await channel.send(
        embed=embed,
        view=DeveloperShiftView()
    )


# =========================================================
# COMMUNITY PANEL
# =========================================================

class CommunitySuggestionModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="💡 Vorschlag")

        self.input = discord.ui.TextInput(
            label="Dein Vorschlag",
            placeholder="Was möchtest du am Server verbessern?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.input)

    async def on_submit(self, interaction):

        channel = get_channel(SUGGESTION_CHANNEL_ID)

        if channel is None:
            await interaction.response.send_message(
                "❌ Der Vorschlagskanal wurde nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="💡 Neuer Community-Vorschlag",
            description=self.input.value,
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )

        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url
        )

        embed.set_footer(
            text=f"User ID: {interaction.user.id}"
        )

        await channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Dein Vorschlag wurde erfolgreich eingereicht!",
            ephemeral=True
        )


class CommunityFeedbackModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="💬 Feedback")

        self.input = discord.ui.TextInput(
            label="Dein Feedback",
            placeholder="Was hältst du vom Server?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.input)

    async def on_submit(self, interaction):

        channel = get_channel(FEEDBACK_CHANNEL_ID)

        if channel is None:
            await interaction.response.send_message(
                "❌ Der Feedback-Kanal wurde nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="💬 Neues Community-Feedback",
            description=self.input.value,
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )

        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url
        )

        embed.set_footer(
            text=f"User ID: {interaction.user.id}"
        )

        await channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Dein Feedback wurde erfolgreich gesendet!",
            ephemeral=True
        )


class CommunityBugModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="🐛 Bug melden")

        self.input = discord.ui.TextInput(
            label="Bug",
            placeholder="Beschreibe den gefundenen Fehler...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.input)

    async def on_submit(self, interaction):

        channel = get_channel(BUG_CHANNEL_ID)

        if channel is None:
            await interaction.response.send_message(
                "❌ Der Bug-Kanal wurde nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🐛 Neue Bug-Meldung",
            description=self.input.value,
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )

        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url
        )

        embed.set_footer(
            text=f"User ID: {interaction.user.id}"
        )

        await channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Deine Bug-Meldung wurde erfolgreich gesendet!",
            ephemeral=True
        )


class CommunitySuggestionButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Vorschlag",
            emoji="💡",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_community_suggestion"
        )

    async def callback(self, interaction):
        await interaction.response.send_modal(
            CommunitySuggestionModal()
        )


class CommunityFeedbackButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Feedback",
            emoji="💬",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_community_feedback"
        )

    async def callback(self, interaction):
        await interaction.response.send_modal(
            CommunityFeedbackModal()
        )


class CommunityBugButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Bug melden",
            emoji="🐛",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_community_bug"
        )

    async def callback(self, interaction):
        await interaction.response.send_modal(
            CommunityBugModal()
        )


class CommunityPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(CommunitySuggestionButton())
        self.add_item(CommunityFeedbackButton())
        self.add_item(CommunityBugButton())


async def update_community_panel():

    # Das Panel wird in den aktuellen Community-Kanal
    # nur über !communitypanel gepostet.
    pass


# =========================================================
# OWNER PANEL
# =========================================================

class AnnouncementModal(discord.ui.Modal):
    def __init__(self, channel):
        super().__init__(title="Ankündigung")

        self.channel = channel

        self.title_input = discord.ui.TextInput(
            label="Titel",
            placeholder="Titel der Ankündigung",
            required=True,
            max_length=256
        )

        self.message_input = discord.ui.TextInput(
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
            text=f"Ankündigung von {interaction.user.display_name}"
        )

        try:

            await self.channel.send(embed=embed)

            await interaction.response.send_message(
                f"✅ Ankündigung wurde in {self.channel.mention} gesendet.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Der Bot kann in diesem Kanal keine Nachrichten "
                "oder Embeds senden.",
                ephemeral=True
            )

        except Exception as e:

            print(f"Announcement Error: {e}")

            await interaction.response.send_message(
                "❌ Beim Senden ist ein Fehler aufgetreten.",
                ephemeral=True
            )


class BotSayModal(discord.ui.Modal):
    def __init__(self, channel):
        super().__init__(title="Bot Say")

        self.channel = channel

        self.message_input = discord.ui.TextInput(
            label="Nachricht",
            placeholder="Was soll der Bot schreiben?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=4000
        )

        self.add_item(self.message_input)

    async def on_submit(self, interaction):

        if not is_owner(interaction.user):
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
                f"✅ Nachricht wurde in {self.channel.mention} gesendet.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Der Bot kann in diesem Kanal nicht schreiben.",
                ephemeral=True
            )

        except Exception as e:

            print(f"Bot Say Error: {e}")

            await interaction.response.send_message(
                "❌ Beim Senden ist ein Fehler aufgetreten.",
                ephemeral=True
            )


class OwnerChannelSelectView(discord.ui.View):
    def __init__(self, action):
        super().__init__(timeout=180)

        self.action = action

        self.select = discord.ui.ChannelSelect(
            placeholder="Wähle einen Textkanal...",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1
        )

        self.select.callback = self.channel_selected

        self.add_item(self.select)

    async def channel_selected(self, interaction):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        try:

            selected = self.select.values[0]

            channel_id = selected.id

            channel = interaction.guild.get_channel(channel_id)

            if not isinstance(channel, discord.TextChannel):
                await interaction.response.send_message(
                    "❌ Der ausgewählte Kanal ist kein Textkanal.",
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
                    reason=f"Channel Lock durch {interaction.user}"
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
                    reason=f"Channel Unlock durch {interaction.user}"
                )

                await interaction.followup.send(
                    f"🔓 {channel.mention} wurde entsperrt.",
                    ephemeral=True
                )

                return

        except discord.Forbidden:

            if interaction.response.is_done():

                await interaction.followup.send(
                    "❌ Der Bot hat für diesen Kanal "
                    "nicht genügend Berechtigungen.",
                    ephemeral=True
                )

            else:

                await interaction.response.send_message(
                    "❌ Der Bot hat für diesen Kanal "
                    "nicht genügend Berechtigungen.",
                    ephemeral=True
                )

        except Exception as e:

            print(
                f"OWNER CHANNEL SELECT ERROR: "
                f"{type(e).__name__}: {e}"
            )

            if interaction.response.is_done():

                await interaction.followup.send(
                    "❌ Beim Ausführen ist ein Fehler aufgetreten.",
                    ephemeral=True
                )

            else:

                await interaction.response.send_message(
                    "❌ Beim Ausführen ist ein Fehler aufgetreten.",
                    ephemeral=True
                )


class OwnerAnnouncementButton(discord.ui.Button):
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
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "📢 **Wähle den Kanal für die Ankündigung:**",
            view=OwnerChannelSelectView("announcement"),
            ephemeral=True
        )


class OwnerSayButton(discord.ui.Button):
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
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "💬 **Wähle den Kanal, in dem der Bot schreiben soll:**",
            view=OwnerChannelSelectView("say"),
            ephemeral=True
        )


class OwnerLockButton(discord.ui.Button):
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
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🔒 **Wähle den Kanal, der gesperrt werden soll:**",
            view=OwnerChannelSelectView("lock"),
            ephemeral=True
        )


class OwnerUnlockButton(discord.ui.Button):
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
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🔓 **Wähle den Kanal, der entsperrt werden soll:**",
            view=OwnerChannelSelectView("unlock"),
            ephemeral=True
        )


class OwnerStatusButton(discord.ui.Button):
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
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        latency = round(bot.latency * 1000)

        total_members = sum(
            guild.member_count or 0
            for guild in bot.guilds
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
            name="🌐 Server",
            value=str(len(bot.guilds)),
            inline=True
        )

        embed.add_field(
            name="👥 Nutzer",
            value=str(total_members),
            inline=True
        )

        embed.add_field(
            name="⏱️ Uptime",
            value=format_uptime(
                time.time() - BOT_START_TIME
            ),
            inline=True
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


class OwnerServerInfoButton(discord.ui.Button):
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
                "❌ Du hast keine Berechtigung.",
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


class OwnerPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(OwnerAnnouncementButton())
        self.add_item(OwnerSayButton())
        self.add_item(OwnerLockButton())
        self.add_item(OwnerUnlockButton())
        self.add_item(OwnerStatusButton())
        self.add_item(OwnerServerInfoButton())


async def send_owner_panel(channel):

    embed = discord.Embed(
        title="👑 Owner Panel",
        description=(
            "Hier kannst du verschiedene "
            "Server- und Bot-Funktionen verwalten.\n\n"

            "📢 **Ankündigung**\n"
            "Kanal auswählen → Titel und Nachricht eingeben.\n\n"

            "💬 **Bot Say**\n"
            "Kanal auswählen → Nachricht eingeben.\n\n"

            "🔒 **Channel Lock**\n"
            "Kanal auswählen → Kanal wird gesperrt.\n\n"

            "🔓 **Channel Unlock**\n"
            "Kanal auswählen → Kanal wird entsperrt.\n\n"

            "📊 **Bot Status**\n"
            "Zeigt den aktuellen Bot-Status.\n\n"

            "🖥️ **Server Info**\n"
            "Zeigt Informationen über den Server."
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
# COMMUNITY INFO COMMANDS
# =========================================================

@bot.command()
async def help(ctx):

    embed = discord.Embed(
        title="📚 Community Commands",
        description="Alle Befehle für normale Mitglieder:",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👥 Community",
        value=(
            "`!suggest <Text>` — Vorschlag\n"
            "`!feedback <Text>` — Feedback\n"
            "`!bug <Text>` — Bug melden\n"
            "`!report <Text>` — Problem melden"
        ),
        inline=False
    )

    embed.add_field(
        name="📊 Informationen",
        value=(
            "`!userinfo [@User]`\n"
            "`!avatar [@User]`\n"
            "`!serverinfo`\n"
            "`!membercount`\n"
            "`!ping`\n"
            "`!uptime`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎮 Fun",
        value=(
            "`!8ball <Frage>`\n"
            "`!coinflip`\n"
            "`!dice`\n"
            "`!choose A | B | C`\n"
            "`!random <Min> <Max>`\n"
            "`!member`"
        ),
        inline=False
    )

    embed.add_field(
        name="ℹ️ Weitere",
        value=(
            "`!rules`\n"
            "`!socials`\n"
            "`!website`\n"
            "`!team`\n"
            "`!apply`"
        ),
        inline=False
    )

    await ctx.send(embed=embed)


@bot.command()
async def ping(ctx):

    await ctx.send(
        f"🏓 Pong! `{round(bot.latency * 1000)}ms`"
    )


@bot.command()
async def uptime(ctx):

    await ctx.send(
        f"⏱️ Der Bot ist seit "
        f"**{format_uptime(time.time() - BOT_START_TIME)}** online."
    )


@bot.command()
async def membercount(ctx):

    await ctx.send(
        f"👥 Aktuell befinden sich "
        f"**{ctx.guild.member_count}** Mitglieder auf dem Server."
    )


@bot.command()
async def serverinfo(ctx):

    guild = ctx.guild

    embed = discord.Embed(
        title="🖥️ Serverinformationen",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Server",
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

    embed.add_field(
        name="Erstellt",
        value=discord.utils.format_dt(
            guild.created_at,
            style="D"
        ),
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

    await ctx.send(embed=embed)


@bot.command()
async def userinfo(ctx, member: discord.Member = None):

    member = member or ctx.author

    embed = discord.Embed(
        title="👤 Benutzerinformationen",
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
            style="D"
        ),
        inline=False
    )

    if member.joined_at:
        embed.add_field(
            name="Server beigetreten",
            value=discord.utils.format_dt(
                member.joined_at,
                style="D"
            ),
            inline=False
        )

    roles = [
        role.mention
        for role in member.roles
        if role != ctx.guild.default_role
    ]

    embed.add_field(
        name="Rollen",
        value=", ".join(roles) if roles else "Keine",
        inline=False
    )

    await ctx.send(embed=embed)


@bot.command()
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


@bot.command()
async def botinfo(ctx):

    embed = discord.Embed(
        title="🤖 Bot Informationen",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Bot",
        value=str(bot.user),
        inline=True
    )

    embed.add_field(
        name="Server",
        value=str(len(bot.guilds)),
        inline=True
    )

    embed.add_field(
        name="Ping",
        value=f"{round(bot.latency * 1000)} ms",
        inline=True
    )

    embed.add_field(
        name="Uptime",
        value=format_uptime(
            time.time() - BOT_START_TIME
        ),
        inline=True
    )

    embed.add_field(
        name="Python",
        value=platform.python_version(),
        inline=True
    )

    embed.add_field(
        name="discord.py",
        value=discord.__version__,
        inline=True
    )

    await ctx.send(embed=embed)


@bot.command()
async def roleinfo(ctx, role: discord.Role):

    embed = discord.Embed(
        title="🎭 Rolleninformationen",
        color=role.color
    )

    embed.add_field(
        name="Rolle",
        value=role.mention,
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

    embed.add_field(
        name="Position",
        value=str(role.position),
        inline=True
    )

    embed.add_field(
        name="Verwaltet",
        value="Ja" if role.managed else "Nein",
        inline=True
    )

    await ctx.send(embed=embed)


@bot.command()
async def channelinfo(ctx, channel: discord.TextChannel = None):

    channel = channel or ctx.channel

    embed = discord.Embed(
        title="📁 Kanalinformationen",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Kanal",
        value=channel.mention,
        inline=True
    )

    embed.add_field(
        name="ID",
        value=str(channel.id),
        inline=True
    )

    embed.add_field(
        name="Kategorie",
        value=channel.category.name
        if channel.category else "Keine",
        inline=True
    )

    embed.add_field(
        name="Erstellt",
        value=discord.utils.format_dt(
            channel.created_at,
            style="D"
        ),
        inline=False
    )

    await ctx.send(embed=embed)


@bot.command()
async def rolelist(ctx):

    roles = [
        role.mention
        for role in reversed(ctx.guild.roles)
        if role != ctx.guild.default_role
    ]

    text = "\n".join(roles)

    if not text:
        text = "Keine Rollen vorhanden."

    if len(text) > 4000:
        text = text[:3950] + "\n..."

    embed = discord.Embed(
        title="🎭 Rollen",
        description=text,
        color=discord.Color.blurple()
    )

    await ctx.send(embed=embed)


@bot.command()
async def channellist(ctx):

    text_channels = len(ctx.guild.text_channels)
    voice_channels = len(ctx.guild.voice_channels)
    categories = len(ctx.guild.categories)

    embed = discord.Embed(
        title="📁 Kanalübersicht",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="💬 Textkanäle",
        value=str(text_channels),
        inline=True
    )

    embed.add_field(
        name="🔊 Sprachkanäle",
        value=str(voice_channels),
        inline=True
    )

    embed.add_field(
        name="📂 Kategorien",
        value=str(categories),
        inline=True
    )

    await ctx.send(embed=embed)


# =========================================================
# COMMUNITY COMMANDS
# =========================================================

async def send_community_submission(
    ctx,
    channel_id,
    title,
    text_content,
    color,
    emoji
):

    channel = get_channel(channel_id)

    if channel is None:
        await ctx.send(
            "❌ Der Zielkanal wurde nicht gefunden.",
            delete_after=5
        )
        return

    embed = discord.Embed(
        title=f"{emoji} {title}",
        description=text_content,
        color=color,
        timestamp=discord.utils.utcnow()
    )

    embed.set_author(
        name=ctx.author.display_name,
        icon_url=ctx.author.display_avatar.url
    )

    embed.set_footer(
        text=f"User ID: {ctx.author.id}"
    )

    await channel.send(embed=embed)

    await ctx.send(
        f"✅ Deine Meldung wurde erfolgreich eingereicht!",
        delete_after=5
    )


@bot.command()
async def suggest(ctx, *, text=None):

    if not text:
        await ctx.send(
            "❌ Nutzung: `!suggest <Dein Vorschlag>`",
            delete_after=6
        )
        return

    await send_community_submission(
        ctx,
        SUGGESTION_CHANNEL_ID,
        "Neuer Vorschlag",
        text,
        discord.Color.gold(),
        "💡"
    )


@bot.command()
async def feedback(ctx, *, text=None):

    if not text:
        await ctx.send(
            "❌ Nutzung: `!feedback <Dein Feedback>`",
            delete_after=6
        )
        return

    await send_community_submission(
        ctx,
        FEEDBACK_CHANNEL_ID,
        "Neues Feedback",
        text,
        discord.Color.blue(),
        "💬"
    )


@bot.command()
async def bug(ctx, *, text=None):

    if not text:
        await ctx.send(
            "❌ Nutzung: `!bug <Beschreibung des Bugs>`",
            delete_after=6
        )
        return

    await send_community_submission(
        ctx,
        BUG_CHANNEL_ID,
        "Neue Bug-Meldung",
        text,
        discord.Color.red(),
        "🐛"
    )


@bot.command()
async def report(ctx, *, text=None):

    if not text:
        await ctx.send(
            "❌ Nutzung: `!report <Beschreibung>`",
            delete_after=6
        )
        return

    await send_community_submission(
        ctx,
        BUG_CHANNEL_ID,
        "Neue Meldung",
        text,
        discord.Color.red(),
        "🚨"
    )


@bot.command()
async def rules(ctx):

    await ctx.send(
        "📜 **Serverregeln**\n\n"
        "> Bitte verhalte dich respektvoll gegenüber allen Mitgliedern.\n"
        "> Kein Spam, keine Beleidigungen und kein unnötiges Drama.\n"
        "> Die vollständigen Regeln findest du im Regelkanal."
    )


@bot.command()
async def socials(ctx):

    await ctx.send(
        "🌐 **Unsere Socials**\n\n"
        "> Die Social-Media-Links können hier ergänzt werden."
    )


@bot.command()
async def website(ctx):

    await ctx.send(
        "🌐 **Website**\n\n"
        "> Unsere Website ist hier erreichbar."
    )


@bot.command()
async def team(ctx):

    embed = discord.Embed(
        title="👥 Team",
        description=(
            "Die Teammitglieder findest du in der "
            "entsprechenden Teamübersicht des Servers."
        ),
        color=discord.Color.blurple()
    )

    await ctx.send(embed=embed)


@bot.command()
async def apply(ctx):

    channel = get_channel(APPLICATION_CHANNEL_ID)

    if channel:

        await ctx.send(
            f"📝 Bewerbungen kannst du hier einreichen: "
            f"{channel.mention}",
            delete_after=10
        )

    else:

        await ctx.send(
            "❌ Der Bewerbungskanal wurde nicht gefunden.",
            delete_after=5
        )


@bot.command()
async def support(ctx):

    channel = get_channel(SUPPORT_VOICE_CHANNEL_ID)

    if channel:

        await ctx.send(
            f"🎧 **Support**\n\n"
            f"Bei Fragen kannst du unserem Support beitreten:\n"
            f"{channel.mention}"
        )

    else:

        await ctx.send(
            "❌ Der Support-Kanal wurde nicht gefunden."
        )


@bot.command()
async def supportinfo(ctx):

    channel = get_channel(SUPPORT_VOICE_CHANNEL_ID)

    await ctx.send(
        f"🎧 **Support-Informationen**\n\n"
        f"Bei Fragen oder Problemen kannst du unserem Support "
        f"beitreten.\n\n"
        f"📍 Kanal: {channel.mention if channel else 'Nicht gefunden'}"
    )


# =========================================================
# FUN
# =========================================================

EIGHT_BALL_ANSWERS = [
    "Ja.",
    "Nein.",
    "Sehr wahrscheinlich.",
    "Eher nicht.",
    "Sieht gut aus.",
    "Frag später nochmal.",
    "Definitiv.",
    "Das ist schwer zu sagen."
]


@bot.command(name="8ball")
async def eightball(ctx, *, question=None):

    if not question:
        await ctx.send(
            "❌ Nutzung: `!8ball <Frage>`",
            delete_after=5
        )
        return

    await ctx.send(
        f"🎱 **8-Ball**\n\n"
        f"❓ {question}\n"
        f"💬 **{random.choice(EIGHT_BALL_ANSWERS)}**"
    )


@bot.command()
async def coinflip(ctx):

    result = random.choice(
        ["Kopf", "Zahl"]
    )

    await ctx.send(
        f"🪙 Die Münze zeigt: **{result}**!"
    )


@bot.command()
async def dice(ctx):

    number = random.randint(1, 6)

    await ctx.send(
        f"🎲 Du hast eine **{number}** gewürfelt!"
    )


@bot.command()
async def choose(ctx, *, choices=None):

    if not choices:
        await ctx.send(
            "❌ Nutzung: `!choose A | B | C`",
            delete_after=5
        )
        return

    options = [
        option.strip()
        for option in choices.split("|")
        if option.strip()
    ]

    if len(options) < 2:
        await ctx.send(
            "❌ Gib mindestens zwei Optionen an.",
            delete_after=5
        )
        return

    result = random.choice(options)

    await ctx.send(
        f"🎯 Meine Auswahl: **{result}**"
    )


@bot.command()
async def random(ctx, minimum: int = None, maximum: int = None):

    if minimum is None or maximum is None:
        await ctx.send(
            "❌ Nutzung: `!random <Min> <Max>`",
            delete_after=5
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


# Alias für den random-Befehl, damit der Python-Name
# random nicht mit dem Modul kollidiert.
random_module = random


@bot.command()
async def serverage(ctx):

    delta = datetime.now(timezone.utc) - ctx.guild.created_at

    days = delta.days

    await ctx.send(
        f"📅 Dieser Server ist **{days} Tage** alt."
    )


@bot.command()
async def member(ctx):

    members = [
        m for m in ctx.guild.members
        if not m.bot
    ]

    if not members:
        await ctx.send(
            "❌ Keine Mitglieder gefunden."
        )
        return

    selected = random.choice(members)

    await ctx.send(
        f"🎲 Zufälliges Community-Mitglied:\n"
        f"👤 {selected.mention}"
    )


# =========================================================
# OWNER COMMANDS
# =========================================================

@bot.command()
async def ownerpanel(ctx):

    if not is_owner(ctx.author):
        await ctx.send(
            "❌ Du hast keine Berechtigung.",
            delete_after=5
        )
        return

    await send_owner_panel(ctx.channel)


@bot.command()
async def owner(ctx):

    if not is_owner(ctx.author):
        await ctx.send(
            "❌ Du hast keine Berechtigung.",
            delete_after=5
        )
        return

    await send_owner_panel(ctx.channel)


@bot.command()
async def communitypanel(ctx):

    embed = discord.Embed(
        title="🌐 Community Panel",
        description=(
            "Hier kannst du direkt mit dem Server interagieren.\n\n"

            "💡 **Vorschlag**\n"
            "Du hast eine Idee für den Server?\n\n"

            "💬 **Feedback**\n"
            "Teile uns deine Meinung mit.\n\n"

            "🐛 **Bug melden**\n"
            "Du hast einen Fehler gefunden?"
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Panel",
        value=COMMUNITY_PANEL_MARKER,
        inline=False
    )

    await ctx.send(
        embed=embed,
        view=CommunityPanelView()
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
# MESSAGE / QUIZ
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
                f"✅ **Richtig!** {message.author.mention}"
            )

            await asyncio.sleep(4)

            await safe_delete(
                success_message
            )

            await send_quiz_question()

            return

        await safe_delete(message)

        wrong_message = await message.channel.send(
            f"❌ **Falsch!** {message.author.mention}"
        )

        await asyncio.sleep(4)

        await safe_delete(
            wrong_message
        )

        return

    await bot.process_commands(message)


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    print("====================================")
    print(f"Bot online: {bot.user}")
    print(f"Guilds: {len(bot.guilds)}")
    print("====================================")

    # Persistent Views
    bot.add_view(NametagView())
    bot.add_view(LicensePlateView())
    bot.add_view(ApplicationView())
    bot.add_view(DeveloperTaskView())
    bot.add_view(DeveloperShiftView())
    bot.add_view(OwnerPanelView())
    bot.add_view(CommunityPanelView())

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
