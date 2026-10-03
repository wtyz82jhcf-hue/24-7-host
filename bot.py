import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Modal, TextInput
import asyncio
import json
import os
import random
import re

# =========================================================
# KONFIGURATION
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1519481018221072454

QUIZ_CHANNEL_ID = 1533409789256925185

APPLICATION_CHANNEL_ID = 1541391365219295343
REVIEW_CHANNEL_ID = 1548404201493762181

NAMETAG_CHANNEL_ID = 1555684071911202836
LICENSE_PLATE_CHANNEL_ID = 1527350468832006276

SUPPORT_VOICE_CHANNEL_ID = 1519788919254679602
SUPPORT_LOG_CHANNEL_ID = 1521439818146648064

DEVELOPER_TASK_CHANNEL_ID = 1540442867334385715
DEVELOPER_SHIFT_CHANNEL_ID = 1555923435056795648

NAMETAG_ROLE_ID = 1520102928398942348

SHIFT_PERMISSION_ROLE_ID = 1523674698574200904
DEVELOPER_SHIFT_ROLE_ID = 1527372148979798086

NAMETAG = "RLP "

DATA_FILE = "bot_data.json"

# =========================================================
# BOT
# =========================================================

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# =========================================================
# DATEN
# =========================================================

DEFAULT_DATA = {
    "nametag_opt_out": [],
    "nametag_original_names": {},
    "quiz_scores": {},
    "developer_shifts": {},
    "developer_tasks": {},
    "developer_task_counter": 0,
    "license_plates": {},
    "support_case_counter": 0
}

data = DEFAULT_DATA.copy()


def load_data():
    global data

    if not os.path.exists(DATA_FILE):
        save_data()
        return

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        for key, value in DEFAULT_DATA.items():
            if key not in loaded:
                loaded[key] = value

        data = loaded

    except Exception:
        data = DEFAULT_DATA.copy()
        save_data()


def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


load_data()

# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def get_guild():
    return bot.get_guild(GUILD_ID)


def has_role(member: discord.Member, role_id: int):
    return any(role.id == role_id for role in member.roles)


async def safe_send(channel, *args, **kwargs):
    try:
        return await channel.send(*args, **kwargs)
    except (discord.Forbidden, discord.HTTPException):
        return None


def clean_nametag(name: str):
    while name.startswith(NAMETAG):
        name = name[len(NAMETAG):]

    return name


def make_nametag(name: str):
    name = clean_nametag(name)

    if not name:
        name = "User"

    return NAMETAG + name


async def update_member_nametag(member: discord.Member):
    """
    WICHTIG:
    Diese Funktion VERGIBT NIEMALS die Nametag-Rolle.

    Sie prüft nur:
    - Rolle vorhanden -> RLP wird gesetzt
    - Rolle nicht vorhanden -> RLP wird entfernt
    """

    if member.bot:
        return

    has_nametag_role = has_role(member, NAMETAG_ROLE_ID)

    user_id = str(member.id)

    if has_nametag_role:

        current_name = member.nick if member.nick is not None else member.name

        # Bereits korrekt
        if current_name.startswith(NAMETAG):
            return

        # Originalen Namen speichern
        if user_id not in data["nametag_original_names"]:
            data["nametag_original_names"][user_id] = member.nick

        new_name = make_nametag(current_name)

        # Discord-Nickname max. 32 Zeichen
        new_name = new_name[:32]

        try:
            await member.edit(
                nick=new_name,
                reason="Nametag-Rolle erkannt"
            )
            save_data()

        except (discord.Forbidden, discord.HTTPException):
            pass

    else:

        current_name = member.nick

        if current_name is None:
            return

        if not current_name.startswith(NAMETAG):
            return

        original = data["nametag_original_names"].get(user_id)

        try:
            await member.edit(
                nick=original,
                reason="Nametag-Rolle entfernt"
            )

            if user_id in data["nametag_original_names"]:
                del data["nametag_original_names"][user_id]

            save_data()

        except (discord.Forbidden, discord.HTTPException):
            pass


# =========================================================
# QUIZ
# =========================================================

