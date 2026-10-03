import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Modal, TextInput
import asyncio
import json
import os
import random

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
    "quiz_scores": {},
    "developer_shifts": {},
    "developer_tasks": {},
    "developer_task_counter": 0,
    "license_plates": {},
    "nametag_original_names": {},
    "support_case_counter": 0
}

data = {}


def load_data():
    global data

    if not os.path.exists(DATA_FILE):
        data = dict(DEFAULT_DATA)
        save_data()
        return

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            loaded = json.load(file)

        data = dict(DEFAULT_DATA)

        if isinstance(loaded, dict):
            for key in DEFAULT_DATA:
                if key in loaded:
                    data[key] = loaded[key]

    except Exception as error:
        print(f"[DATA] Fehler beim Laden: {error}")
        data = dict(DEFAULT_DATA)
        save_data()


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )
    except Exception as error:
        print(f"[DATA] Fehler beim Speichern: {error}")


load_data()

# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def get_guild():
    return bot.get_guild(GUILD_ID)


def member_has_role(member: discord.Member, role_id: int) -> bool:
    return any(role.id == role_id for role in member.roles)


async def safe_delete(message):
    try:
        await message.delete()
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        pass


async def safe_send(channel, *args, **kwargs):
    try:
        return await channel.send(*args, **kwargs)
    except (discord.Forbidden, discord.HTTPException):
        return None


def clean_nametag(name: str) -> str:
    while name.startswith(NAMETAG):
        name = name[len(NAMETAG):]

    return name


def create_nametag(name: str) -> str:
    clean_name = clean_nametag(name)

    if not clean_name:
        clean_name = "User"

    return (NAMETAG + clean_name)[:32]


# =========================================================
# NAMETAG
# =========================================================

