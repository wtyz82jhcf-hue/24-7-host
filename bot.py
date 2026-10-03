import os
import json
import asyncio
import random

import discord
from discord.ext import commands, tasks


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

NAMETAG = "RLP "

DATA_FILE = "bot_data.json"

NAMETAG_PANEL_MARKER = "RLP_NAMETAG_PANEL"
LICENSE_PANEL_MARKER = "RLP_LICENSE_PANEL"
SHIFT_PANEL_MARKER = "RLP_SHIFT_PANEL"
APPLICATION_PANEL_MARKER = "RLP_APPLICATION_PANEL"
DEV_TASK_PANEL_MARKER = "RLP_DEV_TASK_PANEL"
OWNER_PANEL_MARKER = "RLP_OWNER_PANEL"


# =========================================================
# BOT
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
            "developer_tasks": {}
        }

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if "license_plates" not in data:
            data["license_plates"] = {}

        if "developer_tasks" not in data:
            data["developer_tasks"] = {}

        return data

    except Exception as error:
        print("❌ Fehler beim Laden der Daten:", error)

        return {
            "license_plates": {},
            "developer_tasks": {}
        }


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
        print("❌ Fehler beim Speichern:", error)


data = load_data()


# =========================================================
# QUIZ
# =========================================================

QUIZ_QUESTIONS = [
    ("🇩🇪🇩🇪🇩🇪", "Deutschland"),
    ("🇫🇷🥐🗼", "Frankreich"),
    ("🇮🇹🍕🍝", "Italien"),
    ("🇪🇸💃🌮", "Spanien"),
    ("🇬🇧👑🎡", "England"),
    ("🇺🇸🗽🍔", "Amerika"),
    ("🇯🇵🍣🗼", "Japan"),
    ("🇧🇷⚽🌴", "Brasilien"),
    ("🇨🇭🏔️🧀", "Schweiz"),
    ("🇦🇹🏔️🎿", "Österreich"),
    ("🚗💨🏁", "Auto"),
    ("⚽🥅🏆", "Fußball"),
    ("🐶🦴", "Hund"),
    ("🐱🐟", "Katze"),
    ("🌧️☔", "Regen"),
    ("☀️🏖️", "Sommer"),
    ("❄️⛄", "Winter"),
    ("🍎🍏", "Apfel"),
    ("🍌🐒", "Banane"),
    ("🍕🧀🍅", "Pizza"),
    ("🎮🕹️", "Gaming"),
    ("💻⌨️🖱️", "Computer"),
    ("🚓🚨👮", "Polizei"),
    ("🚒🔥👨‍🚒", "Feuerwehr"),
    ("🚑🏥", "Rettungsdienst"),
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
        print("❌ Quiz-Kanal nicht gefunden.")
        return

    emoji, answer = random.choice(QUIZ_QUESTIONS)

    quiz_state["round"] += 1
    quiz_state["answer"] = answer.lower()

    embed = discord.Embed(
        title="🎯 Emoji Quiz",
        description=(
            f"**Welche Antwort passt zu diesen Emojis?**\n\n"
            f"# {emoji}\n\n"
            f"💬 Schreibe deine Antwort in den Chat!"
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=f"Runde {quiz_state['round']}"
    )

    try:
        message = await channel.send(embed=embed)

        quiz_state["message_id"] = message.id

        print(
            f"🧠 Quiz gestartet: "
            f"{emoji} → {answer}"
        )

    except Exception as error:
        print("❌ Fehler beim Senden der Quizfrage:", error)


async def ensure_quiz():
    channel = bot.get_channel(QUIZ_CHANNEL_ID)

    if channel is None:
        return

    message_id = quiz_state.get("message_id")

    if message_id:
        try:
            await channel.fetch_message(message_id)
            return

        except Exception:
            quiz_state["message_id"] = None
            quiz_state["answer"] = None

    await send_quiz_question()


# =========================================================
# PANEL HELPER
# =========================================================

async def find_panel_message(channel, marker):
    found = None

    try:
        async for message in channel.history(limit=100):

            if not message.author.bot:
                continue

            if not message.embeds:
                continue

            for embed in message.embeds:

                text = ""

                if embed.title:
                    text += embed.title + "\n"

                if embed.description:
                    text += embed.description + "\n"

                if marker in text:

                    if found is None:
                        found = message

                    else:
                        try:
                            await message.delete()
                        except Exception:
                            pass

                    break

    except Exception as error:
        print(
            f"Panel-Suche Fehler ({marker}):",
            error
        )

    return found


# =========================================================
# NAMETAG PANEL
# =========================================================

class NametagView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Nametag zurücksetzen",
        style=discord.ButtonStyle.danger,
        emoji="🗑️",
        custom_id="nametag_reset"
    )
    async def reset_nametag(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        member = interaction.guild.get_member(
            interaction.user.id
        )

        if member is None:
            await interaction.response.send_message(
                "❌ Benutzer nicht gefunden.",
                ephemeral=True
            )
            return

        if not member.display_name.startswith(NAMETAG):
            await interaction.response.send_message(
                "ℹ️ Du hast aktuell keinen `RLP `-Nametag.",
                ephemeral=True
            )
            return

        new_name = member.display_name[len(NAMETAG):]

        if not new_name:
            new_name = member.name

        try:
            await member.edit(
                nick=new_name
            )

            await interaction.response.send_message(
                "✅ Dein Nametag wurde entfernt.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich darf deinen Nicknamen nicht ändern.",
                ephemeral=True
            )

        except Exception as error:
            print("❌ Nametag Reset:", error)

            await interaction.response.send_message(
                "❌ Beim Zurücksetzen ist ein Fehler aufgetreten.",
                ephemeral=True
            )


async def update_nametag_panel():

    channel = bot.get_channel(
        NAMETAG_CHANNEL_ID
    )

    if channel is None:
        return

    embed = discord.Embed(
        title="🏷️ Nametag System",
        description=(
            "Hier kannst du deinen Nametag verwalten.\n\n"
            "Der Bot nimmt beim Start **keine automatischen "
            "Nametag-Änderungen** vor.\n\n"
            "Mit dem Button kannst du deinen aktuellen "
            "`RLP `-Nametag entfernen."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=NAMETAG_PANEL_MARKER
    )

    message = await find_panel_message(
        channel,
        NAMETAG_PANEL_MARKER
    )

    if message:
        try:
            await message.edit(
                embed=embed,
                view=NametagView()
            )
        except Exception as error:
            print("❌ Nametag Panel Update:", error)

    else:
        try:
            await channel.send(
                embed=embed,
                view=NametagView()
            )
        except Exception as error:
            print("❌ Nametag Panel Erstellung:", error)


# =========================================================
# LICENSE PLATE
# =========================================================

def get_plate_number(plate):
    parts = plate.strip().split()

    if not parts:
        return None

    last = parts[-1]

    if not last.isdigit():
        return None

    return int(last)


def plate_number_used(number):
    for plate in data["license_plates"].values():

        if get_plate_number(plate) == number:
            return True

    return False


class LicensePlateModal(discord.ui.Modal):

    def __init__(self):
        super().__init__(
            title="Kennzeichen registrieren"
        )

        self.plate = discord.ui.TextInput(
            label="Kennzeichen",
            placeholder="z.B. RLP 01",
            required=True,
            max_length=30
        )

        self.add_item(self.plate)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        plate = self.plate.value.strip()

        number = get_plate_number(plate)

        if number is None:
            await interaction.response.send_message(
                "❌ Das Kennzeichen muss mit einer Nummer enden.\n"
                "Beispiel: `RLP 01`",
                ephemeral=True
            )
            return

        if plate_number_used(number):
            await interaction.response.send_message(
                "❌ Diese Nummer ist bereits vergeben.",
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

        data["license_plates"][user_id] = plate

        save_data()

        await update_license_plate_panel()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen **{plate}** wurde registriert.",
            ephemeral=True
        )


class LicensePlateDeleteButton(
    discord.ui.Button
):

    def __init__(self):
        super().__init__(
            label="Eigenes Kennzeichen löschen",
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            custom_id="license_delete"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        user_id = str(interaction.user.id)

        if user_id not in data["license_plates"]:
            await interaction.response.send_message(
                "❌ Du hast kein registriertes Kennzeichen.",
                ephemeral=True
            )
            return

        plate = data["license_plates"].pop(
            user_id
        )

        save_data()

        await update_license_plate_panel()

        await interaction.response.send_message(
            f"✅ Kennzeichen **{plate}** wurde gelöscht.",
            ephemeral=True
        )


class LicensePlateView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(
            discord.ui.Button(
                label="Kennzeichen registrieren",
                style=discord.ButtonStyle.success,
                emoji="🚗",
                custom_id="license_add"
            )
        )

        self.add_item(
            LicensePlateDeleteButton()
        )

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ):

        return True

    @discord.ui.button(
        label="",
        style=discord.ButtonStyle.secondary,
        custom_id="license_dummy"
    )
    async def dummy(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        pass


# Separate handler for register button
@bot.event
async def on_interaction(interaction: discord.Interaction):

    if (
        interaction.type == discord.InteractionType.component
        and interaction.data
    ):

        custom_id = interaction.data.get(
            "custom_id"
        )

        if custom_id == "license_add":

            await interaction.response.send_modal(
                LicensePlateModal()
            )

            return

    # Important: normal interaction processing continues
    await bot.process_application_commands(interaction)


async def update_license_plate_panel():

    channel = bot.get_channel(
        LICENSE_PLATE_CHANNEL_ID
    )

    if channel is None:
        return

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
                f"🚗 **{plate}** — {name}"
            )

        description = "\n".join(lines)

    else:
        description = (
            "Noch keine Kennzeichen registriert."
        )

    embed = discord.Embed(
        title="🚗 Kennzeichen Verwaltung",
        description=description,
        color=discord.Color.green()
    )

    embed.add_field(
        name="Hinweis",
        value=(
            "Die letzte Zahl muss global eindeutig sein.\n"
            "Beispiel: Wenn `RLP 01` vergeben ist, "
            "kann `RY ZE 01` nicht mehr verwendet werden."
        ),
        inline=False
    )

    embed.set_footer(
        text=LICENSE_PANEL_MARKER
    )

    message = await find_panel_message(
        channel,
        LICENSE_PANEL_MARKER
    )

    if message:

        try:
            await message.edit(
                embed=embed,
                view=LicensePlateView()
            )
        except Exception as error:
            print(
                "❌ Kennzeichen Panel Update:",
                error
            )

    else:

        try:
            await channel.send(
                embed=embed,
                view=LicensePlateView()
            )
        except Exception as error:
            print(
                "❌ Kennzeichen Panel Erstellung:",
                error
            )


# =========================================================
# SHIFT SYSTEM
# =========================================================

class ShiftView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Schicht starten",
        style=discord.ButtonStyle.success,
        emoji="🟢",
        custom_id="shift_start"
    )
    async def start_shift(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        member = interaction.guild.get_member(
            interaction.user.id
        )

        if member is None:
            await interaction.response.send_message(
                "❌ Benutzer nicht gefunden.",
                ephemeral=True
            )
            return

        permission_role = interaction.guild.get_role(
            SHIFT_PERMISSION_ROLE_ID
        )

        active_role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if permission_role is None:
            await interaction.response.send_message(
                "❌ Berechtigungsrolle nicht gefunden.",
                ephemeral=True
            )
            return

        if permission_role not in member.roles:
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung für eine Schicht.",
                ephemeral=True
            )
            return

        if active_role is None:
            await interaction.response.send_message(
                "❌ Aktive Schichtrolle nicht gefunden.",
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
            await member.add_roles(
                active_role,
                reason="Entwickler-Schicht gestartet"
            )

            await interaction.response.send_message(
                "🟢 Deine Schicht wurde gestartet.",
                ephemeral=True
            )

            log_channel = bot.get_channel(
                SHIFT_LOG_CHANNEL_ID
            )

            if log_channel:
                await log_channel.send(
                    f"🟢 **Schicht gestartet**\n"
                    f"Benutzer: {member.mention}"
                )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich darf die Schichtrolle nicht vergeben.",
                ephemeral=True
            )

        except Exception as error:
            print("❌ Schichtstart:", error)


    @discord.ui.button(
        label="Schicht beenden",
        style=discord.ButtonStyle.danger,
        emoji="🔴",
        custom_id="shift_end"
    )
    async def end_shift(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        member = interaction.guild.get_member(
            interaction.user.id
        )

        if member is None:
            await interaction.response.send_message(
                "❌ Benutzer nicht gefunden.",
                ephemeral=True
            )
            return

        active_role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if active_role is None:
            await interaction.response.send_message(
                "❌ Aktive Schichtrolle nicht gefunden.",
                ephemeral=True
            )
            return

        if active_role not in member.roles:
            await interaction.response.send_message(
                "ℹ️ Du bist aktuell nicht im Dienst.",
                ephemeral=True
            )
            return

        try:
            await member.remove_roles(
                active_role,
                reason="Entwickler-Schicht beendet"
            )

            await interaction.response.send_message(
                "🔴 Deine Schicht wurde beendet.",
                ephemeral=True
            )

            log_channel = bot.get_channel(
                SHIFT_LOG_CHANNEL_ID
            )

            if log_channel:
                await log_channel.send(
                    f"🔴 **Schicht beendet**\n"
                    f"Benutzer: {member.mention}"
                )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich darf die Schichtrolle nicht entfernen.",
                ephemeral=True
            )

        except Exception as error:
            print("❌ Schichtende:", error)


async def update_shift_panel():

    channel = bot.get_channel(
        DEVELOPER_SHIFT_CHANNEL_ID
    )

    if channel is None:
        return

    embed = discord.Embed(
        title="🛠️ Entwickler-Schicht",
        description=(
            "Nutze die Buttons unten, um deine "
            "Entwickler-Schicht zu starten oder zu beenden.\n\n"
            "🟢 **Schicht starten**\n"
            "🔴 **Schicht beenden**"
        ),
        color=discord.Color.orange()
    )

    embed.set_footer(
        text=SHIFT_PANEL_MARKER
    )

    message = await find_panel_message(
        channel,
        SHIFT_PANEL_MARKER
    )

    if message:

        try:
            await message.edit(
                embed=embed,
                view=ShiftView()
            )
        except Exception as error:
            print(
                "❌ Schicht Panel Update:",
                error
            )

    else:

        try:
            await channel.send(
                embed=embed,
                view=ShiftView()
            )
        except Exception as error:
            print(
                "❌ Schicht Panel Erstellung:",
                error
            )


# =========================================================
# APPLICATION SYSTEM
# =========================================================

class ApplicationModal(discord.ui.Modal):

    def __init__(self):
        super().__init__(
            title="Bewerbung"
        )

        self.name = discord.ui.TextInput(
            label="Name",
            placeholder="Dein Name",
            required=True,
            max_length=100
        )

        self.age = discord.ui.TextInput(
            label="Alter",
            placeholder="Dein Alter",
            required=True,
            max_length=3
        )

        self.reason = discord.ui.TextInput(
            label="Warum möchtest du dich bewerben?",
            placeholder="Schreibe etwas über dich...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )

        self.add_item(self.name)
        self.add_item(self.age)
        self.add_item(self.reason)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        channel = bot.get_channel(
            APPLICATION_CHANNEL_ID
        )

        if channel is None:
            await interaction.response.send_message(
                "❌ Bewerbungs-Channel nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📨 Neue Bewerbung",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="👤 Discord",
            value=interaction.user.mention,
            inline=False
        )

        embed.add_field(
            name="📝 Name",
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
            text=f"User ID: {interaction.user.id}"
        )

        await channel.send(
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Deine Bewerbung wurde erfolgreich abgeschickt.",
            ephemeral=True
        )


class ApplicationView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Bewerbung starten",
        style=discord.ButtonStyle.success,
        emoji="📨",
        custom_id="application_start"
    )
    async def application_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
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

    embed = discord.Embed(
        title="📨 Bewerbungen",
        description=(
            "Du möchtest dich bewerben?\n\n"
            "Klicke unten auf **Bewerbung starten** "
            "und fülle das Formular aus."
        ),
        color=discord.Color.blue()
    )

    embed.set_footer(
        text=APPLICATION_PANEL_MARKER
    )

    message = await find_panel_message(
        channel,
        APPLICATION_PANEL_MARKER
    )

    if message:

        try:
            await message.edit(
                embed=embed,
                view=ApplicationView()
            )
        except Exception as error:
            print(
                "❌ Bewerbungs Panel Update:",
                error
            )

    else:

        try:
            await channel.send(
                embed=embed,
                view=ApplicationView()
            )
        except Exception as error:
            print(
                "❌ Bewerbungs Panel Erstellung:",
                error
            )


# =========================================================
# DEVELOPER TASKS
# =========================================================

class DeveloperTaskModal(discord.ui.Modal):

    def __init__(self):
        super().__init__(
            title="Neue Entwickler-Aufgabe"
        )

        self.title_input = discord.ui.TextInput(
            label="Titel",
            placeholder="Titel der Aufgabe",
            required=True,
            max_length=100
        )

        self.description = discord.ui.TextInput(
            label="Beschreibung",
            placeholder="Was soll gemacht werden?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1500
        )

        self.add_item(self.title_input)
        self.add_item(self.description)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        member = interaction.guild.get_member(
            interaction.user.id
        )

        permission_role = interaction.guild.get_role(
            SHIFT_PERMISSION_ROLE_ID
        )

        if (
            member is None
            or permission_role is None
            or permission_role not in member.roles
        ):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung dafür.",
                ephemeral=True
            )
            return

        task_id = str(
            max(
                [int(x) for x in data["developer_tasks"].keys()]
                + [0]
            ) + 1
        )

        data["developer_tasks"][task_id] = {
            "title": self.title_input.value,
            "description": self.description.value,
            "creator": interaction.user.id
        }

        save_data()

        channel = bot.get_channel(
            DEVELOPER_TASK_CHANNEL_ID
        )

        if channel:

            embed = discord.Embed(
                title=f"🛠️ Aufgabe #{task_id}",
                description=self.description.value,
                color=discord.Color.orange()
            )

            embed.add_field(
                name="📌 Titel",
                value=self.title_input.value,
                inline=False
            )

            embed.add_field(
                name="👤 Erstellt von",
                value=interaction.user.mention,
                inline=False
            )

            await channel.send(
                embed=embed
            )

        await update_dev_task_panel()

        await interaction.response.send_message(
            f"✅ Aufgabe #{task_id} wurde erstellt.",
            ephemeral=True
        )


class DeveloperTaskView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Aufgabe erstellen",
        style=discord.ButtonStyle.primary,
        emoji="🛠️",
        custom_id="dev_task_create"
    )
    async def create_task(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            DeveloperTaskModal()
        )