QUIZ_QUESTIONS = [
    {
        "emoji": "🐶🍖",
        "answer": "hund"
    },
    {
        "emoji": "🌧️☂️",
        "answer": "regen"
    },
    {
        "emoji": "🚗⛽",
        "answer": "auto"
    },
    {
        "emoji": "🍎📱",
        "answer": "iphone"
    },
    {
        "emoji": "⚽🥅",
        "answer": "fußball"
    },
    {
        "emoji": "🌞🏖️",
        "answer": "sommer"
    },
    {
        "emoji": "❄️☃️",
        "answer": "winter"
    },
    {
        "emoji": "🐱🐭",
        "answer": "katze"
    },
    {
        "emoji": "🍕🇮🇹",
        "answer": "pizza"
    },
    {
        "emoji": "✈️🌍",
        "answer": "reise"
    }
]

current_quiz = {
    "answer": None,
    "message_id": None
}

quiz_lock = asyncio.Lock()


async def send_new_quiz():
    channel = bot.get_channel(QUIZ_CHANNEL_ID)

    if channel is None:
        return

    question = random.choice(QUIZ_QUESTIONS)

    embed = discord.Embed(
        title="🧩 Emoji-Quiz",
        description=(
            f"Errate den Begriff:\n\n"
            f"# {question['emoji']}\n\n"
            f"Schreibe deine Antwort in den Chat."
        ),
        color=discord.Color.blurple()
    )

    message = await safe_send(channel, embed=embed)

    if message:
        current_quiz["answer"] = question["answer"].lower()
        current_quiz["message_id"] = message.id


class QuizAnswerModal(Modal, title="Emoji-Quiz Antwort"):

    answer = TextInput(
        label="Deine Antwort",
        placeholder="Antwort eingeben...",
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):

        async with quiz_lock:

            if current_quiz["answer"] is None:
                await interaction.response.send_message(
                    "❌ Aktuell ist kein Quiz aktiv.",
                    ephemeral=True
                )
                return

            answer = self.answer.value.strip().lower()

            if answer != current_quiz["answer"]:
                await interaction.response.send_message(
                    "❌ Falsch! Versuch es weiter.",
                    ephemeral=True
                )
                return

            user_id = str(interaction.user.id)

            data["quiz_scores"][user_id] = (
                data["quiz_scores"].get(user_id, 0) + 1
            )

            save_data()

            current_quiz["answer"] = None

            quiz_message_id = current_quiz["message_id"]
            current_quiz["message_id"] = None

            await interaction.response.send_message(
                "✅ Richtig! Du hast einen Punkt bekommen.",
                ephemeral=True
            )

            channel = bot.get_channel(QUIZ_CHANNEL_ID)

            if channel and quiz_message_id:

                try:
                    message = await channel.fetch_message(
                        quiz_message_id
                    )
                    await message.delete()

                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    pass

        await asyncio.sleep(2)
        await send_new_quiz()


class QuizButtonView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Antwort eingeben",
        style=discord.ButtonStyle.primary,
        emoji="🧩",
        custom_id="quiz_answer_button"
    )
    async def answer_button(
        self,
        interaction: discord.Interaction,
        button: Button
    ):
        await interaction.response.send_modal(
            QuizAnswerModal()
        )


@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if message.channel.id == QUIZ_CHANNEL_ID:

        if (
            current_quiz["message_id"] is not None
            and message.id != current_quiz["message_id"]
        ):
            try:
                await message.delete()
            except:
                pass

    await bot.process_commands(message)


@tasks.loop(seconds=5)
async def quiz_cleanup():

    channel = bot.get_channel(QUIZ_CHANNEL_ID)

    if channel is None:
        return

    try:

        async for message in channel.history(limit=100):

            if message.id == current_quiz["message_id"]:
                continue

            try:
                await message.delete()
            except:
                pass

    except:
        pass


# =========================================================
# KENNZEICHEN
# =========================================================

def get_plate_number(plate: str):
    parts = plate.strip().split()

    if len(parts) < 2:
        return None

    number = parts[-1]

    if not number.isdigit():
        return None

    return number


