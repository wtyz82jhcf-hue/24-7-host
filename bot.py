import os
import json
import random
import asyncio
from datetime import datetime

import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Modal, TextInput


# ============================================================
# KONFIGURATION
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1519481018221072454

QUIZ_CHANNEL_ID = 1533409789256925185

APPLICATION_CHANNEL_ID = 1541391365219295343
REVIEW_CHANNEL_ID = 1548404201493762181

NAMETAG_CHANNEL_ID = 1555684071911202836
NAMETAG_ROLE_ID = 1520102928398942348

LICENSE_PLATE_CHANNEL_ID = 1527350468832006276

SUPPORT_VOICE_CHANNEL_ID = 1519788919254679602
SUPPORT_LOG_CHANNEL_ID = 1521439818146648064

DEVELOPER_TASK_CHANNEL_ID = 1540442867334385715

DEVELOPER_SHIFT_CHANNEL_ID = 1555923435056795648
SHIFT_PERMISSION_ROLE_ID = 1523674698574200904
DEVELOPER_SHIFT_ROLE_ID = 1527372148979798086

DATA_FILE = "bot_data.json"

NAMETAG = "RLP "


# ============================================================
# INTENTS
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

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "license_plates": {},
            "nametag_original_names": {},
            "quiz_points": {},
            "tasks": [],
            "support_cases": 0
        }

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        data.setdefault("license_plates", {})
        data.setdefault("nametag_original_names", {})
        data.setdefault("quiz_points", {})
        data.setdefault("tasks", [])
        data.setdefault("support_cases", 0)

        return data

    except Exception:
        return {
            "license_plates": {},
            "nametag_original_names": {},
            "quiz_points": {},
            "tasks": [],
            "support_cases": 0
        }


data = load_data()


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[DATA] Fehler beim Speichern: {e}")


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

async def get_channel(channel_id):
    channel = bot.get_channel(channel_id)

    if channel is not None:
        return channel

    try:
        return await bot.fetch_channel(channel_id)
    except Exception as e:
        print(f"[CHANNEL] Konnte Kanal {channel_id} nicht laden: {e}")
        return None


async def safe_delete(message):
    try:
        await message.delete()
    except Exception:
        pass


async def safe_send(channel, *args, **kwargs):
    try:
        return await channel.send(*args, **kwargs)
    except Exception as e:
        print(f"[SEND] Fehler: {e}")
        return None


# ============================================================
# EMOJI QUIZ
# ============================================================

