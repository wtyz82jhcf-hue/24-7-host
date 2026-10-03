import os
import json
import random
import asyncio
import discord

from discord.ext import commands, tasks
from discord.ui import View, Button, Modal, TextInput


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
# INTENTS
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
    "support_case_counter": 0,
    "applications": {}
}

data = {}


def load_data():
    global data

    if not os.path.exists(DATA_FILE):
        data = json.loads(
            json.dumps(DEFAULT_DATA)
        )
        save_data()
        return

    try:
        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            loaded = json.load(file)

        data = json.loads(
            json.dumps(DEFAULT_DATA)
        )

        if isinstance(loaded, dict):
            for key in DEFAULT_DATA:
                if key in loaded:
                    data[key] = loaded[key]

    except Exception as error:
        print(
            f"[DATA] Fehler beim Laden: {error}"
        )

        data = json.loads(
            json.dumps(DEFAULT_DATA)
        )

        save_data()


def save_data():
    try:
        with open(
            DATA_FILE,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )
    except Exception as error:
        print(
            f"[DATA] Fehler beim Speichern: {error}"
        )


load_data()


# =========================================================
# ALLGEMEINE HILFSFUNKTIONEN
# =========================================================

def has_role(member, role_id):
    return any(
        role.id == role_id
        for role in member.roles
    )


async def safe_delete(message):
    try:
        await message.delete()
    except (
        discord.NotFound,
        discord.Forbidden,
        discord.HTTPException
    ):
        pass


async def safe_send(channel, *args, **kwargs):
    if channel is None:
        return None

    try:
        return await channel.send(
            *args,
            **kwargs
        )
    except (
        discord.Forbidden,
        discord.HTTPException
    ):
        return None


# =========================================================
# NAMETAG
# =========================================================

def remove_nametag(name):
    while name.startswith(NAMETAG):
        name = name[len(NAMETAG):]

    return name


def create_nametag(name):
    clean = remove_nametag(name)

    if not clean:
        clean = "User"

    return (
        NAMETAG + clean
    )[:32]


async def update_member_nametag(member):

    if member.bot:
        return

    user_id = str(member.id)

    role_exists = has_role(
        member,
        NAMETAG_ROLE_ID
    )

    current_name = (
        member.nick
        if member.nick is not None
        else member.name
    )

    # -----------------------------------------------------
    # Rolle vorhanden
    # -----------------------------------------------------

    if role_exists:

        if current_name.startswith(NAMETAG):
            return

        if user_id not in data[
            "nametag_original_names"
        ]:
            data[
                "nametag_original_names"
            ][user_id] = member.nick

        new_name = create_nametag(
            current_name
        )

        try:
            await member.edit(
                nick=new_name,
                reason="Nametag-Rolle vorhanden"
            )

            save_data()

        except (
            discord.Forbidden,
            discord.HTTPException
        ):
            pass

        return

    # -----------------------------------------------------
    # Rolle nicht vorhanden
    # -----------------------------------------------------

    if not current_name.startswith(NAMETAG):
        return

    original_name = data[
        "nametag_original_names"
    ].get(user_id)

    clean_name = remove_nametag(
        current_name
    )

    # Falls kein gespeicherter Name existiert,
    # wird der bereinigte Name verwendet.
    if original_name is None:
        original_name = clean_name[:32]

    try:
        await member.edit(
            nick=original_name,
            reason="Nametag-Rolle nicht vorhanden"
        )

        data[
            "nametag_original_names"
        ].pop(user_id, None)

        save_data()

    except (
        discord.Forbidden,
        discord.HTTPException
    ):
        pass


class NametagResetButton(Button):

    def __init__(self):
        super().__init__(
            label="Nametag zurücksetzen",
            style=discord.ButtonStyle.danger,
            emoji="🔄",
            custom_id="rlp_nametag_reset"
        )

    async def callback(self, interaction):

        member = interaction.guild.get_member(
            interaction.user.id
        )

        if member is None:
            await interaction.response.send_message(
                "❌ Benutzer nicht gefunden.",
                ephemeral=True
            )
            return

        current_name = (
            member.nick
            if member.nick is not None
            else member.name
        )

        if not current_name.startswith(NAMETAG):

            await interaction.response.send_message(
                "ℹ️ Dein Name hat aktuell keinen Nametag.",
                ephemeral=True
            )
            return

        clean_name = remove_nametag(
            current_name
        )

        if not clean_name:
            clean_name = member.name

        try:

            await member.edit(
                nick=clean_name[:32],
                reason="Nametag manuell zurückgesetzt"
            )

            data[
                "nametag_original_names"
            ].pop(
                str(member.id),
                None
            )

            save_data()

            await interaction.response.send_message(
                "✅ Dein Nametag wurde zurückgesetzt.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Ich kann deinen Namen nicht ändern. "
                "Meine Bot-Rolle muss über deiner höchsten Rolle stehen.",
                ephemeral=True
            )

        except discord.HTTPException:

            await interaction.response.send_message(
                "❌ Der Name konnte nicht geändert werden.",
                ephemeral=True
            )