async def update_dev_task_panel():

    channel = bot.get_channel(
        DEVELOPER_TASK_CHANNEL_ID
    )

    if channel is None:
        return

    embed = discord.Embed(
        title="🛠️ Entwickler-Aufgaben",
        description=(
            "Über den Button können berechtigte "
            "Entwickler neue Aufgaben erstellen."
        ),
        color=discord.Color.orange()
    )

    embed.set_footer(
        text=DEV_TASK_PANEL_MARKER
    )

    message = await find_panel_message(
        channel,
        DEV_TASK_PANEL_MARKER
    )

    if message:

        try:
            await message.edit(
                embed=embed,
                view=DeveloperTaskView()
            )
        except Exception as error:
            print(
                "❌ Dev-Aufgaben Panel Update:",
                error
            )

    else:

        try:
            await channel.send(
                embed=embed,
                view=DeveloperTaskView()
            )
        except Exception as error:
            print(
                "❌ Dev-Aufgaben Panel Erstellung:",
                error
            )


# =========================================================
# OWNER PANEL MODALS
# =========================================================

class AnnouncementModal(discord.ui.Modal):

    def __init__(self, channel_id):
        super().__init__(
            title="Ankündigung"
        )

        self.channel_id = channel_id

        self.message = discord.ui.TextInput(
            label="Nachricht",
            placeholder="Deine Ankündigung...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.message)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        channel = bot.get_channel(
            self.channel_id
        )

        if channel is None:
            await interaction.response.send_message(
                "❌ Channel nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📢 Ankündigung",
            description=self.message.value,
            color=discord.Color.blue()
        )

        embed.set_footer(
            text=f"Ankündigung von {interaction.user}"
        )

        await channel.send(
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Ankündigung gesendet.",
            ephemeral=True
        )


