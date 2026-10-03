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
        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            loaded = json.load(file)

        if "license_plates" not in loaded:
            loaded["license_plates"] = {}

        if "developer_tasks" not in loaded:
            loaded["developer_tasks"] = {}

        return loaded

    except Exception as error:

        print(
            "❌ Fehler beim Laden der Daten:",
            error
        )

        return {
            "license_plates": {},
            "developer_tasks": {}
        }


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
            "❌ Fehler beim Speichern:",
            error
        )


data = load_data()


# =========================================================
# EMOJI QUIZ
# =========================================================

QUIZ_QUESTIONS = [

    # Länder
    ("🇺🇸🗽🍔", "Amerika"),
    ("🇩🇪🍺🥨", "Deutschland"),
    ("🇫🇷🥐🗼", "Frankreich"),
    ("🇮🇹🍕🍝", "Italien"),
    ("🇪🇸💃🌮", "Spanien"),
    ("🇬🇧👑🎡", "England"),
    ("🇯🇵🍣🗼", "Japan"),
    ("🇧🇷⚽🌴", "Brasilien"),
    ("🇨🇭🏔️🧀", "Schweiz"),
    ("🇦🇹🏔️🎿", "Österreich"),
    ("🇳🇱🌷🚲", "Niederlande"),
    ("🇬🇷🏛️🇬🇷", "Griechenland"),
    ("🇹🇷🕌🥙", "Türkei"),
    ("🇨🇦🍁🏒", "Kanada"),
    ("🇦🇺🦘🏖️", "Australien"),
    ("🇲🇽🌮🌵", "Mexiko"),
    ("🇮🇳🐘🍛", "Indien"),
    ("🇨🇳🐼🏯", "China"),
    ("🇰🇷🎮🍜", "Korea"),
    ("🇵🇹⚽🌊", "Portugal"),

    # Tiere
    ("🐶🦴🏠", "Hund"),
    ("🐱🐟🏠", "Katze"),
    ("🐭🧀", "Maus"),
    ("🐹🌻", "Hamster"),
    ("🐰🥕", "Hase"),
    ("🦊🌲", "Fuchs"),
    ("🐻🍯", "Bär"),
    ("🐼🎋", "Panda"),
    ("🐨🌿", "Koala"),
    ("🐯🌴", "Tiger"),
    ("🦁👑", "Löwe"),
    ("🐮🥛", "Kuh"),
    ("🐷🐖", "Schwein"),
    ("🐸💧", "Frosch"),
    ("🐵🍌", "Affe"),
    ("🐔🥚", "Huhn"),
    ("🐧❄️", "Pinguin"),
    ("🐦🌳", "Vogel"),
    ("🦆💧", "Ente"),
    ("🦅☁️", "Adler"),
    ("🦉🌙", "Eule"),
    ("🐺🌕", "Wolf"),
    ("🐴🏇", "Pferd"),
    ("🐑🌿", "Schaf"),
    ("🐐⛰️", "Ziege"),
    ("🦒🌳", "Giraffe"),
    ("🐘🌿", "Elefant"),
    ("🦏🌿", "Nashorn"),
    ("🦛💧", "Nilpferd"),
    ("🐊🌊", "Krokodil"),
    ("🐍🌿", "Schlange"),
    ("🐢🐢", "Schildkröte"),
    ("🐙🌊", "Oktopus"),
    ("🦀🌊", "Krabbe"),
    ("🐠🌊", "Fisch"),
    ("🐬🌊", "Delfin"),
    ("🐳🌊", "Wal"),
    ("🦈🌊", "Hai"),
    ("🦋🌸", "Schmetterling"),
    ("🐝🍯", "Biene"),
    ("🐞🌿", "Marienkäfer"),

    # Essen
    ("🍕🧀🍅", "Pizza"),
    ("🍔🍟🥤", "Burger"),
    ("🌭🥫", "Hotdog"),
    ("🍟🧂", "Pommes"),
    ("🍝🍅", "Nudeln"),
    ("🍣🍚🐟", "Sushi"),
    ("🌮🌶️", "Taco"),
    ("🥪🥬🍞", "Sandwich"),
    ("🍎🍏", "Apfel"),
    ("🍌🐒", "Banane"),
    ("🍓❤️", "Erdbeere"),
    ("🍉☀️", "Wassermelone"),
    ("🍇🍇", "Trauben"),
    ("🍒🍒", "Kirsche"),
    ("🍑🍑", "Pfirsich"),
    ("🍍🌴", "Ananas"),
    ("🥝💚", "Kiwi"),
    ("🥥🌴", "Kokosnuss"),
    ("🍋🍋", "Zitrone"),
    ("🍊🧡", "Orange"),
    ("🥕🐰", "Karotte"),
    ("🌽🌽", "Mais"),
    ("🍿🎬", "Popcorn"),
    ("🍫🍫", "Schokolade"),
    ("🍩☕", "Donut"),
    ("🍪🥛", "Keks"),
    ("🍰🎂", "Kuchen"),
    ("🍦☀️", "Eis"),
    ("🍭🍬", "Süßigkeiten"),
    ("🍯🐝", "Honig"),

    # Getränke
    ("☕🔥", "Kaffee"),
    ("🍵🌿", "Tee"),
    ("🥛🐄", "Milch"),
    ("🧃🍎", "Saft"),
    ("💧🥤", "Wasser"),
    ("🥤🧊", "Cola"),
    ("🍋🥤", "Limonade"),

    # Fahrzeuge
    ("🚗🛣️", "Auto"),
    ("🚕💰", "Taxi"),
    ("🚌👥", "Bus"),
    ("🚓🚨", "Polizei"),
    ("🚑🏥", "Krankenwagen"),
    ("🚒🔥", "Feuerwehr"),
    ("🚚📦", "LKW"),
    ("🏎️🏁", "Rennwagen"),
    ("🏍️🛣️", "Motorrad"),
    ("🚲🚴", "Fahrrad"),
    ("🛴🛣️", "Roller"),
    ("🚂🚉", "Zug"),
    ("✈️☁️", "Flugzeug"),
    ("🚁🌤️", "Helikopter"),
    ("🚢🌊", "Schiff"),
    ("⛵🌊", "Segelboot"),

    # Berufe
    ("👨‍⚕️🏥", "Arzt"),
    ("👩‍⚕️💉", "Ärztin"),
    ("👨‍🚒🔥", "Feuerwehrmann"),
    ("👮🚓", "Polizist"),
    ("👩‍🏫📚", "Lehrerin"),
    ("👨‍🍳🍳", "Koch"),
    ("👨‍🔧🔧", "Mechaniker"),
    ("👩‍💻💻", "Programmiererin"),
    ("👨‍🌾🚜", "Landwirt"),
    ("👨‍✈️✈️", "Pilot"),
    ("👨‍🎨🎨", "Künstler"),
    ("📷👤", "Fotograf"),
    ("🎤🎵", "Sänger"),
    ("🎸🎵", "Musiker"),

    # Freizeit
    ("⚽🥅🏆", "Fußball"),
    ("🏀🏀", "Basketball"),
    ("🏈🏈", "Football"),
    ("🎾🎾", "Tennis"),
    ("🏐🏐", "Volleyball"),
    ("🏓🏓", "Tischtennis"),
    ("🥊🥊", "Boxen"),
    ("🏊🌊", "Schwimmen"),
    ("🚴🏁", "Radfahren"),
    ("🎮🕹️", "Gaming"),
    ("🎬🍿", "Kino"),
    ("🎵🎧", "Musik"),
    ("📚📖", "Lesen"),
    ("🎨🖌️", "Malen"),
    ("📸📷", "Fotografie"),

    # Wetter / Natur
    ("☀️🌞", "Sonne"),
    ("🌧️☔", "Regen"),
    ("⛈️⚡", "Gewitter"),
    ("❄️⛄", "Schnee"),
    ("🌈☀️", "Regenbogen"),
    ("🌪️💨", "Tornado"),
    ("🌊🏖️", "Meer"),
    ("🏔️❄️", "Berg"),
    ("🌲🌳", "Wald"),
    ("🌴🏖️", "Palme"),
    ("🌵☀️", "Kaktus"),
    ("🌸🌺", "Blumen"),
    ("🌻☀️", "Sonnenblume"),

    # Gegenstände
    ("📱📞", "Handy"),
    ("💻⌨️🖱️", "Computer"),
    ("⌚⏰", "Uhr"),
    ("🎒📚", "Rucksack"),
    ("🔑🚪", "Schlüssel"),
    ("☂️🌧️", "Regenschirm"),
    ("🛏️😴", "Bett"),
    ("🪑🪑", "Stuhl"),
    ("🚪🏠", "Tür"),
    ("🪟🏠", "Fenster"),
    ("💡⚡", "Lampe"),
    ("🔦🌙", "Taschenlampe"),
    ("✏️📚", "Stift"),
    ("📓✏️", "Notizbuch"),
    ("🎁🎀", "Geschenk"),
    ("🎈🎉", "Ballon"),
    ("⚽🏟️", "Ball"),
    ("👓👀", "Brille"),
    ("🎧🎵", "Kopfhörer"),
    ("📺🛋️", "Fernseher"),

    # Einfach
    ("❤️💖💕", "Liebe"),
    ("😂🤣😆", "Lachen"),
    ("😴🛏️", "Schlafen"),
    ("😡🔥", "Wut"),
    ("😭💧", "Weinen"),
    ("😎🕶️", "Cool"),
    ("🎉🥳🎈", "Party"),
    ("🎂🎁🎉", "Geburtstag"),
    ("🎄🎁🎅", "Weihnachten"),
    ("🎃👻🕷️", "Halloween"),
    ("☀️🏖️🍦", "Sommer"),
    ("❄️⛄🎿", "Winter"),
    ("🌸🌷☀️", "Frühling"),
    ("🍂🍁🌧️", "Herbst"),
]