QUIZ_QUESTIONS = [

    # Länder
    ("🇩🇪", "deutschland"),
    ("🇫🇷", "frankreich"),
    ("🇮🇹", "italien"),
    ("🇪🇸", "spanien"),
    ("🇬🇧", "england"),
    ("🇺🇸", "usa"),
    ("🇺🇸", "amerika"),
    ("🇯🇵", "japan"),
    ("🇨🇳", "china"),
    ("🇰🇷", "südkorea"),
    ("🇧🇷", "brasilien"),
    ("🇦🇺", "australien"),
    ("🇨🇦", "kanada"),
    ("🇲🇽", "mexiko"),
    ("🇮🇳", "indien"),
    ("🇹🇷", "türkei"),
    ("🇳🇱", "niederlande"),
    ("🇧🇪", "belgien"),
    ("🇦🇹", "österreich"),
    ("🇨🇭", "schweiz"),
    ("🇵🇱", "polen"),
    ("🇺🇦", "ukraine"),
    ("🇳🇴", "norwegen"),
    ("🇸🇪", "schweden"),
    ("🇩🇰", "dänemark"),
    ("🇫🇮", "finnland"),
    ("🇬🇷", "griechenland"),
    ("🇵🇹", "portugal"),
    ("🇮🇪", "irland"),
    ("🇪🇬", "ägypten"),

    # Tiere
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
    ("🐞", "käfer"),
    ("🐢", "schildkröte"),
    ("🐍", "schlange"),
    ("🦎", "eidechse"),
    ("🐙", "oktopus"),
    ("🦀", "krabbe"),
    ("🐠", "fisch"),
    ("🐬", "delfin"),
    ("🐳", "wal"),
    ("🦈", "hai"),

    # Essen
    ("🍕", "pizza"),
    ("🍔", "burger"),
    ("🍟", "pommes"),
    ("🌭", "hotdog"),
    ("🌮", "taco"),
    ("🌯", "burrito"),
    ("🍝", "nudeln"),
    ("🍜", "ramen"),
    ("🍣", "sushi"),
    ("🍚", "reis"),
    ("🍗", "hähnchen"),
    ("🥩", "steak"),
    ("🍎", "apfel"),
    ("🍌", "banane"),
    ("🍓", "erdbeere"),
    ("🍉", "wassermelone"),
    ("🍇", "trauben"),
    ("🍒", "kirsche"),
    ("🍍", "ananas"),
    ("🥝", "kiwi"),
    ("🍋", "zitrone"),
    ("🍫", "schokolade"),
    ("🍩", "donut"),
    ("🍪", "keks"),
    ("🍰", "kuchen"),
    ("🍦", "eis"),
    ("🍿", "popcorn"),

    # Fahrzeuge
    ("🚗", "auto"),
    ("🚕", "taxi"),
    ("🚌", "bus"),
    ("🚎", "bus"),
    ("🚓", "polizei"),
    ("🚑", "rettungswagen"),
    ("🚒", "feuerwehr"),
    ("🚚", "lkw"),
    ("🚜", "traktor"),
    ("🏎️", "rennwagen"),
    ("🏍️", "motorrad"),
    ("🚲", "fahrrad"),
    ("✈️", "flugzeug"),
    ("🚁", "hubschrauber"),
    ("🚀", "rakete"),
    ("🚢", "schiff"),
    ("⛵", "segelboot"),
    ("🚂", "zug"),
    ("🚆", "zug"),
    ("🚇", "u-bahn"),

    # Wetter/Natur
    ("☀️", "sonne"),
    ("🌙", "mond"),
    ("⭐", "stern"),
    ("🌈", "regenbogen"),
    ("☁️", "wolke"),
    ("🌧️", "regen"),
    ("⛈️", "gewitter"),
    ("❄️", "schnee"),
    ("🌪️", "tornado"),
    ("🌊", "welle"),
    ("🔥", "feuer"),
    ("🌲", "baum"),
    ("🌳", "baum"),
    ("🌴", "palme"),
    ("🌵", "kaktus"),
    ("🌹", "rose"),
    ("🌻", "sonnenblume"),

    # Gegenstände
    ("📱", "handy"),
    ("💻", "computer"),
    ("⌨️", "tastatur"),
    ("🖱️", "maus"),
    ("🎧", "kopfhörer"),
    ("📷", "kamera"),
    ("⌚", "uhr"),
    ("🔑", "schlüssel"),
    ("🔒", "schloss"),
    ("💡", "lampe"),
    ("📚", "bücher"),
    ("✏️", "stift"),
    ("🎒", "rucksack"),
    ("⚽", "fußball"),
    ("🏀", "basketball"),
    ("🎾", "tennis"),
    ("🏆", "pokal"),
    ("🎮", "gaming"),
    ("🎸", "gitarre"),
    ("🎹", "klavier"),
    ("🎤", "mikrofon"),

    # Spaß
    ("😂", "lachen"),
    ("🤣", "lachen"),
    ("❤️", "liebe"),
    ("💔", "herz"),
    ("😎", "cool"),
    ("😴", "schlafen"),
    ("🤔", "denken"),
    ("😡", "wütend"),
    ("😱", "angst"),
    ("🥳", "party"),
    ("🤩", "star"),
    ("😭", "weinen"),
    ("🤖", "roboter"),
    ("👻", "geist"),
    ("💀", "totenkopf"),
    ("👽", "alien"),
    ("🎉", "party"),
    ("🎁", "geschenk"),
    ("💰", "geld"),
    ("💎", "diamant"),
]

quiz_state = {
    "message_id": None,
    "answer": None,
    "round": 0,
    "busy": False
}

quiz_lock = asyncio.Lock()


