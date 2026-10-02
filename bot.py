```python
import os
import json
import random
import string
import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands


# ============================================================
#                         KONFIGURATION
# ============================================================

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")

GUILD_ID = 1519481018221072454

# -------------------------
# CHANNELS
# -------------------------

QUIZ_CHANNEL_ID = 1533409789256925185

APPLICATION_CHANNEL_ID = 1541391365219295343
REVIEW_CHANNEL_ID = 1548404201493762181

NICKNAME_CHANNEL_ID = 1555684071911202836

# Support-Call
SUPPORT_VOICE_CHANNEL_ID = 1519788919254679602

# Support-Abschlussberichte / Support-Panel
SUPPORT_LOG_CHANNEL_ID = 1521439818146648064

# Teamler-Registrierung
TEAM_REGISTER_CHANNEL_ID = 1527350468832006276

# Developer
DEVELOPER_TASK_CHANNEL_ID = 1540442867334385715
DEVELOPER_SHIFT_CHANNEL_ID = 1540797414863151155


# -------------------------
# ROLES
# -------------------------

NAMETAG_ROLE_ID = 1520102928398942348

# Nur diese Rolle darf !quiz benutzen
QUIZ_COMMAND_ROLE_ID = 1530188150456979526


# -------------------------
# NAMETAG
# -------------------------

NAMETAG = "RLP "


# -------------------------
# DATEI
# -------------------------

DATA_FILE = "bot_data.json"


# ============================================================
#                         INTENTS
# ============================================================

intents = discord.Intents.default()

intents.message_content = True
intents.members = True
intents.presences = True
intents.voice_states = True


# ============================================================
#                         DATEN
# ============================================================

nametag_removed_users = set()

quiz_scores = {}

active_support_cases = {}

active_team_members = set()

active_developer_shifts = {}

developer_tasks = []

active_applications = {}

quiz_bag = []

current_quiz = None
current_quiz_message = None

quiz_lock = asyncio.Lock()

startup_finished = False


# ============================================================
#                         HILFSFUNKTIONEN
# ============================================================

def now():
    return datetime.now(timezone.utc)


def normalize(value):
    return " ".join(
        str(value).strip().lower().split()
    )


def format_datetime(dt):
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)

    return dt.astimezone().strftime(
        "%d.%m.%Y %H:%M"
    )


def format_duration(seconds):
    seconds = max(0, int(seconds))

    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours:
        return f"{hours} Std. {minutes} Min."

    if minutes:
        return f"{minutes} Min. {seconds} Sek."

    return f"{seconds} Sek."


def generate_case_id():
    letters = string.ascii_uppercase

    return "#S-" + "".join(
        random.choice(letters)
        for _ in range(10)
    )


async def safe_delete(message):
    try:
        await message.delete()
    except Exception:
        pass


def base_embed(
    title,
    description="",
    color=None
):
    if color is None:
        color = discord.Color.blurple()

    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=now()
    )

    embed.set_footer(
        text="RLP System"
    )

    return embed


async def clean_bot_panel(
    channel,
    title
):
    if not hasattr(channel, "history"):
        return

    async for message in channel.history(
        limit=None
    ):
        if (
            message.author == bot.user
            and message.embeds
            and message.embeds[0].title == title
        ):
            await safe_delete(message)

            await asyncio.sleep(0.1)


# ============================================================
#                         DATENBANK
# ============================================================

def load_data():
    global nametag_removed_users
    global quiz_scores
    global active_team_members
    global active_developer_shifts
    global developer_tasks

    if not os.path.exists(DATA_FILE):
        return

    try:
        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        nametag_removed_users = set(
            int(user_id)
            for user_id in data.get(
                "nametag_removed_users",
                []
            )
        )

        quiz_scores = {
            str(user_id): int(score)
            for user_id, score
            in data.get(
                "quiz_scores",
                {}
            ).items()
        }

        active_team_members = set(
            int(user_id)
            for user_id in data.get(
                "active_team_members",
                []
            )
        )

        active_developer_shifts = {
            str(user_id): value
            for user_id, value
            in data.get(
                "active_developer_shifts",
                {}
            ).items()
        }

        developer_tasks = data.get(
            "developer_tasks",
            []
        )

        print("[DATA] Daten erfolgreich geladen.")

    except Exception as error:
        print(
            f"[DATA] Fehler beim Laden: {error}"
        )


def save_data():
    try:
        data = {
            "nametag_removed_users": list(
                nametag_removed_users
            ),

            "quiz_scores": quiz_scores,

            "active_team_members": list(
                active_team_members
            ),

            "active_developer_shifts":
                active_developer_shifts,

            "developer_tasks":
                developer_tasks
        }

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


# ============================================================
#                         NAMETAG SYSTEM
# ============================================================

def get_clean_name(member):
    name = member.display_name

    while name.startswith(NAMETAG):
        name = name[len(NAMETAG):]

    return name.strip()


async def set_rlp_nickname(
    member,
    force=False
):
    if not isinstance(
        member,
        discord.Member
    ):
        return

    role = member.guild.get_role(
        NAMETAG_ROLE_ID
    )

    if role is None:
        return

    if role not in member.roles:
        return

    # Wenn der Nutzer das Nametag selbst entfernt hat,
    # bleibt es normalerweise entfernt.
    if (
        member.id in nametag_removed_users
        and not force
    ):
        return

    # Rolle wurde neu vergeben -> Nametag wieder aktivieren.
    if force:
        nametag_removed_users.discard(
            member.id
        )

        save_data()

    clean_name = get_clean_name(
        member
    )

    nickname = f"{NAMETAG}{clean_name}"

    if len(nickname) > 32:
        nickname = nickname[:32]

    try:
        if member.nick != nickname:
            await member.edit(
                nick=nickname,
                reason="RLP Nametag System"
            )

    except discord.Forbidden:
        print(
            f"[NAMETAG] Keine Rechte für {member}"
        )

    except discord.HTTPException as error:
        print(
            f"[NAMETAG] Discord-Fehler: {error}"
        )


async def remove_rlp_nickname(member):
    clean_name = get_clean_name(
        member
    )

    nametag_removed_users.add(
        member.id
    )

    save_data()

    try:
        await member.edit(
            nick=clean_name,
            reason="RLP Nametag entfernt"
        )

    except discord.Forbidden:
        pass

    except discord.HTTPException:
        pass


async def update_all_rlp_nicknames():
    guild = bot.get_guild(
        GUILD_ID
    )

    if guild is None:
        return

    role = guild.get_role(
        NAMETAG_ROLE_ID
    )

    if role is None:
        print(
            "[NAMETAG] Rolle nicht gefunden."
        )
        return

    for member in role.members:
        await set_rlp_nickname(
            member
        )

        await asyncio.sleep(0.05)


# ============================================================
#                         NAMETAG PANEL
# ============================================================

class NicknamePanelView(
    discord.ui.View
):

    def __init__(self):
        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Nametag entfernen",
        emoji="🏷️",
        style=discord.ButtonStyle.secondary,
        custom_id="rlp_remove_nametag"
    )
    async def remove_nametag(
        self,
        interaction,
        button
    ):
        if not isinstance(
            interaction.user,
            discord.Member
        ):
            return

        await remove_rlp_nickname(
            interaction.user
        )

        embed = base_embed(
            "🏷️ Nametag entfernt",
            (
                "Dein **RLP Nametag** wurde "
                "erfolgreich entfernt.\n\n"
                "Wenn dir die RLP-Rolle später "
                "neu gegeben wird, wird das "
                "Nametag automatisch wieder gesetzt."
            ),
            discord.Color.green()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


async def send_nickname_panel():
    channel = bot.get_channel(
        NICKNAME_CHANNEL_ID
    )

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        return

    await clean_bot_panel(
        channel,
        "🏷️ Nametag-System"
    )

    embed = base_embed(
        "🏷️ Nametag-System",
        (
            "Hier kannst du dein **RLP Nametag** verwalten.\n\n"
            "🏷️ **Nametag entfernen**\n"
            "Entfernt `RLP ` aus deinem Namen.\n\n"
            "🔄 **Automatisch**\n"
            "Wenn dir die RLP-Rolle später erneut gegeben "
            "wird, wird das Nametag automatisch wieder gesetzt."
        )
    )

    await channel.send(
        embed=embed,
        view=NicknamePanelView()
    )


# ============================================================
#                         QUIZ DATEN
# ============================================================

COUNTRIES = [
    ("🇩🇪", "Deutschland"),
    ("🇫🇷", "Frankreich"),
    ("🇮🇹", "Italien"),
    ("🇪🇸", "Spanien"),
    ("🇬🇧", "Vereinigtes Königreich"),
    ("🇺🇸", "USA"),
    ("🇨🇦", "Kanada"),
    ("🇯🇵", "Japan"),
    ("🇰🇷", "Südkorea"),
    ("🇨🇳", "China"),
    ("🇧🇷", "Brasilien"),
    ("🇦🇷", "Argentinien"),
    ("🇲🇽", "Mexiko"),
    ("🇦🇺", "Australien"),
    ("🇳🇿", "Neuseeland"),
    ("🇳🇴", "Norwegen"),
    ("🇸🇪", "Schweden"),
    ("🇫🇮", "Finnland"),
    ("🇩🇰", "Dänemark"),
    ("🇳🇱", "Niederlande"),
    ("🇧🇪", "Belgien"),
    ("🇨🇭", "Schweiz"),
    ("🇦🇹", "Österreich"),
    ("🇵🇱", "Polen"),
    ("🇨🇿", "Tschechien"),
    ("🇬🇷", "Griechenland"),
    ("🇵🇹", "Portugal"),
    ("🇮🇪", "Irland"),
    ("🇮🇸", "Island"),
    ("🇹🇷", "Türkei"),
    ("🇷🇺", "Russland"),
    ("🇺🇦", "Ukraine"),
    ("🇮🇳", "Indien"),
    ("🇿🇦", "Südafrika"),
    ("🇪🇬", "Ägypten"),
    ("🇲🇦", "Marokko"),
    ("🇸🇦", "Saudi-Arabien"),
    ("🇦🇪", "Vereinigte Arabische Emirate"),
    ("🇮🇱", "Israel"),
    ("🇹🇭", "Thailand"),
    ("🇻🇳", "Vietnam"),
    ("🇸🇬", "Singapur"),
    ("🇮🇩", "Indonesien"),
    ("🇵🇭", "Philippinen"),
    ("🇲🇾", "Malaysia"),
    ("🇨🇱", "Chile"),
    ("🇨🇴", "Kolumbien"),
    ("🇵🇪", "Peru"),
    ("🇺🇾", "Uruguay"),
    ("🇨🇺", "Kuba"),
]

COLORS = [
    ("🔴", "Rot"),
    ("🔵", "Blau"),
    ("🟢", "Grün"),
    ("🟡", "Gelb"),
    ("🟠", "Orange"),
    ("🟣", "Lila"),
    ("⚫", "Schwarz"),
    ("⚪", "Weiß"),
    ("🟤", "Braun"),
    ("🩷", "Pink"),
    ("🩵", "Hellblau"),
    ("🩶", "Grau"),
]

ANIMALS = [
    ("🐶", "Hund"),
    ("🐱", "Katze"),
    ("🦁", "Löwe"),
    ("🐯", "Tiger"),
    ("🐻", "Bär"),
    ("🐼", "Panda"),
    ("🐨", "Koala"),
    ("🐵", "Affe"),
    ("🦊", "Fuchs"),
    ("🐺", "Wolf"),
    ("🐸", "Frosch"),
    ("🐰", "Hase"),
    ("🐭", "Maus"),
    ("🐹", "Hamster"),
    ("🐮", "Kuh"),
    ("🐷", "Schwein"),
    ("🐔", "Huhn"),
    ("🐧", "Pinguin"),
    ("🐦", "Vogel"),
    ("🦆", "Ente"),
    ("🦅", "Adler"),
    ("🦉", "Eule"),
    ("🐗", "Wildschwein"),
    ("🐴", "Pferd"),
    ("🦄", "Einhorn"),
    ("🐝", "Biene"),
    ("🦋", "Schmetterling"),
    ("🐢", "Schildkröte"),
    ("🐍", "Schlange"),
    ("🦎", "Eidechse"),
    ("🐊", "Krokodil"),
    ("🐬", "Delfin"),
    ("🐳", "Wal"),
    ("🦈", "Hai"),
    ("🐙", "Oktopus"),
    ("🦀", "Krabbe"),
]

FOOD = [
    ("🍕", "Pizza"),
    ("🍔", "Burger"),
    ("🍟", "Pommes"),
    ("🌭", "Hotdog"),
    ("🌮", "Taco"),
    ("🌯", "Burrito"),
    ("🍝", "Pasta"),
    ("🍜", "Nudeln"),
    ("🍣", "Sushi"),
    ("🍚", "Reis"),
    ("🍛", "Curry"),
    ("🍱", "Bento"),
    ("🥪", "Sandwich"),
    ("🥗", "Salat"),
    ("🍳", "Ei"),
    ("🥞", "Pfannkuchen"),
    ("🧇", "Waffel"),
    ("🍩", "Donut"),
    ("🍪", "Keks"),
    ("🎂", "Kuchen"),
    ("🍰", "Torte"),
    ("🍫", "Schokolade"),
    ("🍿", "Popcorn"),
    ("🍎", "Apfel"),
    ("🍌", "Banane"),
    ("🍓", "Erdbeere"),
    ("🍉", "Wassermelone"),
    ("🍇", "Trauben"),
    ("🍒", "Kirsche"),
    ("🥝", "Kiwi"),
    ("🥭", "Mango"),
    ("🍍", "Ananas"),
]

DRINKS = [
    ("🥤", "Softdrink"),
    ("🧃", "Saft"),
    ("☕", "Kaffee"),
    ("🍵", "Tee"),
    ("🥛", "Milch"),
    ("🧋", "Bubble Tea"),
    ("🍹", "Cocktail"),
    ("🧊", "Eisgetränk"),
]

VEHICLES = [
    ("🚗", "Auto"),
    ("🚕", "Taxi"),
    ("🚌", "Bus"),
    ("🚓", "Polizeiauto"),
    ("🚑", "Krankenwagen"),
    ("🚒", "Feuerwehr"),
    ("🚚", "LKW"),
    ("🏎️", "Rennwagen"),
    ("🚲", "Fahrrad"),
    ("🏍️", "Motorrad"),
    ("🚜", "Traktor"),
    ("✈️", "Flugzeug"),
    ("🚁", "Helikopter"),
    ("🚀", "Rakete"),
    ("🚢", "Schiff"),
    ("⛵", "Segelboot"),
    ("🚂", "Zug"),
    ("🚇", "U-Bahn"),
]

SPORTS = [
    ("⚽", "Fußball"),
    ("🏀", "Basketball"),
    ("🏈", "American Football"),
    ("⚾", "Baseball"),
    ("🎾", "Tennis"),
    ("🏐", "Volleyball"),
    ("🏉", "Rugby"),
    ("🥊", "Boxen"),
    ("🥋", "Kampfsport"),
    ("🏓", "Tischtennis"),
    ("🏸", "Badminton"),
    ("⛳", "Golf"),
    ("🏹", "Bogenschießen"),
    ("🎳", "Bowling"),
    ("🏊", "Schwimmen"),
    ("🚴", "Radsport"),
    ("⛷️", "Skifahren"),
    ("🏆", "Wettkampf"),
]

NATURE = [
    ("🌳", "Baum"),
    ("🌲", "Nadelbaum"),
    ("🌴", "Palme"),
    ("🌵", "Kaktus"),
    ("🌻", "Sonnenblume"),
    ("🌹", "Rose"),
    ("🌷", "Tulpe"),
    ("🌸", "Blüte"),
    ("🍀", "Klee"),
    ("🌱", "Pflanze"),
    ("🌿", "Kräuter"),
    ("🍁", "Ahornblatt"),
    ("🍂", "Herbstblatt"),
    ("🌊", "Welle"),
    ("🔥", "Feuer"),
    ("❄️", "Schnee"),
    ("☀️", "Sonne"),
    ("🌙", "Mond"),
    ("⭐", "Stern"),
    ("🌈", "Regenbogen"),
]

TECH = [
    ("💻", "Laptop"),
    ("🖥️", "Computer"),
    ("📱", "Smartphone"),
    ("⌨️", "Tastatur"),
    ("🖱️", "Maus"),
    ("🎧", "Kopfhörer"),
    ("📷", "Kamera"),
    ("📺", "Fernseher"),
    ("🎮", "Controller"),
    ("🕹️", "Joystick"),
    ("💾", "Diskette"),
    ("💿", "CD"),
    ("🔋", "Batterie"),
    ("🔌", "Stecker"),
    ("📡", "Antenne"),
    ("🤖", "Roboter"),
]

JOBS = [
    ("👨‍💻", "Developer"),
    ("👨‍⚕️", "Arzt"),
    ("👨‍🚒", "Feuerwehrmann"),
    ("👮", "Polizist"),
    ("👨‍🏫", "Lehrer"),
    ("👨‍🍳", "Koch"),
    ("👨‍🔧", "Mechaniker"),
    ("👨‍🎨", "Künstler"),
    ("👨‍✈️", "Pilot"),
    ("👨‍🌾", "Landwirt"),
    ("🧑‍💼", "Manager"),
    ("🧑‍⚖️", "Richter"),
    ("🕵️", "Detektiv"),
    ("🧑‍🚀", "Astronaut"),
    ("🎤", "Sänger"),
]

OBJECTS = [
    ("🔑", "Schlüssel"),
    ("🔒", "Schloss"),
    ("🎒", "Rucksack"),
    ("📚", "Bücher"),
    ("✏️", "Stift"),
    ("📏", "Lineal"),
    ("🕒", "Uhr"),
    ("💡", "Glühbirne"),
    ("🔨", "Hammer"),
    ("🪛", "Schraubenzieher"),
    ("🧹", "Besen"),
    ("🪑", "Stuhl"),
    ("🛏️", "Bett"),
    ("🚪", "Tür"),
    ("🪟", "Fenster"),
    ("🎁", "Geschenk"),
]


def create_quiz(
    category_name,
    category
):
    correct = random.choice(
        category
    )

    wrong_pool = [
        item
        for item in category
        if item != correct
    ]

    wrong = random.sample(
        wrong_pool,
        min(3, len(wrong_pool))
    )

    options = [
        correct,
        *wrong
    ]

    random.shuffle(
        options
    )

    return {
        "category": category_name,
        "emoji": correct[0],
        "answer": correct[1],
        "options": options,
        "correct_position":
            options.index(correct)
    }


def build_quizzes():
    quizzes = []

    categories = [
        ("Länder", COUNTRIES),
        ("Farben", COLORS),
        ("Tiere", ANIMALS),
        ("Essen", FOOD),
        ("Getränke", DRINKS),
        ("Fahrzeuge", VEHICLES),
        ("Sport", SPORTS),
        ("Natur", NATURE),
        ("Technik", TECH),
        ("Berufe", JOBS),
        ("Gegenstände", OBJECTS),
    ]

    for category_name, category in categories:
        amount = min(
            len(category),
            30
        )

        for _ in range(amount):
            quizzes.append(
                create_quiz(
                    category_name,
                    category
                )
            )

    return quizzes


QUIZZES = build_quizzes()


# ============================================================
#                         QUIZ SYSTEM
# ============================================================

def refill_quiz_bag():
    global quiz_bag

    quiz_bag = list(
        range(len(QUIZZES))
    )

    random.shuffle(
        quiz_bag
    )


async def send_new_quiz(channel):
    global current_quiz
    global current_quiz_message

    if channel is None:
        return

    async with quiz_lock:

        if not quiz_bag:
            refill_quiz_bag()

        index = quiz_bag.pop()

        current_quiz = QUIZZES[index]

        quiz = current_quiz

        embed = base_embed(
            "🧩 Emoji-Quiz",
            (
                f"**Kategorie:** {quiz['category']}\n\n"
                "Welcher Begriff gehört zu diesem Emoji?\n\n"
                f"# {quiz['emoji']}"
            )
        )

        view = QuizView(
            quiz
        )

        message = await channel.send(
            embed=embed,
            view=view
        )

        current_quiz_message = message


class QuizAnswerButton(
    discord.ui.Button
):

    def __init__(
        self,
        position,
        label
    ):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.primary,
            custom_id=f"quiz_answer_{position}"
        )

        self.position = position

    async def callback(
        self,
        interaction
    ):
        global current_quiz
        global current_quiz_message

        if current_quiz is None:
            await interaction.response.send_message(
                "❌ Dieses Quiz ist nicht mehr aktiv.",
                ephemeral=True
            )
            return

        if (
            current_quiz_message is None
            or interaction.message.id
            != current_quiz_message.id
        ):
            await interaction.response.send_message(
                "❌ Dieses Quiz ist nicht mehr aktiv.",
                ephemeral=True
            )
            return

        quiz = current_quiz

        if self.position != quiz[
            "correct_position"
        ]:

            await interaction.response.send_message(
                "❌ Falsch! Versuch es weiter.",
                ephemeral=True
            )

            return

        user_id = str(
            interaction.user.id
        )

        quiz_scores[user_id] = (
            quiz_scores.get(
                user_id,
                0
            ) + 1
        )

        save_data()

        current_quiz = None

        embed = base_embed(
            "✅ Richtige Antwort!",
            (
                f"{interaction.user.mention} "
                "hat die richtige Antwort gewählt.\n\n"
                f"**Antwort:** {quiz['answer']}\n"
                "**+1 Punkt**"
            ),
            discord.Color.green()
        )

        await interaction.response.edit_message(
            embed=embed,
            view=None
        )

        await asyncio.sleep(3)

        if interaction.channel:
            await send_new_quiz(
                interaction.channel
            )


class QuizHintButton(
    discord.ui.Button
):

    def __init__(self):
        super().__init__(
            label="Hinweis",
            emoji="💡",
            style=discord.ButtonStyle.secondary,
            custom_id="quiz_hint_button"
        )

    async def callback(
        self,
        interaction
    ):
        if current_quiz is None:
            await interaction.response.send_message(
                "❌ Kein aktives Quiz.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            (
                f"💡 Der Begriff gehört zur "
                f"Kategorie **{current_quiz['category']}**."
            ),
            ephemeral=True
        )


class QuizSkipButton(
    discord.ui.Button
):

    def __init__(self):
        super().__init__(
            label="Überspringen",
            emoji="⏭️",
            style=discord.ButtonStyle.danger,
            custom_id="quiz_skip_button"
        )

    async def callback(
        self,
        interaction
    ):
        global current_quiz

        if current_quiz is None:
            await interaction.response.send_message(
                "❌ Kein aktives Quiz.",
                ephemeral=True
            )
            return

        current_quiz = None

        await interaction.response.edit_message(
            embed=base_embed(
                "⏭️ Quiz übersprungen",
                "Das Quiz wurde übersprungen.",
                discord.Color.orange()
            ),
            view=None
        )

        await asyncio.sleep(2)

        if interaction.channel:
            await send_new_quiz(
                interaction.channel
            )


class QuizView(
    discord.ui.View
):

    def __init__(
        self,
        quiz=None
    ):
        super().__init__(
            timeout=None
        )

        if quiz is not None:

            for index, option in enumerate(
                quiz["options"]
            ):

                self.add_item(
                    QuizAnswerButton(
                        index,
                        option[1]
                    )
                )

        self.add_item(
            QuizHintButton()
        )

        self.add_item(
            QuizSkipButton()
        )


# ============================================================
#                         QUIZ COMMANDS
# ============================================================

@bot.command(name="quiz")
async def quiz_command(ctx):

    if not isinstance(
        ctx.author,
        discord.Member
    ):
        return

    has_role = any(
        role.id == QUIZ_COMMAND_ROLE_ID
        for role in ctx.author.roles
    )

    if not has_role:

        embed = base_embed(
            "🔒 Keine Berechtigung",
            (
                "Du benötigst die entsprechende "
                "Team-Rolle, um `!quiz` zu verwenden."
            ),
            discord.Color.red()
        )

        await ctx.send(
            embed=embed,
            delete_after=5
        )

        return

    if ctx.channel.id != QUIZ_CHANNEL_ID:

        await ctx.send(
            embed=base_embed(
                "📍 Falscher Kanal",
                (
                    "Der `!quiz`-Command kann "
                    "nur im vorgesehenen Quiz-Kanal "
                    "verwendet werden."
                ),
                discord.Color.orange()
            ),
            delete_after=5
        )

        return

    await send_new_quiz(
        ctx.channel
    )


@bot.command(name="punkte")
async def punkte_command(ctx):

    score = quiz_scores.get(
        str(ctx.author.id),
        0
    )

    embed = base_embed(
        "📊 Dein Punktestand",
        (
            f"👤 **Spieler:** {ctx.author.mention}\n"
            f"🏆 **Punkte:** `{score}`"
        )
    )

    await ctx.send(
        embed=embed
    )


@bot.command(name="top")
async def top_command(ctx):

    if not quiz_scores:

        await ctx.send(
            embed=base_embed(
                "🏆 Rangliste",
                "Aktuell wurden noch keine Punkte gesammelt."
            )
        )

        return

    sorted_scores = sorted(
        quiz_scores.items(),
        key=lambda item: item[1],
        reverse=True
    )

    lines = []

    for index, (
        user_id,
        score
    ) in enumerate(
        sorted_scores[:10],
        start=1
    ):

        member = None

        if ctx.guild:
            member = ctx.guild.get_member(
                int(user_id)
            )

        if member:
            name = member.display_name
        else:
            name = f"User {user_id}"

        lines.append(
            f"**{index}.** {name} — `{score} Punkte`"
        )

    embed = base_embed(
        "🏆 Top 10",
        "\n".join(lines),
        discord.Color.gold()
    )

    await ctx.send(
        embed=embed
    )


# ============================================================
#                         SUPPORT SYSTEM
# ============================================================

async def find_supporter(
    voice_channel,
    user_id
):
    """
    Der erste andere Member im Support-Call
    wird als Supporter übernommen.
    """

    if voice_channel is None:
        return None

    for member in voice_channel.members:

        if member.id == user_id:
            continue

        if member.bot:
            continue

        return member

    return None


async def create_support_case(member):

    if member.id in active_support_cases:
        return

    active_support_cases[
        member.id
    ] = {
        "case_id": generate_case_id(),
        "user_id": member.id,
        "started_at": now().isoformat(),
        "supporter_id": None
    }


async def finish_support_case(
    member
):
    case = active_support_cases.pop(
        member.id,
        None
    )

    if case is None:
        return

    ended_at = now()

    started_at = datetime.fromisoformat(
        case["started_at"]
    )

    duration = (
        ended_at - started_at
    ).total_seconds()

    supporter_id = case.get(
        "supporter_id"
    )

    supporter_text = (
        "Nicht festgestellt"
    )

    if supporter_id:

        supporter_member = member.guild.get_member(
            int(supporter_id)
        )

        if supporter_member:
            supporter_text = (
                supporter_member.mention
            )

    channel = bot.get_channel(
        SUPPORT_LOG_CHANNEL_ID
    )

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        return

    embed = discord.Embed(
        title="🛡️ Support-Fall beendet",
        description=(
            f"{member.mention} wurde "
            "erfolgreich supportet."
        ),
        color=discord.Color.green(),
        timestamp=ended_at
    )

    embed.add_field(
        name="🆔 CaseID",
        value=f"`{case['case_id']}`",
        inline=True
    )

    embed.add_field(
        name="👤 Nutzer",
        value=member.mention,
        inline=True
    )

    embed.add_field(
        name="🛠️ Supporter",
        value=supporter_text,
        inline=True
    )

    embed.add_field(
        name="🕐 Erstellt am",
        value=format_datetime(
            started_at
        ),
        inline=True
    )

    embed.add_field(
        name="⏱️ Dauer",
        value=format_duration(
            duration
        ),
        inline=True
    )

    embed.add_field(
        name="🔒 Status",
        value="Erfolgreich beendet",
        inline=True
    )

    embed.set_footer(
        text="RLP Support System"
    )

    await channel.send(
        embed=embed
    )


async def update_supporter_for_case(
    voice_channel
):
    if voice_channel is None:
        return

    for user_id, case in list(
        active_support_cases.items()
    ):

        member = voice_channel.guild.get_member(
            user_id
        )

        if member is None:
            continue

        if member not in voice_channel.members:
            continue

        if case.get("supporter_id"):
            continue

        supporter = await find_supporter(
            voice_channel,
            user_id
        )

        if supporter:

            case["supporter_id"] = supporter.id

            active_support_cases[
                user_id
            ] = case


class SupportView(
    discord.ui.View
):

    def __init__(self):
        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Support-Informationen",
        emoji="🎫",
        style=discord.ButtonStyle.primary,
        custom_id="support_info"
    )
    async def support_info(
        self,
        interaction,
        button
    ):

        embed = base_embed(
            "🎫 Support-System",
            (
                "Willkommen im Support-System.\n\n"
                "1. Betritt den Support-Call.\n"
                "2. Dein Support-Fall wird automatisch erstellt.\n"
                "3. Eine eindeutige CaseID wird vergeben.\n"
                "4. Der Supporter wird erfasst.\n"
                "5. Beim Verlassen wird der Fall automatisch abgeschlossen.\n\n"
                "Der Abschluss wird mit Nutzer, Supporter, "
                "Erstellungszeit, Dauer und CaseID dokumentiert."
            )
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


async def send_support_panel():

    channel = bot.get_channel(
        SUPPORT_LOG_CHANNEL_ID
    )

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        return

    await clean_bot_panel(
        channel,
        "🎫 Support-System"
    )

    embed = base_embed(
        "🎫 Support-System",
        (
            "Willkommen im offiziellen Support-System.\n\n"
            "📞 **Support starten**\n"
            "Betritt den vorgesehenen Support-Call.\n\n"
            "🆔 **Automatische CaseID**\n"
            "Für jeden Fall wird eine eindeutige CaseID erstellt.\n\n"
            "⏱️ **Automatische Dauer**\n"
            "Die Supportdauer wird automatisch erfasst.\n\n"
            "📋 **Abschlussbericht**\n"
            "Nach Ende des Falls wird ein sauberer Bericht erstellt."
        )
    )

    await channel.send(
        embed=embed,
        view=SupportView()
    )


# ============================================================
#                         TEAMLER SYSTEM
# ============================================================

class TeamRegistrationView(
    discord.ui.View
):

    def __init__(self):
        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Eintragen",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        custom_id="team_register"
    )
    async def register(
        self,
        interaction,
        button
    ):

        active_team_members.add(
            interaction.user.id
        )

        save_data()

        await interaction.response.send_message(
            embed=base_embed(
                "🟢 Eingetragen",
                (
                    "Du bist jetzt als verfügbarer "
                    "Teamler eingetragen."
                ),
                discord.Color.green()
            ),
            ephemeral=True
        )

    @discord.ui.button(
        label="Austragen",
        emoji="🔴",
        style=discord.ButtonStyle.danger,
        custom_id="team_unregister"
    )
    async def unregister(
        self,
        interaction,
        button
    ):

        active_team_members.discard(
            interaction.user.id
        )

        save_data()

        await interaction.response.send_message(
            embed=base_embed(
                "🔴 Ausgetragen",
                (
                    "Du wurdest erfolgreich "
                    "ausgetragen."
                ),
                discord.Color.red()
            ),
            ephemeral=True
        )

    @discord.ui.button(
        label="Team anzeigen",
        emoji="👥",
        style=discord.ButtonStyle.secondary,
        custom_id="team_list"
    )
    async def list_team(
        self,
        interaction,
        button
    ):

        guild = interaction.guild

        if guild is None:
            return

        members = []

        for user_id in active_team_members:

            member = guild.get_member(
                user_id
            )

            if member:
                members.append(
                    f"🟢 {member.mention}"
                )

        if not members:
            description = (
                "Aktuell ist kein Teamler "
                "als verfügbar eingetragen."
            )
        else:
            description = "\n".join(
                members[:25]
            )

        await interaction.response.send_message(
            embed=base_embed(
                "👥 Verfügbare Teamler",
                description
            ),
            ephemeral=True
        )


async def send_team_registration_panel():

    channel = bot.get_channel(
        TEAM_REGISTER_CHANNEL_ID
    )

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        return

    await clean_bot_panel(
        channel,
        "👥 Teamler-System"
    )

    embed = base_embed(
        "👥 Teamler-System",
        (
            "Hier kannst du deinen aktuellen Team-Status "
            "selbst verwalten.\n\n"
            "🟢 **Eintragen**\n"
            "Du bist aktuell verfügbar.\n\n"
            "🔴 **Austragen**\n"
            "Du bist aktuell nicht verfügbar.\n\n"
            "👥 **Team anzeigen**\n"
            "Zeigt die aktuell eingetragenen Teamler."
        )
    )

    await channel.send(
        embed=embed,
        view=TeamRegistrationView()
    )


# ============================================================
#                         DEVELOPER SCHICHT
# ============================================================

class DeveloperShiftView(
    discord.ui.View
):

    def __init__(self):
        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Schicht starten",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        custom_id="developer_shift_start"
    )
    async def start_shift(
        self,
        interaction,
        button
    ):

        user_id = str(
            interaction.user.id
        )

        if user_id in active_developer_shifts:

            await interaction.response.send_message(
                "⚠️ Du hast bereits eine aktive Developer-Schicht.",
                ephemeral=True
            )

            return

        active_developer_shifts[
            user_id
        ] = {
            "started_at":
                now().isoformat()
        }

        save_data()

        await interaction.response.send_message(
            embed=base_embed(
                "🟢 Schicht gestartet",
                (
                    f"{interaction.user.mention}\n\n"
                    "Deine Developer-Schicht wurde "
                    "erfolgreich gestartet."
                ),
                discord.Color.green()
            ),
            ephemeral=True
        )

    @discord.ui.button(
        label="Schicht beenden",
        emoji="🔴",
        style=discord.ButtonStyle.danger,
        custom_id="developer_shift_end"
    )
    async def end_shift(
        self,
        interaction,
        button
    ):

        user_id = str(
            interaction.user.id
        )

        shift = active_developer_shifts.get(
            user_id
        )

        if not shift:

            await interaction.response.send_message(
                "⚠️ Du hast aktuell keine aktive Schicht.",
                ephemeral=True
            )

            return

        try:
            started_at = datetime.fromisoformat(
                shift["started_at"]
            )

        except Exception:

            started_at = now()

        duration = (
            now() - started_at
        ).total_seconds()

        del active_developer_shifts[
            user_id
        ]

        save_data()

        await interaction.response.send_message(
            embed=base_embed(
                "🔴 Schicht beendet",
                (
                    f"{interaction.user.mention}\n\n"
                    f"⏱️ **Schichtdauer:** "
                    f"{format_duration(duration)}"
                ),
                discord.Color.red()
            ),
            ephemeral=True
        )


async def send_developer_shift_panel():

    channel = bot.get_channel(
        DEVELOPER_SHIFT_CHANNEL_ID
    )

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        return

    await clean_bot_panel(
        channel,
        "💻 Developer-Schichtsystem"
    )

    embed = base_embed(
        "💻 Developer-Schichtsystem",
        (
            "Verwalte hier deine Developer-Schicht.\n\n"
            "🟢 **Schicht starten**\n"
            "Startet deine Arbeitszeit.\n\n"
            "🔴 **Schicht beenden**\n"
            "Beendet deine Arbeitszeit und zeigt die Dauer an."
        )
    )

    await channel.send(
        embed=embed,
        view=DeveloperShiftView()
    )


# ============================================================
#                         DEVELOPER AUFGABEN
# ============================================================

def get_next_task_id():
    if not developer_tasks:
        return 1

    return max(
        int(task.get("id", 0))
        for task in developer_tasks
    ) + 1


def find_task(task_id):
    for task in developer_tasks:
        if int(task.get("id", 0)) == task_id:
            return task

    return None


class DeveloperTaskModal(
    discord.ui.Modal,
    title="Neue Developer-Aufgabe"
):

    task = discord.ui.TextInput(
        label="Aufgabe",
        placeholder="Beschreibe die Aufgabe...",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True
    )

    async def on_submit(
        self,
        interaction
    ):

        task_id = get_next_task_id()

        developer_tasks.append(
            {
                "id": task_id,
                "text": str(self.task),
                "creator_id":
                    interaction.user.id,
                "completed": False,
                "claimed_by": None,
                "created_at":
                    now().isoformat()
            }
        )

        save_data()

        await interaction.response.send_message(
            embed=base_embed(
                "📋 Aufgabe erstellt",
                (
                    f"**Aufgabe #{task_id}** wurde "
                    "erfolgreich erstellt."
                ),
                discord.Color.green()
            ),
            ephemeral=True
        )

        await send_developer_tasks()


class DeveloperTaskView(
    discord.ui.View
):

    def __init__(self):
        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Aufgabe erstellen",
        emoji="➕",
        style=discord.ButtonStyle.success,
        custom_id="developer_task_create"
    )
    async def create_task(
        self,
        interaction,
        button
    ):

        await interaction.response.send_modal(
            DeveloperTaskModal()
        )

    @discord.ui.button(
        label="Aufgabe übernehmen",
        emoji="📌",
        style=discord.ButtonStyle.primary,
        custom_id="developer_task_claim_info"
    )
    async def claim_info(
        self,
        interaction,
        button
    ):

        await interaction.response.send_message(
            embed=base_embed(
                "📌 Aufgabe übernehmen",
                (
                    "Nutze:\n"
                    "`!devclaim <Aufgaben-ID>`\n\n"
                    "Beispiel:\n"
                    "`!devclaim 4`"
                )
            ),
            ephemeral=True
        )


async def send_developer_tasks():

    channel = bot.get_channel(
        DEVELOPER_TASK_CHANNEL_ID
    )

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        return

    await clean_bot_panel(
        channel,
        "💻 Developer-Aufgaben"
    )

    embed = base_embed(
        "💻 Developer-Aufgaben",
        (
            "Hier werden die aktuellen Developer-Aufgaben "
            "übersichtlich verwaltet.\n\n"
            "➕ `!devtask <Aufgabe>` — Aufgabe erstellen\n"
            "📌 `!devclaim <ID>` — Aufgabe übernehmen\n"
            "✅ `!devdone <ID>` — Aufgabe abschließen"
        )
    )

    open_tasks = [
        task
        for task in developer_tasks
        if not task.get("completed", False)
    ]

    completed_tasks = [
        task
        for task in developer_tasks
        if task.get("completed", False)
    ]

    if not developer_tasks:

        embed.add_field(
            name="📋 Keine Aufgaben",
            value=(
                "Aktuell sind keine Developer-Aufgaben vorhanden."
            ),
            inline=False
        )

    else:

        for task in developer_tasks[-15:]:

            if task.get("completed"):
                status = "✅ Erledigt"
            elif task.get("claimed_by"):
                status = "🟡 In Bearbeitung"
            else:
                status = "⚪ Offen"

            if task.get("claimed_by"):
                claimed = (
                    f"<@{task['claimed_by']}>"
                )
            else:
                claimed = "Niemand"

            text = str(
                task.get(
                    "text",
                    "Keine Beschreibung"
                )
            )

            embed.add_field(
                name=(
                    f"#{task['id']} • {status}"
                ),
                value=(
                    f"{text}\n"
                    f"👤 Bearbeiter: {claimed}"
                )[:1024],
                inline=False
            )

    embed.add_field(
        name="📊 Übersicht",
        value=(
            f"⚪ Offen: `{len(open_tasks)}`\n"
            f"✅ Erledigt: `{len(completed_tasks)}`"
        ),
        inline=False
    )

    await channel.send(
        embed=embed,
        view=DeveloperTaskView()
    )


@bot.command(name="devtask")
@commands.has_permissions(
    administrator=True
)
async def devtask_command(
    ctx,
    *,
    task: str
):

    task = task.strip()

    if not task:

        await ctx.send(
            "❌ Bitte gib eine Aufgabe an.",
            delete_after=5
        )

        return

    task_id = get_next_task_id()

    developer_tasks.append(
        {
            "id": task_id,
            "text": task,
            "creator_id":
                ctx.author.id,
            "completed": False,
            "claimed_by": None,
            "created_at":
                now().isoformat()
        }
    )

    save_data()

    await send_developer_tasks()

    try:
        await ctx.message.delete()
    except Exception:
        pass


@bot.command(name="devclaim")
async def devclaim_command(
    ctx,
    task_id: int
):

    task = find_task(
        task_id
    )

    if task is None:

        await ctx.send(
            "❌ Diese Aufgabe wurde nicht gefunden.",
            delete_after=5
        )

        return

    if task.get("completed"):

        await ctx.send(
            "⚠️ Diese Aufgabe ist bereits abgeschlossen.",
            delete_after=5
        )

        return

    if task.get("claimed_by"):

        await ctx.send(
            (
                "⚠️ Diese Aufgabe wird bereits von "
                f"<@{task['claimed_by']}> bearbeitet."
            ),
            delete_after=5
        )

        return

    task["claimed_by"] = ctx.author.id

    save_data()

    await send_developer_tasks()

    await ctx.send(
        embed=base_embed(
            "📌 Aufgabe übernommen",
            (
                f"{ctx.author.mention} hat "
                f"**Aufgabe #{task_id}** übernommen."
            ),
            discord.Color.blurple()
        ),
        delete_after=5
    )


@bot.command(name="devdone")
async def devdone_command(
    ctx,
    task_id: int
):

    task = find_task(
        task_id
    )

    if task is None:

        await ctx.send(
            "❌ Diese Aufgabe wurde nicht gefunden.",
            delete_after=5
        )

        return

    if task.get("completed"):

        await ctx.send(
            "⚠️ Diese Aufgabe ist bereits abgeschlossen.",
            delete_after=5
        )

        return

    # Nur Administratoren oder der aktuelle Bearbeiter
    # dürfen eine Aufgabe abschließen.
    claimed_by = task.get(
        "claimed_by"
    )

    if (
        not ctx.author.guild_permissions.administrator
        and claimed_by != ctx.author.id
    ):

        await ctx.send(
            (
                "🔒 Du kannst diese Aufgabe nicht "
                "abschließen. Übernimm sie zuerst."
            ),
            delete_after=5
        )

        return

    task["completed"] = True

    save_data()

    await send_developer_tasks()

    await ctx.send(
        embed=base_embed(
            "✅ Aufgabe abgeschlossen",
            (
                f"**Aufgabe #{task_id}** wurde von "
                f"{ctx.author.mention} abgeschlossen."
            ),
            discord.Color.green()
        ),
        delete_after=5
    )


# ============================================================
#                         DEVELOPER BEWERBUNG
# ============================================================

DEVELOPER_QUESTIONS = [
    "Wie lange bist du bereits auf Discord aktiv?",
    "Welche Erfahrungen hast du mit Discord Bots?",
    "Welche Programmiersprachen beherrschst du?",
    "Wie viel Zeit kannst du pro Woche investieren?",
    "Warum möchtest du Developer werden?",
    "Welche Projekte hast du bereits umgesetzt?"
]


class DeveloperApplicationView(
    discord.ui.View
):

    def __init__(self):
        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Developer bewerben",
        emoji="💻",
        style=discord.ButtonStyle.primary,
        custom_id="developer_apply"
    )
    async def apply(
        self,
        interaction,
        button
    ):

        if interaction.user.id in active_applications:

            await interaction.response.send_message(
                "⚠️ Du hast bereits eine aktive Bewerbung.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "📨 Ich habe dir eine DM für die Bewerbung geschickt.",
            ephemeral=True
        )

        try:

            await run_developer_application(
                interaction.user
            )

        except discord.Forbidden:

            await interaction.followup.send(
                (
                    "❌ Ich konnte dir keine DM schicken.\n"
                    "Bitte aktiviere deine Direktnachrichten "
                    "für diesen Server."
                ),
                ephemeral=True
            )


async def run_developer_application(
    user
):

    active_applications[
        user.id
    ] = True

    answers = []

    try:

        await user.send(
            embed=base_embed(
                "💻 Developer-Bewerbung",
                (
                    "Willkommen bei der Developer-Bewerbung.\n\n"
                    "Beantworte bitte alle Fragen nacheinander.\n"
                    "Für jede Antwort hast du 5 Minuten Zeit."
                )
            )
        )

        for index, question in enumerate(
            DEVELOPER_QUESTIONS,
            start=1
        ):

            await user.send(
                embed=base_embed(
                    (
                        f"Frage {index}/"
                        f"{len(DEVELOPER_QUESTIONS)}"
                    ),
                    question
                )
            )

            def check(message):
                return (
                    message.author.id == user.id
                    and isinstance(
                        message.channel,
                        discord.DMChannel
                    )
                )

            try:

                message = await bot.wait_for(
                    "message",
                    timeout=300,
                    check=check
                )

            except asyncio.TimeoutError:

                await user.send(
                    embed=base_embed(
                        "⏰ Bewerbung abgebrochen",
                        (
                            "Die Bewerbung wurde wegen "
                            "Zeitüberschreitung beendet."
                        ),
                        discord.Color.red()
                    )
                )

                return

            answers.append(
                (
                    question,
                    message.content
                )
            )

        await send_application_review(
            user,
            answers
        )

        await user.send(
            embed=base_embed(
                "✅ Bewerbung eingereicht",
                (
                    "Deine Developer-Bewerbung wurde "
                    "erfolgreich an das zuständige Team "
                    "weitergeleitet."
                ),
                discord.Color.green()
            )
        )

    finally:

        active_applications.pop(
            user.id,
            None
        )


async def send_application_review(
    user,
    answers
):

    channel = bot.get_channel(
        REVIEW_CHANNEL_ID
    )

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        return

    embed = base_embed(
        "💻 Neue Developer-Bewerbung",
        (
            f"**Bewerber:** {user.mention}\n"
            f"**User-ID:** `{user.id}`"
        )
    )

    for index, (
        question,
        answer
    ) in enumerate(
        answers,
        start=1
    ):

        embed.add_field(
            name=f"{index}. {question}",
            value=answer[:1024],
            inline=False
        )

    await channel.send(
        embed=embed
    )


async def send_application_panel():

    channel = bot.get_channel(
        APPLICATION_CHANNEL_ID
    )

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        return

    await clean_bot_panel(
        channel,
        "💻 Developer-Bewerbung"
    )

    embed = base_embed(
        "💻 Developer-Bewerbung",
        (
            "Du möchtest unser Developer-Team unterstützen?\n\n"
            "Klicke auf **Developer bewerben** und fülle "
            "die Bewerbung per DM aus.\n\n"
            "Bitte beantworte alle Fragen ehrlich und ausführlich."
        )
    )

    await channel.send(
        embed=embed,
        view=DeveloperApplicationView()
    )


# ============================================================
#                         BOT KLASSE
# ============================================================

class RLPBot(
    commands.Bot
):

    async def setup_hook(
        self
    ):

        load_data()

        self.add_view(
            NicknamePanelView()
        )

        self.add_view(
            DeveloperApplicationView()
        )

        self.add_view(
            TeamRegistrationView()
        )

        self.add_view(
            DeveloperShiftView()
        )

        self.add_view(
            DeveloperTaskView()
        )

        self.add_view(
            SupportView()
        )

        self.add_view(
            QuizView()
        )


# ============================================================
#                         BOT
# ============================================================

bot = RLPBot(
    command_prefix="!",
    intents=intents,
    help_command=None
)


# ============================================================
#                         EVENTS
# ============================================================

@bot.event
async def on_ready():

    global startup_finished

    print(
        f"✅ Bot online als {bot.user} "
        f"({bot.user.id})"
    )

    if startup_finished:
        return

    guild = bot.get_guild(
        GUILD_ID
    )

    if guild is None:

        print(
            "❌ Guild nicht gefunden."
        )

        return

    try:

        refill_quiz_bag()

        # -------------------------
        # RLP Nametags
        # -------------------------

        await update_all_rlp_nicknames()

        # -------------------------
        # Quiz
        # -------------------------

        quiz_channel = bot.get_channel(
            QUIZ_CHANNEL_ID
        )

        if isinstance(
            quiz_channel,
            discord.TextChannel
        ):

            async for message in quiz_channel.history(
                limit=None
            ):

                if message.author == bot.user:

                    await safe_delete(
                        message
                    )

                    await asyncio.sleep(
                        0.05
                    )

            await send_new_quiz(
                quiz_channel
            )

        # -------------------------
        # Panels
        # -------------------------

        await send_nickname_panel()

        await send_application_panel()

        await send_team_registration_panel()

        await send_developer_shift_panel()

        await send_developer_tasks()

        await send_support_panel()

        startup_finished = True

        print(
            "✅ Alle Systeme wurden erfolgreich geladen."
        )

        print(
            f"🧩 Quiz-Fragen: {len(QUIZZES)}"
        )

    except Exception as error:

        print(
            f"❌ Fehler beim Startup: {error}"
        )

        # Bleibt False, damit ein späterer Ready-
        # Event einen erneuten Startversuch machen kann.
        startup_finished = False


@bot.event
async def on_member_join(
    member
):

    if member.guild.id != GUILD_ID:
        return

    await asyncio.sleep(2)

    await set_rlp_nickname(
        member,
        force=True
    )


@bot.event
async def on_member_update(
    before,
    after
):

    if before.guild.id != GUILD_ID:
        return

    before_has_role = any(
        role.id == NAMETAG_ROLE_ID
        for role in before.roles
    )

    after_has_role = any(
        role.id == NAMETAG_ROLE_ID
        for role in after.roles
    )

    # Rolle neu bekommen
    if (
        not before_has_role
        and after_has_role
    ):

        await set_rlp_nickname(
            after,
            force=True
        )

    # Rolle verloren -> Opt-Out entfernen,
    # damit die Rolle bei späterer Vergabe wieder greift.
    if (
        before_has_role
        and not after_has_role
    ):

        if after.id in nametag_removed_users:
            nametag_removed_users.discard(
                after.id
            )

            save_data()


@bot.event
async def on_voice_state_update(
    member,
    before,
    after
):

    if member.guild.id != GUILD_ID:
        return

    # ========================================================
    # Support betreten
    # ========================================================

    joined_support = (
        after.channel is not None
        and after.channel.id
        == SUPPORT_VOICE_CHANNEL_ID
    )

    left_support = (
        before.channel is not None
        and before.channel.id
        == SUPPORT_VOICE_CHANNEL_ID
    )

    if joined_support:

        # Nur normale Nutzer erhalten einen neuen Case.
        if member.id not in active_support_cases:

            await create_support_case(
                member
            )

        # Prüfen, ob bereits ein anderer Nutzer
        # als Supporter im Call ist.
        await update_supporter_for_case(
            after.channel
        )

    # ========================================================
    # Support verlassen
    # ========================================================

    if left_support:

        # Wenn der Fall-Nutzer den Call verlässt,
        # wird sein Case abgeschlossen.
        if member.id in active_support_cases:

            await finish_support_case(
                member
            )

        # Wenn ein Supporter beitritt/verlassen hat,
        # bleiben die Cases anderer Nutzer bestehen.
        # Danach prüfen wir erneut, ob ein anderer
        # Supporter vorhanden ist.
        if after.channel is not None:

            await update_supporter_for_case(
                after.channel
            )


# ============================================================
#                         COMMAND ERRORS
# ============================================================

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
        commands.MissingPermissions
    ):

        await ctx.send(
            embed=base_embed(
                "🔒 Keine Berechtigung",
                (
                    "Du hast keine Berechtigung "
                    "für diesen Command."
                ),
                discord.Color.red()
            ),
            delete_after=5
        )

        return

    if isinstance(
        error,
        commands.MissingRequiredArgument
    ):

        await ctx.send(
            embed=base_embed(
                "❌ Fehlende Eingabe",
                (
                    "Für diesen Command fehlt "
                    "eine benötigte Eingabe."
                ),
                discord.Color.red()
            ),
            delete_after=5
        )

        return

    if isinstance(
        error,
        commands.BadArgument
    ):

        await ctx.send(
            embed=base_embed(
                "❌ Ungültige Eingabe",
                (
                    "Bitte überprüfe deine Eingabe."
                ),
                discord.Color.red()
            ),
            delete_after=5
        )

        return

    print(
        f"[COMMAND ERROR] {repr(error)}"
    )


# ============================================================
#                         MESSAGE EVENT
# ============================================================

@bot.event
async def on_message(
    message
):

    if message.author.bot:
        return

    await bot.process_commands(
        message
    )


# ============================================================
#                         START
# ============================================================

if not DISCORD_TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN wurde nicht gefunden."
    )


bot.run(
    DISCORD_TOKEN
)
```

**Wichtig:** Deinen bisherigen `bot.py` komplett löschen und **genau diesen Inhalt** als neuen `bot.py` einsetzen. Die `DISCORD_TOKEN`-Umgebungsvariable bleibt wie bisher.

Die wichtigsten Commands sind jetzt:

```text
!quiz
!punkte
!top

!devtask <Aufgabe>
!devclaim <ID>
!devdone <ID>
```

`!quiz` ist ausschließlich für die Rolle `1530188150456979526` freigeschaltet. `!top` und `!punkte` bleiben für alle nutzbar.
