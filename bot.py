import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Modal, TextInput, ChannelSelect
import asyncio
import json
import os
import random
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
SUPPORT_LOG_CHANNEL_ID = 1521439818146648064
DEVELOPER_TASK_CHANNEL_ID = 1540442867334385715
DEVELOPER_SHIFT_CHANNEL_ID = 1555923435056795648
SHIFT_LOG_CHANNEL_ID = 1540797414863151155

NAMETAG_ROLE_ID = 1520102928398942348
SHIFT_PERMISSION_ROLE_ID = 1523674698574200904
DEVELOPER_SHIFT_ROLE_ID = 1527372148979798086
OWNER_ROLE_ID = 1544691379613999164

NAMETAG = "RLP "
DATA_FILE = "bot_data.json"

NAMETAG_PANEL_MARKER = "RLP_NAMETAG_PANEL"
LICENSE_PANEL_MARKER = "RLP_LICENSE_PANEL"
SHIFT_PANEL_MARKER = "RLP_SHIFT_PANEL"
APPLICATION_PANEL_MARKER = "RLP_APPLICATION_PANEL"
DEV_TASK_PANEL_MARKER = "RLP_DEV_TASK_PANEL"
OWNER_PANEL_MARKER = "RLP_OWNER_PANEL"

# =========================================================
# INTENTS
# =========================================================

intents = discord.Intents.all()

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
            "support_cases": 0,
            "nametag_original_names": {},
            "developer_tasks": {}
        }

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        data.setdefault("license_plates", {})
        data.setdefault("support_cases", 0)
        data.setdefault("nametag_original_names", {})
        data.setdefault("developer_tasks", {})

        return data

    except Exception:
        return {
            "license_plates": {},
            "support_cases": 0,
            "nametag_original_names": {},
            "developer_tasks": {}
        }


data = load_data()


def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# =========================================================
# QUIZ
# =========================================================

QUIZ_QUESTIONS = [
    ("🇩🇪🇩🇪🇩🇪", "Deutschland"),
    ("🇫🇷🥐🗼", "Frankreich"),
    ("🇮🇹🍕🍝", "Italien"),
    ("🇪🇸💃🌞", "Spanien"),
    ("🇬🇧🎡☕", "England"),
    ("🇺🇸🗽🍔", "USA"),
    ("🇯🇵🍣🗾", "Japan"),
    ("🇨🇳🐼🏯", "China"),
    ("🇧🇷⚽🌴", "Brasilien"),
    ("🇦🇺🦘🌊", "Australien"),
    ("🇨🇦🍁🏒", "Kanada"),
    ("🇳🇱🌷🚲", "Niederlande"),
    ("🇨🇭🏔️🧀", "Schweiz"),
    ("🇦🇹🏔️🎿", "Österreich"),
    ("🇬🇷🏛️🌊", "Griechenland"),
    ("🇹🇷🕌🌙", "Türkei"),
    ("🇵🇹⚽🌊", "Portugal"),
    ("🇲🇽🌮🌵", "Mexiko"),
    ("🇰🇷🎮🍜", "Südkorea"),
    ("🇳🇴❄️🏔️", "Norwegen"),
    ("🇸🇪🧊🏠", "Schweden"),
    ("🇩🇰🧱🚲", "Dänemark"),
    ("🇫🇮❄️🦌", "Finnland"),
    ("🇮🇪☘️🍀", "Irland"),
    ("🇮🇸🌋❄️", "Island"),
    ("🐶", "Hund"),
    ("🐱", "Katze"),
    ("🦁👑", "Löwe"),
    ("🐘🌍", "Elefant"),
    ("🐼🎋", "Panda"),
    ("🦒🌳", "Giraffe"),
    ("🐧❄️", "Pinguin"),
    ("🦈🌊", "Hai"),
    ("🐬🌊", "Delfin"),
    ("🦅☁️", "Adler"),
    ("🍎🍏", "Apfel"),
    ("🍌🐒", "Banane"),
    ("🍉☀️", "Wassermelone"),
    ("🍕🧀", "Pizza"),
    ("🍔🍟", "Burger"),
    ("🍫😋", "Schokolade"),
    ("⚽🥅", "Fußball"),
    ("🏀⛹️", "Basketball"),
    ("🎾", "Tennis"),
    ("🏎️🏁", "Formel 1"),
    ("🎮🕹️", "Gaming"),
    ("🚗🛣️", "Auto"),
    ("✈️☁️", "Flugzeug"),
    ("🚢🌊", "Schiff"),
    ("🌞🔥", "Sonne"),
    ("🌙⭐", "Mond"),
    ("🌍🌎🌏", "Erde"),
    ("🔥💧", "Feuer"),
]

quiz_state = {
    "message_id": None,
    "answer": None,
    "round": 0
}

quiz_lock = asyncio.Lock()


