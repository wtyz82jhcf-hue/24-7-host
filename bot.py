import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import json
import os
import random
from datetime import datetime, timezone


# ============================================================
# KONFIGURATION
# ============================================================

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

# Schicht-Panel bleibt hier:
DEVELOPER_SHIFT_CHANNEL_ID = 1555923435056795648

# NEU: Schicht Start/Ende Logs gehen hier rein:
SHIFT_LOG_CHANNEL_ID = 1540797414863151155

NAMETAG_ROLE_ID = 1520102928398942348

SHIFT_PERMISSION_ROLE_ID = 1523674698574200904
DEVELOPER_SHIFT_ROLE_ID = 1527372148979798086

OWNER_ROLE_ID = 1544691379613999164

NAMETAG = "RLP "

DATA_FILE = "bot_data.json"


# ============================================================
# BOT
# ============================================================

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)


# ============================================================
# DATEN
# ============================================================

DEFAULT_DATA = {
    "quiz_scores": {},
    "license_plates": {},
    "nametag_original_names": {},
    "support_cases": 0,
    "developer_tasks": [],
    "shifts": {}
}


def load_data():
    if not os.path.exists(DATA_FILE):
        return DEFAULT_DATA.copy()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            loaded = json.load(file)

        for key, value in DEFAULT_DATA.items():
            if key not in loaded:
                loaded[key] = value.copy() if isinstance(value, (dict, list)) else value

        return loaded

    except Exception as error:
        print(f"Fehler beim Laden der Daten: {error}")
        return DEFAULT_DATA.copy()


data = load_data()


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

    except Exception as error:
        print(f"Fehler beim Speichern: {error}")


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def has_role(member: discord.Member, role_id: int):
    return any(role.id == role_id for role in member.roles)


def is_owner_role(member: discord.Member):
    return has_role(member, OWNER_ROLE_ID)


async def safe_send(channel, *args, **kwargs):
    if channel is None:
        return None

    try:
        return await channel.send(*args, **kwargs)
    except Exception as error:
        print(f"Fehler beim Senden: {error}")
        return None


async def get_channel(channel_id: int):
    channel = bot.get_channel(channel_id)

    if channel:
        return channel

    try:
        return await bot.fetch_channel(channel_id)
    except Exception:
        return None


# ============================================================
# EMOJI QUIZ
# ============================================================

QUIZ_QUESTIONS = [
    ("🇩🇪", "deutschland"),
    ("🇫🇷", "frankreich"),
    ("🇮🇹", "italien"),
    ("🇪🇸", "spanien"),
    ("🇵🇹", "portugal"),
    ("🇳🇱", "niederlande"),
    ("🇧🇪", "belgien"),
    ("🇦🇹", "österreich"),
    ("🇨🇭", "schweiz"),
    ("🇵🇱", "polen"),
    ("🇬🇷", "griechenland"),
    ("🇹🇷", "türkei"),
    ("🇺🇸", "usa"),
    ("🇨🇦", "kanada"),
    ("🇧🇷", "brasilien"),
    ("🇦🇷", "argentinien"),
    ("🇲🇽", "mexiko"),
    ("🇯🇵", "japan"),
    ("🇨🇳", "china"),
    ("🇮🇳", "indien"),
    ("🇦🇺", "australien"),
    ("🇸🇪", "schweden"),
    ("🇳🇴", "norwegen"),
    ("🇩🇰", "dänemark"),
    ("🇫🇮", "finnland"),
    ("🇮🇸", "island"),
    ("🇮🇪", "irland"),
    ("🇬🇧", "großbritannien"),

    ("🐶", "hund"),
    ("🐱", "katze"),
    ("🐭", "maus"),
    ("🐹", "hamster"),
    ("🐰", "hase"),
    ("🦊", "fuchs"),
    ("🐻", "bär"),
    ("🐼", "panda"),
    ("🐨", "koala"),
    ("🐯", "tiger"),
    ("🦁", "löwe"),
    ("🐮", "kuh"),
    ("🐷", "schwein"),
    ("🐸", "frosch"),
    ("🐵", "affe"),
    ("🐔", "huhn"),
    ("🐧", "pinguin"),
    ("🐦", "vogel"),
    ("🦆", "ente"),
    ("🦅", "adler"),
    ("🦉", "eule"),
    ("🐺", "wolf"),
    ("🐗", "wildschwein"),
    ("🐴", "pferd"),
    ("🦄", "einhorn"),
    ("🐝", "biene"),
    ("🦋", "schmetterling"),
    ("🐌", "schnecke"),
    ("🐞", "marienkäfer"),
    ("🐢", "schildkröte"),
    ("🐍", "schlange"),
    ("🦎", "eidechse"),
    ("🐙", "krake"),
    ("🦀", "krabbe"),
    ("🐬", "delfin"),
    ("🐳", "wal"),
    ("🦈", "hai"),

    ("🍎", "apfel"),
    ("🍐", "birne"),
    ("🍊", "orange"),
    ("🍋", "zitrone"),
    ("🍌", "banane"),
    ("🍉", "wassermelone"),
    ("🍇", "trauben"),
    ("🍓", "erdbeere"),
    ("🫐", "blaubeere"),
    ("🍒", "kirsche"),
    ("🍑", "pfirsich"),
    ("🥝", "kiwi"),
    ("🍅", "tomate"),
    ("🥑", "avocado"),
    ("🥕", "karotte"),
    ("🌽", "mais"),
    ("🥔", "kartoffel"),
    ("🍕", "pizza"),
    ("🍔", "burger"),
    ("🍟", "pommes"),
    ("🌭", "hotdog"),
    ("🍿", "popcorn"),
    ("🍩", "donut"),
    ("🍪", "keks"),
    ("🎂", "kuchen"),
    ("🍫", "schokolade"),
    ("🍦", "eis"),

    ("⚽", "fußball"),
    ("🏀", "basketball"),
    ("🏈", "football"),
    ("⚾", "baseball"),
    ("🎾", "tennis"),
    ("🏐", "volleyball"),
    ("🎱", "billard"),
    ("🏓", "tischtennis"),
    ("🥊", "boxen"),
    ("🏆", "pokal"),
    ("🚗", "auto"),
    ("🚕", "taxi"),
    ("🚌", "bus"),
    ("🚓", "polizei"),
    ("🚑", "krankenwagen"),
    ("🚒", "feuerwehr"),
    ("🚲", "fahrrad"),
    ("✈️", "flugzeug"),
    ("🚁", "hubschrauber"),
    ("🚀", "rakete"),
    ("🚢", "schiff"),

    ("☀️", "sonne"),
    ("🌙", "mond"),
    ("⭐", "stern"),
    ("🌈", "regenbogen"),
    ("☁️", "wolke"),
    ("❄️", "schnee"),
    ("🔥", "feuer"),
    ("💧", "wasser"),
    ("🌍", "erde"),
    ("❤️", "herz"),
    ("💎", "diamant"),
    ("👑", "krone"),
    ("🎮", "controller"),
    ("🎧", "kopfhörer"),
    ("📱", "handy"),
    ("💻", "laptop"),
    ("⌨️", "tastatur"),
    ("🖱️", "maus"),
    ("📷", "kamera"),
    ("🔑", "schlüssel"),
    ("🎁", "geschenk"),
    ("🎈", "ballon")
]