def plate_number_exists(number: str, except_user_id=None):

    for user_id, plate in data["license_plates"].items():

        if except_user_id is not None and str(user_id) == str(except_user_id):
            continue

        existing_number = get_plate_number(plate)

        if existing_number == number:
            return True

    return False


class LicensePlateModal(Modal, title="Kennzeichen registrieren"):

    plate = TextInput(
        label="Kennzeichen",
        placeholder="z.B. RLP 01",
        max_length=20
    )

    async def on_submit(self, interaction: discord.Interaction):

        user_id = str(interaction.user.id)

        if user_id in data["license_plates"]:
            await interaction.response.send_message(
                "❌ Du hast bereits ein Kennzeichen registriert.",
                ephemeral=True
            )
            return

        plate = self.plate.value.strip().upper()

        number = get_plate_number(plate)

        if number is None:
            await interaction.response.send_message(
                "❌ Ungültiges Kennzeichen.\n"
                "Nutze z.B. `RLP 01`.",
                ephemeral=True
            )
            return

        parts = plate.split()

        if len(parts) < 2:
            await interaction.response.send_message(
                "❌ Das Kennzeichen muss aus Präfix und Nummer bestehen.",
                ephemeral=True
            )
            return

        if not parts[-1].isdigit():
            await interaction.response.send_message(
                "❌ Die letzte Stelle muss eine Zahl sein.",
                ephemeral=True
            )
            return

        if plate_number_exists(number):
            await interaction.response.send_message(
                f"❌ Die Nummer `{number}` ist bereits vergeben.",
                ephemeral=True
            )
            return

        data["license_plates"][user_id] = plate

        save_data()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen wurde registriert: **{plate}**",
            ephemeral=True
        )

        await update_license_plate_panel()


class LicensePlateDeleteButton(Button):

    def __init__(self):
        super().__init__(
            label="Kennzeichen löschen",
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            custom_id="license_delete"
        )

    async def callback(self, interaction: discord.Interaction):

        user_id = str(interaction.user.id)

        if user_id not in data["license_plates"]:
            await interaction.response.send_message(
                "❌ Du hast kein Kennzeichen.",
                ephemeral=True
            )
            return

        plate = data["license_plates"].pop(user_id)

        save_data()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen **{plate}** wurde gelöscht.",
            ephemeral=True
        )

        await update_license_plate_panel()


class LicensePlateView(View):

    def __init__(self):
        super().__init__(timeout=None)

        register = Button(
            label="Kennzeichen registrieren",
            style=discord.ButtonStyle.success,
            emoji="🚗",
            custom_id="license_register"
        )

        async def register_callback(
            interaction: discord.Interaction
        ):
            await interaction.response.send_modal(
                LicensePlateModal()
            )

        register.callback = register_callback

        self.add_item(register)
        self.add_item(LicensePlateDeleteButton())


async def update_license_plate_panel():

    channel = bot.get_channel(LICENSE_PLATE_CHANNEL_ID)

    if channel is None:
        return

    marker = "RLP_LICENSE_PANEL"

    existing = None

    try:
        async for message in channel.history(limit=100):

            if message.author.id != bot.user.id:
                continue

            if message.embeds:

                if message.embeds[0].footer.text == marker:
                    existing = message
                    break

    except:
        return

    embed = discord.Embed(
        title="🚗 Kennzeichen-System",
        description=(
            "Hier kannst du dein persönliches Kennzeichen registrieren.\n\n"
            "• Jeder Nutzer kann **ein Kennzeichen** besitzen.\n"
            "• Die **Nummer am Ende** muss weltweit innerhalb des Systems frei sein.\n"
            "• Der Präfix darf mehrfach verwendet werden.\n"
            "• Beim Löschen wird die Nummer wieder freigegeben.\n\n"
            "**Beispiel:**\n"
            "`RLP 01`\n"
            "`RY ZE 02`"
        ),
        color=discord.Color.blue()
    )

    embed.set_footer(text=marker)

    if existing:

        try:
            await existing.edit(
                embed=embed,
                view=LicensePlateView()
            )
        except:
            pass

    else:

        await safe_send(
            channel,
            embed=embed,
            view=LicensePlateView()
        )