async def send_quiz_question():
    channel = bot.get_channel(QUIZ_CHANNEL_ID)

    if channel is None:
        return

    emoji, answer = random.choice(QUIZ_QUESTIONS)

    embed = discord.Embed(
        title="🎯 Emoji-Länder & Fun Quiz",
        description=(
            f"## {emoji}\n\n"
            "💬 **Was ist gesucht?**\n"
            "Schreibe deine Antwort in den Chat!"
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="⚡ Wer zuerst richtig antwortet, gewinnt!"
    )

    message = await channel.send(embed=embed)

    quiz_state["message_id"] = message.id
    quiz_state["answer"] = answer.lower()
    quiz_state["round"] += 1


async def ensure_quiz():
    channel = bot.get_channel(QUIZ_CHANNEL_ID)

    if channel is None:
        return

    if quiz_state["message_id"] is not None:
        try:
            await channel.fetch_message(quiz_state["message_id"])
            return
        except discord.NotFound:
            quiz_state["message_id"] = None

    await send_quiz_question()


@tasks.loop(seconds=5)
async def quiz_cleanup():
    channel = bot.get_channel(QUIZ_CHANNEL_ID)

    if channel is None:
        return

    try:
        async for message in channel.history(limit=100):
            if message.author.bot:
                if message.id == quiz_state["message_id"]:
                    continue
                continue

            try:
                await message.delete()
            except Exception:
                pass

    except Exception as e:
        print("Quiz Cleanup Fehler:", e)


# =========================================================
# PANEL HELPERS
# =========================================================

async def find_panel_message(channel, marker):
    found = None

    try:
        async for message in channel.history(limit=100):
            if not message.author.bot:
                continue

            if not message.embeds:
                continue

            embed = message.embeds[0]

            if embed.description and marker in embed.description:
                if found is None:
                    found = message
                else:
                    try:
                        await message.delete()
                    except Exception:
                        pass

    except Exception as e:
        print("Panel-Suche Fehler:", e)

    return found


# =========================================================
# NAMETAG
# =========================================================

def remove_rlp_prefix(text):
    if text.startswith(NAMETAG):
        return text[len(NAMETAG):]
    return text


async def apply_nametag_from_role(member):
    """
    Wird NICHT beim Bot-Start verwendet.

    Diese Funktion wird nur ausgeführt, wenn der Nametag
    anderweitig aktiv verarbeitet wird.
    """

    role = member.guild.get_role(NAMETAG_ROLE_ID)

    if role is None:
        return

    if role not in member.roles:
        return

    current = member.nick if member.nick is not None else member.name

    if current.startswith(NAMETAG):
        return

    data["nametag_original_names"][str(member.id)] = member.nick
    save_data()

    try:
        await member.edit(nick=NAMETAG + current)
    except Exception as e:
        print("Nametag setzen Fehler:", e)


async def remove_nametag(member):
    role = member.guild.get_role(NAMETAG_ROLE_ID)

    if role is None:
        return

    if role in member.roles:
        return

    current = member.nick if member.nick is not None else member.name

    if not current.startswith(NAMETAG):
        return

    original = data["nametag_original_names"].get(str(member.id))

    try:
        if original is not None:
            await member.edit(nick=original)
        else:
            cleaned = remove_rlp_prefix(current)

            if cleaned == member.name:
                await member.edit(nick=None)
            else:
                await member.edit(nick=cleaned)

    except Exception as e:
        print("Nametag entfernen Fehler:", e)

    data["nametag_original_names"].pop(str(member.id), None)
    save_data()


class NametagResetButton(Button):
    def __init__(self):
        super().__init__(
            label="Nametag zurücksetzen",
            style=discord.ButtonStyle.danger,
            emoji="🔄"
        )

    async def callback(self, interaction: discord.Interaction):
        member = interaction.guild.get_member(interaction.user.id)

        if member is None:
            await interaction.response.send_message(
                "❌ Benutzer nicht gefunden.",
                ephemeral=True
            )
            return

        current = member.nick if member.nick is not None else member.name

        if not current.startswith(NAMETAG):
            await interaction.response.send_message(
                "ℹ️ Dein Name enthält kein `RLP `.",
                ephemeral=True
            )
            return

        cleaned = remove_rlp_prefix(current)

        try:
            if cleaned == member.name:
                await member.edit(nick=None)
            else:
                await member.edit(nick=cleaned)

            data["nametag_original_names"].pop(str(member.id), None)
            save_data()

            await interaction.response.send_message(
                "✅ Dein Nametag wurde zurückgesetzt.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich habe keine Berechtigung, deinen Nicknamen zu ändern.",
                ephemeral=True
            )


class NametagView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(NametagResetButton())


async def update_nametag_panel():
    channel = bot.get_channel(NAMETAG_CHANNEL_ID)

    if channel is None:
        return

    embed = discord.Embed(
        title="🏷️ Nametag System",
        description=(
            f"{NAMETAG_PANEL_MARKER}\n\n"
            "Das Nametag-System wird über die entsprechende Rolle gesteuert.\n\n"
            "🔄 **Nametag zurücksetzen**\n"
            "Mit dem Button kannst du `RLP ` aus deinem eigenen Namen entfernen.\n\n"
            "⚠️ Der Bot vergibt die Nametag-Rolle nicht automatisch."
        ),
        color=discord.Color.blue()
    )

    message = await find_panel_message(channel, NAMETAG_PANEL_MARKER)

    if message:
        await message.edit(embed=embed, view=NametagView())
    else:
        await channel.send(embed=embed, view=NametagView())


# =========================================================
# KENNZEICHEN
# =========================================================

def get_plate_number(plate):
    return plate.split()[-1]


def is_number_used(number):
    for plate in data["license_plates"].values():
        if get_plate_number(plate) == number:
            return True

    return False


def build_license_embed():
    lines = []

    plates = list(data["license_plates"].items())

    plates.sort(
        key=lambda x: (
            int(get_plate_number(x[1]))
            if get_plate_number(x[1]).isdigit()
            else 999999
        )
    )

    for user_id, plate in plates:
        guild = bot.get_guild(GUILD_ID)

        if guild:
            member = guild.get_member(int(user_id))
        else:
            member = None

        name = member.display_name if member else f"User {user_id}"

        lines.append(f"🚗 **{plate}** — {name}")

    if not lines:
        description = "Noch keine Kennzeichen registriert."
    else:
        description = "\n".join(lines)

    return discord.Embed(
        title="🚗 Kennzeichen",
        description=f"{LICENSE_PANEL_MARKER}\n\n{description}",
        color=discord.Color.green()
    )


class LicensePlateModal(Modal, title="🚗 Kennzeichen registrieren"):
    plate = TextInput(
        label="Kennzeichen",
        placeholder="z. B. RLP 01 oder RY ZE 02",
        max_length=30,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        value = self.plate.value.strip().upper()

        parts = value.split()

        if len(parts) < 2:
            await interaction.response.send_message(
                "❌ Das Kennzeichen muss aus Prefix + Nummer bestehen.\n"
                "Beispiel: `RLP 01`",
                ephemeral=True
            )
            return

        number = parts[-1]

        if not number.isdigit():
            await interaction.response.send_message(
                "❌ Die letzte Stelle muss eine Zahl sein.",
                ephemeral=True
            )
            return

        if is_number_used(number):
            await interaction.response.send_message(
                f"❌ Die Nummer **{number}** ist bereits vergeben.",
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

        data["license_plates"][user_id] = value
        save_data()

        await update_license_plate_panel()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen **{value}** wurde registriert.",
            ephemeral=True
        )


class LicenseDeleteButton(Button):
    def __init__(self):
        super().__init__(
            label="Kennzeichen löschen",
            style=discord.ButtonStyle.danger,
            emoji="🗑️"
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
        await update_license_plate_panel()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen **{plate}** wurde gelöscht.",
            ephemeral=True
        )


class LicenseRegisterButton(Button):
    def __init__(self):
        super().__init__(
            label="Kennzeichen registrieren",
            style=discord.ButtonStyle.success,
            emoji="🚗"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(LicensePlateModal())


class LicensePlateView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(LicenseRegisterButton())
        self.add_item(LicenseDeleteButton())


async def update_license_plate_panel():
    channel = bot.get_channel(LICENSE_PLATE_CHANNEL_ID)

    if channel is None:
        return

    embed = build_license_embed()

    message = await find_panel_message(
        channel,
        LICENSE_PANEL_MARKER
    )

    if message:
        await message.edit(
            embed=embed,
            view=LicensePlateView()
        )
    else:
        await channel.send(
            embed=embed,
            view=LicensePlateView()
        )


# =========================================================
# DEVELOPER SHIFT
# =========================================================

class ShiftStartButton(Button):
    def __init__(self):
        super().__init__(
            label="Schicht starten",
            style=discord.ButtonStyle.success,
            emoji="🟢"
        )

    async def callback(self, interaction: discord.Interaction):
        member = interaction.guild.get_member(interaction.user.id)

        permission_role = interaction.guild.get_role(
            SHIFT_PERMISSION_ROLE_ID
        )

        active_role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if permission_role not in member.roles:
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung für eine Entwicklerschicht.",
                ephemeral=True
            )
            return

        if active_role in member.roles:
            await interaction.response.send_message(
                "ℹ️ Du bist bereits im Dienst.",
                ephemeral=True
            )
            return

        try:
            await member.add_roles(active_role)

            log_channel = bot.get_channel(SHIFT_LOG_CHANNEL_ID)

            if log_channel:
                await log_channel.send(
                    f"🟢 **Schicht gestartet**\n"
                    f"👤 {member.mention}\n"
                    f"🕒 <t:{int(datetime.now().timestamp())}:F>"
                )

            await update_shift_panel()

            await interaction.response.send_message(
                "✅ Deine Entwicklerschicht wurde gestartet.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich kann die Schichtrolle nicht vergeben.",
                ephemeral=True
            )


class ShiftEndButton(Button):
    def __init__(self):
        super().__init__(
            label="Schicht beenden",
            style=discord.ButtonStyle.danger,
            emoji="🔴"
        )

    async def callback(self, interaction: discord.Interaction):
        member = interaction.guild.get_member(interaction.user.id)

        active_role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if active_role not in member.roles:
            await interaction.response.send_message(
                "ℹ️ Du bist aktuell nicht im Dienst.",
                ephemeral=True
            )
            return

        try:
            await member.remove_roles(active_role)

            log_channel = bot.get_channel(SHIFT_LOG_CHANNEL_ID)

            if log_channel:
                await log_channel.send(
                    f"🔴 **Schicht beendet**\n"
                    f"👤 {member.mention}\n"
                    f"🕒 <t:{int(datetime.now().timestamp())}:F>"
                )

            await update_shift_panel()

            await interaction.response.send_message(
                "✅ Deine Entwicklerschicht wurde beendet.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich kann die Schichtrolle nicht entfernen.",
                ephemeral=True
            )


class ShiftView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ShiftStartButton())
        self.add_item(ShiftEndButton())


async def update_shift_panel():
    channel = bot.get_channel(DEVELOPER_SHIFT_CHANNEL_ID)

    if channel is None:
        return

    embed = discord.Embed(
        title="🛠️ Entwickler-Schicht",
        description=(
            f"{SHIFT_PANEL_MARKER}\n\n"
            "Hier kannst du deine Entwicklerschicht starten oder beenden.\n\n"
            "🟢 **Schicht starten**\n"
            "🔴 **Schicht beenden**"
        ),
        color=discord.Color.orange()
    )

    message = await find_panel_message(
        channel,
        SHIFT_PANEL_MARKER
    )

    if message:
        await message.edit(
            embed=embed,
            view=ShiftView()
        )
    else:
        await channel.send(
            embed=embed,
            view=ShiftView()
        )


# =========================================================
# BEWERBUNG
# =========================================================

class ApplicationModal(Modal, title="📋 Bewerbung"):
    name = TextInput(
        label="Name",
        placeholder="Dein Name",
        required=True
    )

    age = TextInput(
        label="Alter",
        placeholder="Dein Alter",
        required=True
    )

    reason = TextInput(
        label="Warum möchtest du ins Team?",
        placeholder="Schreibe etwas über dich...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(
            APPLICATION_CHANNEL_ID
        )

        if channel is None:
            await interaction.response.send_message(
                "❌ Bewerbungskanal nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📋 Neue Bewerbung",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )

        embed.add_field(
            name="👤 Name",
            value=self.name.value,
            inline=False
        )

        embed.add_field(
            name="🎂 Alter",
            value=self.age.value,
            inline=False
        )

        embed.add_field(
            name="💬 Warum?",
            value=self.reason.value,
            inline=False
        )

        embed.set_footer(
            text=f"Bewerbung von {interaction.user}"
        )

        await channel.send(
            content=interaction.user.mention,
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Deine Bewerbung wurde abgeschickt.",
            ephemeral=True
        )


class ApplicationButton(Button):
    def __init__(self):
        super().__init__(
            label="Bewerben",
            style=discord.ButtonStyle.success,
            emoji="📋"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            ApplicationModal()
        )


class ApplicationView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ApplicationButton())