quiz_state = {
    "message_id": None,
    "answer": None,
    "round": 0
}

quiz_lock = asyncio.Lock()


async def send_quiz_question():
    channel = await get_channel(QUIZ_CHANNEL_ID)

    if channel is None:
        return

    emoji, answer = random.choice(QUIZ_QUESTIONS)

    quiz_state["round"] += 1
    quiz_state["answer"] = answer.lower()

    embed = discord.Embed(
        title="🎮 Emoji Quiz",
        description=(
            f"# {emoji}\n\n"
            "Welches Wort passt zu diesem Emoji?\n\n"
            "💬 Schreibe die richtige Antwort in den Chat!"
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=f"Runde #{quiz_state['round']} • Viel Glück!"
    )

    message = await channel.send(embed=embed)

    quiz_state["message_id"] = message.id


async def ensure_quiz():
    async with quiz_lock:
        channel = await get_channel(QUIZ_CHANNEL_ID)

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


@tasks.loop(seconds=5)
async def quiz_cleanup():
    channel = await get_channel(QUIZ_CHANNEL_ID)

    if channel is None:
        return

    active_message_id = quiz_state.get("message_id")

    try:
        async for message in channel.history(limit=100):

            if active_message_id and message.id == active_message_id:
                continue

            try:
                await message.delete()
            except Exception:
                pass

    except Exception as error:
        print(f"Quiz Cleanup Fehler: {error}")

    await ensure_quiz()


@quiz_cleanup.before_loop
async def before_quiz_cleanup():
    await bot.wait_until_ready()


# ============================================================
# NAMETAG
# ============================================================

async def apply_nametag(member: discord.Member):
    if not has_role(member, NAMETAG_ROLE_ID):
        return

    current_name = member.nick or member.name

    if current_name.startswith(NAMETAG):
        return

    user_id = str(member.id)

    if user_id not in data["nametag_original_names"]:
        data["nametag_original_names"][user_id] = member.nick

    new_name = f"{NAMETAG}{current_name}"

    try:
        await member.edit(
            nick=new_name[:32],
            reason="Nametag-Rolle vorhanden"
        )

        save_data()

    except discord.Forbidden:
        print(f"Keine Berechtigung für Nametag bei {member}")

    except Exception as error:
        print(f"Nametag Fehler: {error}")


async def remove_nametag(member: discord.Member):
    user_id = str(member.id)

    current_name = member.nick or member.name

    if not current_name.startswith(NAMETAG):
        data["nametag_original_names"].pop(user_id, None)
        save_data()
        return

    original = data["nametag_original_names"].get(user_id)

    try:
        if original is not None:
            await member.edit(
                nick=original,
                reason="Nametag-Rolle entfernt"
            )

        else:
            clean_name = current_name[len(NAMETAG):].strip()

            if clean_name == member.name:
                await member.edit(
                    nick=None,
                    reason="Nametag zurückgesetzt"
                )
            else:
                await member.edit(
                    nick=clean_name[:32],
                    reason="Nametag zurückgesetzt"
                )

        data["nametag_original_names"].pop(user_id, None)
        save_data()

    except discord.Forbidden:
        print(f"Keine Berechtigung zum Entfernen des Nametags bei {member}")

    except Exception as error:
        print(f"Nametag Entfernen Fehler: {error}")


async def reset_own_nametag(member: discord.Member):
    current_name = member.nick or member.name

    if not current_name.startswith(NAMETAG):
        return False

    user_id = str(member.id)

    original = data["nametag_original_names"].get(user_id)

    try:
        if original is not None:
            await member.edit(
                nick=original,
                reason="Nametag selbst zurückgesetzt"
            )
        else:
            clean_name = current_name[len(NAMETAG):].strip()

            if clean_name == member.name:
                await member.edit(
                    nick=None,
                    reason="Nametag selbst zurückgesetzt"
                )
            else:
                await member.edit(
                    nick=clean_name[:32],
                    reason="Nametag selbst zurückgesetzt"
                )

        data["nametag_original_names"].pop(user_id, None)
        save_data()

        return True

    except Exception:
        return False


class NametagView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Nametag zurücksetzen",
        emoji="🔄",
        style=discord.ButtonStyle.secondary,
        custom_id="nametag_reset"
    )
    async def reset_nametag_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "❌ Das funktioniert nur auf dem Server.",
                ephemeral=True
            )
            return

        success = await reset_own_nametag(interaction.user)

        if success:
            await interaction.response.send_message(
                "✅ Dein `RLP ` Nametag wurde zurückgesetzt.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "ℹ️ Du hast aktuell keinen `RLP ` Nametag.",
                ephemeral=True
            )