# =========================================================
# NAMETAG
# =========================================================

class NametagInfoView(View):

    def __init__(self):
        super().__init__(timeout=None)


async def update_nametag_panel():

    channel = bot.get_channel(NAMETAG_CHANNEL_ID)

    if channel is None:
        return

    marker = "RLP_NAMETAG_PANEL"

    existing = None

    try:
        async for message in channel.history(limit=100):

            if message.author.id != bot.user.id:
                continue

            if message.embeds:

                if message.embeds[0].footer.text == marker:
                    existing = message
                    break

    except:
        return

    embed = discord.Embed(
        title="🏷️ Nametag-System",
        description=(
            "Die Nametag-Rolle steuert automatisch deinen Namen.\n\n"
            "Besitzt du die entsprechende Nametag-Rolle, wird "
            f"`{NAMETAG}` automatisch vor deinen Namen gesetzt.\n\n"
            "Wird die Rolle entfernt, wird der Nametag wieder entfernt.\n\n"
            "⚠️ Der Bot vergibt die Nametag-Rolle **nicht automatisch**."
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(text=marker)

    if existing:

        try:
            await existing.edit(
                embed=embed,
                view=NametagInfoView()
            )
        except:
            pass

    else:

        await safe_send(
            channel,
            embed=embed,
            view=NametagInfoView()
        )


# =========================================================
# ENTWICKLER-SCHICHT
# =========================================================

class ShiftView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Schicht starten",
        style=discord.ButtonStyle.success,
        emoji="▶️",
        custom_id="shift_start"
    )
    async def start(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        member = interaction.guild.get_member(
            interaction.user.id
        )

        if member is None:
            return

        if not has_role(
            member,
            SHIFT_PERMISSION_ROLE_ID
        ):
            await interaction.response.send_message(
                "❌ Du besitzt nicht die benötigte Entwicklerrolle.",
                ephemeral=True
            )
            return

        if str(member.id) in data["developer_shifts"]:
            await interaction.response.send_message(
                "⚠️ Du bist bereits im Dienst.",
                ephemeral=True
            )
            return

        role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if role is None:
            await interaction.response.send_message(
                "❌ Die aktive Schichtrolle wurde nicht gefunden.",
                ephemeral=True
            )
            return

        try:
            await member.add_roles(
                role,
                reason="Entwicklerschicht gestartet"
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Der Bot kann die Schichtrolle nicht vergeben.",
                ephemeral=True
            )
            return

        data["developer_shifts"][str(member.id)] = {
            "started": discord.utils.utcnow().isoformat()
        }

        save_data()

        await interaction.response.send_message(
            "✅ Deine Entwicklerschicht wurde gestartet.",
            ephemeral=True
        )

        await log_shift(
            member,
            "🟢 Schicht gestartet"
        )

    @discord.ui.button(
        label="Schicht beenden",
        style=discord.ButtonStyle.danger,
        emoji="⏹️",
        custom_id="shift_end"
    )
    async def end(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        member = interaction.guild.get_member(
            interaction.user.id
        )

        if member is None:
            return

        user_id = str(member.id)

        if user_id not in data["developer_shifts"]:
            await interaction.response.send_message(
                "⚠️ Du bist aktuell nicht im Dienst.",
                ephemeral=True
            )
            return

        role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if role:

            try:
                await member.remove_roles(
                    role,
                    reason="Entwicklerschicht beendet"
                )
            except:
                pass

        data["developer_shifts"].pop(user_id, None)

        save_data()

        await interaction.response.send_message(
            "✅ Deine Entwicklerschicht wurde beendet.",
            ephemeral=True
        )

        await log_shift(
            member,
            "🔴 Schicht beendet"
        )


async def log_shift(
    member: discord.Member,
    action: str
):

    channel = bot.get_channel(
        DEVELOPER_SHIFT_CHANNEL_ID
    )

    if channel is None:
        return

    embed = discord.Embed(
        title="👨‍💻 Entwicklerschicht",
        description=(
            f"{action}\n\n"
            f"**Benutzer:** {member.mention}\n"
            f"**ID:** `{member.id}`"
        ),
        color=discord.Color.green()
        if "gestartet" in action
        else discord.Color.red()
    )

    await safe_send(
        channel,
        embed=embed
    )


async def update_shift_panel():

    channel = bot.get_channel(
        DEVELOPER_SHIFT_CHANNEL_ID
    )

    if channel is None:
        return

    marker = "RLP_SHIFT_PANEL"

    existing = None

    try:

        async for message in channel.history(limit=100):

            if message.author.id != bot.user.id:
                continue

            if message.embeds:

                if message.embeds[0].footer.text == marker:
                    existing = message
                    break

    except:
        return

    embed = discord.Embed(
        title="👨‍💻 Entwickler-Schicht",
        description=(
            "Nutze die Buttons, um deine Entwicklerschicht "
            "zu verwalten.\n\n"
            "▶️ **Schicht starten**\n"
            "Vergibt die aktive Schichtrolle.\n\n"
            "⏹️ **Schicht beenden**\n"
            "Entfernt die aktive Schichtrolle.\n\n"
            "Die benötigte Entwicklerrolle wird vom Bot "
            "nicht vergeben."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(text=marker)

    if existing:

        try:
            await existing.edit(
                embed=embed,
                view=ShiftView()
            )
        except:
            pass

    else:

        await safe_send(
            channel,
            embed=embed,
            view=ShiftView()
        )


# =========================================================
# SUPPORT
# =========================================================

async def log_support(message):

    channel = bot.get_channel(
        SUPPORT_LOG_CHANNEL_ID
    )

    if channel is None:
        return

    await safe_send(
        channel,
        f"🎧 Support-Aktivität: {message}"
    )


# =========================================================
# BEWERBUNGEN
# =========================================================

class ApplicationModal(Modal, title="Bewerbung"):

    name = TextInput(
        label="Name",
        max_length=100
    )

    age = TextInput(
        label="Alter",
        max_length=3
    )

    reason = TextInput(
        label="Warum möchtest du dich bewerben?",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):

        channel = bot.get_channel(
            APPLICATION_CHANNEL_ID
        )

        if channel is None:
            await interaction.response.send_message(
                "❌ Bewerbungskanal nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📝 Neue Bewerbung",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Bewerber",
            value=interaction.user.mention,
            inline=False
        )

        embed.add_field(
            name="Name",
            value=self.name.value,
            inline=False
        )

        embed.add_field(
            name="Alter",
            value=self.age.value,
            inline=False
        )

        embed.add_field(
            name="Warum?",
            value=self.reason.value,
            inline=False
        )

        embed.set_footer(
            text=f"User ID: {interaction.user.id}"
        )

        await safe_send(
            channel,
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Deine Bewerbung wurde eingereicht.",
            ephemeral=True
        )


class ApplicationView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Bewerben",
        style=discord.ButtonStyle.primary,
        emoji="📝",
        custom_id="application_button"
    )
    async def apply(
        self,
        interaction: discord.Interaction,
        button: Button
    ):
        await interaction.response.send_modal(
            ApplicationModal()
        )


async def update_application_panel():

    channel = bot.get_channel(
        APPLICATION_CHANNEL_ID
    )

    if channel is None:
        return

    marker = "RLP_APPLICATION_PANEL"

    existing = None

    try:

        async for message in channel.history(limit=100):

            if message.author.id != bot.user.id:
                continue

            if message.embeds:

                if message.embeds[0].footer.text == marker:
                    existing = message
                    break

    except:
        return

    embed = discord.Embed(
        title="📝 Bewerbungen",
        description=(
            "Du möchtest dich bewerben?\n\n"
            "Klicke auf den Button und fülle das Formular aus."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(text=marker)

    if existing:

        try:
            await existing.edit(
                embed=embed,
                view=ApplicationView()
            )
        except:
            pass

    else:

        await safe_send(
            channel,
            embed=embed,
            view=ApplicationView()
        )


# =========================================================
# ENTWICKLER-AUFGABEN
# =========================================================

class DeveloperTaskModal(Modal, title="Neue Entwickler-Aufgabe"):

    task = TextInput(
        label="Aufgabe",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):

        user_id = str(interaction.user.id)

        if not has_role(
            interaction.user,
            SHIFT_PERMISSION_ROLE_ID
        ):
            await interaction.response.send_message(
                "❌ Du besitzt nicht die benötigte Entwicklerrolle.",
                ephemeral=True
            )
            return

        data["developer_task_counter"] += 1

        task_id = data["developer_task_counter"]

        data["developer_tasks"][str(task_id)] = {
            "task": self.task.value,
            "created_by": user_id,
            "completed": False
        }

        save_data()

        channel = bot.get_channel(
            DEVELOPER_TASK_CHANNEL_ID
        )

        if channel:

            embed = discord.Embed(
                title=f"🛠️ Entwickler-Aufgabe #{task_id}",
                description=self.task.value,
                color=discord.Color.orange()
            )

            embed.add_field(
                name="Erstellt von",
                value=interaction.user.mention
            )

            await safe_send(
                channel,
                embed=embed
            )

        await interaction.response.send_message(
            f"✅ Aufgabe #{task_id} wurde erstellt.",
            ephemeral=True
        )


class DeveloperTaskView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Aufgabe erstellen",
        style=discord.ButtonStyle.primary,
        emoji="🛠️",
        custom_id="developer_task_create"
    )
    async def create_task(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if not has_role(
            interaction.user,
            SHIFT_PERMISSION_ROLE_ID
        ):
            await interaction.response.send_message(
                "❌ Du besitzt nicht die benötigte Entwicklerrolle.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            DeveloperTaskModal()
        )


async def update_developer_task_panel():

    channel = bot.get_channel(
        DEVELOPER_TASK_CHANNEL_ID
    )

    if channel is None:
        return

    marker = "RLP_DEVELOPER_TASK_PANEL"

    existing = None

    try:

        async for message in channel.history(limit=100):

            if message.author.id != bot.user.id:
                continue

            if message.embeds:

                if message.embeds[0].footer.text == marker:
                    existing = message
                    break

    except:
        return

    embed = discord.Embed(
        title="🛠️ Entwickler-Aufgaben",
        description=(
            "Hier können Entwickler neue Aufgaben erstellen."
        ),
        color=discord.Color.orange()
    )

    embed.set_footer(text=marker)

    if existing:

        try:
            await existing.edit(
                embed=embed,
                view=DeveloperTaskView()
            )
        except:
            pass

    else:

        await safe_send(
            channel,
            embed=embed,
            view=DeveloperTaskView()
        )


# =========================================================
# PANELS
# =========================================================

async def send_all_panels():

    await update_nametag_panel()
    await update_license_plate_panel()
    await update_application_panel()
    await update_shift_panel()
    await update_developer_task_panel()


# =========================================================
# MEMBER EVENTS
# =========================================================

@bot.event
async def on_member_join(member):

    if member.guild.id != GUILD_ID:
        return

    # NUR Nametag prüfen.
    # KEINE Rolle vergeben.
    await update_member_nametag(member)


@bot.event
async def on_member_update(
    before: discord.Member,
    after: discord.Member
):

    if before.guild.id != GUILD_ID:
        return

    before_has = has_role(
        before,
        NAMETAG_ROLE_ID
    )

    after_has = has_role(
        after,
        NAMETAG_ROLE_ID
    )

    if before_has != after_has:
        await update_member_nametag(after)


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    print("----------------------------------------")
    print(f"Bot online: {bot.user}")
    print(f"Guild: {GUILD_ID}")
    print("----------------------------------------")

    guild = bot.get_guild(GUILD_ID)

    if guild:

        # Bestehende Nametag-Rollen prüfen.
        # Dabei wird KEINE Rolle vergeben.
        for member in guild.members:

            if member.bot:
                continue

            await update_member_nametag(member)

    await send_all_panels()

    if not quiz_cleanup.is_running():
        quiz_cleanup.start()

    if current_quiz["message_id"] is None:
        await send_new_quiz()


# =========================================================
# START
# =========================================================

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN wurde nicht gefunden."
    )

bot.run(TOKEN)