async def update_application_panel():
    channel = bot.get_channel(APPLICATION_CHANNEL_ID)

    if channel is None:
        return

    embed = discord.Embed(
        title="📋 Bewerbung",
        description=(
            f"{APPLICATION_PANEL_MARKER}\n\n"
            "Du möchtest dem Team beitreten?\n\n"
            "Klicke auf **Bewerben** und fülle das Formular aus."
        ),
        color=discord.Color.green()
    )

    message = await find_panel_message(
        channel,
        APPLICATION_PANEL_MARKER
    )

    if message:
        await message.edit(
            embed=embed,
            view=ApplicationView()
        )
    else:
        await channel.send(
            embed=embed,
            view=ApplicationView()
        )


# =========================================================
# DEVELOPER TASKS
# =========================================================

class DeveloperTaskModal(Modal, title="🛠️ Entwickler-Aufgabe"):
    task = TextInput(
        label="Aufgabe",
        placeholder="Was soll erledigt werden?",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        permission_role = interaction.guild.get_role(
            SHIFT_PERMISSION_ROLE_ID
        )

        if permission_role not in interaction.user.roles:
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        channel = interaction.guild.get_channel(
            DEVELOPER_TASK_CHANNEL_ID
        )

        if channel is None:
            await interaction.response.send_message(
                "❌ Aufgabenkanal nicht gefunden.",
                ephemeral=True
            )
            return

        task_id = str(
            max(
                [int(x) for x in data["developer_tasks"].keys()]
                if data["developer_tasks"]
                else [0]
            ) + 1
        )

        data["developer_tasks"][task_id] = {
            "task": self.task.value,
            "creator": interaction.user.id,
            "created": datetime.now().isoformat()
        }

        save_data()

        embed = discord.Embed(
            title=f"🛠️ Entwickler-Aufgabe #{task_id}",
            description=self.task.value,
            color=discord.Color.orange()
        )

        embed.add_field(
            name="👤 Erstellt von",
            value=interaction.user.mention
        )

        await channel.send(embed=embed)

        await update_dev_task_panel()

        await interaction.response.send_message(
            f"✅ Aufgabe **#{task_id}** wurde erstellt.",
            ephemeral=True
        )


class DeveloperTaskButton(Button):
    def __init__(self):
        super().__init__(
            label="Aufgabe erstellen",
            style=discord.ButtonStyle.primary,
            emoji="🛠️"
        )

    async def callback(self, interaction: discord.Interaction):
        permission_role = interaction.guild.get_role(
            SHIFT_PERMISSION_ROLE_ID
        )

        if permission_role not in interaction.user.roles:
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


async def update_dev_task_panel():
    channel = bot.get_channel(DEVELOPER_TASK_CHANNEL_ID)

    if channel is None:
        return

    embed = discord.Embed(
        title="🛠️ Entwickler-Aufgaben",
        description=(
            f"{DEV_TASK_PANEL_MARKER}\n\n"
            "Hier können neue Entwickler-Aufgaben erstellt werden."
        ),
        color=discord.Color.orange()
    )

    message = await find_panel_message(
        channel,
        DEV_TASK_PANEL_MARKER
    )

    if message:
        await message.edit(
            embed=embed,
            view=DeveloperTaskView()
        )
    else:
        await channel.send(
            embed=embed,
            view=DeveloperTaskView()
        )


# =========================================================
# OWNER PANEL - MODALS
# =========================================================

class AnnouncementModal(Modal, title="📢 Ankündigung"):
    text = TextInput(
        label="Ankündigung",
        placeholder="Was möchtest du ankündigen?",
        style=discord.TextStyle.paragraph,
        max_length=2000,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(
            int(self.view.selected_channel_id)
        ) if self.view else None

        if channel is None:
            await interaction.response.send_message(
                "❌ Channel nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📢 Ankündigung",
            description=self.text.value,
            color=discord.Color.blurple(),
            timestamp=datetime.now()
        )

        embed.set_footer(
            text=f"Ankündigung von {interaction.user}"
        )

        await channel.send(embed=embed)

        await interaction.response.send_message(
            f"✅ Ankündigung wurde in {channel.mention} gesendet.",
            ephemeral=True
        )


class SayModal(Modal, title="💬 Bot schreiben lassen"):
    text = TextInput(
        label="Nachricht",
        placeholder="Was soll der Bot schreiben?",
        style=discord.TextStyle.paragraph,
        max_length=2000,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(
            int(self.view.selected_channel_id)
        ) if self.view else None

        if channel is None:
            await interaction.response.send_message(
                "❌ Channel nicht gefunden.",
                ephemeral=True
            )
            return

        await channel.send(self.text.value)

        await interaction.response.send_message(
            f"✅ Nachricht wurde in {channel.mention} gesendet.",
            ephemeral=True
        )


class EmbedModal(Modal, title="✨ Embed erstellen"):
    title_text = TextInput(
        label="Titel",
        placeholder="Embed-Titel",
        max_length=256,
        required=True
    )

    description = TextInput(
        label="Beschreibung",
        placeholder="Embed-Text",
        style=discord.TextStyle.paragraph,
        max_length=4000,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(
            int(self.view.selected_channel_id)
        ) if self.view else None

        if channel is None:
            await interaction.response.send_message(
                "❌ Channel nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=self.title_text.value,
            description=self.description.value,
            color=discord.Color.blurple(),
            timestamp=datetime.now()
        )

        embed.set_footer(
            text=f"Erstellt von {interaction.user}"
        )

        await channel.send(embed=embed)

        await interaction.response.send_message(
            f"✅ Embed wurde in {channel.mention} erstellt.",
            ephemeral=True
        )


class ClearModal(Modal, title="🧹 Nachrichten löschen"):
    amount = TextInput(
        label="Anzahl",
        placeholder="1 bis 100",
        max_length=3,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(
            int(self.view.selected_channel_id)
        ) if self.view else None

        if channel is None:
            await interaction.response.send_message(
                "❌ Channel nicht gefunden.",
                ephemeral=True
            )
            return

        try:
            amount = int(self.amount.value)

            if amount < 1 or amount > 100:
                raise ValueError

        except ValueError:
            await interaction.response.send_message(
                "❌ Bitte eine Zahl zwischen 1 und 100 eingeben.",
                ephemeral=True
            )
            return

        deleted = await channel.purge(limit=amount)

        await interaction.response.send_message(
            f"🧹 **{len(deleted)}** Nachrichten wurden in "
            f"{channel.mention} gelöscht.",
            ephemeral=True
        )


# =========================================================
# OWNER CHANNEL SELECT VIEWS
# =========================================================

class AnnouncementChannelView(View):
    def __init__(self):
        super().__init__(timeout=120)

        select = ChannelSelect(
            placeholder="📢 Channel für die Ankündigung auswählen",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1
        )

        async def callback(interaction: discord.Interaction):
            modal = AnnouncementModal()
            modal.view = type(
                "SelectedChannel",
                (),
                {"selected_channel_id": select.values[0].id}
            )()

            await interaction.response.send_modal(modal)

        select.callback = callback
        self.add_item(select)


class SayChannelView(View):
    def __init__(self):
        super().__init__(timeout=120)

        select = ChannelSelect(
            placeholder="💬 Channel auswählen",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1
        )

        async def callback(interaction: discord.Interaction):
            modal = SayModal()
            modal.view = type(
                "SelectedChannel",
                (),
                {"selected_channel_id": select.values[0].id}
            )()

            await interaction.response.send_modal(modal)

        select.callback = callback
        self.add_item(select)


class EmbedChannelView(View):
    def __init__(self):
        super().__init__(timeout=120)

        select = ChannelSelect(
            placeholder="✨ Channel für das Embed auswählen",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1
        )

        async def callback(interaction: discord.Interaction):
            modal = EmbedModal()
            modal.view = type(
                "SelectedChannel",
                (),
                {"selected_channel_id": select.values[0].id}
            )()

            await interaction.response.send_modal(modal)

        select.callback = callback
        self.add_item(select)


class ClearChannelView(View):
    def __init__(self):
        super().__init__(timeout=120)

        select = ChannelSelect(
            placeholder="🧹 Channel auswählen",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1
        )

        async def callback(interaction: discord.Interaction):
            modal = ClearModal()
            modal.view = type(
                "SelectedChannel",
                (),
                {"selected_channel_id": select.values[0].id}
            )()

            await interaction.response.send_modal(modal)

        select.callback = callback
        self.add_item(select)


class LockChannelView(View):
    def __init__(self):
        super().__init__(timeout=120)

        select = ChannelSelect(
            placeholder="🔒 Channel auswählen",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1
        )

        async def callback(interaction: discord.Interaction):
            channel = select.values[0]

            everyone = interaction.guild.default_role

            try:
                await channel.set_permissions(
                    everyone,
                    send_messages=False
                )

                await interaction.response.send_message(
                    f"🔒 {channel.mention} wurde gesperrt.",
                    ephemeral=True
                )

            except discord.Forbidden:
                await interaction.response.send_message(
                    "❌ Ich habe keine Berechtigung für diesen Channel.",
                    ephemeral=True
                )

        select.callback = callback
        self.add_item(select)


class UnlockChannelView(View):
    def __init__(self):
        super().__init__(timeout=120)

        select = ChannelSelect(
            placeholder="🔓 Channel auswählen",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1
        )

        async def callback(interaction: discord.Interaction):
            channel = select.values[0]

            everyone = interaction.guild.default_role

            try:
                await channel.set_permissions(
                    everyone,
                    send_messages=None
                )

                await interaction.response.send_message(
                    f"🔓 {channel.mention} wurde entsperrt.",
                    ephemeral=True
                )

            except discord.Forbidden:
                await interaction.response.send_message(
                    "❌ Ich habe keine Berechtigung für diesen Channel.",
                    ephemeral=True
                )

        select.callback = callback
        self.add_item(select)


# =========================================================
# OWNER PANEL
# =========================================================

class OwnerPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def interaction_check(self, interaction):
        role = interaction.guild.get_role(OWNER_ROLE_ID)

        if role not in interaction.user.roles:
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung für das OwnerPanel.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="Ankündigung",
        style=discord.ButtonStyle.primary,
        emoji="📢",
        custom_id="owner_announcement"
    )
    async def announcement(
        self,
        interaction: discord.Interaction,
        button: Button
    ):
        await interaction.response.send_message(
            "📢 Wähle den Channel für die Ankündigung:",
            view=AnnouncementChannelView(),
            ephemeral=True
        )

    @discord.ui.button(
        label="Bot schreiben lassen",
        style=discord.ButtonStyle.primary,
        emoji="💬",
        custom_id="owner_say"
    )
    async def say(
        self,
        interaction: discord.Interaction,
        button: Button
    ):
        await interaction.response.send_message(
            "💬 Wähle den Channel, in dem der Bot schreiben soll:",
            view=SayChannelView(),
            ephemeral=True
        )

    @discord.ui.button(
        label="Embed erstellen",
        style=discord.ButtonStyle.primary,
        emoji="✨",
        custom_id="owner_embed"
    )
    async def embed(
        self,
        interaction: discord.Interaction,
        button: Button
    ):
        await interaction.response.send_message(
            "✨ Wähle den Channel für das Embed:",
            view=EmbedChannelView(),
            ephemeral=True
        )

    @discord.ui.button(
        label="Nachrichten löschen",
        style=discord.ButtonStyle.danger,
        emoji="🧹",
        custom_id="owner_clear"
    )
    async def clear(
        self,
        interaction: discord.Interaction,
        button: Button
    ):
        await interaction.response.send_message(
            "🧹 Wähle den Channel, in dem Nachrichten gelöscht werden sollen:",
            view=ClearChannelView(),
            ephemeral=True
        )

    @discord.ui.button(
        label="Channel sperren",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="owner_lock"
    )
    async def lock(
        self,
        interaction: discord.Interaction,
        button: Button
    ):
        await interaction.response.send_message(
            "🔒 Wähle den Channel, der gesperrt werden soll:",
            view=LockChannelView(),
            ephemeral=True
        )

    @discord.ui.button(
        label="Channel entsperren",
        style=discord.ButtonStyle.success,
        emoji="🔓",
        custom_id="owner_unlock"
    )
    async def unlock(
        self,
        interaction: discord.Interaction,
        button: Button
    ):
        await interaction.response.send_message(
            "🔓 Wähle den Channel, der entsperrt werden soll:",
            view=UnlockChannelView(),
            ephemeral=True
        )

    @discord.ui.button(
        label="Quiz starten",
        style=discord.ButtonStyle.success,
        emoji="🎮",
        custom_id="owner_quiz_start"
    )
    async def quiz_start(
        self,
        interaction: discord.Interaction,
        button: Button
    ):
        await send_quiz_question()

        await interaction.response.send_message(
            "🎮 Neues Quiz wurde gestartet.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Quiz zurücksetzen",
        style=discord.ButtonStyle.danger,
        emoji="🔄",
        custom_id="owner_quiz_reset"
    )
    async def quiz_reset(
        self,
        interaction: discord.Interaction,
        button: Button
    ):
        channel = bot.get_channel(QUIZ_CHANNEL_ID)

        if channel:
            try:
                async for message in channel.history(limit=100):
                    if message.author == bot.user:
                        await message.delete()
            except Exception:
                pass

        quiz_state["message_id"] = None
        quiz_state["answer"] = None

        await send_quiz_question()

        await interaction.response.send_message(
            "🔄 Quiz wurde zurückgesetzt.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Bot-Status",
        style=discord.ButtonStyle.secondary,
        emoji="📊",
        custom_id="owner_status"
    )
    async def status(
        self,
        interaction: discord.Interaction,
        button: Button
    ):
        guild_count = len(bot.guilds)
        latency = round(bot.latency * 1000)

        embed = discord.Embed(
            title="📊 Bot-Status",
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
            value=str(guild_count),
            inline=True
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @discord.ui.button(
        label="Serverinfo",
        style=discord.ButtonStyle.secondary,
        emoji="🌐",
        custom_id="owner_serverinfo"
    )
    async def serverinfo(
        self,
        interaction: discord.Interaction,
        button: Button
    ):
        guild = interaction.guild

        embed = discord.Embed(
            title="🌐 Serverinfo",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="🏠 Server",
            value=guild.name,
            inline=False
        )

        embed.add_field(
            name="👥 Mitglieder",
            value=str(guild.member_count),
            inline=True
        )

        embed.add_field(
            name="💬 Channels",
            value=str(len(guild.channels)),
            inline=True
        )

        embed.add_field(
            name="🎭 Rollen",
            value=str(len(guild.roles)),
            inline=True
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


async def update_owner_panel():
    embed = discord.Embed(
        title="👑 Owner Control Center",
        description=(
            f"{OWNER_PANEL_MARKER}\n\n"
            "🎛️ **Owner-Steuerung**\n\n"
            "📢 Ankündigung\n"
            "💬 Bot schreiben lassen\n"
            "✨ Embed erstellen\n"
            "🧹 Nachrichten löschen\n"
            "🔒 Channel sperren\n"
            "🔓 Channel entsperren\n"
            "🎮 Quiz starten\n"
            "🔄 Quiz zurücksetzen\n"
            "📊 Bot-Status\n"
            "🌐 Serverinfo"
        ),
        color=discord.Color.gold()
    )

    for guild in bot.guilds:
        for channel in guild.text_channels:
            try:
                message = await find_panel_message(
                    channel,
                    OWNER_PANEL_MARKER
                )

                if message:
                    await message.edit(
                        embed=embed,
                        view=OwnerPanelView()
                    )
                    return

            except Exception:
                pass


async def send_owner_panel(channel):
    embed = discord.Embed(
        title="👑 Owner Control Center",
        description=(
            f"{OWNER_PANEL_MARKER}\n\n"
            "🎛️ **Owner-Steuerung**\n\n"
            "📢 Ankündigung\n"
            "💬 Bot schreiben lassen\n"
            "✨ Embed erstellen\n"
            "🧹 Nachrichten löschen\n"
            "🔒 Channel sperren\n"
            "🔓 Channel entsperren\n"
            "🎮 Quiz starten\n"
            "🔄 Quiz zurücksetzen\n"
            "📊 Bot-Status\n"
            "🌐 Serverinfo"
        ),
        color=discord.Color.gold()
    )

    message = await find_panel_message(
        channel,
        OWNER_PANEL_MARKER
    )

    if message:
        await message.edit(
            embed=embed,
            view=OwnerPanelView()
        )
    else:
        await channel.send(
            embed=embed,
            view=OwnerPanelView()
        )


# =========================================================
# SUPPORT
# =========================================================

@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel == after.channel:
        return

    if after.channel and after.channel.id == SUPPORT_VOICE_CHANNEL_ID:
        data["support_cases"] += 1
        save_data()

        channel = bot.get_channel(SUPPORT_LOG_CHANNEL_ID)

        if channel:
            await channel.send(
                f"📞 **Support betreten**\n"
                f"👤 {member.mention}\n"
                f"📊 Support-Fall #{data['support_cases']}"
            )

    elif before.channel and before.channel.id == SUPPORT_VOICE_CHANNEL_ID:
        channel = bot.get_channel(SUPPORT_LOG_CHANNEL_ID)

        if channel:
            await channel.send(
                f"📴 **Support verlassen**\n"
                f"👤 {member.mention}"
            )


# =========================================================
# COMMANDS
# =========================================================

@bot.command()
async def ping(ctx):
    await ctx.send(
        f"🏓 Pong! `{round(bot.latency * 1000)}ms`"
    )


@bot.command()
async def hilfe(ctx):
    embed = discord.Embed(
        title="📚 Bot-Hilfe",
        description=(
            "`!ping` — Bot-Latenz\n"
            "`!hilfe` — Diese Hilfe\n"
            "`!owner` — OwnerPanel\n"
            "`!ownerpanel` — OwnerPanel\n"
            "`!nametag` — Nametag-Panel\n"
            "`!kennzeichen` — Kennzeichen-Panel\n"
            "`!schicht` — Entwickler-Schicht\n"
            "`!bewerbung` — Bewerbungs-Panel\n"
            "`!devtask` — Entwickler-Aufgaben"
        ),
        color=discord.Color.blurple()
    )

    await ctx.send(embed=embed)


@bot.command()
async def ownerpanel(ctx):
    role = ctx.guild.get_role(OWNER_ROLE_ID)

    if role not in ctx.author.roles:
        await ctx.send(
            "❌ Du hast keine Berechtigung.",
            delete_after=5
        )
        return

    await send_owner_panel(ctx.channel)


@bot.command()
async def owner(ctx):
    role = ctx.guild.get_role(OWNER_ROLE_ID)

    if role not in ctx.author.roles:
        await ctx.send(
            "❌ Du hast keine Berechtigung.",
            delete_after=5
        )
        return

    await send_owner_panel(ctx.channel)


@bot.command()
async def nametag(ctx):
    await update_nametag_panel()


@bot.command()
async def kennzeichen(ctx):
    await update_license_plate_panel()


@bot.command()
async def schicht(ctx):
    await update_shift_panel()


@bot.command()
async def bewerbung(ctx):
    await update_application_panel()


@bot.command()
async def devtask(ctx):
    await update_dev_task_panel()


# =========================================================
# MESSAGE HANDLING
# =========================================================

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # QUIZ CHANNEL
    if message.channel.id == QUIZ_CHANNEL_ID:
        async with quiz_lock:
            answer = quiz_state["answer"]

            try:
                await message.delete()
            except Exception:
                pass

            if answer and message.content.strip().lower() == answer:
                quiz_message_id = quiz_state["message_id"]

                if quiz_message_id:
                    try:
                        quiz_message = await message.channel.fetch_message(
                            quiz_message_id
                        )
                        await quiz_message.delete()
                    except Exception:
                        pass

                await message.channel.send(
                    f"🎉 **{message.author.mention}** hat richtig geraten! "
                    f"🏆 **{answer.title()}**",
                    delete_after=4
                )

                quiz_state["message_id"] = None
                quiz_state["answer"] = None

                await asyncio.sleep(1)
                await send_quiz_question()

        return

    await bot.process_commands(message)


# =========================================================
# COMMAND ERROR
# =========================================================

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    print("Command Error:", error)


# =========================================================
# STARTUP
# =========================================================

views_registered = False
startup_finished = False


async def update_all_panels():
    await update_nametag_panel()
    await update_license_plate_panel()
    await update_shift_panel()
    await update_application_panel()
    await update_dev_task_panel()
    await update_owner_panel()


@bot.event
async def on_ready():
    global views_registered
    global startup_finished

    print(f"✅ Eingeloggt als {bot.user} ({bot.user.id})")

    if not views_registered:
        bot.add_view(NametagView())
        bot.add_view(LicensePlateView())
        bot.add_view(ShiftView())
        bot.add_view(ApplicationView())
        bot.add_view(DeveloperTaskView())
        bot.add_view(OwnerPanelView())

        views_registered = True

    # =====================================================
    # WICHTIG:
    # BEIM START KEINE NAMETAGS VERÄNDERN.
    #
    # Kein RLP hinzufügen.
    # Kein RLP entfernen.
    # Keine Nametag-Rolle vergeben.
    # =====================================================

    # Aktive Schichtrollen werden ebenfalls NICHT
    # automatisch wiederhergestellt.

    if not startup_finished:
        await update_all_panels()
        await ensure_quiz()

        if not quiz_cleanup.is_running():
            quiz_cleanup.start()

        startup_finished = True

    print("🟢 Bot ist vollständig bereit.")


# =========================================================
# START
# =========================================================

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN wurde nicht gefunden."
    )

bot.run(TOKEN)
