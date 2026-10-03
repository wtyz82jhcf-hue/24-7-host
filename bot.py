import os
import json
import random
import asyncio
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput

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

# GENAUER NAMETAG
NAMETAG = "RLP | "

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

views_registered = False

quiz_lock = asyncio.Lock()

quiz_message_id = None
quiz_answer = None
quiz_starting = False


# =========================================================
# DATA
# =========================================================

def load_data():

    if not os.path.exists(DATA_FILE):
        return {
            "license_plates": {},
            "developer_tasks": {},
            "nametags": {}
        }

    try:

        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        data.setdefault("license_plates", {})
        data.setdefault("developer_tasks", {})
        data.setdefault("nametags", {})

        return data

    except Exception:

        return {
            "license_plates": {},
            "developer_tasks": {},
            "nametags": {}
        }


data = load_data()


def save_data():

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )


# =========================================================
# HELPER
# =========================================================

def has_role(member, role_id):

    return any(
        role.id == role_id
        for role in member.roles
    )


async def get_channel(channel_id):

    channel = bot.get_channel(channel_id)

    if channel is not None:
        return channel

    try:
        return await bot.fetch_channel(channel_id)
    except Exception:
        return None


# =========================================================
# NAMETAG
# =========================================================

class NametagResetButton(Button):

    def __init__(self):

        super().__init__(
            label="Nametag entfernen",
            style=discord.ButtonStyle.danger,
            emoji="🔄",
            custom_id="nametag_reset_button"
        )

    async def callback(self, interaction: discord.Interaction):

        member = interaction.guild.get_member(
            interaction.user.id
        )

        if member is None:

            try:
                member = await interaction.guild.fetch_member(
                    interaction.user.id
                )

            except Exception:

                await interaction.response.send_message(
                    "❌ Dein Benutzer konnte nicht gefunden werden.",
                    ephemeral=True
                )

                return

        # -------------------------------------------------
        # AKTUELLEN NICKNAMEN HOLEN
        # -------------------------------------------------

        current_nick = member.nick

        # Falls kein Nickname vorhanden ist
        if current_nick is None:

            await interaction.response.send_message(
                "ℹ️ Du hast aktuell keinen Nicknamen mit Nametag.",
                ephemeral=True
            )

            return

        # -------------------------------------------------
        # ALLE MÖGLICHEN SCHREIBWEISEN VON RLP | ENTFERNEN
        # -------------------------------------------------

        new_name = current_nick

        prefixes = [
            "RLP | ",
            "RLP | ",
            "RLP |",
            "RLP| ",
            "RLP| ",
            "RLP|"
        ]

        found = False

        for prefix in prefixes:

            if new_name.startswith(prefix):

                new_name = new_name[len(prefix):]
                found = True
                break

        # -------------------------------------------------
        # ZUSÄTZLICHE SICHERHEIT
        # -------------------------------------------------

        if not found:

            # Falls normale Leerzeichen / NBSP vorhanden sind
            cleaned = new_name.replace("\u00a0", " ")

            if cleaned.startswith("RLP | "):

                new_name = cleaned[len("RLP | "):]
                found = True

            elif cleaned.startswith("RLP |"):

                new_name = cleaned[len("RLP |"):].lstrip()
                found = True

        # -------------------------------------------------
        # KEIN RLP GEFUNDEN
        # -------------------------------------------------

        if not found:

            await interaction.response.send_message(
                "ℹ️ Bei dir wurde kein `RLP | `-Nametag gefunden.",
                ephemeral=True
            )

            return

        # Leerzeichen am Anfang/Ende entfernen
        new_name = new_name.strip()

        # -------------------------------------------------
        # FALLS NAME LEER WÄRE
        # -------------------------------------------------

        if not new_name:

            new_name = member.name

        # -------------------------------------------------
        # NICKNAME ÄNDERN
        # -------------------------------------------------

        try:

            await member.edit(
                nick=new_name,
                reason="RLP | Nametag entfernt"
            )

            await interaction.response.send_message(
                f"✅ Dein Nametag wurde entfernt.\n"
                f"👤 Neuer Name: **{new_name}**",
                ephemeral=True
            )

            print(
                f"[NAMETAG] {member} -> {new_name}"
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Ich kann deinen Namen nicht ändern.\n\n"
                "Bitte überprüfe, ob die Bot-Rolle über "
                "den Member-Rollen steht.",
                ephemeral=True
            )

        except Exception as e:

            print(
                f"[NAMETAG FEHLER] {e}"
            )

            await interaction.response.send_message(
                "❌ Beim Entfernen des Nametags ist ein Fehler aufgetreten.",
                ephemeral=True
            )