async def update_member_nametag(member: discord.Member):
    """
    WICHTIG:

    Diese Funktion vergibt KEINE Rolle.

    Sie prüft ausschließlich, ob der Benutzer die bereits
    vorhandene Nametag-Rolle besitzt.

    Rolle vorhanden:
        RLP wird vor den Namen gesetzt.

    Rolle nicht vorhanden:
        RLP wird entfernt.
    """

    if member.bot:
        return

    has_nametag_role = member_has_role(
        member,
        NAMETAG_ROLE_ID
    )

    user_id = str(member.id)

    if has_nametag_role:

        current_name = (
            member.nick
            if member.nick is not None
            else member.name
        )

        # Bereits korrekt
        if current_name.startswith(NAMETAG):
            return

        # Original-Nickname merken
        if user_id not in data["nametag_original_names"]:
            data["nametag_original_names"][user_id] = member.nick

        new_name = create_nametag(current_name)

        try:
            await member.edit(
                nick=new_name,
                reason="Nametag-Rolle vorhanden"
            )

            save_data()

        except (discord.Forbidden, discord.HTTPException):
            pass

    else:

        current_nick = member.nick

        if current_nick is None:
            return

        if not current_nick.startswith(NAMETAG):
            return

        original_nick = data["nametag_original_names"].get(
            user_id
        )

        try:
            await member.edit(
                nick=original_nick,
                reason="Nametag-Rolle entfernt"
            )

            data["nametag_original_names"].pop(
                user_id,
                None
            )

            save_data()

        except (discord.Forbidden, discord.HTTPException):
            pass


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

            if not message.embeds:
                continue

            if message.embeds[0].footer.text == marker:
                existing = message
                break

    except (discord.Forbidden, discord.HTTPException):
        return

    embed = discord.Embed(
        title="🏷️ RLP Nametag",
        description=(
            "Das Nametag-System funktioniert automatisch.\n\n"
            f"Besitzt du die Nametag-Rolle, wird `{NAMETAG}` "
            "vor deinen Namen gesetzt.\n\n"
            "Wird die Rolle entfernt, wird der Nametag wieder "
            "zurückgesetzt.\n\n"
            "⚠️ Der Bot vergibt die Nametag-Rolle nicht."
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(text=marker)

    if existing:

        try:
            await existing.edit(
                embed=embed,
                view=NametagView()
            )
        except (discord.Forbidden, discord.HTTPException):
            pass

    else:
        await safe_send(
            channel,
            embed=embed,
            view=NametagView()
        )


class NametagView(View):

    def __init__(self):
        super().__init__(timeout=None)


# =========================================================
# KENNZEICHEN
# =========================================================

license_lock = asyncio.Lock()


def get_plate_number(plate: str):
    parts = plate.strip().upper().split()

    if len(parts) < 2:
        return None

    number = parts[-1]

    if not number.isdigit():
        return None

    return number


def valid_license_plate(plate: str) -> bool:

    parts = plate.strip().upper().split()

    if len(parts) < 2:
        return False

    if not parts[-1].isdigit():
        return False

    for part in parts[:-1]:

        if not part.isalnum():
            return False

    return True


def plate_number_exists(
    number: str,
    except_user_id=None
) -> bool:

    for user_id, plate in data["license_plates"].items():

        if (
            except_user_id is not None
            and str(user_id) == str(except_user_id)
        ):
            continue

        existing_number = get_plate_number(plate)

        if existing_number == number:
            return True

    return False


class LicensePlateModal(
    Modal,
    title="Kennzeichen registrieren"
):

    plate = TextInput(
        label="Kennzeichen",
        placeholder="z.B. RLP 01",
        max_length=20,
        required=True
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        user_id = str(interaction.user.id)

        async with license_lock:

            if user_id in data["license_plates"]:

                await interaction.response.send_message(
                    "❌ Du hast bereits ein Kennzeichen.",
                    ephemeral=True
                )
                return

            plate = self.plate.value.strip().upper()

            if not valid_license_plate(plate):

                await interaction.response.send_message(
                    "❌ Ungültiges Kennzeichen.\n\n"
                    "Beispiel: `RLP 01`",
                    ephemeral=True
                )
                return

            number = get_plate_number(plate)

            if number is None:

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
            f"✅ Dein Kennzeichen **{plate}** wurde registriert.",
            ephemeral=True
        )

        await update_license_plate_panel()


class LicenseDeleteButton(Button):

    def __init__(self):

        super().__init__(
            label="Kennzeichen löschen",
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            custom_id="rlp_license_delete"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        user_id = str(interaction.user.id)

        async with license_lock:

            plate = data["license_plates"].pop(
                user_id,
                None
            )

            if plate is None:

                await interaction.response.send_message(
                    "❌ Du hast kein Kennzeichen.",
                    ephemeral=True
                )
                return

            save_data()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen **{plate}** wurde gelöscht.\n"
            "Die Nummer ist jetzt wieder frei.",
            ephemeral=True
        )

        await update_license_plate_panel()


class LicensePlateView(View):

    def __init__(self):
        super().__init__(timeout=None)

        register_button = Button(
            label="Kennzeichen registrieren",
            style=discord.ButtonStyle.success,
            emoji="🚗",
            custom_id="rlp_license_register"
        )

        async def register_callback(
            interaction: discord.Interaction
        ):
            await interaction.response.send_modal(
                LicensePlateModal()
            )

        register_button.callback = register_callback

        self.add_item(register_button)
        self.add_item(LicenseDeleteButton())


async def update_license_plate_panel():

    channel = bot.get_channel(
        LICENSE_PLATE_CHANNEL_ID
    )

    if channel is None:
        return

    marker = "RLP_LICENSE_PANEL"

    existing = None

    try:

        async for message in channel.history(limit=100):

            if message.author.id != bot.user.id:
                continue

            if not message.embeds:
                continue

            if message.embeds[0].footer.text == marker:

                existing = message
                break

    except (discord.Forbidden, discord.HTTPException):
        return

    embed = discord.Embed(
        title="🚗 Kennzeichen-System",
        description=(
            "Hier kannst du dein Kennzeichen verwalten.\n\n"
            "### Regeln\n"
            "• Pro Benutzer ist **ein Kennzeichen** möglich.\n"
            "• Die **Nummer am Ende** muss einzigartig sein.\n"
            "• Der Präfix darf mehrfach verwendet werden.\n"
            "• Gelöschte Nummern werden wieder freigegeben.\n\n"
            "### Beispiele\n"
            "`RLP 01` → gültig\n"
            "`RLP 02` → gültig\n"
            "`RY ZE 03` → gültig\n\n"
            "Wenn `01` bereits vergeben ist, kann auch ein "
            "anderer Präfix mit `01` nicht verwendet werden."
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
        except (discord.Forbidden, discord.HTTPException):
            pass

    else:

        await safe_send(
            channel,
            embed=embed,
            view=LicensePlateView()
        )


# =========================================================
# EMOJI QUIZ
# =========================================================

QUIZ_QUESTIONS = [
    ("🐶🍖", "hund"),
    ("🌧️☂️", "regen"),
    ("🚗⛽", "auto"),
    ("🍎📱", "iphone"),
    ("⚽🥅", "fußball"),
    ("🌞🏖️", "sommer"),
    ("❄️☃️", "winter"),
    ("🐱🐭", "katze"),
    ("🍕🇮🇹", "pizza"),
    ("✈️🌍", "reise"),
    ("🌙⭐", "nacht"),
    ("🍔🍟", "fastfood"),
    ("🐟🌊", "fisch"),
    ("🎸🎵", "musik"),
    ("🚓👮", "polizei")
]

quiz_lock = asyncio.Lock()

current_quiz = {
    "answer": None,
    "message_id": None
}


async def send_new_quiz():

    channel = bot.get_channel(
        QUIZ_CHANNEL_ID
    )

    if channel is None:
        return

    async with quiz_lock:

        if current_quiz["answer"] is not None:
            return

        emoji, answer = random.choice(
            QUIZ_QUESTIONS
        )

        embed = discord.Embed(
            title="🧩 RLP Emoji-Quiz",
            description=(
                "Errate den Begriff anhand der Emojis.\n\n"
                f"# {emoji}\n\n"
                "Schreibe deine Antwort in den Chat."
            ),
            color=discord.Color.blurple()
        )

        embed.set_footer(
            text="RLP Quiz"
        )

        message = await safe_send(
            channel,
            embed=embed
        )

        if message:

            current_quiz["answer"] = answer
            current_quiz["message_id"] = message.id


class QuizAnswerModal(
    Modal,
    title="Emoji-Quiz"
):

    answer = TextInput(
        label="Deine Antwort",
        placeholder="Antwort eingeben...",
        max_length=100
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        next_quiz = False

        async with quiz_lock:

            correct_answer = current_quiz["answer"]

            if correct_answer is None:

                await interaction.response.send_message(
                    "❌ Aktuell ist kein Quiz aktiv.",
                    ephemeral=True
                )
                return

            answer = self.answer.value.strip().lower()

            if answer != correct_answer:

                await interaction.response.send_message(
                    "❌ Falsch! Versuch es weiter.",
                    ephemeral=True
                )
                return

            user_id = str(interaction.user.id)

            data["quiz_scores"][user_id] = (
                data["quiz_scores"].get(user_id, 0) + 1
            )

            quiz_message_id = current_quiz["message_id"]

            current_quiz["answer"] = None
            current_quiz["message_id"] = None

            save_data()

            await interaction.response.send_message(
                "✅ Richtig! Du hast einen Punkt bekommen.",
                ephemeral=True
            )

            if quiz_message_id:

                channel = bot.get_channel(
                    QUIZ_CHANNEL_ID
                )

                if channel:

                    try:

                        message = await channel.fetch_message(
                            quiz_message_id
                        )

                        await message.delete()

                    except (
                        discord.NotFound,
                        discord.Forbidden,
                        discord.HTTPException
                    ):
                        pass

            next_quiz = True

        if next_quiz:

            await asyncio.sleep(2)
            await send_new_quiz()


@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if message.channel.id == QUIZ_CHANNEL_ID:

        active_id = current_quiz["message_id"]

        if active_id is not None:
            if message.id != active_id:
                await safe_delete(message)

    await bot.process_commands(message)


@tasks.loop(seconds=5)
async def quiz_cleanup():

    channel = bot.get_channel(
        QUIZ_CHANNEL_ID
    )

    if channel is None:
        return

    active_id = current_quiz["message_id"]

    try:

        async for message in channel.history(limit=100):

            if message.id == active_id:
                continue

            await safe_delete(message)

    except (discord.Forbidden, discord.HTTPException):
        pass


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
        custom_id="rlp_shift_start"
    )
    async def start_shift(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        member = interaction.guild.get_member(
            interaction.user.id
        )

        if member is None:
            return

        if not member_has_role(
            member,
            SHIFT_PERMISSION_ROLE_ID
        ):

            await interaction.response.send_message(
                "❌ Du besitzt nicht die benötigte Entwicklerrolle.",
                ephemeral=True
            )
            return

        user_id = str(member.id)

        if user_id in data["developer_shifts"]:

            await interaction.response.send_message(
                "⚠️ Du bist bereits im Dienst.",
                ephemeral=True
            )
            return

        active_role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if active_role is None:

            await interaction.response.send_message(
                "❌ Die aktive Schichtrolle wurde nicht gefunden.",
                ephemeral=True
            )
            return

        try:

            # DIE EINZIGE automatische Rollenvergabe
            await member.add_roles(
                active_role,
                reason="Entwicklerschicht gestartet"
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Der Bot kann die aktive Schichtrolle "
                "nicht vergeben.",
                ephemeral=True
            )
            return

        except discord.HTTPException:

            await interaction.response.send_message(
                "❌ Beim Aktivieren der Schicht ist ein Fehler "
                "aufgetreten.",
                ephemeral=True
            )
            return

        data["developer_shifts"][user_id] = {
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
        custom_id="rlp_shift_end"
    )
    async def end_shift(
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

        active_role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if active_role:

            try:
                await member.remove_roles(
                    active_role,
                    reason="Entwicklerschicht beendet"
                )
            except (
                discord.Forbidden,
                discord.HTTPException
            ):
                pass

        data["developer_shifts"].pop(
            user_id,
            None
        )

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

    color = (
        discord.Color.green()
        if "gestartet" in action
        else discord.Color.red()
    )

    embed = discord.Embed(
        title="👨‍💻 Entwicklerschicht",
        description=(
            f"{action}\n\n"
            f"**Benutzer:** {member.mention}\n"
            f"**ID:** `{member.id}`"
        ),
        color=color
    )

    embed.timestamp = discord.utils.utcnow()

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

            if not message.embeds:
                continue

            if message.embeds[0].footer.text == marker:

                existing = message
                break

    except (discord.Forbidden, discord.HTTPException):
        return

    embed = discord.Embed(
        title="👨‍💻 Entwickler-Schicht",
        description=(
            "Verwalte hier deine Entwicklerschicht.\n\n"
            "▶️ **Schicht starten**\n"
            "Aktiviert die Schichtrolle.\n\n"
            "⏹️ **Schicht beenden**\n"
            "Entfernt die Schichtrolle.\n\n"
            "Die erforderliche Entwicklerrolle wird vom Bot "
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
        except (
            discord.Forbidden,
            discord.HTTPException
        ):
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

@bot.event
async def on_voice_state_update(
    member: discord.Member,
    before: discord.VoiceState,
    after: discord.VoiceState
):

    if member.bot:
        return

    if member.guild.id != GUILD_ID:
        return

    support_channel = bot.get_channel(
        SUPPORT_VOICE_CHANNEL_ID
    )

    if support_channel is None:
        return

    joined = (
        after.channel is not None
        and after.channel.id == SUPPORT_VOICE_CHANNEL_ID
    )

    left = (
        before.channel is not None
        and before.channel.id == SUPPORT_VOICE_CHANNEL_ID
    )

    log_channel = bot.get_channel(
        SUPPORT_LOG_CHANNEL_ID
    )

    if log_channel is None:
        return

    if joined and not left:

        data["support_case_counter"] += 1
        case_number = data["support_case_counter"]

        save_data()

        embed = discord.Embed(
            title="🎧 Support betreten",
            color=discord.Color.green()
        )

        embed.add_field(
            name="Benutzer",
            value=member.mention
        )

        embed.add_field(
            name="Fall",
            value=f"#{case_number}"
        )

        embed.timestamp = discord.utils.utcnow()

        await safe_send(
            log_channel,
            embed=embed
        )

    elif left and not joined:

        embed = discord.Embed(
            title="🎧 Support verlassen",
            color=discord.Color.red()
        )

        embed.add_field(
            name="Benutzer",
            value=member.mention
        )

        embed.timestamp = discord.utils.utcnow()

        await safe_send(
            log_channel,
            embed=embed
        )


# =========================================================
# BEWERBUNGEN
# =========================================================

class ApplicationModal(
    Modal,
    title="Bewerbung"
):

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

    reason = TextInput(
        label="Warum möchtest du dich bewerben?",
        placeholder="Deine Antwort...",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

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
            name="Motivation",
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
            "✅ Deine Bewerbung wurde erfolgreich eingereicht.",
            ephemeral=True
        )


class ApplicationView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Bewerben",
        style=discord.ButtonStyle.primary,
        emoji="📝",
        custom_id="rlp_application"
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

            if not message.embeds:
                continue

            if message.embeds[0].footer.text == marker:

                existing = message
                break

    except (discord.Forbidden, discord.HTTPException):
        return

    embed = discord.Embed(
        title="📝 Bewerbungen",
        description=(
            "Du möchtest dich bei uns bewerben?\n\n"
            "Klicke auf **Bewerben** und fülle das Formular aus."
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
        except (
            discord.Forbidden,
            discord.HTTPException
        ):
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

class DeveloperTaskModal(
    Modal,
    title="Neue Entwickler-Aufgabe"
):

    task = TextInput(
        label="Aufgabe",
        placeholder="Aufgabe beschreiben...",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        if not member_has_role(
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
            "created_by": str(interaction.user.id),
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
        custom_id="rlp_developer_task"
    )
    async def create_task(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if not member_has_role(
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

            if not message.embeds:
                continue

            if message.embeds[0].footer.text == marker:

                existing = message
                break

    except (discord.Forbidden, discord.HTTPException):
        return

    embed = discord.Embed(
        title="🛠️ Entwickler-Aufgaben",
        description=(
            "Hier können berechtigte Entwickler neue "
            "Aufgaben erstellen."
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
        except (
            discord.Forbidden,
            discord.HTTPException
        ):
            pass

    else:

        await safe_send(
            channel,
            embed=embed,
            view=DeveloperTaskView()
        )


# =========================================================
# ALLE PANELS
# =========================================================

async def update_all_panels():

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

    # Nur Nametag prüfen.
    # KEINE Rolle vergeben.
    await update_member_nametag(member)


@bot.event
async def on_member_update(
    before: discord.Member,
    after: discord.Member
):

    if after.guild.id != GUILD_ID:
        return

    before_has_role = member_has_role(
        before,
        NAMETAG_ROLE_ID
    )

    after_has_role = member_has_role(
        after,
        NAMETAG_ROLE_ID
    )

    if before_has_role != after_has_role:

        await update_member_nametag(after)


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    print("========================================")
    print(f"Bot online: {bot.user}")
    print(f"Guild: {GUILD_ID}")
    print("========================================")

    guild = bot.get_guild(GUILD_ID)

    if guild:

        # Vorhandene Nametag-Rollen prüfen.
        #
        # WICHTIG:
        # Hier wird KEINE Rolle vergeben.
        for member in guild.members:

            if member.bot:
                continue

            try:
                await update_member_nametag(member)
            except Exception as error:
                print(
                    f"[NAMETAG] Fehler bei {member}: {error}"
                )

    await update_all_panels()

    if not quiz_cleanup.is_running():
        quiz_cleanup.start()

    if current_quiz["message_id"] is None:
        await send_new_quiz()


# =========================================================
# FEHLERBEHANDLUNG
# =========================================================

@bot.event
async def on_command_error(
    interaction,
    error
):

    if isinstance(
        error,
        commands.CommandNotFound
    ):
        return

    print(f"[COMMAND ERROR] {error}")


# =========================================================
# START
# =========================================================

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN wurde nicht gefunden. "
        "Setze die Umgebungsvariable DISCORD_TOKEN."
    )


bot.run(TOKEN)
