import os
import json
import random
import asyncio

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

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "license_plates": {},
            "developer_tasks": []
        }

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        data.setdefault("license_plates", {})
        data.setdefault("developer_tasks", [])

        return data

    except Exception:
        return {
            "license_plates": {},
            "developer_tasks": []
        }


data = load_data()


def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# =========================================================
# HELPERS
# =========================================================

def has_role(member: discord.Member, role_id: int):
    return any(role.id == role_id for role in member.roles)


def get_channel(channel_id: int):
    return bot.get_channel(channel_id)


async def safe_delete(message):
    try:
        await message.delete()
    except Exception:
        pass


# =========================================================
# NAMETAG
# =========================================================

class NametagResetButton(Button):
    def __init__(self):
        super().__init__(
            label="Nametag entfernen",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_nametag_reset"
        )

    async def callback(self, interaction: discord.Interaction):

        member = interaction.guild.get_member(interaction.user.id)

        if member is None:
            await interaction.response.send_message(
                "❌ Mitglied konnte nicht gefunden werden.",
                ephemeral=True
            )
            return

        if not member.nick:
            await interaction.response.send_message(
                "ℹ️ Du hast aktuell keinen Nametag.",
                ephemeral=True
            )
            return

        old_nick = member.nick

        prefixes = [
            "RLP | ",
            "RLP |",
            "RLP| ",
            "RLP|",
            "RLP\u00a0|\u00a0",
            "RLP\u00a0| ",
            "RLP |\u00a0",
            "RLP|\u00a0"
        ]

        new_nick = old_nick

        for prefix in prefixes:
            if new_nick.startswith(prefix):
                new_nick = new_nick[len(prefix):]
                break

        if new_nick == old_nick:
            await interaction.response.send_message(
                "ℹ️ Ich konnte keinen `RLP |` Nametag in deinem Nickname finden.",
                ephemeral=True
            )
            return

        if not new_nick.strip():
            new_nick = None

        try:
            await member.edit(nick=new_nick, reason="Nametag entfernt")

            await interaction.response.send_message(
                "✅ Dein Nametag wurde entfernt.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich kann deinen Nickname nicht ändern. "
                "Prüfe, ob meine Rolle über deiner Rolle steht und ich "
                "`Nicknames verwalten` habe.",
                ephemeral=True
            )

        except Exception as e:
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

    async for message in channel.history(limit=50):

        if message.author == bot.user and message.embeds:
            if any(
                field.name == "Panel"
                and NAMETAG_PANEL_MARKER in field.value
                for field in message.embeds[0].fields
            ):
                return

    embed = discord.Embed(
        title="🏷️ Nametag",
        description=(
            "Hier kannst du deinen **Nametag entfernen**.\n\n"
            f"Dein Nametag besteht aus `{NAMETAG}`.\n\n"
            "Klicke auf den Button, um den Nametag von deinem "
            "Nickname zu entfernen."
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
# LICENSE PLATES
# =========================================================

class LicensePlateModal(Modal, title="Kennzeichen erstellen"):

    plate = TextInput(
        label="Kennzeichen",
        placeholder="z.B. RLP 01",
        required=True,
        max_length=30
    )

    async def on_submit(self, interaction: discord.Interaction):

        plate_value = self.plate.value.strip().upper()

        parts = plate_value.split()

        if len(parts) < 2:
            await interaction.response.send_message(
                "❌ Das Kennzeichen muss aus Präfix und Zahl bestehen.\n"
                "Beispiel: `RLP 01`",
                ephemeral=True
            )
            return

        number = parts[-1]

        if not number.isdigit():
            await interaction.response.send_message(
                "❌ Die letzte Angabe muss eine Zahl sein.",
                ephemeral=True
            )
            return

        for existing_plate in data["license_plates"].values():

            existing_parts = existing_plate.split()

            if existing_parts and existing_parts[-1] == number:
                await interaction.response.send_message(
                    f"❌ Die Nummer `{number}` ist bereits vergeben.",
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

        data["license_plates"][user_id] = plate_value
        save_data()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen **{plate_value}** wurde erstellt.",
            ephemeral=True
        )

        await update_license_panel()


class LicensePlateButton(Button):

    def __init__(self):
        super().__init__(
            label="Kennzeichen erstellen",
            emoji="🚗",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_license_create"
        )

    async def callback(self, interaction: discord.Interaction):

        user_id = str(interaction.user.id)

        if user_id in data["license_plates"]:
            await interaction.response.send_message(
                f"❌ Du hast bereits das Kennzeichen "
                f"`{data['license_plates'][user_id]}`.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(LicensePlateModal())


class LicensePlateView(View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(LicensePlateButton())


async def update_license_panel():

    channel = get_channel(LICENSE_PLATE_CHANNEL_ID)

    if channel is None:
        return

    panel_message = None

    async for message in channel.history(limit=100):

        if message.author == bot.user and message.embeds:

            for field in message.embeds[0].fields:

                if (
                    field.name == "Panel"
                    and LICENSE_PANEL_MARKER in field.value
                ):
                    panel_message = message
                    break

        if panel_message:
            break

    lines = []

    for user_id, plate in data["license_plates"].items():

        member = channel.guild.get_member(int(user_id))

        if member:
            name = member.display_name
        else:
            name = f"User {user_id}"

        lines.append(f"`{plate}` — **{name}**")

    if lines:
        description = "\n".join(lines)
    else:
        description = "Noch keine Kennzeichen vergeben."

    embed = discord.Embed(
        title="🚗 Kennzeichen",
        description=description,
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Panel",
        value=LICENSE_PANEL_MARKER,
        inline=False
    )

    if panel_message:

        try:
            await panel_message.edit(
                embed=embed,
                view=LicensePlateView()
            )
        except Exception:
            pass

    else:

        await channel.send(
            embed=embed,
            view=LicensePlateView()
        )


# =========================================================
# APPLICATIONS
# =========================================================

class ApplicationModal(Modal, title="Bewerbung"):

    name = TextInput(
        label="Name",
        placeholder="Dein Name",
        required=True,
        max_length=100
    )

    age = TextInput(
        label="Alter",
        placeholder="Dein Alter",
        required=True,
        max_length=3
    )

    reason = TextInput(
        label="Warum möchtest du ins Team?",
        placeholder="Schreibe etwas über dich...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):

        channel = get_channel(APPLICATION_CHANNEL_ID)

        if channel is None:
            await interaction.response.send_message(
                "❌ Bewerbungskanal wurde nicht gefunden.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📨 Neue Bewerbung",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
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
            name="Bewerber",
            value=interaction.user.mention,
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

        await channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Deine Bewerbung wurde abgeschickt.",
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

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ApplicationModal())


class ApplicationView(View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ApplicationButton())


async def update_application_panel():

    channel = get_channel(APPLICATION_CHANNEL_ID)

    if channel is None:
        return

    async for message in channel.history(limit=50):

        if message.author == bot.user and message.embeds:

            if any(
                field.name == "Panel"
                and APPLICATION_PANEL_MARKER in field.value
                for field in message.embeds[0].fields
            ):
                return

    embed = discord.Embed(
        title="📨 Bewerbung",
        description=(
            "Du möchtest dich bewerben?\n\n"
            "Klicke auf **Bewerben** und fülle das Formular aus."
        ),
        color=discord.Color.green()
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
# DEVELOPER TASKS
# =========================================================

class DeveloperTaskModal(Modal, title="Developer Aufgabe"):

    task = TextInput(
        label="Aufgabe",
        placeholder="Was soll erledigt werden?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):

        if not has_role(interaction.user, SHIFT_PERMISSION_ROLE_ID):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung dafür.",
                ephemeral=True
            )
            return

        task_data = {
            "user_id": interaction.user.id,
            "task": self.task.value,
            "created_at": discord.utils.utcnow().isoformat()
        }

        data["developer_tasks"].append(task_data)
        save_data()

        channel = get_channel(DEVELOPER_TASK_CHANNEL_ID)

        if channel:

            embed = discord.Embed(
                title="🛠️ Neue Developer Aufgabe",
                description=self.task.value,
                color=discord.Color.orange(),
                timestamp=discord.utils.utcnow()
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


class DeveloperTaskButton(Button):

    def __init__(self):
        super().__init__(
            label="Aufgabe erstellen",
            emoji="🛠️",
            style=discord.ButtonStyle.primary,
            custom_id="rlp_dev_task_button"
        )

    async def callback(self, interaction: discord.Interaction):

        if not has_role(interaction.user, SHIFT_PERMISSION_ROLE_ID):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung dafür.",
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

    channel = get_channel(DEVELOPER_TASK_CHANNEL_ID)

    if channel is None:
        return

    async for message in channel.history(limit=50):

        if message.author == bot.user and message.embeds:

            if any(
                field.name == "Panel"
                and DEV_TASK_PANEL_MARKER in field.value
                for field in message.embeds[0].fields
            ):
                return

    embed = discord.Embed(
        title="🛠️ Developer Aufgaben",
        description=(
            "Mit diesem Panel können berechtigte Mitglieder "
            "neue Developer-Aufgaben erstellen."
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
            emoji="▶️",
            style=discord.ButtonStyle.success,
            custom_id="rlp_dev_shift_start"
        )

    async def callback(self, interaction: discord.Interaction):

        if not has_role(interaction.user, SHIFT_PERMISSION_ROLE_ID):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung dafür.",
                ephemeral=True
            )
            return

        role = interaction.guild.get_role(DEVELOPER_SHIFT_ROLE_ID)

        if role is None:
            await interaction.response.send_message(
                "❌ Developer-Schichtrolle wurde nicht gefunden.",
                ephemeral=True
            )
            return

        if role in interaction.user.roles:
            await interaction.response.send_message(
                "ℹ️ Du bist bereits im Developer-Dienst.",
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
                "✅ Deine Developer-Schicht wurde gestartet.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich kann die Developer-Schichtrolle nicht vergeben.",
                ephemeral=True
            )


class DeveloperShiftEndButton(Button):

    def __init__(self):
        super().__init__(
            label="Schicht beenden",
            emoji="⏹️",
            style=discord.ButtonStyle.danger,
            custom_id="rlp_dev_shift_end"
        )

    async def callback(self, interaction: discord.Interaction):

        if not has_role(interaction.user, SHIFT_PERMISSION_ROLE_ID):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung dafür.",
                ephemeral=True
            )
            return

        role = interaction.guild.get_role(DEVELOPER_SHIFT_ROLE_ID)

        if role is None:
            await interaction.response.send_message(
                "❌ Developer-Schichtrolle wurde nicht gefunden.",
                ephemeral=True
            )
            return

        if role not in interaction.user.roles:
            await interaction.response.send_message(
                "ℹ️ Du bist aktuell nicht im Developer-Dienst.",
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
                "✅ Deine Developer-Schicht wurde beendet.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich kann die Developer-Schichtrolle nicht entfernen.",
                ephemeral=True
            )


class DeveloperShiftView(View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(DeveloperShiftStartButton())
        self.add_item(DeveloperShiftEndButton())


async def update_developer_shift_panel():

    channel = get_channel(DEVELOPER_SHIFT_CHANNEL_ID)

    if channel is None:
        return

    async for message in channel.history(limit=50):

        if message.author == bot.user and message.embeds:

            if any(
                field.name == "Panel"
                and SHIFT_PANEL_MARKER in field.value
                for field in message.embeds[0].fields
            ):
                return

    embed = discord.Embed(
        title="🛠️ Developer-Schicht",
        description=(
            "Hier kannst du deine Developer-Schicht starten "
            "oder beenden."
        ),
        color=discord.Color.blurple()
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
# EMOJI QUIZ
# =========================================================

QUIZ_QUESTIONS = [
    ("🎉🥳🎈", "party"),
    ("🎂🎁🎉", "geburtstag"),
    ("🎄🎁🎅", "weihnachten"),
    ("🎃👻🕷️", "halloween"),
    ("🐶🦴", "hund"),
    ("🐱🐟", "katze"),
    ("🐭🧀", "maus"),
    ("🐰🥕", "hase"),
    ("🦁👑", "löwe"),
    ("🐘🌍", "elefant"),
    ("🐸💧", "frosch"),
    ("🐵🍌", "affe"),
    ("🍕🧀", "pizza"),
    ("🍔🍟", "burger"),
    ("🌭", "hotdog"),
    ("🍎🍏", "apfel"),
    ("🍌", "banane"),
    ("🍓", "erdbeere"),
    ("🍉", "wassermelone"),
    ("🍇", "trauben"),
    ("🍩", "donut"),
    ("🍪", "keks"),
    ("🍦", "eis"),
    ("🍫", "schokolade"),
    ("☕", "kaffee"),
    ("🥤", "getränk"),
    ("🚗", "auto"),
    ("🚌", "bus"),
    ("🚑", "rettungswagen"),
    ("🚒", "feuerwehr"),
    ("🚓", "polizei"),
    ("✈️", "flugzeug"),
    ("🚢", "schiff"),
    ("🚲", "fahrrad"),
    ("⚽", "fußball"),
    ("🏀", "basketball"),
    ("🎾", "tennis"),
    ("🏊", "schwimmen"),
    ("🏆🥇", "sieger"),
    ("🌧️☔", "regen"),
    ("☀️😎", "sonne"),
    ("❄️⛄", "winter"),
    ("🌸🌷", "frühling"),
    ("🍂🍁", "herbst"),
    ("🏖️☀️", "sommer"),
    ("🇺🇸🗽", "usa"),
    ("🇩🇪🥨", "deutschland"),
    ("🇫🇷🥐", "frankreich"),
    ("🇮🇹🍕", "italien"),
    ("🏠🔑", "haus"),
    ("📱", "handy"),
    ("💻", "computer"),
    ("⌚", "uhr"),
    ("📚✏️", "schule"),
    ("👨‍⚕️🏥", "arzt"),
    ("👨‍🚒🔥", "feuerwehrmann"),
    ("👮🚓", "polizist"),
    ("👨‍🍳🍳", "koch"),
    ("😢💧", "traurig"),
    ("😂🤣", "lachen"),
    ("❤️", "liebe"),
    ("😡🔥", "wut"),
    ("😴🛏️", "schlafen")
]

quiz_message_id = None
quiz_answer = None
quiz_starting = False
quiz_lock = asyncio.Lock()
used_quiz_questions = set()


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

            emoji, answer = random.choice(available)

            used_quiz_questions.add(emoji)

            embed = discord.Embed(
                title="🧩 Emoji Quiz",
                description=(
                    f"**Was ist das?**\n\n"
                    f"# {emoji}\n\n"
                    "Schreibe deine Antwort in den Chat!"
                ),
                color=discord.Color.blurple()
            )

            message = await channel.send(embed=embed)

            quiz_message_id = message.id
            quiz_answer = answer.lower().strip()

        finally:
            quiz_starting = False


# =========================================================
# OWNER PANEL
# =========================================================

def is_owner(member: discord.Member):

    return has_role(member, OWNER_ROLE_ID)


class OwnerChannelSelect(View):

    def __init__(self, action: str):
        super().__init__(timeout=60)
        self.action = action

        self.select = ChannelSelect(
            placeholder="Wähle einen Textkanal...",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1
        )

        self.select.callback = self.channel_selected

        self.add_item(self.select)

    async def channel_selected(self, interaction: discord.Interaction):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        channel = self.select.values[0]

        if self.action == "announcement":

            await interaction.response.send_modal(
                AnnouncementModal(channel)
            )

        elif self.action == "say":

            await interaction.response.send_modal(
                BotSayModal(channel)
            )

        elif self.action == "lock":

            await interaction.response.defer(ephemeral=True)

            try:

                overwrite = channel.overwrites_for(
                    interaction.guild.default_role
                )

                overwrite.send_messages = False

                await channel.set_permissions(
                    interaction.guild.default_role,
                    overwrite=overwrite,
                    reason=f"Channel Lock von {interaction.user}"
                )

                await interaction.followup.send(
                    f"🔒 {channel.mention} wurde gesperrt.",
                    ephemeral=True
                )

            except discord.Forbidden:

                await interaction.followup.send(
                    "❌ Ich habe keine Berechtigung, diesen Kanal zu sperren.",
                    ephemeral=True
                )

            except Exception as e:

                await interaction.followup.send(
                    f"❌ Fehler: `{e}`",
                    ephemeral=True
                )

        elif self.action == "unlock":

            await interaction.response.defer(ephemeral=True)

            try:

                overwrite = channel.overwrites_for(
                    interaction.guild.default_role
                )

                overwrite.send_messages = None

                await channel.set_permissions(
                    interaction.guild.default_role,
                    overwrite=overwrite,
                    reason=f"Channel Unlock von {interaction.user}"
                )

                await interaction.followup.send(
                    f"🔓 {channel.mention} wurde entsperrt.",
                    ephemeral=True
                )

            except discord.Forbidden:

                await interaction.followup.send(
                    "❌ Ich habe keine Berechtigung, diesen Kanal zu entsperren.",
                    ephemeral=True
                )

            except Exception as e:

                await interaction.followup.send(
                    f"❌ Fehler: `{e}`",
                    ephemeral=True
                )


class AnnouncementModal(Modal):

    def __init__(self, channel):
        super().__init__(title="Ankündigung")
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

        self.add_item(self.title_input)
        self.add_item(self.message_input)

    async def on_submit(self, interaction: discord.Interaction):

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
                "❌ Ich kann in diesen Kanal nicht schreiben.",
                ephemeral=True
            )


class BotSayModal(Modal):

    def __init__(self, channel):
        super().__init__(title="Bot Say")
        self.channel = channel

        self.message_input = TextInput(
            label="Nachricht",
            placeholder="Was soll der Bot schreiben?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=4000
        )

        self.add_item(self.message_input)

    async def on_submit(self, interaction: discord.Interaction):

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
                "❌ Ich kann in diesen Kanal nicht schreiben.",
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

    async def callback(self, interaction: discord.Interaction):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "📢 Wähle den Kanal für die Ankündigung:",
            view=OwnerChannelSelect("announcement"),
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

    async def callback(self, interaction: discord.Interaction):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "💬 Wähle den Kanal, in dem der Bot schreiben soll:",
            view=OwnerChannelSelect("say"),
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

    async def callback(self, interaction: discord.Interaction):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🔒 Wähle den Kanal, der gesperrt werden soll:",
            view=OwnerChannelSelect("lock"),
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

    async def callback(self, interaction: discord.Interaction):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🔓 Wähle den Kanal, der entsperrt werden soll:",
            view=OwnerChannelSelect("unlock"),
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

    async def callback(self, interaction: discord.Interaction):

        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
                ephemeral=True
            )
            return

        latency = round(bot.latency * 1000)

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
            value=str(sum(g.member_count or 0 for g in bot.guilds)),
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

    async def callback(self, interaction: discord.Interaction):

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
            embed.set_thumbnail(url=guild.icon.url)

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


class OwnerPanelView(View):

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
            "Hier kannst du verschiedene Server- und Bot-Funktionen "
            "verwalten.\n\n"
            "📢 **Ankündigung** — Nachricht als Embed senden\n"
            "💬 **Bot Say** — Bot schreibt eine normale Nachricht\n"
            "🔒 **Channel Lock** — Kanal für @everyone sperren\n"
            "🔓 **Channel Unlock** — Kanal wieder entsperren\n"
            "📊 **Bot Status** — Bot-Informationen anzeigen\n"
            "🖥️ **Server Info** — Serverinformationen anzeigen"
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
# SUPPORT VOICE LOG
# =========================================================

@bot.event
async def on_voice_state_update(
    member: discord.Member,
    before: discord.VoiceState,
    after: discord.VoiceState
):

    log_channel = get_channel(SUPPORT_LOG_CHANNEL_ID)

    if log_channel is None:
        return

    support_channel = get_channel(SUPPORT_VOICE_CHANNEL_ID)

    if support_channel is None:
        return

    if before.channel != support_channel and after.channel == support_channel:

        await log_channel.send(
            f"🔊 **Support beigetreten**\n"
            f"👤 {member.mention}\n"
            f"📍 {support_channel.mention}"
        )

    elif before.channel == support_channel and after.channel != support_channel:

        await log_channel.send(
            f"🔇 **Support verlassen**\n"
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


# =========================================================
# MESSAGE HANDLER
# =========================================================

@bot.event
async def on_message(message: discord.Message):

    global quiz_message_id
    global quiz_answer

    if message.author.bot:
        return

    # -------------------------
    # QUIZ
    # -------------------------

    if message.channel.id == QUIZ_CHANNEL_ID:

        # Wenn gerade keine Frage existiert,
        # normale Nachricht nach 6 Sekunden löschen.
        if quiz_answer is None:

            await asyncio.sleep(6)
            await safe_delete(message)

            return

        user_answer = message.content.strip().lower()

        # -------------------------
        # RICHTIG
        # -------------------------

        if user_answer == quiz_answer:

            current_question_id = quiz_message_id

            await safe_delete(message)

            if current_question_id:

                try:

                    question_message = await message.channel.fetch_message(
                        current_question_id
                    )

                    await safe_delete(question_message)

                except Exception:
                    pass

            quiz_message_id = None
            quiz_answer = None

            success_message = await message.channel.send(
                f"✅ **Richtig!** {message.author.mention}"
            )

            await asyncio.sleep(4)

            await safe_delete(success_message)

            await send_quiz_question()

            return

        # -------------------------
        # FALSCH
        # -------------------------

        await safe_delete(message)

        wrong_message = await message.channel.send(
            f"❌ **Falsch!** {message.author.mention}"
        )

        await asyncio.sleep(4)

        await safe_delete(wrong_message)

        return

    # Andere Nachrichten normal verarbeiten.
    await bot.process_commands(message)


# =========================================================
# ERROR HANDLER
# =========================================================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "❌ Du hast keine Berechtigung.",
            delete_after=5
        )
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            "❌ Es fehlt ein Argument.",
            delete_after=5
        )
        return

    print(f"Command Error: {error}")


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    print("====================================")
    print(f"Bot online: {bot.user}")
    print(f"Guilds: {len(bot.guilds)}")
    print("====================================")

    # Persistente Views registrieren
    bot.add_view(NametagView())
    bot.add_view(LicensePlateView())
    bot.add_view(ApplicationView())
    bot.add_view(DeveloperTaskView())
    bot.add_view(DeveloperShiftView())
    bot.add_view(OwnerPanelView())

    # Panels aktualisieren / erstellen
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

    # Quiz starten
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