class SayModal(discord.ui.Modal):

    def __init__(self, channel_id):
        super().__init__(
            title="Bot schreiben lassen"
        )

        self.channel_id = channel_id

        self.message = discord.ui.TextInput(
            label="Nachricht",
            placeholder="Was soll der Bot schreiben?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.message)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        channel = bot.get_channel(
            self.channel_id
        )

        if channel is None:
            await interaction.response.send_message(
                "❌ Channel nicht gefunden.",
                ephemeral=True
            )
            return

        await channel.send(
            self.message.value
        )

        await interaction.response.send_message(
            "✅ Nachricht gesendet.",
            ephemeral=True
        )


class EmbedModal(discord.ui.Modal):

    def __init__(self, channel_id):
        super().__init__(
            title="Embed erstellen"
        )

        self.channel_id = channel_id

        self.title_input = discord.ui.TextInput(
            label="Titel",
            required=True,
            max_length=256
        )

        self.description = discord.ui.TextInput(
            label="Beschreibung",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=4000
        )

        self.add_item(self.title_input)
        self.add_item(self.description)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        channel = bot.get_channel(
            self.channel_id
        )

        if channel is None:
            await interaction.response.send_message(
                "❌ Channel nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=self.title_input.value,
            description=self.description.value,
            color=discord.Color.blurple()
        )

        await channel.send(
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Embed gesendet.",
            ephemeral=True
        )