async def send_nametag_panel(channel):
    embed = discord.Embed(
        title="🏷️ Nametag System",
        description=(
            "Mit der Nametag-Rolle wird automatisch **RLP ** "
            "vor deinen Namen gesetzt.\n\n"
            "Der Bot **vergibt die Rolle nicht automatisch**.\n\n"
            "Mit dem Button kannst du deinen aktuellen "
            "`RLP ` Nametag zurücksetzen."
        ),
        color=discord.Color.blue()
    )

    embed.set_footer(text="RLP Nametag System")

    await channel.send(
        embed=embed,
        view=NametagView()
    )


# ============================================================
# KENNZEICHEN
# ============================================================

def normalize_plate(text: str):
    return " ".join(text.upper().strip().split())


def get_plate_number(plate: str):
    parts = plate.split()

    if len(parts) < 2:
        return None

    number = parts[-1]

    if not number.isdigit():
        return None

    return number


def find_user_by_plate_number(number: str):
    for user_id, plate in data["license_plates"].items():
        existing_number = get_plate_number(plate)

        if existing_number == number:
            return user_id

    return None


class LicensePlateModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Kennzeichen registrieren"
        )

        self.plate = discord.ui.TextInput(
            label="Kennzeichen",
            placeholder="z.B. RLP 01 oder RY ZE 02",
            required=True,
            max_length=20
        )

        self.add_item(self.plate)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)

        if user_id in data["license_plates"]:
            await interaction.response.send_message(
                f"❌ Du besitzt bereits das Kennzeichen "
                f"`{data['license_plates'][user_id]}`.\n"
                f"Lösche es zuerst.",
                ephemeral=True
            )
            return

        plate = normalize_plate(str(self.plate.value))

        number = get_plate_number(plate)

        if number is None:
            await interaction.response.send_message(
                "❌ Das Kennzeichen muss aus einem Präfix und "
                "einer Zahl bestehen.\n"
                "Beispiel: `RLP 01` oder `RY ZE 02`",
                ephemeral=True
            )
            return

        owner_id = find_user_by_plate_number(number)

        if owner_id is not None:
            await interaction.response.send_message(
                f"❌ Die Nummer `{number}` ist bereits vergeben.\n"
                "Bitte wähle eine andere Nummer.",
                ephemeral=True
            )
            return

        data["license_plates"][user_id] = plate
        save_data()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen `{plate}` wurde registriert.",
            ephemeral=True
        )

        await update_license_plate_panel()


class LicensePlateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Kennzeichen registrieren",
        emoji="🚘",
        style=discord.ButtonStyle.success,
        custom_id="license_plate_register"
    )
    async def register_plate(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            LicensePlateModal()
        )

    @discord.ui.button(
        label="Kennzeichen löschen",
        emoji="🗑️",
        style=discord.ButtonStyle.danger,
        custom_id="license_plate_delete"
    )
    async def delete_plate(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        user_id = str(interaction.user.id)

        if user_id not in data["license_plates"]:
            await interaction.response.send_message(
                "❌ Du hast kein Kennzeichen registriert.",
                ephemeral=True
            )
            return

        old_plate = data["license_plates"].pop(user_id)

        save_data()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen `{old_plate}` wurde gelöscht.\n"
            "Die Nummer ist jetzt wieder frei.",
            ephemeral=True
        )

        await update_license_plate_panel()


LICENSE_PANEL_MARKER = "RLP-KENNZEICHEN-PANEL"


def build_license_plate_embed():
    lines = []

    guild = bot.get_guild(GUILD_ID)

    sorted_plates = sorted(
        data["license_plates"].items(),
        key=lambda item: (
            int(get_plate_number(item[1]))
            if get_plate_number(item[1])
            and get_plate_number(item[1]).isdigit()
            else 999999
        )
    )

    for user_id, plate in sorted_plates:
        display_name = f"User {user_id}"

        if guild:
            member = guild.get_member(int(user_id))

            if member:
                display_name = member.display_name

        lines.append(
            f"`{plate}` — {display_name}"
        )

    if lines:
        plate_list = "\n".join(lines)
    else:
        plate_list = "*Noch keine Kennzeichen registriert.*"

    embed = discord.Embed(
        title="🚘 Kennzeichen Registrierung",
        description=(
            "Registriere dein persönliches Kennzeichen.\n\n"
            "**Regeln:**\n"
            "• Jeder Benutzer darf nur **ein Kennzeichen** besitzen.\n"
            "• Die letzte Zahl muss **serverweit einzigartig** sein.\n"
            "• Präfixe dürfen mehrfach benutzt werden.\n\n"
            "Beispiele:\n"
            "`RLP 01`\n"
            "`RY ZE 02`\n\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "### 📋 Vergebene Kennzeichen\n"
            f"{plate_list}\n\n"
            f"`{LICENSE_PANEL_MARKER}`"
        ),
        color=discord.Color.blue()
    )

    embed.set_footer(
        text="RLP Kennzeichen System"
    )

    return embed


async def update_license_plate_panel():
    channel = await get_channel(LICENSE_PLATE_CHANNEL_ID)

    if channel is None:
        return

    existing_panel = None
    duplicates = []

    try:
        async for message in channel.history(limit=100):

            if message.author.id != bot.user.id:
                continue

            if not message.embeds:
                continue

            embed = message.embeds[0]

            if LICENSE_PANEL_MARKER in (embed.description or ""):
                if existing_panel is None:
                    existing_panel = message
                else:
                    duplicates.append(message)

        for message in duplicates:
            try:
                await message.delete()
            except Exception:
                pass

        embed = build_license_plate_embed()

        if existing_panel:
            await existing_panel.edit(
                embed=embed,
                view=LicensePlateView()
            )
        else:
            await channel.send(
                embed=embed,
                view=LicensePlateView()
            )

    except Exception as error:
        print(f"Kennzeichen Panel Fehler: {error}")