quiz_state = {
    "message_id": None,
    "answer": None,
    "round": 0,
    "starting": False
}

quiz_lock = asyncio.Lock()


# =========================================================
# QUIZ
# =========================================================

async def send_quiz_question():

    async with quiz_lock:

        # Niemals eine zweite Frage erstellen,
        # wenn bereits eine Frage aktiv ist.
        if quiz_state["message_id"] is not None:
            return

        # Schutz gegen doppelte Erstellung
        if quiz_state["starting"]:
            return

        quiz_state["starting"] = True

        try:

            channel = bot.get_channel(
                QUIZ_CHANNEL_ID
            )

            if channel is None:
                print(
                    "❌ Quiz-Kanal nicht gefunden."
                )
                return

            emoji, answer = random.choice(
                QUIZ_QUESTIONS
            )

            quiz_state["round"] += 1
            quiz_state["answer"] = answer.lower()

            embed = discord.Embed(
                title="🎯 Emoji Quiz",
                description=(
                    "**Welche Antwort passt zu diesen Emojis?**\n\n"
                    f"# {emoji}\n\n"
                    "💬 Schreibe deine Antwort in den Chat!"
                ),
                color=discord.Color.blurple()
            )

            embed.set_footer(
                text=f"Runde {quiz_state['round']}"
            )

            message = await channel.send(
                embed=embed
            )

            quiz_state["message_id"] = message.id

            print(
                f"🧠 Quiz gestartet: "
                f"{emoji} → {answer}"
            )

        except Exception as error:

            print(
                "❌ Fehler beim Quiz:",
                error
            )

            quiz_state["message_id"] = None
            quiz_state["answer"] = None

        finally:

            quiz_state["starting"] = False