def normalize_answer(text):
    text = text.lower().strip()

    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss"
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def answers_match(user_answer, correct_answer):
    a = normalize_answer(user_answer)
    b = normalize_answer(correct_answer)

    if a == b:
        return True

    alternatives = {
        "deutschland": ["germany"],
        "frankreich": ["france"],
        "italien": ["italy"],
        "spanien": ["spain"],
        "england": ["uk", "united kingdom"],
        "usa": ["amerika", "america", "united states"],
        "amerika": ["usa", "america", "united states"],
        "niederlande": ["holland"],
        "holland": ["niederlande"],
        "hund": ["dog"],
        "katze": ["cat"],
        "fuchs": ["fox"],
        "löwe": ["lion"],
        "bär": ["bear"],
        "pizza": ["pizza"],
        "burger": ["hamburger"],
        "pommes": ["fries"],
        "auto": ["car"],
        "flugzeug": ["plane", "airplane"],
        "hubschrauber": ["heli", "helicopter"],
        "handy": ["smartphone", "phone"],
        "computer": ["pc"],
        "lachen": ["laugh"],
        "geist": ["ghost"],
        "roboter": ["robot"],
    }

    for key, values in alternatives.items():
        if normalize_answer(b) == normalize_answer(key):
            return a in [normalize_answer(x) for x in values]

    return False


async def send_quiz_question():
    async with quiz_lock:
        if quiz_state["busy"]:
            return

        quiz_state["busy"] = True

        try:
            channel = await get_channel(QUIZ_CHANNEL_ID)

            if channel is None:
                print("[QUIZ] Kanal nicht gefunden!")
                return

            emoji, answer = random.choice(QUIZ_QUESTIONS)

            quiz_state["round"] += 1
            quiz_state["answer"] = answer
            quiz_state["message_id"] = None

            embed = discord.Embed(
                title="🎯 EMOJI QUIZ",
                description=(
                    f"## {emoji}\n\n"
                    "❓ **Was stellt dieses Emoji dar?**\n\n"
                    "💬 Schreibe deine Antwort in den Chat!"
                ),
                color=discord.Color.blurple()
            )

            embed.set_footer(
                text=f"Runde {quiz_state['round']} • Viel Glück!"
            )

            message = await channel.send(embed=embed)

            quiz_state["message_id"] = message.id

            print(
                f"[QUIZ] Neue Frage: {emoji} = {answer}"
            )

        except Exception as e:
            print(f"[QUIZ] Fehler: {e}")

        finally:
            quiz_state["busy"] = False


async def ensure_quiz():
    channel = await get_channel(QUIZ_CHANNEL_ID)

    if channel is None:
        return

    current_id = quiz_state["message_id"]

    if current_id is not None:
        try:
            await channel.fetch_message(current_id)
            return
        except Exception:
            quiz_state["message_id"] = None
            quiz_state["answer"] = None

    await send_quiz_question()


@tasks.loop(seconds=5)
async def emoji_quiz_cleanup():
    channel = await get_channel(QUIZ_CHANNEL_ID)

    if channel is None:
        return

    active_id = quiz_state["message_id"]

    try:
        messages = []

        async for message in channel.history(limit=50):
            messages.append(message)

        for message in messages:
            if message.id != active_id:
                await safe_delete(message)

    except Exception as e:
        print(f"[QUIZ CLEANUP] Fehler: {e}")


# ============================================================
# NAMETAG
# ============================================================

async def normalize_nametag(member):
    role = member.guild.get_role(NAMETAG_ROLE_ID)

    if role is None:
        return

    has_role = role in member.roles

    current_name = member.nick or member.name

    if has_role:

        if not current_name.startswith(NAMETAG):
            if str(member.id) not in data["nametag_original_names"]:
                data["nametag_original_names"][str(member.id)] = current_name

            new_name = NAMETAG + current_name

            try:
                await member.edit(nick=new_name)
            except Exception as e:
                print(f"[NAMETAG] Fehler bei {member}: {e}")

            save_data()

    else:

        if current_name.startswith(NAMETAG):
            new_name = current_name[len(NAMETAG):]

            original = data["nametag_original_names"].get(
                str(member.id)
            )

            if original:
                new_name = original

            try:
                await member.edit(nick=new_name)
            except Exception as e:
                print(f"[NAMETAG] Entfernen fehlgeschlagen: {e}")

            data["nametag_original_names"].pop(
                str(member.id),
                None
            )

            save_data()