class NametagView(View):

    def __init__(self):

        super().__init__(timeout=None)

        self.add_item(
            NametagResetButton()
        )


async def update_nametag_panel():

    channel = await get_channel(
        NAMETAG_CHANNEL_ID
    )

    if channel is None:
        return

    embed = discord.Embed(
        title="🏷️ Nametag",
        description=(
            "**RLP | Nametag entfernen**\n\n"
            "Wenn dein Name zum Beispiel so aussieht:\n\n"
            "👤 `RLP | RyZe`\n\n"
            "klicke unten auf den Button.\n\n"
            "Danach steht dort nur noch:\n\n"
            "👤 `RyZe`\n\n"
            "⚠️ Es wird dabei keine Rolle verändert."
        ),
        color=discord.Color.blue()
    )

    embed.set_footer(
        text=NAMETAG_PANEL_MARKER
    )

    try:

        async for message in channel.history(
            limit=100
        ):

            if (
                message.author == bot.user
                and message.embeds
                and message.embeds[0].footer.text
                == NAMETAG_PANEL_MARKER
            ):

                await message.edit(
                    embed=embed,
                    view=NametagView()
                )

                return

    except Exception as e:

        print(
            f"[NAMETAG PANEL] {e}"
        )

    try:

        await channel.send(
            embed=embed,
            view=NametagView()
        )

    except Exception as e:

        print(
            f"[NAMETAG PANEL SEND] {e}"
        )


# =========================================================
# KENNZEICHEN
# =========================================================