class ClearMessagesModal(discord.ui.Modal):

    def __init__(self, channel_id):
        super().__init__(
            title="Nachrichten löschen"
        )

        self.channel_id = channel_id

        self.amount = discord.ui.TextInput(
            label="Anzahl",
            placeholder="z.B. 10",
            required=True,
            max_length=4
        )

        self.add_item(self.amount)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        channel = bot.get_channel(
            self.channel_id
        )

        if channel is None:
            await interaction.response.send_message(
                "❌ Channel nicht gefunden.",
                ephemeral=True
            )
            return

        try:
            amount = int(
                self.amount.value
            )
        except ValueError:
            await interaction.response.send_message(
                "❌ Bitte eine gültige Zahl eingeben.",
                ephemeral=True
            )
            return

        amount = max(
            1,
            min(amount, 100)
        )

        try:
            deleted = await channel.purge(
                limit=amount
            )

            await interaction.response.send_message(
                f"🧹 {len(deleted)} Nachrichten gelöscht.",
                ephemeral=True
            )

        except Exception as error:
            print(
                "❌ Nachrichten löschen:",
                error
            )

            await interaction.response.send_message(
                "❌ Nachrichten konnten nicht gelöscht werden.",
                ephemeral=True
            )


# =========================================================
# CHANNEL SELECTS
# =========================================================