class NametagResetView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Nametag zurücksetzen",
        style=discord.ButtonStyle.danger,
        emoji="🔄",
        custom_id="nametag_reset"
    )
    async def reset_nametag(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        member = interaction.guild.get_member(
            interaction.user.id
        )

        if member is None:
            await interaction.response.send_message(
                "❌ Benutzer konnte nicht gefunden werden.",
                ephemeral=True
            )
            return

        current_name = member.nick or member.name

        if not current_name.startswith(NAMETAG):
            await interaction.response.send_message(
                "ℹ️ Dein Nametag ist bereits zurückgesetzt.",
                ephemeral=True
            )
            return

        new_name = current_name[len(NAMETAG):]

        try:
            await member.edit(nick=new_name)

            data["nametag_original_names"].pop(
                str(member.id),
                None
            )

            save_data()

            await interaction.response.send_message(
                "✅ Dein Nametag wurde zurückgesetzt.",
                ephemeral=True
            )

        except Exception:
            await interaction.response.send_message(
                "❌ Ich konnte deinen Namen nicht ändern.",
                ephemeral=True
            )


class NametagView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Nametag zurücksetzen",
        style=discord.ButtonStyle.secondary,
        emoji="🔄",
        custom_id="nametag_reset_main"
    )
    async def reset_button(
        self,
        interaction: discord.Interaction,
        button: Button
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

        current_name = member.nick or member.name

        if not current_name.startswith(NAMETAG):
            await interaction.response.send_message(
                "ℹ️ Dein Name hat kein RLP-Nametag.",
                ephemeral=True
            )
            return

        try:
            await member.edit(
                nick=current_name[len(NAMETAG):]
            )

            data["nametag_original_names"].pop(
                str(member.id),
                None
            )

            save_data()

            await interaction.response.send_message(
                "✅ Nametag entfernt.",
                ephemeral=True
            )

        except Exception:
            await interaction.response.send_message(
                "❌ Nametag konnte nicht entfernt werden.",
                ephemeral=True
            )


async def setup_nametag_panel():

    channel = await get_channel(NAMETAG_CHANNEL_ID)

    if channel is None:
        return

    embed = discord.Embed(
        title="🏷️ Nametag",
        description=(
            "Hier kannst du dein Nametag verwalten.\n\n"
            "Wenn du die entsprechende Nametag-Rolle bereits "
            "besitzt, wird dein Name automatisch mit\n"
            f"`{NAMETAG}`\n"
            "versehen.\n\n"
            "🔄 **Nametag zurücksetzen**\n"
            "Entfernt nur `RLP ` aus deinem Namen."
        ),
        color=discord.Color.blue()
    )

    embed.set_footer(
        text="Die Rolle wird vom Bot niemals automatisch vergeben."
    )

    marker = "NAMETAG_PANEL"

    async for message in channel.history(limit=100):
        if (
            message.author == bot.user
            and message.embeds
            and message.embeds[0].footer
            and marker in message.embeds[0].footer.text
        ):
            return

    embed.set_footer(text=marker)

    await channel.send(
        embed=embed,
        view=NametagView()
    )


# ============================================================
# KENNZEICHEN
# ============================================================

def get_used_plate_numbers():
    used = set()

    for plate in data["license_plates"].values():

        parts = plate.strip().split()

        if parts:
            number = parts[-1]

            if number.isdigit():
                used.add(number)

    return used


def create_license_embed():
    embed = discord.Embed(
        title="🚗 Aktuelle Kennzeichen",
        description="",
        color=discord.Color.green()
    )

    if not data["license_plates"]:
        embed.description = "Noch keine Kennzeichen vergeben."
        return embed

    lines = []

    for user_id, plate in data["license_plates"].items():

        member = None

        guild = bot.get_guild(GUILD_ID)

        if guild:
            member = guild.get_member(int(user_id))

        if member:
            name = member.display_name
        else:
            name = f"User {user_id}"

        lines.append(
            f"🚘 `{plate}` — **{name}**"
        )

    lines.sort(key=lambda x: x.lower())

    embed.description = "\n".join(lines)

    return embed


class LicensePlateModal(Modal, title="🚗 Kennzeichen registrieren"):

    plate = TextInput(
        label="Kennzeichen",
        placeholder="z.B. RLP 01",
        required=True,
        max_length=30
    )

    async def on_submit(self, interaction):

        raw = self.plate.value.strip()

        parts = raw.split()

        if len(parts) < 2:
            await interaction.response.send_message(
                "❌ Bitte nutze ein Format wie `RLP 01`.",
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

        used_numbers = get_used_plate_numbers()

        if number in used_numbers:
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

        data["license_plates"][user_id] = raw

        save_data()

        await update_license_panel()

        await interaction.response.send_message(
            f"✅ Dein Kennzeichen `{raw}` wurde registriert.",
            ephemeral=True
        )


class DeleteLicensePlateView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Mein Kennzeichen löschen",
        style=discord.ButtonStyle.danger,
        emoji="🗑️",
        custom_id="delete_license_plate"
    )
    async def delete_plate(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        user_id = str(interaction.user.id)

        if user_id not in data["license_plates"]:
            await interaction.response.send_message(
                "❌ Du hast kein Kennzeichen.",
                ephemeral=True
            )
            return

        plate = data["license_plates"].pop(user_id)

        save_data()

        await update_license_panel()

        await interaction.response.send_message(
            f"🗑️ Dein Kennzeichen `{plate}` wurde gelöscht.",
            ephemeral=True
        )


class LicensePlateView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Kennzeichen registrieren",
        style=discord.ButtonStyle.success,
        emoji="🚗",
        custom_id="register_license_plate"
    )
    async def register(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        await interaction.response.send_modal(
            LicensePlateModal()
        )

    @discord.ui.button(
        label="Mein Kennzeichen löschen",
        style=discord.ButtonStyle.danger,
        emoji="🗑️",
        custom_id="delete_license_plate_main"
    )
    async def delete(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        user_id = str(interaction.user.id)

        if user_id not in data["license_plates"]:
            await interaction.response.send_message(
                "❌ Du hast kein Kennzeichen.",
                ephemeral=True
            )
            return

        plate = data["license_plates"].pop(user_id)

        save_data()

        await update_license_panel()

        await interaction.response.send_message(
            f"🗑️ `{plate}` wurde gelöscht.",
            ephemeral=True
        )


async def update_license_panel():

    channel = await get_channel(LICENSE_PLATE_CHANNEL_ID)

    if channel is None:
        return

    embed = create_license_embed()

    marker = "LICENSE_PLATE_PANEL"

    found = None

    async for message in channel.history(limit=100):

        if (
            message.author == bot.user
            and message.embeds
            and message.embeds[0].footer
            and marker in message.embeds[0].footer.text
        ):
            if found is None:
                found = message
            else:
                await safe_delete(message)

    embed.set_footer(text=marker)

    if found:
        try:
            await found.edit(
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


# ============================================================
# ENTWICKLER-SCHICHT
# ============================================================

class ShiftView(View):

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
        button: Button
    ):

        member = interaction.guild.get_member(
            interaction.user.id
        )

        permission_role = interaction.guild.get_role(
            SHIFT_PERMISSION_ROLE_ID
        )

        active_role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if not permission_role or not active_role:
            await interaction.response.send_message(
                "❌ Rollen konnten nicht gefunden werden.",
                ephemeral=True
            )
            return

        if permission_role not in member.roles:
            await interaction.response.send_message(
                "❌ Du darfst keine Entwicklerschicht starten.",
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
                reason="Entwicklerschicht gestartet"
            )

            await interaction.response.send_message(
                "🟢 Deine Entwicklerschicht wurde gestartet.",
                ephemeral=True
            )

            channel = await get_channel(
                DEVELOPER_SHIFT_CHANNEL_ID
            )

            if channel:
                await channel.send(
                    f"🟢 **Schicht gestartet:** {member.mention}\n"
                    f"🕐 <t:{int(datetime.now().timestamp())}:F>"
                )

        except Exception:
            await interaction.response.send_message(
                "❌ Schicht konnte nicht gestartet werden.",
                ephemeral=True
            )

    @discord.ui.button(
        label="Schicht beenden",
        style=discord.ButtonStyle.danger,
        emoji="🔴",
        custom_id="shift_end"
    )
    async def end_shift(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        member = interaction.guild.get_member(
            interaction.user.id
        )

        active_role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if not active_role:
            await interaction.response.send_message(
                "❌ Schichtrolle nicht gefunden.",
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
                reason="Entwicklerschicht beendet"
            )

            await interaction.response.send_message(
                "🔴 Deine Entwicklerschicht wurde beendet.",
                ephemeral=True
            )

            channel = await get_channel(
                DEVELOPER_SHIFT_CHANNEL_ID
            )

            if channel:
                await channel.send(
                    f"🔴 **Schicht beendet:** {member.mention}\n"
                    f"🕐 <t:{int(datetime.now().timestamp())}:F>"
                )

        except Exception:
            await interaction.response.send_message(
                "❌ Schicht konnte nicht beendet werden.",
                ephemeral=True
            )


async def setup_shift_panel():

    channel = await get_channel(
        DEVELOPER_SHIFT_CHANNEL_ID
    )

    if channel is None:
        return

    marker = "SHIFT_PANEL"

    async for message in channel.history(limit=100):

        if (
            message.author == bot.user
            and message.embeds
            and message.embeds[0].footer
            and marker in message.embeds[0].footer.text
        ):
            return

    embed = discord.Embed(
        title="🛠️ Entwickler-Schicht",
        description=(
            "Hier kannst du deine Entwicklerschicht verwalten.\n\n"
            "🟢 **Schicht starten**\n"
            "Du erhältst die aktive Schichtrolle.\n\n"
            "🔴 **Schicht beenden**\n"
            "Die aktive Schichtrolle wird entfernt."
        ),
        color=discord.Color.orange()
    )

    embed.set_footer(text=marker)

    await channel.send(
        embed=embed,
        view=ShiftView()
    )


# ============================================================
# BEWERBUNGEN
# ============================================================

class ApplicationModal(Modal, title="📋 Bewerbung"):

    name = TextInput(
        label="Name",
        placeholder="Dein Name",
        required=True,
        max_length=50
    )

    age = TextInput(
        label="Alter",
        placeholder="Wie alt bist du?",
        required=True,
        max_length=3
    )

    reason = TextInput(
        label="Warum möchtest du dich bewerben?",
        placeholder="Schreibe etwas über dich...",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    async def on_submit(self, interaction):

        channel = await get_channel(
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
            inline=True
        )

        embed.add_field(
            name="🎂 Alter",
            value=self.age.value,
            inline=True
        )

        embed.add_field(
            name="💬 Bewerbung",
            value=self.reason.value,
            inline=False
        )

        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url
        )

        await channel.send(
            content=interaction.user.mention,
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Deine Bewerbung wurde abgeschickt.",
            ephemeral=True
        )


class ApplicationView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Bewerben",
        style=discord.ButtonStyle.primary,
        emoji="📋",
        custom_id="application_start"
    )
    async def apply(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        await interaction.response.send_modal(
            ApplicationModal()
        )


async def setup_application_panel():

    channel = await get_channel(
        APPLICATION_CHANNEL_ID
    )

    if channel is None:
        return

    marker = "APPLICATION_PANEL"

    async for message in channel.history(limit=100):

        if (
            message.author == bot.user
            and message.embeds
            and message.embeds[0].footer
            and marker in message.embeds[0].footer.text
        ):
            return

    embed = discord.Embed(
        title="📋 Bewerbungen",
        description=(
            "Du möchtest dich bewerben?\n\n"
            "Klicke unten auf **Bewerben** und fülle "
            "das Formular aus."
        ),
        color=discord.Color.blue()
    )

    embed.set_footer(text=marker)

    await channel.send(
        embed=embed,
        view=ApplicationView()
    )


# ============================================================
# ENTWICKLER-AUFGABEN
# ============================================================

class DeveloperTaskModal(
    Modal,
    title="🛠️ Neue Entwickler-Aufgabe"
):

    task = TextInput(
        label="Aufgabe",
        placeholder="Was soll erledigt werden?",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    async def on_submit(self, interaction):

        permission_role = interaction.guild.get_role(
            SHIFT_PERMISSION_ROLE_ID
        )

        if permission_role not in interaction.user.roles:
            await interaction.response.send_message(
                "❌ Du darfst keine Entwickler-Aufgaben erstellen.",
                ephemeral=True
            )
            return

        task_entry = {
            "user_id": interaction.user.id,
            "task": self.task.value,
            "created_at": datetime.now().isoformat()
        }

        data["tasks"].append(task_entry)

        save_data()

        channel = await get_channel(
            DEVELOPER_TASK_CHANNEL_ID
        )

        if channel:

            embed = discord.Embed(
                title="🛠️ Neue Entwickler-Aufgabe",
                description=self.task.value,
                color=discord.Color.orange(),
                timestamp=datetime.now()
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
            "✅ Aufgabe wurde erstellt.",
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

        permission_role = interaction.guild.get_role(
            SHIFT_PERMISSION_ROLE_ID
        )

        if permission_role not in interaction.user.roles:
            await interaction.response.send_message(
                "❌ Du darfst keine Entwickler-Aufgaben erstellen.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            DeveloperTaskModal()
        )


async def setup_task_panel():

    channel = await get_channel(
        DEVELOPER_TASK_CHANNEL_ID
    )

    if channel is None:
        return

    marker = "TASK_PANEL"

    async for message in channel.history(limit=100):

        if (
            message.author == bot.user
            and message.embeds
            and message.embeds[0].footer
            and marker in message.embeds[0].footer.text
        ):
            return

    embed = discord.Embed(
        title="🛠️ Entwickler-Aufgaben",
        description=(
            "Hier können berechtigte Entwickler "
            "neue Aufgaben erstellen."
        ),
        color=discord.Color.orange()
    )

    embed.set_footer(text=marker)

    await channel.send(
        embed=embed,
        view=DeveloperTaskView()
    )


# ============================================================
# SUPPORT VOICE LOG
# ============================================================

@bot.event
async def on_voice_state_update(
    member,
    before,
    after
):

    if before.channel == after.channel:
        return

    support_channel = (
        after.channel
        if after.channel
        and after.channel.id == SUPPORT_VOICE_CHANNEL_ID
        else None
    )

    log_channel = await get_channel(
        SUPPORT_LOG_CHANNEL_ID
    )

    if log_channel is None:
        return

    if support_channel:

        data["support_cases"] += 1
        save_data()

        case_number = data["support_cases"]

        embed = discord.Embed(
            title="🎧 Support betreten",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )

        embed.add_field(
            name="👤 Benutzer",
            value=member.mention,
            inline=True
        )

        embed.add_field(
            name="📁 Fall",
            value=f"#{case_number}",
            inline=True
        )

        await log_channel.send(
            embed=embed
        )

    elif before.channel and before.channel.id == SUPPORT_VOICE_CHANNEL_ID:

        embed = discord.Embed(
            title="🎧 Support verlassen",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )

        embed.add_field(
            name="👤 Benutzer",
            value=member.mention,
            inline=False
        )

        await log_channel.send(
            embed=embed
        )


# ============================================================
# NAMETAG BEI ROLLENÄNDERUNG
# ============================================================

@bot.event
async def on_member_update(before, after):

    role_before = (
        before.guild.get_role(NAMETAG_ROLE_ID)
        in before.roles
    )

    role_after = (
        after.guild.get_role(NAMETAG_ROLE_ID)
        in after.roles
    )

    if role_before != role_after:
        await normalize_nametag(after)


# ============================================================
# NUR EIN EINZIGES on_message
# ============================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # --------------------------------------------------------
    # EMOJI QUIZ
    # --------------------------------------------------------

    if message.channel.id == QUIZ_CHANNEL_ID:

        active_message_id = quiz_state["message_id"]
        correct_answer = quiz_state["answer"]

        # Alles löschen, was NICHT die aktive Quiz-Nachricht ist.
        if (
            active_message_id is not None
            and message.id == active_message_id
        ):
            return

        user_answer = message.content.strip()

        await safe_delete(message)

        if not correct_answer:
            return

        if answers_match(
            user_answer,
            correct_answer
        ):

            user_id = str(message.author.id)

            data["quiz_points"][user_id] = (
                data["quiz_points"].get(user_id, 0) + 1
            )

            points = data["quiz_points"][user_id]

            save_data()

            channel = message.channel

            old_id = quiz_state["message_id"]

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

            result = await channel.send(
                f"🎉 **Richtig, {message.author.mention}!**\n"
                f"⭐ Punktestand: **{points}**"
            )

            await asyncio.sleep(2)

            await safe_delete(result)

            await send_quiz_question()

        return

    # --------------------------------------------------------
    # NORMALE COMMANDS
    # --------------------------------------------------------

    await bot.process_commands(message)


# ============================================================
# START
# ============================================================

@bot.event
async def on_ready():

    print("========================================")
    print(f"🤖 Bot online: {bot.user}")
    print(f"🆔 ID: {bot.user.id}")
    print("========================================")

    # Persistent Views
    bot.add_view(NametagView())
    bot.add_view(LicensePlateView())
    bot.add_view(ShiftView())
    bot.add_view(ApplicationView())
    bot.add_view(DeveloperTaskView())

    guild = bot.get_guild(GUILD_ID)

    if guild:

        print(
            f"🏠 Server gefunden: {guild.name}"
        )

        # Bestehende Nametag-Rollen prüfen.
        for member in guild.members:

            role = guild.get_role(NAMETAG_ROLE_ID)

            if role and role in member.roles:
                await normalize_nametag(member)

    else:
        print(
            "⚠️ Server nicht im Cache gefunden."
        )

    # Panels
    try:
        await setup_nametag_panel()
    except Exception as e:
        print(f"[PANEL] Nametag: {e}")

    try:
        await update_license_panel()
    except Exception as e:
        print(f"[PANEL] Kennzeichen: {e}")

    try:
        await setup_shift_panel()
    except Exception as e:
        print(f"[PANEL] Schicht: {e}")

    try:
        await setup_application_panel()
    except Exception as e:
        print(f"[PANEL] Bewerbung: {e}")

    try:
        await setup_task_panel()
    except Exception as e:
        print(f"[PANEL] Aufgaben: {e}")

    # Quiz starten
    try:
        if not emoji_quiz_cleanup.is_running():
            emoji_quiz_cleanup.start()

        await ensure_quiz()

        print("🎯 Emoji Quiz gestartet!")

    except Exception as e:
        print(f"[QUIZ START] Fehler: {e}")


# ============================================================
# COMMANDS
# ============================================================

@bot.command()
async def ping(ctx):
    await ctx.send(
        f"🏓 Pong! `{round(bot.latency * 1000)}ms`"
    )


@bot.command()
async def quizpunkte(ctx):
    user_id = str(ctx.author.id)

    points = data["quiz_points"].get(
        user_id,
        0
    )

    await ctx.send(
        f"🏆 {ctx.author.mention}, du hast "
        f"**{points} Quizpunkte**!"
    )


@bot.command()
async def kennzeichen(ctx):

    user_id = str(ctx.author.id)

    plate = data["license_plates"].get(
        user_id
    )

    if plate:
        await ctx.send(
            f"🚗 Dein Kennzeichen ist `{plate}`."
        )
    else:
        await ctx.send(
            "🚗 Du hast aktuell kein Kennzeichen."
        )


@bot.command()
async def botinfo(ctx):

    embed = discord.Embed(
        title="🤖 Bot Info",
        description=(
            "🎯 Emoji Quiz\n"
            "🚗 Kennzeichen\n"
            "🏷️ Nametag\n"
            "🛠️ Entwickler-Schicht\n"
            "📋 Bewerbungen\n"
            "🔧 Entwickler-Aufgaben\n"
            "🎧 Support-Logging"
        ),
        color=discord.Color.blurple()
    )

    await ctx.send(embed=embed)


# ============================================================
# FEHLER
# ============================================================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(
        error,
        commands.CommandNotFound
    ):
        return

    print(
        f"[COMMAND ERROR] {error}"
    )


# ============================================================
# TOKEN
# ============================================================

if not TOKEN:

    print(
        "❌ DISCORD_TOKEN wurde nicht gefunden!"
    )

else:

    print(
        "🚀 Bot wird gestartet..."
    )

    bot.run(TOKEN)