class NametagView(View):

    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(
            NametagResetButton()
        )


async def update_nametag_panel():

    channel = bot.get_channel(
        NAMETAG_CHANNEL_ID
    )

    if channel is None:
        return

    marker = "RLP_NAMETAG_PANEL"

    existing = None

    try:

        async for message in channel.history(
            limit=100
        ):

            if message.author.id != bot.user.id:
                continue

            if not message.embeds:
                continue

            footer = (
                message.embeds[0].footer.text
            )

            if footer != marker:
                continue

            if existing is None:
                existing = message
            else:
                await safe_delete(message)

    except (
        discord.Forbidden,
        discord.HTTPException
    ):
        return

    embed = discord.Embed(
        title="🏷️ RLP Nametag",
        description=(
            "Willkommen beim Nametag-System!\n\n"
            f"🏷️ Wenn du die Nametag-Rolle besitzt, "
            f"wird automatisch `{NAMETAG}` vor deinen Namen gesetzt.\n\n"
            "🔄 **Nametag zurücksetzen**\n"
            "Du kannst deinen Nametag hier jederzeit selbst "
            "zurücksetzen. Dafür benötigst du **keine Rolle**.\n\n"
            "⚠️ Der Bot vergibt die Nametag-Rolle niemals automatisch."
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(
        text=marker
    )

    if existing:

        try:
            await existing.edit(
                embed=embed,
                view=NametagView()
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
            view=NametagView()
        )


# =========================================================
# KENNZEICHEN
# =========================================================

license_lock = asyncio.Lock()


def get_plate_number(plate):

    parts = plate.strip().upper().split()

    if len(parts) < 2:
        return None

    if not parts[-1].isdigit():
        return None

    return parts[-1]


def valid_plate(plate):

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
    number,
    except_user_id=None
):

    for user_id, plate in data[
        "license_plates"
    ].items():

        if (
            except_user_id is not None
            and str(user_id) == str(except_user_id)
        ):
            continue

        if get_plate_number(plate) == number:
            return True

    return False


def get_plate_list():

    result = []

    for user_id, plate in data[
        "license_plates"
    ].items():

        result.append(
            (
                str(user_id),
                plate
            )
        )

    result.sort(
        key=lambda item: (
            int(get_plate_number(item[1]))
            if (
                get_plate_number(item[1])
                and get_plate_number(item[1]).isdigit()
            )
            else 999999999,
            item[1]
        )
    )

    return result


class LicensePlateModal(
    Modal,
    title="🚗 Kennzeichen registrieren"
):

    plate = TextInput(
        label="Kennzeichen",
        placeholder="z.B. RLP 01 oder RY ZE 02",
        max_length=20,
        required=True
    )

    async def on_submit(self, interaction):

        user_id = str(
            interaction.user.id
        )

        async with license_lock:

            # Ein Benutzer darf nur eins haben.
            if user_id in data[
                "license_plates"
            ]:

                await interaction.response.send_message(
                    "❌ Du besitzt bereits ein Kennzeichen.\n"
                    "Lösche zuerst dein aktuelles Kennzeichen.",
                    ephemeral=True
                )
                return

            plate = (
                self.plate.value
                .strip()
                .upper()
            )

            if not valid_plate(plate):

                await interaction.response.send_message(
                    "❌ Ungültiges Kennzeichen.\n\n"
                    "Beispiele:\n"
                    "`RLP 01`\n"
                    "`RY ZE 02`",
                    ephemeral=True
                )
                return

            number = get_plate_number(
                plate
            )

            if number is None:

                await interaction.response.send_message(
                    "❌ Die letzte Stelle muss eine Zahl sein.",
                    ephemeral=True
                )
                return

            # Nur die Nummer muss global einzigartig sein.
            if plate_number_exists(number):

                await interaction.response.send_message(
                    f"❌ Die Nummer `{number}` ist bereits vergeben.\n"
                    "Auch ein anderer Präfix ist damit nicht möglich.",
                    ephemeral=True
                )
                return

            data[
                "license_plates"
            ][user_id] = plate

            save_data()

        await interaction.response.send_message(
            f"✅ **{plate}** wurde erfolgreich registriert.",
            ephemeral=True
        )

        await update_license_plate_panel()


class LicenseDeleteButton(Button):

    def __init__(self):
        super().__init__(
            label="Mein Kennzeichen löschen",
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            custom_id="rlp_license_delete"
        )

    async def callback(self, interaction):

        user_id = str(
            interaction.user.id
        )

        async with license_lock:

            plate = data[
                "license_plates"
            ].pop(
                user_id,
                None
            )

            if plate is None:

                await interaction.response.send_message(
                    "❌ Du besitzt aktuell kein Kennzeichen.",
                    ephemeral=True
                )
                return

            save_data()

        await interaction.response.send_message(
            f"✅ **{plate}** wurde gelöscht.\n"
            "Die Nummer ist wieder frei.",
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

        async def register_callback(interaction):
            await interaction.response.send_modal(
                LicensePlateModal()
            )

        register_button.callback = register_callback

        self.add_item(
            register_button
        )

        self.add_item(
            LicenseDeleteButton()
        )


async def update_license_plate_panel():

    channel = bot.get_channel(
        LICENSE_PLATE_CHANNEL_ID
    )

    if channel is None:
        return

    marker = "RLP_LICENSE_PANEL"

    existing = None

    try:

        async for message in channel.history(
            limit=100
        ):

            if message.author.id != bot.user.id:
                continue

            if not message.embeds:
                continue

            if (
                message.embeds[0].footer.text
                != marker
            ):
                continue

            if existing is None:
                existing = message
            else:
                await safe_delete(message)

    except (
        discord.Forbidden,
        discord.HTTPException
    ):
        return

    embed = discord.Embed(
        title="🚗 RLP Kennzeichen",
        description=(
            "Registriere hier dein Kennzeichen.\n\n"
            "📌 **Regeln**\n"
            "• Jeder Benutzer darf nur **ein** Kennzeichen besitzen.\n"
            "• Die letzte Zahl muss global einzigartig sein.\n"
            "• Der Präfix darf mehrfach vorkommen.\n"
            "• Beim Löschen wird die Nummer wieder frei.\n\n"
            "Beispiele:\n"
            "✅ `RLP 01`\n"
            "❌ `RY ZE 01` wenn `01` schon vergeben ist\n"
            "✅ `RLP 02`"
        ),
        color=discord.Color.blue()
    )

    plates = get_plate_list()

    if plates:

        lines = []

        guild = bot.get_guild(
            GUILD_ID
        )

        for user_id, plate in plates:

            member = None

            if guild:
                member = guild.get_member(
                    int(user_id)
                )

            if member:
                name = member.display_name
            else:
                name = f"User {user_id}"

            lines.append(
                f"🚘 `{plate}` — **{name}**"
            )

        text = "\n".join(lines)

        if len(text) > 3900:
            text = (
                text[:3800]
                + "\n…"
            )

        embed.add_field(
            name=f"📋 Aktuell vergeben ({len(plates)})",
            value=text,
            inline=False
        )

    else:

        embed.add_field(
            name="📋 Aktuell vergeben",
            value="Noch keine Kennzeichen vergeben.",
            inline=False
        )

    embed.set_footer(
        text=marker
    )

    if existing:

        try:
            await existing.edit(
                embed=embed,
                view=LicensePlateView()
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
            view=LicensePlateView()
        )


# =========================================================
# EMOJI QUIZ
# =========================================================

QUIZ_QUESTIONS = [

    # -----------------------------------------------------
    # Tiere
    # -----------------------------------------------------

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
    ("🦄", "einhorn"),
    ("🐝", "biene"),
    ("🦋", "schmetterling"),
    ("🐢", "schildkröte"),
    ("🐍", "schlange"),
    ("🦖", "dinosaurier"),
    ("🐳", "wal"),
    ("🦈", "hai"),
    ("🐙", "oktopus"),
    ("🦀", "krabbe"),

    # -----------------------------------------------------
    # Essen
    # -----------------------------------------------------

    ("🍕", "pizza"),
    ("🍔", "burger"),
    ("🍟", "pommes"),
    ("🌭", "hotdog"),
    ("🌮", "taco"),
    ("🍿", "popcorn"),
    ("🍩", "donut"),
    ("🍪", "keks"),
    ("🍫", "schokolade"),
    ("🍎", "apfel"),
    ("🍌", "banane"),
    ("🍉", "wassermelone"),
    ("🍓", "erdbeere"),
    ("🍇", "trauben"),
    ("🍒", "kirsche"),
    ("🍋", "zitrone"),
    ("🍍", "ananas"),
    ("🥨", "brezel"),
    ("🍰", "kuchen"),
    ("🎂", "geburtstag"),
    ("🍦", "eis"),
    ("🍭", "lutscher"),
    ("☕", "kaffee"),
    ("🥤", "getränk"),

    # -----------------------------------------------------
    # Länder
    # -----------------------------------------------------

    ("🇩🇪", "deutschland"),
    ("🇫🇷", "frankreich"),
    ("🇮🇹", "italien"),
    ("🇪🇸", "spanien"),
    ("🇵🇹", "portugal"),
    ("🇬🇧", "england"),
    ("🇺🇸", "usa"),
    ("🇨🇦", "kanada"),
    ("🇧🇷", "brasilien"),
    ("🇦🇷", "argentinien"),
    ("🇯🇵", "japan"),
    ("🇨🇳", "china"),
    ("🇰🇷", "südkorea"),
    ("🇮🇳", "indien"),
    ("🇦🇺", "australien"),
    ("🇳🇿", "neuseeland"),
    ("🇳🇱", "niederlande"),
    ("🇧🇪", "belgien"),
    ("🇦🇹", "österreich"),
    ("🇨🇭", "schweiz"),
    ("🇵🇱", "polen"),
    ("🇨🇿", "tschechien"),
    ("🇬🇷", "griechenland"),
    ("🇹🇷", "türkei"),
    ("🇪🇬", "ägypten"),
    ("🇳🇴", "norwegen"),
    ("🇸🇪", "schweden"),
    ("🇫🇮", "finnland"),
    ("🇩🇰", "dänemark"),
    ("🇮🇪", "irland"),

    # -----------------------------------------------------
    # Städte
    # -----------------------------------------------------

    ("🗼🇫🇷", "paris"),
    ("🏰🇩🇪", "berlin"),
    ("🎡🇬🇧", "london"),
    ("🗽🇺🇸", "new york"),
    ("🌉🇺🇸", "san francisco"),
    ("🏟️🇪🇸", "madrid"),
    ("🏛️🇮🇹", "rom"),
    ("🚤🇮🇹", "venedig"),
    ("⛪🇨🇿", "prag"),
    ("🏰🇦🇹", "wien"),
    ("🌷🇳🇱", "amsterdam"),
    ("🗻🇯🇵", "tokio"),
    ("🏙️🇦🇪", "dubai"),
    ("🕌🇹🇷", "istanbul"),
    ("🌴🇺🇸", "miami"),

    # -----------------------------------------------------
    # Sport
    # -----------------------------------------------------

    ("⚽🥅", "fußball"),
    ("🏀🏀", "basketball"),
    ("🏈🏈", "football"),
    ("⚾⚾", "baseball"),
    ("🎾🎾", "tennis"),
    ("🏐🏐", "volleyball"),
    ("🏎️🏁", "formel 1"),
    ("🥊🥊", "boxen"),
    ("🏊🌊", "schwimmen"),
    ("🚴🚲", "radfahren"),
    ("🏆🥇", "sieg"),
    ("🥇🏆", "meister"),
    ("⛷️❄️", "skifahren"),
    ("🏄🌊", "surfen"),
    ("🏹🎯", "bogenschießen"),

    # -----------------------------------------------------
    # Fahrzeuge
    # -----------------------------------------------------

    ("🚗⛽", "auto"),
    ("🚕", "taxi"),
    ("🚌", "bus"),
    ("🚓", "polizei"),
    ("🚑", "krankenwagen"),
    ("🚒", "feuerwehr"),
    ("🚲", "fahrrad"),
    ("🏍️", "motorrad"),
    ("✈️", "flugzeug"),
    ("🚁", "hubschrauber"),
    ("🚢", "schiff"),
    ("🚂", "zug"),
    ("🚀", "rakete"),
    ("🚜", "traktor"),
    ("🏎️", "rennwagen"),

    # -----------------------------------------------------
    # Gaming
    # -----------------------------------------------------

    ("⛏️🟩", "minecraft"),
    ("🎮🏎️", "mario kart"),
    ("🧱🎮", "tetris"),
    ("👻🟡", "pacman"),
    ("🔫🎮", "fortnite"),
    ("🏝️🎮", "fortnite"),
    ("🐉⚔️", "zelda"),
    ("🍄👨", "mario"),
    ("💣💥", "bomberman"),
    ("🦔💨", "sonic"),

    # -----------------------------------------------------
    # Filme / Serien
    # -----------------------------------------------------

    ("🧙‍♂️💍", "herr der ringe"),
    ("⚡🧙‍♂️", "harry potter"),
    ("🦁👑", "könig der löwen"),
    ("❄️👸", "frozen"),
    ("🕷️🦸", "spiderman"),
    ("🦇🦸", "batman"),
    ("🦸‍♂️🛡️", "captain america"),
    ("🤖🚗", "transformers"),
    ("🦖🏝️", "jurassic park"),
    ("🚢💔", "titanic"),
    ("👽🚲", "e.t."),
    ("🐠🌊", "findet nemo"),
    ("🤠🐎", "toy story"),

    # -----------------------------------------------------
    # Musik
    # -----------------------------------------------------

    ("🎸🎵", "rock"),
    ("🎤🎵", "sänger"),
    ("🎹🎵", "klavier"),
    ("🥁🎵", "schlagzeug"),
    ("🎻🎵", "geige"),
    ("🎧🎶", "musik"),
    ("🎤🎙️", "sänger"),

    # -----------------------------------------------------
    # Alltag
    # -----------------------------------------------------

    ("📱💬", "handy"),
    ("💻⌨️", "computer"),
    ("📚🏫", "schule"),
    ("✏️📚", "lernen"),
    ("🛏️😴", "schlafen"),
    ("⏰😴", "wecker"),
    ("🚿🧼", "duschen"),
    ("🦷🪥", "zähne"),
    ("🎁🎉", "geschenk"),
    ("🎂🎉", "geburtstag"),
    ("☀️😎", "sommer"),
    ("❄️⛄", "winter"),
    ("🌧️☂️", "regen"),
    ("🌈☀️", "regenbogen"),
    ("🌙⭐", "nacht"),
    ("🔥🏕️", "lagerfeuer"),

    # -----------------------------------------------------
    # Spaß
    # -----------------------------------------------------

    ("😂🤣", "lachen"),
    ("😭😂", "lachflash"),
    ("🤯💥", "verrückt"),
    ("😴💤", "müde"),
    ("😎🕶️", "cool"),
    ("🤔❓", "nachdenken"),
    ("😱👻", "angst"),
    ("❤️🥰", "liebe"),
    ("🎉🥳", "party"),
    ("🤫🤐", "geheimnis"),
    ("👀🔍", "beobachten"),
    ("💩😂", "kacke"),
    ("🐔🏃", "hühnerjagd"),
    ("🧊🔥", "gegensatz"),
    ("🐢💨", "langsam"),
    ("🚀💨", "schnell"),

    # -----------------------------------------------------
    # Kombinationen
    # -----------------------------------------------------

    ("🌞🏖️", "urlaub"),
    ("✈️🏖️", "reise"),
    ("🏠🔑", "haus"),
    ("💰🤑", "geld"),
    ("💳🛒", "einkaufen"),
    ("🎓📚", "abschluss"),
    ("🎂🎁🥳", "geburtstag"),
    ("🌍✈️", "weltreise"),
    ("🏖️🌴", "strand"),
    ("🌋🔥", "vulkan"),
    ("🌊🏄", "surfen"),
    ("🏔️❄️", "berg"),
    ("🌳🌲", "wald"),
    ("🌹❤️", "liebe"),
    ("💡🧠", "idee"),
    ("🔒🔑", "passwort"),
    ("📷🤳", "selfie"),
    ("🎒🏫", "schulranzen"),
    ("🍿🎬", "kino"),
    ("🎮🕹️", "gaming")
]


def normalize_answer(text):

    text = text.lower().strip()

    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss"
    }

    for old, new in replacements.items():
        text = text.replace(
            old,
            new
        )

    text = (
        text
        .replace(".", "")
        .replace(",", "")
        .replace("!", "")
        .replace("?", "")
        .replace("-", " ")
    )

    return " ".join(
        text.split()
    )


current_quiz = {
    "answer": None,
    "message_id": None,
    "question_number": 0
}

quiz_lock = asyncio.Lock()


async def delete_quiz_messages(
    keep_message_id=None
):

    channel = bot.get_channel(
        QUIZ_CHANNEL_ID
    )

    if channel is None:
        return

    try:

        messages = []

        async for message in channel.history(
            limit=100
        ):

            if (
                keep_message_id is not None
                and message.id == keep_message_id
            ):
                continue

            messages.append(message)

        for message in messages:
            await safe_delete(message)

    except (
        discord.Forbidden,
        discord.HTTPException
    ):
        pass


async def send_new_quiz():

    channel = bot.get_channel(
        QUIZ_CHANNEL_ID
    )

    if channel is None:
        print(
            "[QUIZ] Kanal nicht gefunden."
        )
        return

    async with quiz_lock:

        # -------------------------------------------------
        # Prüfen, ob bereits eine Runde läuft
        # -------------------------------------------------

        if current_quiz["message_id"] is not None:

            try:

                await channel.fetch_message(
                    current_quiz["message_id"]
                )

                return

            except (
                discord.NotFound,
                discord.HTTPException
            ):

                current_quiz[
                    "message_id"
                ] = None

                current_quiz[
                    "answer"
                ] = None

        # -------------------------------------------------
        # Alte Nachrichten löschen
        # -------------------------------------------------

        await delete_quiz_messages()

        # -------------------------------------------------
        # Neue Frage
        # -------------------------------------------------

        emoji, answer = random.choice(
            QUIZ_QUESTIONS
        )

        current_quiz[
            "question_number"
        ] += 1

        question_number = current_quiz[
            "question_number"
        ]

        embed = discord.Embed(
            title="🧩 RLP EMOJI QUIZ",
            description=(
                "# 🎯 Errate den Begriff!\n\n"
                f"## {emoji}\n\n"
                "💬 **Schreibe deine Antwort in den Chat.**\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "🏆 **Bei einer richtigen Antwort bekommst du 1 Punkt.**\n"
                "🔄 Danach startet automatisch die nächste Runde.\n"
                "━━━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="💡 Tipp",
            value=(
                "Die Fragen sind bunt gemischt und "
                "meistens nicht zu schwer. 😎"
            ),
            inline=False
        )

        embed.add_field(
            name="📊 Runde",
            value=f"#{question_number}",
            inline=True
        )

        embed.add_field(
            name="🎯 Kategorie",
            value="🎲 Zufällig",
            inline=True
        )

        embed.set_footer(
            text="RLP • Emoji Quiz • Viel Spaß! 🎉"
        )

        try:

            message = await channel.send(
                embed=embed
            )

            current_quiz[
                "answer"
            ] = answer

            current_quiz[
                "message_id"
            ] = message.id

            print(
                f"[QUIZ] Runde #{question_number}: "
                f"{answer}"
            )

        except (
            discord.Forbidden,
            discord.HTTPException
        ) as error:

            print(
                f"[QUIZ] Fehler beim Senden: {error}"
            )


@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # =====================================================
    # QUIZ
    # =====================================================

    if message.channel.id == QUIZ_CHANNEL_ID:

        active_id = current_quiz[
            "message_id"
        ]

        # Keine aktive Runde?
        if active_id is None:

            await safe_delete(message)

            return

        # Das Quiz-Embed selbst bleibt.
        if message.id == active_id:
            return

        user_answer = normalize_answer(
            message.content
        )

        correct_answer = current_quiz[
            "answer"
        ]

        # Nachricht immer löschen.
        await safe_delete(message)

        if correct_answer is None:
            return

        normalized_correct = normalize_answer(
            correct_answer
        )

        # =================================================
        # RICHTIGE ANTWORT
        # =================================================

        if user_answer == normalized_correct:

            async with quiz_lock:

                # Verhindert doppelte Gewinner
                if (
                    current_quiz["answer"]
                    != correct_answer
                ):
                    return

                old_message_id = (
                    current_quiz[
                        "message_id"
                    ]
                )

                current_quiz[
                    "answer"
                ] = None

                current_quiz[
                    "message_id"
                ] = None

                user_id = str(
                    message.author.id
                )

                data[
                    "quiz_scores"
                ][user_id] = (
                    data[
                        "quiz_scores"
                    ].get(
                        user_id,
                        0
                    ) + 1
                )

                score = data[
                    "quiz_scores"
                ][user_id]

                save_data()

                # Quiz-Embed löschen
                if old_message_id:

                    try:

                        old_message = (
                            await message.channel.fetch_message(
                                old_message_id
                            )
                        )

                        await safe_delete(
                            old_message
                        )

                    except (
                        discord.NotFound,
                        discord.Forbidden,
                        discord.HTTPException
                    ):
                        pass

                result_embed = discord.Embed(
                    title="🎉 RICHTIG!",
                    description=(
                        f"🏆 **{message.author.display_name}** "
                        "hat die Antwort erraten!\n\n"
                        f"✅ Antwort: **{correct_answer}**\n\n"
                        f"⭐ Deine Punkte: **{score}**"
                    ),
                    color=discord.Color.green()
                )

                result_embed.set_footer(
                    text="Die nächste Runde startet gleich... 🚀"
                )

                await safe_send(
                    message.channel,
                    embed=result_embed
                )

            await asyncio.sleep(2)

            # Ergebnisnachricht entfernen
            try:

                async for msg in message.channel.history(
                    limit=10
                ):

                    if (
                        msg.author == bot.user
                        and msg.embeds
                        and msg.embeds[0].title
                        == "🎉 RICHTIG!"
                    ):
                        await safe_delete(msg)
                        break

            except (
                discord.Forbidden,
                discord.HTTPException
            ):
                pass

            await send_new_quiz()

        return

    # Andere Nachrichten normal verarbeiten.
    await bot.process_commands(
        message
    )


@tasks.loop(seconds=5)
async def quiz_cleanup():

    channel = bot.get_channel(
        QUIZ_CHANNEL_ID
    )

    if channel is None:
        return

    active_id = current_quiz[
        "message_id"
    ]

    try:

        async for message in channel.history(
            limit=100
        ):

            # Aktuelles Quiz niemals löschen.
            if (
                active_id is not None
                and message.id == active_id
            ):
                continue

            await safe_delete(
                message
            )

    except (
        discord.Forbidden,
        discord.HTTPException
    ):
        pass


# =========================================================
# QUIZ SCORE COMMAND
# =========================================================

@bot.command(
    name="punkte"
)
async def quiz_points(ctx):

    user_id = str(
        ctx.author.id
    )

    score = data[
        "quiz_scores"
    ].get(
        user_id,
        0
    )

    embed = discord.Embed(
        title="🏆 Deine Quiz-Punkte",
        description=(
            f"{ctx.author.mention}\n\n"
            f"⭐ **{score} Punkte**"
        ),
        color=discord.Color.gold()
    )

    await ctx.send(
        embed=embed,
        delete_after=5
    )


# =========================================================
# ENTWICKLERSCHICHT
# =========================================================

class ShiftView(View):

    def __init__(self):
        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Schicht starten",
        style=discord.ButtonStyle.success,
        emoji="▶️",
        custom_id="rlp_shift_start"
    )
    async def start_shift(
        self,
        interaction,
        button
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

        user_id = str(
            member.id
        )

        if user_id in data[
            "developer_shifts"
        ]:

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

            await member.add_roles(
                active_role,
                reason="Entwicklerschicht gestartet"
            )

        except (
            discord.Forbidden,
            discord.HTTPException
        ):

            await interaction.response.send_message(
                "❌ Die Schichtrolle konnte nicht vergeben werden.",
                ephemeral=True
            )
            return

        data[
            "developer_shifts"
        ][user_id] = {
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
        interaction,
        button
    ):

        member = interaction.guild.get_member(
            interaction.user.id
        )

        if member is None:
            return

        user_id = str(
            member.id
        )

        if user_id not in data[
            "developer_shifts"
        ]:

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

        data[
            "developer_shifts"
        ].pop(
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
    member,
    action
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

    embed.timestamp = (
        discord.utils.utcnow()
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

        async for message in channel.history(
            limit=100
        ):

            if message.author.id != bot.user.id:
                continue

            if not message.embeds:
                continue

            if (
                message.embeds[0].footer.text
                != marker
            ):
                continue

            if existing is None:
                existing = message
            else:
                await safe_delete(message)

    except (
        discord.Forbidden,
        discord.HTTPException
    ):
        return

    embed = discord.Embed(
        title="👨‍💻 Entwickler-Schicht",
        description=(
            "Hier kannst du deine Entwicklerschicht verwalten.\n\n"
            "▶️ **Schicht starten**\n"
            "Aktiviert die Schichtrolle.\n\n"
            "⏹️ **Schicht beenden**\n"
            "Entfernt die Schichtrolle.\n\n"
            "⚠️ Nur Benutzer mit der Entwickler-Berechtigungsrolle "
            "können eine Schicht starten."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=marker
    )

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
    member,
    before,
    after
):

    if member.bot:
        return

    if member.guild.id != GUILD_ID:
        return

    joined = (
        after.channel is not None
        and after.channel.id
        == SUPPORT_VOICE_CHANNEL_ID
    )

    left = (
        before.channel is not None
        and before.channel.id
        == SUPPORT_VOICE_CHANNEL_ID
    )

    if not joined and not left:
        return

    channel = bot.get_channel(
        SUPPORT_LOG_CHANNEL_ID
    )

    if channel is None:
        return

    if joined:

        data[
            "support_case_counter"
        ] += 1

        case_number = data[
            "support_case_counter"
        ]

        save_data()

        embed = discord.Embed(
            title="🎧 Support betreten",
            description=(
                f"{member.mention} hat den Support betreten."
            ),
            color=discord.Color.green()
        )

        embed.add_field(
            name="📁 Fall",
            value=f"#{case_number}"
        )

        embed.timestamp = (
            discord.utils.utcnow()
        )

        await safe_send(
            channel,
            embed=embed
        )

    elif left:

        embed = discord.Embed(
            title="🎧 Support verlassen",
            description=(
                f"{member.mention} hat den Support verlassen."
            ),
            color=discord.Color.red()
        )

        embed.timestamp = (
            discord.utils.utcnow()
        )

        await safe_send(
            channel,
            embed=embed
        )


# =========================================================
# BEWERBUNGEN
# =========================================================

class ApplicationModal(
    Modal,
    title="📝 Bewerbung"
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
        label="Warum möchtest du dich bewerben?",
        placeholder="Schreibe etwas über dich...",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True
    )

    async def on_submit(
        self,
        interaction
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
            name="👤 Bewerber",
            value=interaction.user.mention,
            inline=False
        )

        embed.add_field(
            name="📛 Name",
            value=self.name.value,
            inline=False
        )

        embed.add_field(
            name="🎂 Alter",
            value=self.age.value,
            inline=False
        )

        embed.add_field(
            name="💬 Motivation",
            value=self.reason.value,
            inline=False
        )

        embed.set_footer(
            text=f"User ID: {interaction.user.id}"
        )

        message = await safe_send(
            channel,
            embed=embed
        )

        if message:

            data[
                "applications"
            ][str(message.id)] = {
                "user_id": str(
                    interaction.user.id
                ),
                "status": "offen"
            }

            save_data()

        await interaction.response.send_message(
            "✅ Deine Bewerbung wurde eingereicht.",
            ephemeral=True
        )


class ApplicationView(View):

    def __init__(self):
        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Bewerben",
        style=discord.ButtonStyle.primary,
        emoji="📝",
        custom_id="rlp_application"
    )
    async def apply(
        self,
        interaction,
        button
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

        async for message in channel.history(
            limit=100
        ):

            if message.author.id != bot.user.id:
                continue

            if not message.embeds:
                continue

            if (
                message.embeds[0].footer.text
                != marker
            ):
                continue

            if existing is None:
                existing = message
            else:
                await safe_delete(message)

    except (
        discord.Forbidden,
        discord.HTTPException
    ):
        return

    embed = discord.Embed(
        title="📝 Bewerbungen",
        description=(
            "Du möchtest dich bei uns bewerben?\n\n"
            "Klicke auf **📝 Bewerben** und fülle das Formular aus."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=marker
    )

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
    title="🛠️ Neue Entwickler-Aufgabe"
):

    task = TextInput(
        label="Aufgabe",
        placeholder="Aufgabe beschreiben...",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True
    )

    async def on_submit(
        self,
        interaction
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

        data[
            "developer_task_counter"
        ] += 1

        task_id = data[
            "developer_task_counter"
        ]

        data[
            "developer_tasks"
        ][str(task_id)] = {
            "task": self.task.value,
            "created_by": str(
                interaction.user.id
            ),
            "completed": False
        }

        save_data()

        channel = bot.get_channel(
            DEVELOPER_TASK_CHANNEL_ID
        )

        if channel:

            embed = discord.Embed(
                title=(
                    f"🛠️ Entwickler-Aufgabe #{task_id}"
                ),
                description=self.task.value,
                color=discord.Color.orange()
            )

            embed.add_field(
                name="👤 Erstellt von",
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
        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Aufgabe erstellen",
        style=discord.ButtonStyle.primary,
        emoji="🛠️",
        custom_id="rlp_developer_task"
    )
    async def create_task(
        self,
        interaction,
        button
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

        async for message in channel.history(
            limit=100
        ):

            if message.author.id != bot.user.id:
                continue

            if not message.embeds:
                continue

            if (
                message.embeds[0].footer.text
                != marker
            ):
                continue

            if existing is None:
                existing = message
            else:
                await safe_delete(message)

    except (
        discord.Forbidden,
        discord.HTTPException
    ):
        return

    embed = discord.Embed(
        title="🛠️ Entwickler-Aufgaben",
        description=(
            "Berechtigte Entwickler können hier "
            "neue Aufgaben erstellen."
        ),
        color=discord.Color.orange()
    )

    embed.set_footer(
        text=marker
    )

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
# MEMBER EVENTS
# =========================================================

@bot.event
async def on_member_join(member):

    if member.guild.id != GUILD_ID:
        return

    await update_member_nametag(
        member
    )


@bot.event
async def on_member_update(
    before,
    after
):

    if after.guild.id != GUILD_ID:
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
        await update_member_nametag(
            after
        )


# =========================================================
# PERSISTENTE VIEWS
# =========================================================

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


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    print(
        "========================================"
    )

    print(
        f"🤖 BOT ONLINE: {bot.user}"
    )

    print(
        f"🏠 GUILD: {GUILD_ID}"
    )

    print(
        "========================================"
    )

    guild = bot.get_guild(
        GUILD_ID
    )

    if guild:

        # Nur Namen anhand bereits vorhandener
        # Nametag-Rolle synchronisieren.
        #
        # KEINE automatische Rollenvergabe.
        for member in guild.members:

            if member.bot:
                continue

            try:

                await update_member_nametag(
                    member
                )

            except Exception as error:

                print(
                    f"[NAMETAG] "
                    f"{member.id}: {error}"
                )

    await update_nametag_panel()

    await update_license_plate_panel()

    await update_application_panel()

    await update_shift_panel()

    await update_developer_task_panel()

    # Quiz-Cleanup nur einmal starten.
    if not quiz_cleanup.is_running():
        quiz_cleanup.start()

    # Erste Quizrunde starten.
    if current_quiz[
        "message_id"
    ] is None:

        await send_new_quiz()


# =========================================================
# COMMAND ERRORS
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

    print(
        f"[COMMAND ERROR] {error}"
    )


# =========================================================
# TOKEN
# =========================================================

if not TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN fehlt. "
        "Bitte das GitHub Secret DISCORD_TOKEN setzen."
    )


# =========================================================
# START
# =========================================================

bot.run(TOKEN)