class LicensePlateModal(
    Modal,
    title="Kennzeichen erstellen"
):

    plate = TextInput(
        label="Kennzeichen",
        placeholder="z. B. RLP 01",
        max_length=20,
        required=True
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        value = self.plate.value.strip().upper()

        parts = value.split()

        if len(parts) < 2:

            await interaction.response.send_message(
                "❌ Bitte gib ein Kennzeichen mit Nummer ein, "
                "z. B. `RLP 01`.",
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

        # Nummer global prüfen
        for existing_plate in data["license_plates"].values():

            existing_parts = (
                existing_plate.upper().split()
            )

            if (
                existing_parts
                and existing_parts[-1].isdigit()
                and existing_parts[-1] == number
            ):

                await interaction.response.send_message(
                    f"❌ Die Nummer **{number}** ist bereits vergeben.",
                    ephemeral=True
                )

                return

        user_id = str(
            interaction.user.id
        )

        if user_id in data["license_plates"]:

            await interaction.response.send_message(
                "❌ Du besitzt bereits ein Kennzeichen.",
                ephemeral=True
            )

            return

        data["license_plates"][user_id] = value

        save_data()

        await update_license_panel()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen **{value}** wurde gespeichert.",
            ephemeral=True
        )


class LicenseCreateButton(Button):

    def __init__(self):

        super().__init__(
            label="Kennzeichen erstellen",
            style=discord.ButtonStyle.success,
            emoji="🚗",
            custom_id="license_create_button"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        await interaction.response.send_modal(
            LicensePlateModal()
        )


class LicenseView(View):

    def __init__(self):

        super().__init__(timeout=None)

        self.add_item(
            LicenseCreateButton()
        )


async def update_license_panel():

    channel = await get_channel(
        LICENSE_PLATE_CHANNEL_ID
    )

    if channel is None:
        return

    lines = []

    for user_id, plate in data[
        "license_plates"
    ].items():

        try:

            user = await bot.fetch_user(
                int(user_id)
            )

            name = user.display_name

        except Exception:

            name = f"User {user_id}"

        lines.append(
            f"🚗 **{plate}** — {name}"
        )

    description = (
        "Noch keine Kennzeichen vergeben."
        if not lines
        else "\n".join(lines)
    )

    embed = discord.Embed(
        title="🚗 Kennzeichen",
        description=description,
        color=discord.Color.blue()
    )

    embed.set_footer(
        text=LICENSE_PANEL_MARKER
    )

    try:

        async for message in channel.history(
            limit=100
        ):

            if (
                message.author == bot.user
                and message.embeds
                and message.embeds[0].footer.text
                == LICENSE_PANEL_MARKER
            ):

                await message.edit(
                    embed=embed,
                    view=LicenseView()
                )

                return

    except Exception:
        pass

    await channel.send(
        embed=embed,
        view=LicenseView()
    )


# =========================================================
# BEWERBUNG
# =========================================================

class ApplicationModal(
    Modal,
    title="Bewerbung"
):

    name = TextInput(
        label="Name",
        placeholder="Dein Name",
        max_length=100,
        required=True
    )

    age = TextInput(
        label="Alter",
        placeholder="Dein Alter",
        max_length=3,
        required=True
    )

    reason = TextInput(
        label="Warum möchtest du ins Team?",
        placeholder="Schreibe etwas über dich...",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        channel = await get_channel(
            APPLICATION_CHANNEL_ID
        )

        if channel is None:

            await interaction.response.send_message(
                "❌ Bewerbungskanal wurde nicht gefunden.",
                ephemeral=True
            )

            return

        embed = discord.Embed(
            title="📨 Neue Bewerbung",
            color=discord.Color.orange()
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
            name="📝 Grund",
            value=self.reason.value,
            inline=False
        )

        embed.set_author(
            name=str(interaction.user),
            icon_url=interaction.user.display_avatar.url
        )

        await channel.send(
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
            emoji="📨",
            custom_id="application_button"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        await interaction.response.send_modal(
            ApplicationModal()
        )


class ApplicationView(View):

    def __init__(self):

        super().__init__(timeout=None)

        self.add_item(
            ApplicationButton()
        )


async def update_application_panel():

    channel = await get_channel(
        APPLICATION_CHANNEL_ID
    )

    if channel is None:
        return

    embed = discord.Embed(
        title="📨 Team-Bewerbung",
        description=(
            "Du möchtest Teil des Teams werden?\n\n"
            "Klicke auf **Bewerben** und fülle das Formular aus."
        ),
        color=discord.Color.green()
    )

    embed.set_footer(
        text=APPLICATION_PANEL_MARKER
    )

    try:

        async for message in channel.history(
            limit=100
        ):

            if (
                message.author == bot.user
                and message.embeds
                and message.embeds[0].footer.text
                == APPLICATION_PANEL_MARKER
            ):

                await message.edit(
                    embed=embed,
                    view=ApplicationView()
                )

                return

    except Exception:
        pass

    await channel.send(
        embed=embed,
        view=ApplicationView()
    )


# =========================================================
# ENTWICKLER AUFGABEN
# =========================================================

class DeveloperTaskModal(
    Modal,
    title="Entwickler-Aufgabe"
):

    task = TextInput(
        label="Aufgabe",
        placeholder="Was soll erledigt werden?",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        if not has_role(
            interaction.user,
            SHIFT_PERMISSION_ROLE_ID
        ):

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung dafür.",
                ephemeral=True
            )

            return

        task_id = str(
            len(data["developer_tasks"]) + 1
        )

        data["developer_tasks"][task_id] = {
            "task": self.task.value,
            "author": interaction.user.id,
            "status": "Offen"
        }

        save_data()

        channel = await get_channel(
            DEVELOPER_TASK_CHANNEL_ID
        )

        if channel:

            embed = discord.Embed(
                title=f"🛠️ Entwickler-Aufgabe #{task_id}",
                description=self.task.value,
                color=discord.Color.orange()
            )

            embed.add_field(
                name="👤 Erstellt von",
                value=interaction.user.mention,
                inline=False
            )

            embed.add_field(
                name="📌 Status",
                value="Offen",
                inline=False
            )

            await channel.send(
                embed=embed
            )

        await interaction.response.send_message(
            f"✅ Aufgabe **#{task_id}** wurde erstellt.",
            ephemeral=True
        )


class DeveloperTaskButton(Button):

    def __init__(self):

        super().__init__(
            label="Aufgabe erstellen",
            style=discord.ButtonStyle.primary,
            emoji="🛠️",
            custom_id="developer_task_button"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

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

        self.add_item(
            DeveloperTaskButton()
        )


async def update_developer_task_panel():

    channel = await get_channel(
        DEVELOPER_TASK_CHANNEL_ID
    )

    if channel is None:
        return

    embed = discord.Embed(
        title="🛠️ Entwickler-Aufgaben",
        description="Erstelle hier eine neue Entwickler-Aufgabe.",
        color=discord.Color.orange()
    )

    embed.set_footer(
        text=DEV_TASK_PANEL_MARKER
    )

    try:

        async for message in channel.history(
            limit=100
        ):

            if (
                message.author == bot.user
                and message.embeds
                and message.embeds[0].footer.text
                == DEV_TASK_PANEL_MARKER
            ):

                await message.edit(
                    embed=embed,
                    view=DeveloperTaskView()
                )

                return

    except Exception:
        pass

    await channel.send(
        embed=embed,
        view=DeveloperTaskView()
    )


# =========================================================
# ENTWICKLER DIENST
# =========================================================

class DeveloperShiftStartButton(Button):

    def __init__(self):

        super().__init__(
            label="Dienst starten",
            style=discord.ButtonStyle.success,
            emoji="🟢",
            custom_id="developer_shift_start"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        member = interaction.guild.get_member(
            interaction.user.id
        )

        if (
            member is None
            or not has_role(
                member,
                SHIFT_PERMISSION_ROLE_ID
            )
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
                "❌ Dienstrolle nicht gefunden.",
                ephemeral=True
            )

            return

        if role in member.roles:

            await interaction.response.send_message(
                "ℹ️ Du bist bereits im Dienst.",
                ephemeral=True
            )

            return

        try:

            await member.add_roles(
                role,
                reason="Entwicklerdienst gestartet"
            )

            log_channel = await get_channel(
                SHIFT_LOG_CHANNEL_ID
            )

            if log_channel:

                await log_channel.send(
                    f"🟢 **Entwicklerdienst gestartet**\n"
                    f"👤 {member.mention}"
                )

            await interaction.response.send_message(
                "🟢 Dein Entwicklerdienst wurde gestartet.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Ich kann die Dienstrolle nicht vergeben.",
                ephemeral=True
            )


class DeveloperShiftEndButton(Button):

    def __init__(self):

        super().__init__(
            label="Dienst beenden",
            style=discord.ButtonStyle.danger,
            emoji="🔴",
            custom_id="developer_shift_end"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        member = interaction.guild.get_member(
            interaction.user.id
        )

        if (
            member is None
            or not has_role(
                member,
                SHIFT_PERMISSION_ROLE_ID
            )
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
                "❌ Dienstrolle nicht gefunden.",
                ephemeral=True
            )

            return

        if role not in member.roles:

            await interaction.response.send_message(
                "ℹ️ Du bist aktuell nicht im Dienst.",
                ephemeral=True
            )

            return

        try:

            await member.remove_roles(
                role,
                reason="Entwicklerdienst beendet"
            )

            log_channel = await get_channel(
                SHIFT_LOG_CHANNEL_ID
            )

            if log_channel:

                await log_channel.send(
                    f"🔴 **Entwicklerdienst beendet**\n"
                    f"👤 {member.mention}"
                )

            await interaction.response.send_message(
                "🔴 Dein Entwicklerdienst wurde beendet.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Ich kann die Dienstrolle nicht entfernen.",
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


async def update_shift_panel():

    channel = await get_channel(
        DEVELOPER_SHIFT_CHANNEL_ID
    )

    if channel is None:
        return

    embed = discord.Embed(
        title="🛠️ Entwicklerdienst",
        description=(
            "Nutze die Buttons unten, um deinen "
            "Entwicklerdienst zu starten oder zu beenden."
        ),
        color=discord.Color.blue()
    )

    embed.set_footer(
        text=SHIFT_PANEL_MARKER
    )

    try:

        async for message in channel.history(
            limit=100
        ):

            if (
                message.author == bot.user
                and message.embeds
                and message.embeds[0].footer.text
                == SHIFT_PANEL_MARKER
            ):

                await message.edit(
                    embed=embed,
                    view=DeveloperShiftView()
                )

                return

    except Exception:
        pass

    await channel.send(
        embed=embed,
        view=DeveloperShiftView()
    )


# =========================================================
# EMOJI QUIZ
# =========================================================

QUIZ_QUESTIONS = [

    ("🎉🥳🎈", "party"),
    ("🎂🎁🎉", "geburtstag"),
    ("🎄🎁🎅", "weihnachten"),
    ("🎃👻🕷️", "halloween"),

    ("🐶🦴", "hund"),
    ("🐱🐭", "katze"),
    ("🦁🌍", "löwe"),
    ("🐘🌿", "elefant"),
    ("🐼🎋", "panda"),
    ("🐵🍌", "affe"),
    ("🐸🌿", "frosch"),
    ("🐍🌿", "schlange"),

    ("🍕🧀🍅", "pizza"),
    ("🍔🍟🥤", "burger"),
    ("🌭🥫", "hotdog"),
    ("🍎🍏", "apfel"),
    ("🍌🍌", "banane"),
    ("🍓🍓", "erdbeere"),
    ("🍉☀️", "wassermelone"),
    ("🍦❄️", "eis"),

    ("☕🔥", "kaffee"),
    ("🥤🧊", "getränk"),
    ("🧃🍎", "saft"),

    ("🚗🛣️", "auto"),
    ("🚓🚨", "polizei"),
    ("🚑🏥", "rettungswagen"),
    ("🚒🔥", "feuerwehr"),
    ("🚌👥", "bus"),
    ("🚲🚴", "fahrrad"),
    ("✈️☁️", "flugzeug"),
    ("🚢🌊", "schiff"),
    ("🚆🛤️", "zug"),

    ("⚽🥅", "fußball"),
    ("🏀⛹️", "basketball"),
    ("🎾🥎", "tennis"),
    ("🏎️🏁", "rennen"),
    ("🏊🌊", "schwimmen"),

    ("☀️😎", "sommer"),
    ("❄️⛄", "winter"),
    ("🍂🍁", "herbst"),
    ("🌸🌱", "frühling"),

    ("🌧️☔", "regen"),
    ("❄️🌨️", "schnee"),
    ("🌩️⚡", "gewitter"),
    ("🌈☀️", "regenbogen"),

    ("👨‍⚕️🏥", "arzt"),
    ("👨‍🚒🔥", "feuerwehr"),
    ("👮🚓", "polizist"),
    ("👨‍🍳🍳", "koch"),
    ("👨‍🏫📚", "lehrer"),

    ("📱💬", "handy"),
    ("💻⌨️", "computer"),
    ("📚✏️", "schule"),
    ("🔑🚪", "schlüssel"),
    ("⏰🕐", "uhr"),

    ("❤️🥰", "liebe"),
    ("😂🤣", "lachen"),
    ("😢😭", "traurig"),
    ("😡💢", "wut"),
    ("😴🛏️", "müde"),

    ("🇩🇪🦅", "deutschland"),
    ("🇫🇷🥐", "frankreich"),
    ("🇮🇹🍕", "italien"),
    ("🇺🇸🗽", "usa"),
    ("🇯🇵🗾", "japan")
]


async def send_quiz_question():

    global quiz_message_id
    global quiz_answer
    global quiz_starting

    async with quiz_lock:

        if quiz_message_id is not None:
            return

        if quiz_starting:
            return

        quiz_starting = True

        try:

            channel = await get_channel(
                QUIZ_CHANNEL_ID
            )

            if channel is None:
                return

            question, answer = random.choice(
                QUIZ_QUESTIONS
            )

            embed = discord.Embed(
                title="🎯 Emoji-Quiz",
                description=(
                    "Errate den Begriff!\n\n"
                    f"# {question}\n\n"
                    "💬 Schreibe deine Antwort in den Chat!"
                ),
                color=discord.Color.blurple()
            )

            message = await channel.send(
                embed=embed
            )

            quiz_message_id = message.id
            quiz_answer = answer.lower().strip()

        finally:

            quiz_starting = False


# =========================================================
# OWNER PANEL
# =========================================================

class OwnerAnnouncementModal(
    Modal,
    title="Ankündigung"
):

    text = TextInput(
        label="Nachricht",
        placeholder="Deine Ankündigung...",
        style=discord.TextStyle.paragraph,
        max_length=2000,
        required=True
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        if not has_role(
            interaction.user,
            OWNER_ROLE_ID
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        await interaction.channel.send(
            f"📢 **Ankündigung**\n\n{self.text.value}"
        )

        await interaction.response.send_message(
            "✅ Ankündigung gesendet.",
            ephemeral=True
        )


class OwnerAnnouncementButton(Button):

    def __init__(self):

        super().__init__(
            label="Ankündigung",
            style=discord.ButtonStyle.primary,
            emoji="📢",
            custom_id="owner_announcement"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        if not has_role(
            interaction.user,
            OWNER_ROLE_ID
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            OwnerAnnouncementModal()
        )


class OwnerBotSayModal(
    Modal,
    title="Bot Nachricht"
):

    text = TextInput(
        label="Nachricht",
        placeholder="Was soll der Bot sagen?",
        style=discord.TextStyle.paragraph,
        max_length=2000,
        required=True
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        if not has_role(
            interaction.user,
            OWNER_ROLE_ID
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        await interaction.channel.send(
            self.text.value
        )

        await interaction.response.send_message(
            "✅ Nachricht gesendet.",
            ephemeral=True
        )


class OwnerBotSayButton(Button):

    def __init__(self):

        super().__init__(
            label="Bot Say",
            style=discord.ButtonStyle.secondary,
            emoji="💬",
            custom_id="owner_bot_say"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        if not has_role(
            interaction.user,
            OWNER_ROLE_ID
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            OwnerBotSayModal()
        )


class OwnerStatusButton(Button):

    def __init__(self):

        super().__init__(
            label="Bot Status",
            style=discord.ButtonStyle.secondary,
            emoji="🤖",
            custom_id="owner_status"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        if not has_role(
            interaction.user,
            OWNER_ROLE_ID
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        guild = interaction.guild

        await interaction.response.send_message(
            f"🤖 **Bot ist online**\n\n"
            f"👥 Member: **{guild.member_count}**\n"
            f"📁 Channels: **{len(guild.channels)}**\n"
            f"🎭 Rollen: **{len(guild.roles)}**",
            ephemeral=True
        )


class OwnerServerInfoButton(Button):

    def __init__(self):

        super().__init__(
            label="Server Info",
            style=discord.ButtonStyle.secondary,
            emoji="📊",
            custom_id="owner_server_info"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        if not has_role(
            interaction.user,
            OWNER_ROLE_ID
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )

            return

        guild = interaction.guild

        embed = discord.Embed(
            title="📊 Server Informationen",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="🏠 Server",
            value=guild.name,
            inline=False
        )

        embed.add_field(
            name="👥 Member",
            value=str(guild.member_count),
            inline=True
        )

        embed.add_field(
            name="📁 Channels",
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


class OwnerPanelView(View):

    def __init__(self):

        super().__init__(timeout=None)

        self.add_item(
            OwnerAnnouncementButton()
        )

        self.add_item(
            OwnerBotSayButton()
        )

        self.add_item(
            OwnerStatusButton()
        )

        self.add_item(
            OwnerServerInfoButton()
        )


# =========================================================
# SUPPORT VOICE LOG
# =========================================================

@bot.event
async def on_voice_state_update(
    member,
    before,
    after
):

    log_channel = await get_channel(
        SUPPORT_LOG_CHANNEL_ID
    )

    if log_channel is None:
        return

    if (
        before.channel is None
        and after.channel is not None
        and after.channel.id == SUPPORT_VOICE_CHANNEL_ID
    ):

        await log_channel.send(
            f"🎧 {member.mention} ist dem Support-Warteraum beigetreten."
        )

    elif (
        before.channel is not None
        and after.channel is None
        and before.channel.id == SUPPORT_VOICE_CHANNEL_ID
    ):

        await log_channel.send(
            f"🚪 {member.mention} hat den Support-Warteraum verlassen."
        )


# =========================================================
# COMMANDS
# =========================================================

@bot.command()
async def ping(ctx):

    await ctx.send(
        f"🏓 Pong! `{round(bot.latency * 1000)}ms`",
        delete_after=5
    )


@bot.command()
@commands.has_role(OWNER_ROLE_ID)
async def ownerpanel(ctx):

    await ctx.send(
        embed=discord.Embed(
            title="👑 Owner Panel",
            description="Owner-Verwaltung des Bots.",
            color=discord.Color.gold()
        ),
        view=OwnerPanelView()
    )


@bot.command()
@commands.has_role(OWNER_ROLE_ID)
async def owner(ctx):

    await ctx.send(
        embed=discord.Embed(
            title="👑 Owner Panel",
            description="Owner-Verwaltung des Bots.",
            color=discord.Color.gold()
        ),
        view=OwnerPanelView()
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
            "❌ Du hast keine Berechtigung.",
            delete_after=5
        )

        return

    print(
        f"[COMMAND ERROR] {error}"
    )


# =========================================================
# MESSAGE / EMOJI QUIZ
# =========================================================

@bot.event
async def on_message(message):

    global quiz_message_id
    global quiz_answer

    if message.author.bot:
        return

    # -----------------------------------------------------
    # QUIZ CHANNEL
    # -----------------------------------------------------

    if message.channel.id == QUIZ_CHANNEL_ID:

        answer = message.content.strip().lower()

        # -------------------------------------------------
        # RICHTIGE ANTWORT
        # -------------------------------------------------

        if (
            quiz_answer is not None
            and answer == quiz_answer
        ):

            current_question_id = quiz_message_id

            quiz_message_id = None
            quiz_answer = None

            # Alte Frage löschen
            if current_question_id:

                try:

                    old_message = (
                        await message.channel.fetch_message(
                            current_question_id
                        )
                    )

                    await old_message.delete()

                except Exception:
                    pass

            # Antwort löschen
            try:
                await message.delete()
            except Exception:
                pass

            # Erfolg
            result = await message.channel.send(
                f"✅ **Richtig!** "
                f"{message.author.mention} hat es erraten!"
            )

            # 4 Sekunden stehen lassen
            await asyncio.sleep(4)

            try:
                await result.delete()
            except Exception:
                pass

            # Genau eine neue Frage
            await send_quiz_question()

            return

        # -------------------------------------------------
        # FALSCHE ANTWORT
        # -------------------------------------------------

        if quiz_answer is not None:

            try:
                await message.delete()
            except Exception:
                pass

            wrong = await message.channel.send(
                f"❌ **Falsch!** {message.author.mention}"
            )

            await asyncio.sleep(4)

            try:
                await wrong.delete()
            except Exception:
                pass

            return

        # -------------------------------------------------
        # KEINE FRAGE
        # -------------------------------------------------

        await asyncio.sleep(6)

        try:
            await message.delete()
        except Exception:
            pass

        return

    # Andere Commands weiterverarbeiten
    await bot.process_commands(message)


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    global views_registered

    print("========================================")
    print(f"🤖 Bot online: {bot.user}")
    print(f"🏠 Server: {len(bot.guilds)}")
    print("========================================")

    if not views_registered:

        bot.add_view(
            NametagView()
        )

        bot.add_view(
            LicenseView()
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

        views_registered = True

    # Panels
    try:
        await update_nametag_panel()
    except Exception as e:
        print(
            f"[NAMETAG PANEL ERROR] {e}"
        )

    try:
        await update_license_panel()
    except Exception as e:
        print(
            f"[LICENSE PANEL ERROR] {e}"
        )

    try:
        await update_application_panel()
    except Exception as e:
        print(
            f"[APPLICATION PANEL ERROR] {e}"
        )

    try:
        await update_developer_task_panel()
    except Exception as e:
        print(
            f"[DEV TASK PANEL ERROR] {e}"
        )

    try:
        await update_shift_panel()
    except Exception as e:
        print(
            f"[SHIFT PANEL ERROR] {e}"
        )

    # Quiz starten
    try:
        await send_quiz_question()
    except Exception as e:
        print(
            f"[QUIZ ERROR] {e}"
        )


# =========================================================
# START
# =========================================================

if not TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN wurde nicht gefunden."
    )


bot.run(TOKEN)