async def ensure_quiz():

    if quiz_state["message_id"] is not None:
        return

    await send_quiz_question()


# =========================================================
# PANEL SEARCH
# =========================================================

async def find_panel_message(
    channel,
    marker
):

    found = None

    try:

        async for message in channel.history(
            limit=100
        ):

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
            f"❌ Panel-Suche ({marker}):",
            error
        )

    return found


# =========================================================
# NAMETAG
# =========================================================

class NametagView(
    discord.ui.View
):

    def __init__(self):
        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Nametag zurücksetzen",
        style=discord.ButtonStyle.danger,
        emoji="🗑️",
        custom_id="nametag_reset"
    )
    async def reset_nametag(
        self,
        interaction,
        button
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

        if not member.display_name.startswith(
            NAMETAG
        ):

            await interaction.response.send_message(
                "ℹ️ Du hast aktuell keinen `RLP `-Nametag.",
                ephemeral=True
            )
            return

        new_name = member.display_name[
            len(NAMETAG):
        ]

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

            print(
                "❌ Nametag Reset:",
                error
            )

            await interaction.response.send_message(
                "❌ Fehler beim Zurücksetzen.",
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

        await message.edit(
            embed=embed,
            view=NametagView()
        )

    else:

        await channel.send(
            embed=embed,
            view=NametagView()
        )


# =========================================================
# KENNZEICHEN
# =========================================================

def get_plate_number(
    plate
):

    parts = plate.strip().split()

    if not parts:
        return None

    last = parts[-1]

    if not last.isdigit():
        return None

    return int(last)


def plate_number_used(
    number
):

    for plate in data[
        "license_plates"
    ].values():

        if get_plate_number(plate) == number:
            return True

    return False


class LicensePlateModal(
    discord.ui.Modal
):

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

        self.add_item(
            self.plate
        )

    async def on_submit(
        self,
        interaction
    ):

        plate = self.plate.value.strip()

        number = get_plate_number(
            plate
        )

        if number is None:

            await interaction.response.send_message(
                "❌ Das Kennzeichen muss mit einer Nummer enden.\n"
                "Beispiel: `RLP 01`",
                ephemeral=True
            )
            return

        if plate_number_used(
            number
        ):

            await interaction.response.send_message(
                "❌ Diese Nummer ist bereits vergeben.",
                ephemeral=True
            )
            return

        user_id = str(
            interaction.user.id
        )

        if user_id in data[
            "license_plates"
        ]:

            await interaction.response.send_message(
                "❌ Du hast bereits ein Kennzeichen.",
                ephemeral=True
            )
            return

        data[
            "license_plates"
        ][user_id] = plate

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
        interaction
    ):

        user_id = str(
            interaction.user.id
        )

        if user_id not in data[
            "license_plates"
        ]:

            await interaction.response.send_message(
                "❌ Du hast kein registriertes Kennzeichen.",
                ephemeral=True
            )
            return

        plate = data[
            "license_plates"
        ].pop(
            user_id
        )

        save_data()

        await update_license_plate_panel()

        await interaction.response.send_message(
            f"✅ Kennzeichen **{plate}** wurde gelöscht.",
            ephemeral=True
        )


class LicensePlateView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

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


async def update_license_plate_panel():

    channel = bot.get_channel(
        LICENSE_PLATE_CHANNEL_ID
    )

    if channel is None:
        return

    if data[
        "license_plates"
    ]:

        lines = []

        for user_id, plate in data[
            "license_plates"
        ].items():

            member = channel.guild.get_member(
                int(user_id)
            )

            name = (
                member.display_name
                if member
                else f"User {user_id}"
            )

            lines.append(
                f"🚗 **{plate}** — {name}"
            )

        description = "\n".join(
            lines
        )

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
            "Die letzte Zahl muss global eindeutig sein."
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
# SCHICHT
# =========================================================

class ShiftView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Schicht starten",
        style=discord.ButtonStyle.success,
        emoji="🟢",
        custom_id="shift_start"
    )
    async def start_shift(
        self,
        interaction,
        button
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

        if (
            member is None
            or permission_role is None
            or active_role is None
        ):

            await interaction.response.send_message(
                "❌ Rollen konnten nicht gefunden werden.",
                ephemeral=True
            )
            return

        if permission_role not in member.roles:

            await interaction.response.send_message(
                "❌ Du hast keine Berechtigung.",
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

        except Exception as error:

            print(
                "❌ Schichtstart:",
                error
            )

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
        interaction,
        button
    ):

        member = interaction.guild.get_member(
            interaction.user.id
        )

        active_role = interaction.guild.get_role(
            DEVELOPER_SHIFT_ROLE_ID
        )

        if (
            member is None
            or active_role is None
        ):

            await interaction.response.send_message(
                "❌ Rolle konnte nicht gefunden werden.",
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

        except Exception as error:

            print(
                "❌ Schichtende:",
                error
            )


async def update_shift_panel():

    channel = bot.get_channel(
        DEVELOPER_SHIFT_CHANNEL_ID
    )

    if channel is None:
        return

    embed = discord.Embed(
        title="🛠️ Entwickler-Schicht",
        description=(
            "Nutze die Buttons unten.\n\n"
            "🟢 Schicht starten\n"
            "🔴 Schicht beenden"
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

class ApplicationModal(
    discord.ui.Modal
):

    def __init__(self):

        super().__init__(
            title="Bewerbung"
        )

        self.name = discord.ui.TextInput(
            label="Name",
            required=True,
            max_length=100
        )

        self.age = discord.ui.TextInput(
            label="Alter",
            required=True,
            max_length=3
        )

        self.reason = discord.ui.TextInput(
            label="Warum möchtest du dich bewerben?",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )

        self.add_item(self.name)
        self.add_item(self.age)
        self.add_item(self.reason)

    async def on_submit(
        self,
        interaction
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

        await channel.send(
            embed=embed
        )

        await interaction.response.send_message(
            "✅ Deine Bewerbung wurde abgeschickt.",
            ephemeral=True
        )


class ApplicationView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Bewerbung starten",
        style=discord.ButtonStyle.success,
        emoji="📨",
        custom_id="application_start"
    )
    async def application_button(
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

    embed = discord.Embed(
        title="📨 Bewerbungen",
        description=(
            "Du möchtest dich bewerben?\n\n"
            "Klicke unten auf **Bewerbung starten**."
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
# DEV AUFGABEN
# =========================================================

class DeveloperTaskModal(
    discord.ui.Modal
):

    def __init__(self):

        super().__init__(
            title="Neue Entwickler-Aufgabe"
        )

        self.title_input = discord.ui.TextInput(
            label="Titel",
            required=True,
            max_length=100
        )

        self.description = discord.ui.TextInput(
            label="Beschreibung",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1500
        )

        self.add_item(
            self.title_input
        )

        self.add_item(
            self.description
        )

    async def on_submit(
        self,
        interaction
    ):

        member = interaction.guild.get_member(
            interaction.user.id
        )

        role = interaction.guild.get_role(
            SHIFT_PERMISSION_ROLE_ID
        )

        if (
            member is None
            or role is None
            or role not in member.roles
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        task_id = str(
            max(
                [
                    int(x)
                    for x in data[
                        "developer_tasks"
                    ].keys()
                ] + [0]
            ) + 1
        )

        data[
            "developer_tasks"
        ][task_id] = {
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

        await interaction.response.send_message(
            f"✅ Aufgabe #{task_id} erstellt.",
            ephemeral=True
        )


class DeveloperTaskView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Aufgabe erstellen",
        style=discord.ButtonStyle.primary,
        emoji="🛠️",
        custom_id="dev_task_create"
    )
    async def create_task(
        self,
        interaction,
        button
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
            "Berechtigte Entwickler können "
            "hier neue Aufgaben erstellen."
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
# OWNER PANEL
# =========================================================

class OwnerPanelView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    async def check_owner(
        self,
        interaction
    ):

        role = interaction.guild.get_role(
            OWNER_ROLE_ID
        )

        return (
            role is not None
            and role in interaction.user.roles
        )


    @discord.ui.button(
        label="Ankündigung",
        style=discord.ButtonStyle.primary,
        emoji="📢",
        custom_id="owner_announcement"
    )
    async def announcement(
        self,
        interaction,
        button
    ):

        if not await self.check_owner(
            interaction
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "📢 Wähle einen Channel aus.",
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
        interaction,
        button
    ):

        if not await self.check_owner(
            interaction
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "💬 Funktion bereit.",
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
        interaction,
        button
    ):

        if not await self.check_owner(
            interaction
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        await ensure_quiz()

        await interaction.response.send_message(
            "🎮 Quiz ist aktiv.",
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
        interaction,
        button
    ):

        if not await self.check_owner(
            interaction
        ):

            await interaction.response.send_message(
                "❌ Keine Berechtigung.",
                ephemeral=True
            )
            return

        channel = bot.get_channel(
            QUIZ_CHANNEL_ID
        )

        old_id = quiz_state[
            "message_id"
        ]

        quiz_state[
            "message_id"
        ] = None

        quiz_state[
            "answer"
        ] = None

        if channel and old_id:

            try:

                old_message = await channel.fetch_message(
                    old_id
                )

                await old_message.delete()

            except Exception:
                pass

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
        interaction,
        button
    ):

        if not await self.check_owner(
            interaction
        ):

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
            value=f"{latency} ms"
        )

        embed.add_field(
            name="🌐 Server",
            value=str(
                len(bot.guilds)
            )
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
        interaction,
        button
    ):

        if not await self.check_owner(
            interaction
        ):

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
            value=str(
                guild.member_count
            )
        )

        embed.add_field(
            name="💬 Textkanäle",
            value=str(
                len(guild.text_channels)
            )
        )

        embed.add_field(
            name="🔊 Sprachkanäle",
            value=str(
                len(guild.voice_channels)
            )
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


async def update_owner_panel():

    guild = bot.get_guild(
        GUILD_ID
    )

    if guild is None:
        return

    for channel in guild.text_channels:

        try:

            message = await find_panel_message(
                channel,
                OWNER_PANEL_MARKER
            )

            if message:

                embed = discord.Embed(
                    title="👑 Owner Control Center",
                    description=(
                        "Verwaltung des Servers.\n\n"
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

                return

        except Exception as error:

            print(
                "❌ Owner Panel:",
                error
            )


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
            "in den jeweiligen Panels."
        ),
        color=discord.Color.blurple()
    )

    await ctx.send(
        embed=embed
    )


@bot.command()
@commands.has_role(
    OWNER_ROLE_ID
)
async def ownerpanel(ctx):

    embed = discord.Embed(
        title="👑 Owner Control Center",
        description=(
            "Verwaltung des Servers.\n\n"
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
@commands.has_role(
    OWNER_ROLE_ID
)
async def owner(ctx):

    await ownerpanel(
        ctx
    )


@bot.command()
async def nametag(ctx):

    await update_nametag_panel()

    await ctx.send(
        "🏷️ Nametag-Panel aktualisiert.",
        delete_after=5
    )


@bot.command()
async def kennzeichen(ctx):

    await update_license_plate_panel()

    await ctx.send(
        "🚗 Kennzeichen-Panel aktualisiert.",
        delete_after=5
    )


@bot.command()
async def schicht(ctx):

    await update_shift_panel()

    await ctx.send(
        "🛠️ Schicht-Panel aktualisiert.",
        delete_after=5
    )


@bot.command()
async def bewerbung(ctx):

    await update_application_panel()

    await ctx.send(
        "📨 Bewerbungs-Panel aktualisiert.",
        delete_after=5
    )


@bot.command()
@commands.has_role(
    SHIFT_PERMISSION_ROLE_ID
)
async def devtask(ctx):

    await update_dev_task_panel()

    await ctx.send(
        "🛠️ Dev-Aufgaben-Panel aktualisiert.",
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

    log_channel = bot.get_channel(
        SUPPORT_LOG_CHANNEL_ID
    )

    if (
        after.channel
        and after.channel.id
        == SUPPORT_VOICE_CHANNEL_ID
    ):

        if log_channel:

            await log_channel.send(
                f"🔊 **Support beigetreten**\n"
                f"{member.mention}"
            )

    elif (
        before.channel
        and before.channel.id
        == SUPPORT_VOICE_CHANNEL_ID
    ):

        if log_channel:

            await log_channel.send(
                f"🔇 **Support verlassen**\n"
                f"{member.mention}"
            )


# =========================================================
# QUIZ HEALTH CHECK
# =========================================================

@tasks.loop(seconds=5)
async def quiz_cleanup():

    try:

        # Nur wenn keine aktive Frage existiert,
        # wird eine neue erstellt.
        if quiz_state["message_id"] is None:

            await send_quiz_question()

    except Exception as error:

        print(
            "❌ Quiz Health Check:",
            error
        )


# =========================================================
# MESSAGE HANDLER
# =========================================================

@bot.event
async def on_message(
    message
):

    if message.author.bot:
        return

    # =====================================================
    # QUIZ CHANNEL
    # =====================================================

    if message.channel.id == QUIZ_CHANNEL_ID:

        # Jede User-Nachricht 6 Sekunden sichtbar
        async def delete_user_message():

            await asyncio.sleep(6)

            try:

                await message.delete()

            except Exception:
                pass

        asyncio.create_task(
            delete_user_message()
        )

        content = (
            message.content
            .strip()
            .lower()
        )

        # =================================================
        # Antwort prüfen
        # =================================================

        async with quiz_lock:

            answer = quiz_state[
                "answer"
            ]

            quiz_message_id = quiz_state[
                "message_id"
            ]

            # Keine aktive Frage
            if (
                answer is None
                or quiz_message_id is None
            ):

                return

            # FALSCH
            if content != answer:

                try:

                    result = await message.channel.send(
                        f"❌ **{message.author.mention}**, "
                        "das war leider falsch! 😄"
                    )

                    async def delete_wrong_result():

                        await asyncio.sleep(4)

                        try:
                            await result.delete()
                        except Exception:
                            pass

                    asyncio.create_task(
                        delete_wrong_result()
                    )

                except Exception as error:

                    print(
                        "❌ Fehler bei falscher Antwort:",
                        error
                    )

                return

            # =================================================
            # RICHTIG
            # =================================================

            # Frage sofort reservieren.
            # Dadurch kann niemand eine zweite neue
            # Quizfrage gleichzeitig erzeugen.
            quiz_state[
                "message_id"
            ] = None

            quiz_state[
                "answer"
            ] = None

        # =================================================
        # Alte Frage löschen
        # =================================================

        try:

            old_quiz = await message.channel.fetch_message(
                quiz_message_id
            )

            await old_quiz.delete()

        except Exception:
            pass

        # =================================================
        # Gewinnmeldung
        # =================================================

        try:

            result = await message.channel.send(
                f"🎉 **{message.author.mention}** "
                f"hat richtig geantwortet! 🏆\n"
                f"Die Antwort war **{answer.title()}**! 🎯"
            )

            # Bot-Antwort 4 Sekunden
            await asyncio.sleep(4)

            try:

                await result.delete()

            except Exception:
                pass

        except Exception as error:

            print(
                "❌ Fehler bei richtiger Antwort:",
                error
            )

        # =================================================
        # GENAU EINE neue Frage
        # =================================================

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
            "❌ Du hast keine Berechtigung.",
            delete_after=5
        )

        return

    print(
        "❌ Command Fehler:",
        error
    )


# =========================================================
# PANELS AKTUALISIEREN
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
            "✅ Owner Panel aktualisiert."
        )

    except Exception as error:

        print(
            "❌ Owner Panel:",
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

    # Keine automatischen Nametag-Änderungen
    # Keine automatische Rollenvergabe
    # Keine Wiederherstellung von Schichten

    await update_all_panels()

    # Genau eine aktive Quizfrage sicherstellen
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