# ============================================================
# ENTWICKLER SCHICHT
# ============================================================

class ShiftView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Schicht starten",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        custom_id="developer_shift_start"
    )
    async def start_shift(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        member = interaction.user

        if not isinstance(member, discord.Member):
            await interaction.response.send_message(
                "❌ Das funktioniert nur auf dem Server.",
                ephemeral=True
            )
            return

        if not has_role(member, SHIFT_PERMISSION_ROLE_ID):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung, eine Entwicklerschicht zu starten.",
                ephemeral=True
            )
            return

        guild = interaction.guild

        if guild is None:
            return

        active_role = guild.get_role(DEVELOPER_SHIFT_ROLE_ID)

        if active_role is None:
            await interaction.response.send_message(
                "❌ Die aktive Entwicklerrolle wurde nicht gefunden.",
                ephemeral=True
            )
            return

        if active_role in member.roles:
            await interaction.response.send_message(
                "ℹ️ Deine Entwicklerschicht ist bereits aktiv.",
                ephemeral=True
            )
            return

        try:
            # DIE EINZIGE ROLLE, DIE DER BOT AUTOMATISCH HINZUFÜGT:
            await member.add_roles(
                active_role,
                reason="Entwicklerschicht gestartet"
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich kann die aktive Entwicklerrolle nicht vergeben.",
                ephemeral=True
            )
            return

        now = datetime.now(timezone.utc)

        data["shifts"][str(member.id)] = {
            "start": now.isoformat()
        }

        save_data()

        await interaction.response.send_message(
            "🟢 Deine Entwicklerschicht wurde gestartet.",
            ephemeral=True
        )

        # NEU: Log geht in den separaten Log-Channel
        channel = await get_channel(SHIFT_LOG_CHANNEL_ID)

        if channel:
            embed = discord.Embed(
                title="🟢 Entwicklerdienst gestartet",
                description=(
                    f"**Entwickler:** {member.mention}\n"
                    f"**User:** `{member}`\n"
                    f"**ID:** `{member.id}`"
                ),
                color=discord.Color.green(),
                timestamp=now
            )

            embed.set_thumbnail(
                url=member.display_avatar.url
            )

            await channel.send(embed=embed)

    @discord.ui.button(
        label="Schicht beenden",
        emoji="🔴",
        style=discord.ButtonStyle.danger,
        custom_id="developer_shift_end"
    )
    async def end_shift(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        member = interaction.user

        if not isinstance(member, discord.Member):
            await interaction.response.send_message(
                "❌ Das funktioniert nur auf dem Server.",
                ephemeral=True
            )
            return

        if not has_role(member, SHIFT_PERMISSION_ROLE_ID):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung, eine Entwicklerschicht zu beenden.",
                ephemeral=True
            )
            return

        guild = interaction.guild

        if guild is None:
            return

        active_role = guild.get_role(DEVELOPER_SHIFT_ROLE_ID)

        if active_role is None:
            await interaction.response.send_message(
                "❌ Die aktive Entwicklerrolle wurde nicht gefunden.",
                ephemeral=True
            )
            return

        if active_role not in member.roles:
            await interaction.response.send_message(
                "ℹ️ Du hast aktuell keine aktive Entwicklerschicht.",
                ephemeral=True
            )
            return

        try:
            await member.remove_roles(
                active_role,
                reason="Entwicklerschicht beendet"
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich kann die aktive Entwicklerrolle nicht entfernen.",
                ephemeral=True
            )
            return

        start_data = data["shifts"].pop(
            str(member.id),
            None
        )

        save_data()

        now = datetime.now(timezone.utc)

        duration_text = "Unbekannt"

        if start_data and start_data.get("start"):
            try:
                start_time = datetime.fromisoformat(
                    start_data["start"]
                )

                duration = now - start_time

                total_seconds = int(duration.total_seconds())

                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60

                duration_text = (
                    f"{hours}h {minutes}m {seconds}s"
                )

            except Exception:
                pass

        await interaction.response.send_message(
            "🔴 Deine Entwicklerschicht wurde beendet.",
            ephemeral=True
        )

        # NEU: Auch Ende wird im separaten Log-Channel geloggt
        channel = await get_channel(SHIFT_LOG_CHANNEL_ID)

        if channel:
            embed = discord.Embed(
                title="🔴 Entwicklerdienst beendet",
                description=(
                    f"**Entwickler:** {member.mention}\n"
                    f"**User:** `{member}`\n"
                    f"**ID:** `{member.id}`\n"
                    f"**Schichtdauer:** `{duration_text}`"
                ),
                color=discord.Color.red(),
                timestamp=now
            )

            embed.set_thumbnail(
                url=member.display_avatar.url
            )

            await channel.send(embed=embed)