class AnnouncementChannelSelect(
    discord.ui.ChannelSelect
):

    def __init__(self):
        super().__init__(
            placeholder="Channel für Ankündigung auswählen",
            channel_types=[discord.ChannelType.text],
            custom_id="owner_select_announcement"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        channel = self.values[0]

        await interaction.response.send_modal(
            AnnouncementModal(channel.id)
        )


class SayChannelSelect(
    discord.ui.ChannelSelect
):

    def __init__(self):
        super().__init__(
            placeholder="Channel auswählen",
            channel_types=[discord.ChannelType.text],
            custom_id="owner_select_say"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        channel = self.values[0]

        await interaction.response.send_modal(
            SayModal(channel.id)
        )


class EmbedChannelSelect(
    discord.ui.ChannelSelect
):

    def __init__(self):
        super().__init__(
            placeholder="Channel für Embed auswählen",
            channel_types=[discord.ChannelType.text],
            custom_id="owner_select_embed"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        channel = self.values[0]

        await interaction.response.send_modal(
            EmbedModal(channel.id)
        )


class ClearChannelSelect(
    discord.ui.ChannelSelect
):

    def __init__(self):
        super().__init__(
            placeholder="Channel zum Löschen auswählen",
            channel_types=[discord.ChannelType.text],
            custom_id="owner_select_clear"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        channel = self.values[0]

        await interaction.response.send_modal(
            ClearMessagesModal(channel.id)
        )


class LockChannelSelect(
    discord.ui.ChannelSelect
):

    def __init__(self):
        super().__init__(
            placeholder="Channel zum Sperren auswählen",
            channel_types=[discord.ChannelType.text],
            custom_id="owner_select_lock"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        channel = self.values[0]

        try:
            overwrite = channel.overwrites_for(
                interaction.guild.default_role
            )

            overwrite.send_messages = False

            await channel.set_permissions(
                interaction.guild.default_role,
                overwrite=overwrite
            )

            await interaction.response.send_message(
                f"🔒 {channel.mention} wurde gesperrt.",
                ephemeral=True
            )

        except Exception as error:
            print("❌ Channel sperren:", error)

            await interaction.response.send_message(
                "❌ Channel konnte nicht gesperrt werden.",
                ephemeral=True
            )


class UnlockChannelSelect(
    discord.ui.ChannelSelect
):

    def __init__(self):
        super().__init__(
            placeholder="Channel zum Entsperren auswählen",
            channel_types=[discord.ChannelType.text],
            custom_id="owner_select_unlock"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        channel = self.values[0]

        try:
            overwrite = channel.overwrites_for(
                interaction.guild.default_role
            )

            overwrite.send_messages = None

            await channel.set_permissions(
                interaction.guild.default_role,
                overwrite=overwrite
            )

            await interaction.response.send_message(
                f"🔓 {channel.mention} wurde entsperrt.",
                ephemeral=True
            )

        except Exception as error:
            print("❌ Channel entsperren:", error)

            await interaction.response.send_message(
                "❌ Channel konnte nicht entsperrt werden.",
                ephemeral=True
            )


# =========================================================
# OWNER SELECT VIEWS
# =========================================================

class OwnerChannelSelectView(
    discord.ui.View
):

    def __init__(self, select):
        super().__init__(
            timeout=60
        )

        self.add_item(select)


# =========================================================
# OWNER PANEL
# =========================================================

class OwnerPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    async def owner_check(
        self,
        interaction: discord.Interaction
    ):

        role = interaction.guild.get_role(
            OWNER_ROLE_ID
        )

        if role is None:
            return False

        return role in interaction.user.roles


    @discord.ui.button(
        label="Ankündigung",
        style=discord.ButtonStyle.primary,
        emoji="📢",
        custom_id="owner_announcement"
    )
    async def announcement(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not await self.owner_check(interaction):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "📢 Wähle den Channel:",
            view=OwnerChannelSelectView(
                AnnouncementChannelSelect()
            ),
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
        button: discord.ui.Button
    ):

        if not await self.owner_check(interaction):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "💬 Wähle den Channel:",
            view=OwnerChannelSelectView(
                SayChannelSelect()
            ),
            ephemeral=True
        )


    @discord.ui.button(
        label="Embed erstellen",
        style=discord.ButtonStyle.success,
        emoji="✨",
        custom_id="owner_embed"
    )
    async def embed(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not await self.owner_check(interaction):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "✨ Wähle den Channel:",
            view=OwnerChannelSelectView(
                EmbedChannelSelect()
            ),
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
        button: discord.ui.Button
    ):

        if not await self.owner_check(interaction):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🧹 Wähle den Channel:",
            view=OwnerChannelSelectView(
                ClearChannelSelect()
            ),
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
        button: discord.ui.Button
    ):

        if not await self.owner_check(interaction):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🔒 Wähle den Channel:",
            view=OwnerChannelSelectView(
                LockChannelSelect()
            ),
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
        button: discord.ui.Button
    ):

        if not await self.owner_check(interaction):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🔓 Wähle den Channel:",
            view=OwnerChannelSelectView(
                UnlockChannelSelect()
            ),
            ephemeral=True
        )


    @discord.ui.button(
        label="Quiz starten",
        style=discord.ButtonStyle.primary,
        emoji="🎮",
        custom_id="owner_quiz_start"
    )
    async def quiz_start(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not await self.owner_check(interaction):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        await send_quiz_question()

        await interaction.response.send_message(
            "🎮 Quiz wurde gestartet.",
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
        button: discord.ui.Button
    ):

        if not await self.owner_check(interaction):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        channel = bot.get_channel(
            QUIZ_CHANNEL_ID
        )

        if channel and quiz_state["message_id"]:

            try:
                old_message = await channel.fetch_message(
                    quiz_state["message_id"]
                )

                await old_message.delete()

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
        button: discord.ui.Button
    ):

        if not await self.owner_check(interaction):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        latency = round(
            bot.latency * 1000
        )

        embed = discord.Embed(
            title="📊 Bot Status",
            color=discord.Color.green()
        )

        embed.add_field(
            name="🤖 Bot",
            value=str(bot.user),
            inline=False
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
        button: discord.ui.Button
    ):

        if not await self.owner_check(interaction):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        guild = interaction.guild

        embed = discord.Embed(
            title="🌐 Serverinfo",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="📛 Server",
            value=guild.name,
            inline=False
        )

        embed.add_field(
            name="👥 Mitglieder",
            value=str(guild.member_count),
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
            name="🔊 Sprachkanäle",
            value=str(
                len(guild.voice_channels)
            ),
            inline=True
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


async def update_owner_panel():

    role = None

    guild = bot.get_guild(
        GUILD_ID
    )

    if guild:
        role = guild.get_role(
            OWNER_ROLE_ID
        )

    channel = None

    # Existing panel is searched in all text channels.
    # No new panel is created automatically in a random channel.
    if guild:

        for text_channel in guild.text_channels:

            try:
                message = await find_panel_message(
                    text_channel,
                    OWNER_PANEL_MARKER
                )

                if message:
                    channel = text_channel

                    embed = discord.Embed(
                        title="👑 Owner Control Center",
                        description=(
                            "Verwaltung des Servers über dieses Panel.\n\n"
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

                    embed.set_footer(
                        text=OWNER_PANEL_MARKER
                    )

                    await message.edit(
                        embed=embed,
                        view=OwnerPanelView()
                    )

            except Exception as error:
                print(
                    "❌ Owner Panel Suche:",
                    error
                )

    return channel


# =========================================================
# COMMANDS
# =========================================================

@bot.command()
async def ping(ctx):

    latency = round(
        bot.latency * 1000
    )

    await ctx.send(
        f"🏓 Pong! `{latency}ms`"
    )


@bot.command()
async def hilfe(ctx):

    embed = discord.Embed(
        title="📚 Hilfe",
        description=(
            "**Öffentliche Commands**\n\n"
            "`!ping` — Bot-Status und Ping\n"
            "`!hilfe` — Diese Hilfe\n\n"
            "Weitere Funktionen befinden sich "
            "direkt in den jeweiligen Panels."
        ),
        color=discord.Color.blurple()
    )

    await ctx.send(
        embed=embed
    )


@bot.command()
@commands.has_role(OWNER_ROLE_ID)
async def ownerpanel(ctx):

    embed = discord.Embed(
        title="👑 Owner Control Center",
        description=(
            "Verwaltung des Servers über dieses Panel.\n\n"
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

    embed.set_footer(
        text=OWNER_PANEL_MARKER
    )

    await ctx.send(
        embed=embed,
        view=OwnerPanelView()
    )


@bot.command()
@commands.has_role(OWNER_ROLE_ID)
async def owner(ctx):

    await ownerpanel(
        ctx
    )


@bot.command()
async def nametag(ctx):

    await update_nametag_panel()

    await ctx.send(
        "🏷️ Das Nametag-Panel wurde aktualisiert.",
        delete_after=5
    )


@bot.command()
async def kennzeichen(ctx):

    await update_license_plate_panel()

    await ctx.send(
        "🚗 Das Kennzeichen-Panel wurde aktualisiert.",
        delete_after=5
    )


@bot.command()
async def schicht(ctx):

    await update_shift_panel()

    await ctx.send(
        "🛠️ Das Schicht-Panel wurde aktualisiert.",
        delete_after=5
    )


@bot.command()
async def bewerbung(ctx):

    await update_application_panel()

    await ctx.send(
        "📨 Das Bewerbungs-Panel wurde aktualisiert.",
        delete_after=5
    )


@bot.command()
@commands.has_role(SHIFT_PERMISSION_ROLE_ID)
async def devtask(ctx):

    await update_dev_task_panel()

    await ctx.send(
        "🛠️ Das Entwickler-Aufgaben-Panel wurde aktualisiert.",
        delete_after=5
    )


# =========================================================
# VOICE SUPPORT
# =========================================================

@bot.event
async def on_voice_state_update(
    member,
    before,
    after
):

    if before.channel == after.channel:
        return

    support_channel = bot.get_channel(
        SUPPORT_VOICE_CHANNEL_ID
    )

    log_channel = bot.get_channel(
        SUPPORT_LOG_CHANNEL_ID
    )

    if support_channel is None:
        return

    if (
        after.channel
        and after.channel.id == SUPPORT_VOICE_CHANNEL_ID
    ):

        if log_channel:

            await log_channel.send(
                f"🔊 **Support beigetreten**\n"
                f"{member.mention}"
            )

    elif (
        before.channel
        and before.channel.id == SUPPORT_VOICE_CHANNEL_ID
    ):

        if log_channel:

            await log_channel.send(
                f"🔇 **Support verlassen**\n"
                f"{member.mention}"
            )


# =========================================================
# QUIZ CLEANUP
# =========================================================

@tasks.loop(seconds=5)
async def quiz_cleanup():

    # Dieser Loop löscht KEINE normalen User-Nachrichten.
    # Nachrichten werden direkt in on_message nach 6 Sekunden gelöscht.

    try:
        await ensure_quiz()

    except Exception as error:
        print(
            "❌ Quiz-Überprüfung:",
            error
        )


# =========================================================
# MESSAGE HANDLER
# =========================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # =====================================================
    # EMOJI QUIZ
    # =====================================================

    if message.channel.id == QUIZ_CHANNEL_ID:

        # Jede normale User-Nachricht im Quiz-Kanal
        # bleibt genau 6 Sekunden sichtbar.
        async def delete_user_message():

            await asyncio.sleep(6)

            try:
                await message.delete()

            except Exception:
                pass

        asyncio.create_task(
            delete_user_message()
        )

        content = message.content.strip().lower()

        # -------------------------------------------------
        # Falsche Antwort
        # -------------------------------------------------

        current_answer = quiz_state.get(
            "answer"
        )

        if (
            not current_answer
            or content != current_answer
        ):

            try:

                result = await message.channel.send(
                    f"❌ **{message.author.mention}**, "
                    f"das war leider falsch! 😄"
                )

                async def delete_result():

                    await asyncio.sleep(4)

                    try:
                        await result.delete()
                    except Exception:
                        pass

                asyncio.create_task(
                    delete_result()
                )

            except Exception as error:
                print(
                    "❌ Quiz Falsch-Antwort:",
                    error
                )

            return

        # -------------------------------------------------
        # Richtige Antwort
        # -------------------------------------------------

        async with quiz_lock:

            # Noch einmal prüfen, damit nicht zwei
            # Personen gleichzeitig gewinnen.
            if (
                quiz_state.get("answer") != current_answer
                or not quiz_state.get("message_id")
            ):
                return

            answer = quiz_state["answer"]

            quiz_message_id = (
                quiz_state["message_id"]
            )

            # Runde sofort sperren
            quiz_state["message_id"] = None
            quiz_state["answer"] = None

        # Quizfrage löschen
        quiz_message = None

        try:

            quiz_message = await message.channel.fetch_message(
                quiz_message_id
            )

            await quiz_message.delete()

        except Exception:
            pass

        # Antwort des Bots
        try:

            result = await message.channel.send(
                f"🎉 **{message.author.mention}** "
                f"hat richtig geantwortet! 🏆\n"
                f"Die Antwort war **{answer.title()}**!"
            )

            # Bot-Antwort bleibt 4 Sekunden
            await asyncio.sleep(4)

            try:
                await result.delete()
            except Exception:
                pass

        except Exception as error:

            print(
                "❌ Quiz Richtige-Antwort:",
                error
            )

        # Neue Runde starten
        await send_quiz_question()

        return

    # =====================================================
    # NORMALE COMMANDS
    # =====================================================

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
        commands.MissingRole
    ):

        await ctx.send(
            "❌ Du hast keine Berechtigung für diesen Command.",
            delete_after=5
        )

        return

    if isinstance(
        error,
        commands.MissingPermissions
    ):

        await ctx.send(
            "❌ Du hast nicht die nötigen Berechtigungen.",
            delete_after=5
        )

        return

    print(
        "❌ Command Fehler:",
        error
    )


# =========================================================
# UPDATE ALL PANELS
# =========================================================

views_registered = False


async def update_all_panels():

    print(
        "🔄 Aktualisiere alle Panels..."
    )

    try:
        await update_nametag_panel()

        print(
            "✅ Nametag Panel aktualisiert."
        )

    except Exception as error:
        print(
            "❌ Nametag Panel:",
            error
        )

    try:
        await update_license_plate_panel()

        print(
            "✅ Kennzeichen Panel aktualisiert."
        )

    except Exception as error:
        print(
            "❌ Kennzeichen Panel:",
            error
        )

    try:
        await update_shift_panel()

        print(
            "✅ Schicht Panel aktualisiert."
        )

    except Exception as error:
        print(
            "❌ Schicht Panel:",
            error
        )

    try:
        await update_application_panel()

        print(
            "✅ Bewerbungs Panel aktualisiert."
        )

    except Exception as error:
        print(
            "❌ Bewerbungs Panel:",
            error
        )

    try:
        await update_dev_task_panel()

        print(
            "✅ Dev-Aufgaben Panel aktualisiert."
        )

    except Exception as error:
        print(
            "❌ Dev-Aufgaben Panel:",
            error
        )

    try:
        await update_owner_panel()

        print(
            "✅ OwnerPanel aktualisiert."
        )

    except Exception as error:
        print(
            "❌ OwnerPanel:",
            error
        )

    print(
        "🟢 Alle Panels wurden aktualisiert."
    )


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    global views_registered

    print(
        f"✅ Eingeloggt als "
        f"{bot.user} ({bot.user.id})"
    )

    if not views_registered:

        bot.add_view(
            NametagView()
        )

        bot.add_view(
            LicensePlateView()
        )

        bot.add_view(
            ShiftView()
        )

        bot.add_view(
            ApplicationView()
        )

        bot.add_view(
            DeveloperTaskView()
        )

        bot.add_view(
            OwnerPanelView()
        )

        views_registered = True

        print(
            "✅ Permanente Buttons registriert."
        )

    # =====================================================
    # WICHTIG:
    # KEINE Nametag-Änderung beim Start
    # KEINE automatische Rollenvergabe
    # KEINE Wiederherstellung aktiver Schichten
    # =====================================================

    await update_all_panels()

    # Emoji Quiz sicherstellen
    await ensure_quiz()

    if not quiz_cleanup.is_running():

        quiz_cleanup.start()

    print(
        "🟢 Bot ist vollständig bereit."
    )


# =========================================================
# START
# =========================================================

if not TOKEN:

    print(
        "❌ DISCORD_TOKEN wurde nicht gefunden!"
    )

else:

    bot.run(
        TOKEN
    )