async def send_shift_panel(channel):
    embed = discord.Embed(
        title="🛠️ Entwicklerdienst",
        description=(
            "Hier kannst du deinen Entwicklerdienst starten "
            "oder beenden.\n\n"
            "🟢 **Schicht starten**\n"
            "Du erhältst die aktive Entwicklerrolle.\n\n"
            "🔴 **Schicht beenden**\n"
            "Die aktive Entwicklerrolle wird wieder entfernt.\n\n"
            "Nur Benutzer mit der Entwickler-Berechtigungsrolle "
            "können dieses System benutzen."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="RLP Entwicklerdienst"
    )

    await channel.send(
        embed=embed,
        view=ShiftView()
    )


# ============================================================
# SUPPORT VOICE LOG
# ============================================================

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    log_channel = await get_channel(
        SUPPORT_LOG_CHANNEL_ID
    )

    if log_channel is None:
        return

    if (
        after.channel
        and after.channel.id == SUPPORT_VOICE_CHANNEL_ID
        and (
            before.channel is None
            or before.channel.id != SUPPORT_VOICE_CHANNEL_ID
        )
    ):
        data["support_cases"] += 1
        save_data()

        embed = discord.Embed(
            title="📞 Support betreten",
            description=(
                f"{member.mention} hat den Support betreten.\n\n"
                f"**Support-Fall:** `#{data['support_cases']}`\n"
                f"**User-ID:** `{member.id}`"
            ),
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        await log_channel.send(embed=embed)

    if (
        before.channel
        and before.channel.id == SUPPORT_VOICE_CHANNEL_ID
        and (
            after.channel is None
            or after.channel.id != SUPPORT_VOICE_CHANNEL_ID
        )
    ):
        embed = discord.Embed(
            title="📴 Support verlassen",
            description=(
                f"{member.mention} hat den Support verlassen.\n\n"
                f"**User-ID:** `{member.id}`"
            ),
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        await log_channel.send(embed=embed)


# ============================================================
# BEWERBUNG
# ============================================================

class ApplicationModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Bewerbung"
        )

        self.name = discord.ui.TextInput(
            label="Wie heißt du?",
            placeholder="Dein Name",
            required=True,
            max_length=50
        )

        self.age = discord.ui.TextInput(
            label="Wie alt bist du?",
            placeholder="Dein Alter",
            required=True,
            max_length=10
        )

        self.reason = discord.ui.TextInput(
            label="Warum möchtest du ins Team?",
            placeholder="Erzähle uns etwas über dich...",
            required=True,
            style=discord.TextStyle.paragraph,
            max_length=1000
        )

        self.add_item(self.name)
        self.add_item(self.age)
        self.add_item(self.reason)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):
        channel = await get_channel(
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
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc)
        )

        embed.add_field(
            name="👤 Discord",
            value=(
                f"{interaction.user.mention}\n"
                f"`{interaction.user}`\n"
                f"`{interaction.user.id}`"
            ),
            inline=False
        )

        embed.add_field(
            name="📝 Name",
            value=str(self.name.value),
            inline=True
        )

        embed.add_field(
            name="🎂 Alter",
            value=str(self.age.value),
            inline=True
        )

        embed.add_field(
            name="💬 Begründung",
            value=str(self.reason.value),
            inline=False
        )

        embed.set_thumbnail(
            url=interaction.user.display_avatar.url
        )

        await channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Deine Bewerbung wurde erfolgreich abgeschickt.",
            ephemeral=True
        )


class ApplicationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Bewerben",
        emoji="📨",
        style=discord.ButtonStyle.success,
        custom_id="application_open"
    )
    async def application_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            ApplicationModal()
        )


async def send_application_panel(channel):
    embed = discord.Embed(
        title="📨 Bewerbung",
        description=(
            "Du möchtest dich bei uns bewerben?\n\n"
            "Klicke unten auf **Bewerben** und fülle "
            "das Formular vollständig aus."
        ),
        color=discord.Color.blurple()
    )

    await channel.send(
        embed=embed,
        view=ApplicationView()
    )


# ============================================================
# ENTWICKLER AUFGABEN
# ============================================================

class DeveloperTaskModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Neue Entwickler-Aufgabe"
        )

        self.task_title = discord.ui.TextInput(
            label="Titel",
            placeholder="Kurzer Titel der Aufgabe",
            required=True,
            max_length=100
        )

        self.description = discord.ui.TextInput(
            label="Beschreibung",
            placeholder="Was soll gemacht werden?",
            required=True,
            style=discord.TextStyle.paragraph,
            max_length=1500
        )

        self.add_item(self.task_title)
        self.add_item(self.description)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):
        member = interaction.user

        if not isinstance(member, discord.Member):
            return

        if not has_role(
            member,
            SHIFT_PERMISSION_ROLE_ID
        ):
            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung für Entwickler-Aufgaben.",
                ephemeral=True
            )
            return

        task = {
            "title": str(self.task_title.value),
            "description": str(self.description.value),
            "creator": member.id,
            "created_at": datetime.now(
                timezone.utc
            ).isoformat()
        }

        data["developer_tasks"].append(task)
        save_data()

        channel = await get_channel(
            DEVELOPER_TASK_CHANNEL_ID
        )

        if channel:
            embed = discord.Embed(
                title=f"🛠️ {self.task_title.value}",
                description=str(self.description.value),
                color=discord.Color.orange(),
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(
                name="Erstellt von",
                value=member.mention,
                inline=False
            )

            await channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Entwickler-Aufgabe wurde erstellt.",
            ephemeral=True
        )


class DeveloperTaskView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Aufgabe erstellen",
        emoji="🛠️",
        style=discord.ButtonStyle.primary,
        custom_id="developer_task_create"
    )
    async def task_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        member = interaction.user

        if not isinstance(member, discord.Member):
            return

        if not has_role(
            member,
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


async def send_developer_task_panel(channel):
    embed = discord.Embed(
        title="🛠️ Entwickler Aufgaben",
        description=(
            "Hier können berechtigte Entwickler "
            "neue Aufgaben erstellen."
        ),
        color=discord.Color.orange()
    )

    await channel.send(
        embed=embed,
        view=DeveloperTaskView()
    )


# ============================================================
# OWNER PANEL MODALS
# ============================================================

class OwnerAnnouncementModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Ankündigung erstellen"
        )

        self.title_input = discord.ui.TextInput(
            label="Titel",
            placeholder="Titel der Ankündigung",
            required=True,
            max_length=100
        )

        self.message_input = discord.ui.TextInput(
            label="Nachricht",
            placeholder="Deine Ankündigung...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.title_input)
        self.add_item(self.message_input)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):
        if not isinstance(
            interaction.user,
            discord.Member
        ) or not is_owner_role(interaction.user):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"📢 {self.title_input.value}",
            description=str(self.message_input.value),
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc)
        )

        embed.set_footer(
            text=f"Ankündigung von {interaction.user.display_name}"
        )

        await interaction.channel.send(
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Ankündigung wurde gesendet.",
            ephemeral=True
        )


class OwnerSayModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Bot schreiben lassen"
        )

        self.message_input = discord.ui.TextInput(
            label="Nachricht",
            placeholder="Was soll der Bot schreiben?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.message_input)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):
        if not isinstance(
            interaction.user,
            discord.Member
        ) or not is_owner_role(interaction.user):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "✅ Nachricht wird gesendet.",
            ephemeral=True
        )

        await interaction.channel.send(
            str(self.message_input.value)
        )


class OwnerEmbedModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Embed erstellen"
        )

        self.title_input = discord.ui.TextInput(
            label="Embed Titel",
            placeholder="Titel",
            required=True,
            max_length=100
        )

        self.description_input = discord.ui.TextInput(
            label="Embed Text",
            placeholder="Beschreibung",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.title_input)
        self.add_item(self.description_input)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):
        if not isinstance(
            interaction.user,
            discord.Member
        ) or not is_owner_role(interaction.user):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=str(self.title_input.value),
            description=str(
                self.description_input.value
            ),
            color=discord.Color.blurple()
        )

        await interaction.channel.send(
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Embed wurde erstellt.",
            ephemeral=True
        )


class OwnerClearModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Nachrichten löschen"
        )

        self.amount = discord.ui.TextInput(
            label="Anzahl",
            placeholder="1 bis 100",
            required=True,
            max_length=3
        )

        self.add_item(self.amount)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):
        if not isinstance(
            interaction.user,
            discord.Member
        ) or not is_owner_role(interaction.user):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        try:
            amount = int(str(self.amount.value))
        except ValueError:
            await interaction.response.send_message(
                "❌ Bitte gib eine Zahl ein.",
                ephemeral=True
            )
            return

        if amount < 1 or amount > 100:
            await interaction.response.send_message(
                "❌ Erlaubt sind 1 bis 100 Nachrichten.",
                ephemeral=True
            )
            return

        await interaction.response.defer(
            ephemeral=True
        )

        try:
            deleted = await interaction.channel.purge(
                limit=amount
            )

            await interaction.followup.send(
                f"✅ {len(deleted)} Nachrichten gelöscht.",
                ephemeral=True
            )

        except Exception as error:
            await interaction.followup.send(
                f"❌ Nachrichten konnten nicht gelöscht werden.\n`{error}`",
                ephemeral=True
            )


# ============================================================
# OWNER PANEL
# ============================================================

class OwnerPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def check_owner(
        self,
        interaction: discord.Interaction
    ):
        if not isinstance(
            interaction.user,
            discord.Member
        ):
            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return False

        if not is_owner_role(interaction.user):
            await interaction.response.send_message(
                "❌ Dieses Panel ist nur für Owner.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="Ankündigung",
        emoji="📢",
        style=discord.ButtonStyle.primary,
        custom_id="owner_announcement",
        row=0
    )
    async def announcement(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not await self.check_owner(interaction):
            return

        await interaction.response.send_modal(
            OwnerAnnouncementModal()
        )

    @discord.ui.button(
        label="Bot schreiben lassen",
        emoji="💬",
        style=discord.ButtonStyle.primary,
        custom_id="owner_say",
        row=0
    )
    async def say(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not await self.check_owner(interaction):
            return

        await interaction.response.send_modal(
            OwnerSayModal()
        )

    @discord.ui.button(
        label="Embed erstellen",
        emoji="✨",
        style=discord.ButtonStyle.primary,
        custom_id="owner_embed",
        row=0
    )
    async def embed_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not await self.check_owner(interaction):
            return

        await interaction.response.send_modal(
            OwnerEmbedModal()
        )

    @discord.ui.button(
        label="Nachrichten löschen",
        emoji="🧹",
        style=discord.ButtonStyle.danger,
        custom_id="owner_clear",
        row=1
    )
    async def clear(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not await self.check_owner(interaction):
            return

        await interaction.response.send_modal(
            OwnerClearModal()
        )

    @discord.ui.button(
        label="Channel sperren",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="owner_lock",
        row=1
    )
    async def lock(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not await self.check_owner(interaction):
            return

        channel = interaction.channel
        guild = interaction.guild

        if guild is None:
            return

        overwrite = channel.overwrites_for(
            guild.default_role
        )

        overwrite.send_messages = False

        try:
            await channel.set_permissions(
                guild.default_role,
                overwrite=overwrite,
                reason=f"Channel gesperrt von {interaction.user}"
            )

            await interaction.response.send_message(
                "🔒 Der Channel wurde gesperrt.",
                ephemeral=True
            )

        except Exception as error:
            await interaction.response.send_message(
                f"❌ Fehler: `{error}`",
                ephemeral=True
            )

    @discord.ui.button(
        label="Channel entsperren",
        emoji="🔓",
        style=discord.ButtonStyle.success,
        custom_id="owner_unlock",
        row=1
    )
    async def unlock(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not await self.check_owner(interaction):
            return

        channel = interaction.channel
        guild = interaction.guild

        if guild is None:
            return

        overwrite = channel.overwrites_for(
            guild.default_role
        )

        overwrite.send_messages = None

        try:
            await channel.set_permissions(
                guild.default_role,
                overwrite=overwrite,
                reason=f"Channel entsperrt von {interaction.user}"
            )

            await interaction.response.send_message(
                "🔓 Der Channel wurde entsperrt.",
                ephemeral=True
            )

        except Exception as error:
            await interaction.response.send_message(
                f"❌ Fehler: `{error}`",
                ephemeral=True
            )

    @discord.ui.button(
        label="Quiz starten",
        emoji="🎮",
        style=discord.ButtonStyle.success,
        custom_id="owner_quiz_start",
        row=2
    )
    async def quiz_start(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not await self.check_owner(interaction):
            return

        await interaction.response.defer(
            ephemeral=True
        )

        async with quiz_lock:
            channel = await get_channel(
                QUIZ_CHANNEL_ID
            )

            if channel is None:
                await interaction.followup.send(
                    "❌ Quiz-Channel nicht gefunden.",
                    ephemeral=True
                )
                return

            old_id = quiz_state.get(
                "message_id"
            )

            if old_id:
                try:
                    old_message = await channel.fetch_message(
                        old_id
                    )
                    await old_message.delete()
                except Exception:
                    pass

            quiz_state["message_id"] = None
            quiz_state["answer"] = None

            await send_quiz_question()

        await interaction.followup.send(
            "✅ Eine neue Quiz-Runde wurde gestartet.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Quiz zurücksetzen",
        emoji="🔄",
        style=discord.ButtonStyle.secondary,
        custom_id="owner_quiz_reset",
        row=2
    )
    async def quiz_reset(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not await self.check_owner(interaction):
            return

        await interaction.response.defer(
            ephemeral=True
        )

        async with quiz_lock:
            channel = await get_channel(
                QUIZ_CHANNEL_ID
            )

            old_id = quiz_state.get(
                "message_id"
            )

            if channel and old_id:
                try:
                    old_message = await channel.fetch_message(
                        old_id
                    )
                    await old_message.delete()
                except Exception:
                    pass

            quiz_state["message_id"] = None
            quiz_state["answer"] = None
            quiz_state["round"] = 0

            if channel:
                await send_quiz_question()

        await interaction.followup.send(
            "✅ Quiz wurde zurückgesetzt.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Bot-Status",
        emoji="📊",
        style=discord.ButtonStyle.secondary,
        custom_id="owner_bot_status",
        row=2
    )
    async def bot_status(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not await self.check_owner(interaction):
            return

        latency = round(
            bot.latency * 1000
        )

        embed = discord.Embed(
            title="📊 Bot Status",
            color=discord.Color.green()
        )

        embed.add_field(
            name="Status",
            value="🟢 Online",
            inline=True
        )

        embed.add_field(
            name="Ping",
            value=f"`{latency} ms`",
            inline=True
        )

        embed.add_field(
            name="Server",
            value=f"`{len(bot.guilds)}`",
            inline=True
        )

        embed.add_field(
            name="Support-Fälle",
            value=f"`{data['support_cases']}`",
            inline=True
        )

        embed.add_field(
            name="Kennzeichen",
            value=f"`{len(data['license_plates'])}`",
            inline=True
        )

        embed.add_field(
            name="Dev-Aufgaben",
            value=f"`{len(data['developer_tasks'])}`",
            inline=True
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @discord.ui.button(
        label="Serverinfo",
        emoji="🌐",
        style=discord.ButtonStyle.secondary,
        custom_id="owner_server_info",
        row=3
    )
    async def server_info(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not await self.check_owner(interaction):
            return

        guild = interaction.guild

        if guild is None:
            return

        embed = discord.Embed(
            title=f"🌐 {guild.name}",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Server-ID",
            value=f"`{guild.id}`",
            inline=False
        )

        embed.add_field(
            name="Mitglieder",
            value=f"`{guild.member_count}`",
            inline=True
        )

        embed.add_field(
            name="Rollen",
            value=f"`{len(guild.roles)}`",
            inline=True
        )

        embed.add_field(
            name="Channels",
            value=f"`{len(guild.channels)}`",
            inline=True
        )

        if guild.owner:
            embed.add_field(
                name="Discord Server Owner",
                value=guild.owner.mention,
                inline=False
            )

        if guild.icon:
            embed.set_thumbnail(
                url=guild.icon.url
            )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


def build_owner_panel_embed():
    embed = discord.Embed(
        title="👑 Owner Control Center",
        description=(
            "Willkommen im **Owner Control Center**.\n\n"
            "📢 **Ankündigung**\n"
            "Ankündigung als Embed senden.\n\n"
            "💬 **Bot schreiben lassen**\n"
            "Der Bot schreibt deine Nachricht.\n\n"
            "✨ **Embed erstellen**\n"
            "Eigenes Embed erstellen.\n\n"
            "🧹 **Nachrichten löschen**\n"
            "1 bis 100 Nachrichten entfernen.\n\n"
            "🔒 **Channel sperren**\n"
            "Schreibrechte für @everyone sperren.\n\n"
            "🔓 **Channel entsperren**\n"
            "Schreibrechte wieder freigeben.\n\n"
            "🎮 **Quiz starten**\n"
            "Neue Emoji-Quiz-Runde starten.\n\n"
            "🔄 **Quiz zurücksetzen**\n"
            "Quiz vollständig neu starten.\n\n"
            "📊 **Bot-Status**\n"
            "Status und Statistiken anzeigen.\n\n"
            "🌐 **Serverinfo**\n"
            "Informationen über den Server anzeigen."
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(
        text="RLP Owner Control Center"
    )

    return embed


# ============================================================
# COMMANDS
# ============================================================

@bot.command()
async def ownerpanel(ctx):
    if not isinstance(
        ctx.author,
        discord.Member
    ):
        return

    if not is_owner_role(ctx.author):
        await ctx.reply(
            "❌ Dieses Panel ist nur für Owner.",
            mention_author=False
        )
        return

    await ctx.send(
        embed=build_owner_panel_embed(),
        view=OwnerPanelView()
    )


@bot.command()
async def owner(ctx):
    if not isinstance(
        ctx.author,
        discord.Member
    ):
        return

    if not is_owner_role(ctx.author):
        await ctx.reply(
            "❌ Dieses Panel ist nur für Owner.",
            mention_author=False
        )
        return

    await ctx.send(
        embed=build_owner_panel_embed(),
        view=OwnerPanelView()
    )


@bot.command()
async def nametagpanel(ctx):
    if not isinstance(
        ctx.author,
        discord.Member
    ):
        return

    if not is_owner_role(ctx.author):
        return

    await send_nametag_panel(
        ctx.channel
    )


@bot.command()
async def kennzeichenpanel(ctx):
    if not isinstance(
        ctx.author,
        discord.Member
    ):
        return

    if not is_owner_role(ctx.author):
        return

    await update_license_plate_panel()


@bot.command()
async def schichtpanel(ctx):
    if not isinstance(
        ctx.author,
        discord.Member
    ):
        return

    if not is_owner_role(ctx.author):
        return

    await send_shift_panel(
        ctx.channel
    )


@bot.command()
async def bewerbungspanel(ctx):
    if not isinstance(
        ctx.author,
        discord.Member
    ):
        return

    if not is_owner_role(ctx.author):
        return

    await send_application_panel(
        ctx.channel
    )


@bot.command()
async def devpanel(ctx):
    if not isinstance(
        ctx.author,
        discord.Member
    ):
        return

    if not is_owner_role(ctx.author):
        return

    await send_developer_task_panel(
        ctx.channel
    )


# ============================================================
# MEMBER UPDATE - NAMETAG
# ============================================================

@bot.event
async def on_member_update(
    before: discord.Member,
    after: discord.Member
):
    before_has_nametag = has_role(
        before,
        NAMETAG_ROLE_ID
    )

    after_has_nametag = has_role(
        after,
        NAMETAG_ROLE_ID
    )

    # Rolle wurde hinzugefügt
    # Bot vergibt sie NICHT selbst.
    if not before_has_nametag and after_has_nametag:
        await apply_nametag(after)

    # Rolle wurde entfernt
    if before_has_nametag and not after_has_nametag:
        await remove_nametag(after)


# ============================================================
# MESSAGE EVENT / QUIZ
# ============================================================

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.channel.id == QUIZ_CHANNEL_ID:
        active_message_id = quiz_state.get(
            "message_id"
        )

        # Quiz-Nachricht selbst bleibt erhalten
        if message.id == active_message_id:
            return

        content = message.content.strip().lower()

        try:
            await message.delete()
        except Exception:
            pass

        current_answer = quiz_state.get(
            "answer"
        )

        if (
            current_answer
            and content == current_answer.lower()
        ):
            user_id = str(
                message.author.id
            )

            current_score = data[
                "quiz_scores"
            ].get(user_id, 0)

            data["quiz_scores"][
                user_id
            ] = current_score + 1

            save_data()

            async with quiz_lock:
                channel = message.channel

                old_message_id = quiz_state.get(
                    "message_id"
                )

                if old_message_id:
                    try:
                        old_message = await channel.fetch_message(
                            old_message_id
                        )
                        await old_message.delete()
                    except Exception:
                        pass

                quiz_state["message_id"] = None
                quiz_state["answer"] = None

                result_embed = discord.Embed(
                    title="✅ Richtig!",
                    description=(
                        f"{message.author.mention} "
                        f"hat richtig geraten!\n\n"
                        f"🏆 Punkte: "
                        f"`{data['quiz_scores'][user_id]}`"
                    ),
                    color=discord.Color.green()
                )

                result_message = await channel.send(
                    embed=result_embed
                )

                await asyncio.sleep(2)

                try:
                    await result_message.delete()
                except Exception:
                    pass

                await send_quiz_question()

        return

    await bot.process_commands(message)


# ============================================================
# STARTUP
# ============================================================

startup_finished = False


@bot.event
async def on_ready():
    global startup_finished

    print("========================================")
    print(f"Bot online als: {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print("========================================")

    # Persistent Views
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

    if startup_finished:
        return

    startup_finished = True

    # ========================================================
    # NAMETAGS BEIM START PRÜFEN
    # ========================================================

    guild = bot.get_guild(
        GUILD_ID
    )

    if guild:
        for member in guild.members:
            if member.bot:
                continue

            if has_role(
                member,
                NAMETAG_ROLE_ID
            ):
                try:
                    await apply_nametag(
                        member
                    )
                except Exception as error:
                    print(
                        f"Nametag Sync Fehler bei "
                        f"{member}: {error}"
                    )

            else:
                current_name = (
                    member.nick
                    or member.name
                )

                if current_name.startswith(
                    NAMETAG
                ):
                    try:
                        await remove_nametag(
                            member
                        )
                    except Exception as error:
                        print(
                            f"Nametag Remove Sync Fehler "
                            f"bei {member}: {error}"
                        )

    # WICHTIG:
    # KEINE Schichtrollen werden beim Start wiederhergestellt.
    # Nur ein Klick auf "Schicht starten" vergibt die aktive Rolle.

    # Kennzeichen Panel aktualisieren
    await update_license_plate_panel()

    # Quiz starten / prüfen
    await ensure_quiz()

    if not quiz_cleanup.is_running():
        quiz_cleanup.start()

    print("Alle Systeme wurden gestartet.")


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
        commands.MissingPermissions
    ):
        await ctx.reply(
            "❌ Du hast keine Berechtigung für diesen Befehl.",
            mention_author=False
        )
        return

    print(
        f"Command Fehler: {error}"
    )


# ============================================================
# BOT START
# ============================================================

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN wurde nicht gefunden. "
        "Lege den Token als Secret/Umgebungsvariable DISCORD_TOKEN an."
    )

bot.run(TOKEN)
