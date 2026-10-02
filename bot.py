
import os
import random
import re
import asyncio
import json
import discord


# ============================================================
# KANÄLE
# ============================================================

QUIZ_CHANNEL_ID = 1533409789256925185
APPLICATION_CHANNEL_ID = 1541391365219295343
REVIEW_CHANNEL_ID = 1548404201493762181

# Nickname-Panel
NICKNAME_CHANNEL_ID = 1555684071911202836


# ============================================================
# SERVER
# ============================================================

GUILD_ID = 1519481018221072454


# ============================================================
# RLP NAMETAG
# ============================================================

NAMETAG_ROLE_ID = 1520102928398942348

# NUR RLP
NAMETAG = "RLP "

# Hier wird gespeichert, wer RLP selbst entfernt hat
NAMETAG_DATA_FILE = "nametag_data.json"


# ============================================================
# EMOJI QUIZZE
# ============================================================

QUIZZES = [
    (["🍕", "🧀"], "Pizza"),
    (["🌧️", "🌈"], "Regenbogen"),
    (["🐶", "🦴"], "Hund"),
    (["🐱", "🐭"], "Katze"),
    (["🐰", "🥕"], "Hase"),
    (["🐵", "🍌"], "Affe"),
    (["🐼", "🎋"], "Panda"),
    (["🦁", "👑"], "Löwe"),
    (["🐯", "🌴"], "Tiger"),
    (["🐘", "🌳"], "Elefant"),
    (["🦒", "🌳"], "Giraffe"),
    (["🐴", "🏇"], "Pferd"),
    (["🐮", "🥛"], "Kuh"),
    (["🐷", "🌾"], "Schwein"),
    (["🐔", "🥚"], "Huhn"),
    (["🐸", "💧"], "Frosch"),
    (["🐢", "🏁"], "Schildkröte"),
    (["🐍", "🌿"], "Schlange"),
    (["🦋", "🌸"], "Schmetterling"),
    (["🐝", "🍯"], "Biene"),
    (["🐞", "🌿"], "Marienkäfer"),
    (["🦊", "🌲"], "Fuchs"),
    (["🐻", "🍯"], "Bär"),
    (["🐺", "🌙"], "Wolf"),
    (["🦉", "🌙"], "Eule"),
    (["🦅", "☁️"], "Adler"),
    (["🐧", "❄️"], "Pinguin"),
    (["🐬", "🌊"], "Delfin"),
    (["🦈", "🌊"], "Hai"),
    (["🐙", "🌊"], "Oktopus"),
    (["🦀", "🏖️"], "Krabbe"),
    (["🐠", "🌊"], "Fisch"),

    (["🍎", "🍏"], "Apfel"),
    (["🍌", "🍎"], "Banane"),
    (["🍓", "🍒"], "Beeren"),
    (["🍉", "☀️"], "Wassermelone"),
    (["🍋", "🥤"], "Limonade"),
    (["🍊", "🍹"], "Orange"),
    (["🍍", "🌴"], "Ananas"),
    (["🥥", "🏝️"], "Kokosnuss"),
    (["🥕", "🐰"], "Karotte"),
    (["🌽", "🌾"], "Mais"),
    (["🍅", "🥗"], "Salat"),

    (["🍔", "🍟"], "Fast Food"),
    (["🌭", "🥤"], "Hotdog"),
    (["🍿", "🎬"], "Kino"),
    (["🍦", "☀️"], "Eis"),
    (["🍩", "☕"], "Donut"),
    (["🍫", "🥛"], "Schokolade"),
    (["🍰", "🧁"], "Kuchen"),
    (["🍪", "🥛"], "Kekse"),
    (["🍝", "🍅"], "Nudeln"),
    (["🍣", "🥢"], "Sushi"),
    (["🌮", "🌶️"], "Taco"),
    (["🍳", "🥓"], "Frühstück"),
    (["🥪", "🥤"], "Mittagessen"),

    (["🎂", "🎁"], "Geburtstag"),
    (["🎈", "🎉"], "Party"),
    (["🎄", "🎁"], "Weihnachten"),
    (["🎃", "👻"], "Halloween"),
    (["❤️", "🌹"], "Liebe"),
    (["💐", "🌷"], "Blumen"),
    (["😊", "❤️"], "Glück"),
    (["😂", "🤣"], "Lachen"),
    (["😭", "💧"], "Weinen"),
    (["😡", "🔥"], "Wut"),
    (["😎", "🕶️"], "Cool"),
    (["😴", "🛏️"], "Schlafen"),
    (["⏰", "😴"], "Wecker"),
    (["🚿", "🧼"], "Duschen"),
    (["🪥", "😁"], "Zähneputzen"),

    (["👟", "🏃"], "Laufen"),
    (["🏊", "🌊"], "Schwimmen"),
    (["🚴", "🚲"], "Radfahren"),
    (["🏋️", "💪"], "Fitness"),

    (["⚽", "🥅"], "Fußball"),
    (["🏀", "🏆"], "Basketball"),
    (["🏐", "🏆"], "Volleyball"),
    (["🎾", "🏟️"], "Tennis"),
    (["🥊", "🏆"], "Boxen"),
    (["🏎️", "🏁"], "Rennen"),
    (["🎯", "🏆"], "Gewinnen"),
    (["🥇", "🏆"], "Sieger"),

    (["🎸", "🎤"], "Musik"),
    (["🥁", "🎵"], "Schlagzeug"),
    (["🎹", "🎼"], "Klavier"),
    (["🎨", "🖌️"], "Malen"),
    (["📖", "🔦"], "Lesen"),
    (["✏️", "📓"], "Schreiben"),
    (["📷", "🤳"], "Foto"),
    (["🎧", "🎵"], "Musik"),
    (["📺", "🍿"], "Fernsehen"),
    (["🎮", "🕹️"], "Gaming"),
    (["💻", "⌨️"], "Computer"),
    (["📱", "💬"], "Chat"),
    (["📧", "💻"], "E-Mail"),
    (["📞", "📱"], "Anruf"),

    (["🔑", "🚪"], "Schlüssel"),
    (["🔒", "🔑"], "Schloss"),
    (["💰", "🏦"], "Geld"),
    (["💎", "💰"], "Reichtum"),
    (["🎁", "🎀"], "Geschenk"),

    (["🚗", "⛽"], "Auto"),
    (["🚕", "🏙️"], "Taxi"),
    (["🚌", "🚏"], "Bus"),
    (["🚲", "🛣️"], "Fahrrad"),
    (["🏍️", "🛣️"], "Motorrad"),
    (["🚓", "👮"], "Polizei"),
    (["🚑", "🏥"], "Krankenwagen"),
    (["🚒", "🔥"], "Feuerwehr"),
    (["🚁", "🚨"], "Hubschrauber"),
    (["🚢", "⚓"], "Schiff"),
    (["🚆", "🚉"], "Zug"),
    (["✈️", "🧳"], "Flugzeug"),
    (["🚀", "🌕"], "Weltraum"),
    (["🏴‍☠️", "🚢"], "Piraten"),

    (["👑", "🏰"], "König"),
    (["🏰", "⚔️"], "Burg"),
    (["🗺️", "🧳"], "Reise"),
    (["🌍", "✈️"], "Weltreise"),
    (["🏨", "🛏️"], "Hotel"),
    (["🏖️", "☀️"], "Strand"),
    (["🌊", "🐚"], "Meer"),
    (["🏝️", "🌴"], "Insel"),
    (["🏕️", "🔥"], "Camping"),
    (["🏔️", "❄️"], "Berg"),
    (["🏜️", "🐪"], "Wüste"),
    (["🌲", "🏡"], "Wald"),
    (["🌋", "🔥"], "Vulkan"),

    (["🌞", "🌻"], "Sommer"),
    (["❄️", "⛄"], "Winter"),
    (["🍂", "🌳"], "Herbst"),
    (["🌷", "🌸"], "Frühling"),
    (["🌙", "⭐"], "Mond"),
    (["☁️", "💧"], "Regen"),
    (["🌞", "🔥"], "Hitze"),
    (["🌳", "🍎"], "Apfelbaum"),
    (["🌻", "🌞"], "Sonnenblume"),
    (["🌹", "❤️"], "Rose"),

    (["🎓", "📚"], "Abschluss"),
    (["🔬", "🧪"], "Wissenschaft"),
    (["🧑‍🍳", "🍳"], "Kochen"),
    (["🍰", "🧁"], "Backen"),
    (["🧑‍💻", "💻"], "Developer"),
    (["💡", "🧠"], "Idee"),
    (["🎬", "🎟️"], "Film"),
    (["🎨", "🖼️"], "Kunst"),
    (["🎤", "🎙️"], "Sänger"),
    (["🎸", "🥁"], "Band"),
    (["📚", "🏫"], "Schule"),
    (["🎒", "📚"], "Schulranzen"),
    (["📝", "✏️"], "Hausaufgaben"),
    (["📅", "⏰"], "Termin"),
    (["🛒", "🛍️"], "Einkaufen"),
    (["🏠", "🔑"], "Zuhause"),
    (["🛋️", "📺"], "Wohnzimmer"),
    (["🛏️", "🌙"], "Schlafzimmer"),
    (["🚪", "🔔"], "Türklingel"),
    (["📦", "🚚"], "Paket"),
    (["📬", "✉️"], "Brief"),
    (["✉️", "📮"], "Post"),
    (["🔔", "📱"], "Benachrichtigung"),
    (["🎟️", "🎬"], "Kinokarte"),
    (["🎁", "🎉"], "Feier"),
    (["🕯️", "🎂"], "Geburtstag"),
    (["💍", "❤️"], "Hochzeit"),
    (["💌", "❤️"], "Liebesbrief"),
    (["🌹", "💌"], "Valentinstag"),
]


# ============================================================
# DEVELOPER FRAGEN
# ============================================================

DEVELOPER_QUESTIONS = [
    "Welche Erfahrungen hast du bisher mit Discord-Servern und deren Funktionen?",
    "Welche Erfahrungen hast du mit Discord-Bots?",
    "Hast du schon einmal einen Discord-Bot eingerichtet oder verwaltet?",
    "Welche Discord-Bot-Funktionen kennst du und hast du bereits verwendet?",
    "Hast du Erfahrung mit Buttons, Select-Menüs oder Modals?",
    "Hast du schon einmal ein Ticketsystem für Discord erstellt oder verwaltet?",
    "Hast du Erfahrung mit automatisierten Rollen und Reaktionen?",
    "Hast du schon einmal ein Verifizierungs- oder Bewerbungssystem für einen Discord-Server umgesetzt?",
    "Wie würdest du ein professionelles Discord-Bewerbungssystem gestalten?",
]


# ============================================================
# DISCORD
# ============================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = None


# ============================================================
# QUIZ VARIABLEN
# ============================================================

current_quiz = None
current_quiz_message = None

quiz_bag = []
last_quiz_emojis = set()

quiz_lock = asyncio.Lock()

startup_finished = False


# ============================================================
# USER ZÄHLER
# ============================================================

skip_counts = {}
hint_counts = {}


# ============================================================
# TEMPORÄRE BOT-NACHRICHTEN
# ============================================================

temporary_messages = {}


# ============================================================
# BEWERBUNG
# ============================================================

active_applications = set()


# ============================================================
# NAMETAG-DATEN
# ============================================================

def load_nametag_data():

    if not os.path.exists(NAMETAG_DATA_FILE):
        return set()

    try:

        with open(
            NAMETAG_DATA_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

            if not isinstance(data, list):
                return set()

            return {
                int(user_id)
                for user_id in data
            }

    except Exception as error:

        print(
            f"❌ Fehler beim Laden der Nametag-Daten: {error}"
        )

        return set()


nametag_removed_users = load_nametag_data()


def save_nametag_data():

    try:

        with open(
            NAMETAG_DATA_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                list(nametag_removed_users),
                file,
                indent=4
            )

    except Exception as error:

        print(
            f"❌ Fehler beim Speichern der Nametag-Daten: {error}"
        )


# ============================================================
# NORMALISIEREN
# ============================================================

def normalize(text):

    text = text.lower().strip()

    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(
        r"[^a-z0-9]+",
        "",
        text
    )

    return text


# ============================================================
# SICHER LÖSCHEN
# ============================================================

async def safe_delete(message):

    if message is None:
        return

    try:

        await message.delete()

    except discord.NotFound:
        pass

    except discord.Forbidden:

        print(
            "❌ Keine Berechtigung zum Löschen."
        )

    except discord.HTTPException as error:

        print(
            f"❌ Löschfehler: {error}"
        )


# ============================================================
# TEMPORÄRE NACHRICHT SPEICHERN
# ============================================================

async def replace_temporary_message(
    user_id,
    action,
    message
):

    key = (
        user_id,
        action
    )

    old_message = temporary_messages.get(
        key
    )

    if old_message is not None:

        await safe_delete(
            old_message
        )

    temporary_messages[key] = message


# ============================================================
# TEMPORÄRE NACHRICHTEN ALLE 5 SEKUNDEN LÖSCHEN
# ============================================================

async def temporary_message_cleaner():

    await bot.wait_until_ready()

    while not bot.is_closed():

        await asyncio.sleep(5)

        messages_to_delete = list(
            temporary_messages.items()
        )

        for key, message in messages_to_delete:

            await safe_delete(
                message
            )

            if temporary_messages.get(key) == message:

                temporary_messages.pop(
                    key,
                    None
                )


# ============================================================
# QUIZ BAG
# ============================================================

def refill_quiz_bag():

    global quiz_bag

    quiz_bag = list(
        range(len(QUIZZES))
    )

    random.shuffle(
        quiz_bag
    )


def get_next_quiz():

    global quiz_bag
    global last_quiz_emojis

    if not quiz_bag:

        refill_quiz_bag()

    for position, index in enumerate(
        quiz_bag
    ):

        emojis = set(
            QUIZZES[index][0]
        )

        if not (
            emojis & last_quiz_emojis
        ):

            quiz_bag.pop(
                position
            )

            last_quiz_emojis = emojis

            return QUIZZES[index]

    index = quiz_bag.pop(0)

    last_quiz_emojis = set(
        QUIZZES[index][0]
    )

    return QUIZZES[index]


# ============================================================
# QUIZ EMBED
# ============================================================

def create_quiz_embed(emojis):

    embed = discord.Embed(
        title="🎯 Emoji-Quiz",
        description=(
            "**Was bedeutet diese Emoji-Kombination?**\n\n"
            f"# {' '.join(emojis)}\n\n"
            "💬 Schreibe deine Antwort in den Chat!"
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="Viel Glück! 🍀"
    )

    return embed


# ============================================================
# NEUES QUIZ
# ============================================================

async def send_new_quiz():

    global current_quiz
    global current_quiz_message

    channel = bot.get_channel(
        QUIZ_CHANNEL_ID
    )

    if channel is None:

        print(
            "❌ Quiz-Kanal nicht gefunden."
        )

        return

    for key, message in list(
        temporary_messages.items()
    ):

        await safe_delete(
            message
        )

        temporary_messages.pop(
            key,
            None
        )

    skip_counts.clear()
    hint_counts.clear()

    current_quiz = get_next_quiz()

    embed = create_quiz_embed(
        current_quiz[0]
    )

    current_quiz_message = await channel.send(
        embed=embed,
        view=QuizView()
    )

    print(
        f"✅ Neues Quiz: {current_quiz[1]}"
    )


# ============================================================
# ALTE QUIZ-EMBEDS LÖSCHEN
# ============================================================

async def cleanup_old_quizzes(channel):

    try:

        async for message in channel.history(
            limit=100
        ):

            if message.author != bot.user:
                continue

            if not message.embeds:
                continue

            if (
                message.embeds[0].title
                == "🎯 Emoji-Quiz"
            ):

                await safe_delete(
                    message
                )

    except discord.Forbidden:

        print(
            "❌ Keine Berechtigung, alte Quizze zu löschen."
        )


# ============================================================
# QUIZ VIEW
# ============================================================

class QuizView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )


    # ========================================================
    # ÜBERSPRINGEN
    # ========================================================

    @discord.ui.button(
        label="Überspringen",
        emoji="⏭️",
        style=discord.ButtonStyle.secondary,
        custom_id="emoji_quiz_skip"
    )
    async def skip(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        global current_quiz
        global current_quiz_message

        if (
            current_quiz_message is None
            or interaction.message.id
            != current_quiz_message.id
        ):

            await interaction.response.send_message(
                "❌ Dieses Quiz ist nicht mehr aktuell.",
                ephemeral=True
            )

            return

        user_id = interaction.user.id

        used = skip_counts.get(
            user_id,
            0
        )

        if used >= 3:

            await interaction.response.defer()

            message = await interaction.channel.send(
                f"⏭️ {interaction.user.mention} "
                f"Du hast schon **3/3 mal übersprungen**."
            )

            await replace_temporary_message(
                user_id,
                "skip",
                message
            )

            return

        skip_counts[user_id] = used + 1

        current_message = current_quiz_message

        await interaction.response.defer()

        await safe_delete(
            current_message
        )

        current_quiz = get_next_quiz()

        embed = create_quiz_embed(
            current_quiz[0]
        )

        current_quiz_message = await interaction.channel.send(
            embed=embed,
            view=QuizView()
        )

        if skip_counts[user_id] == 3:

            text = (
                f"⏭️ {interaction.user.mention} "
                f"hat **3/3 mal übersprungen**!"
            )

        else:

            text = (
                f"⏭️ {interaction.user.mention} "
                f"hat übersprungen. "
                f"**{skip_counts[user_id]}/3**"
            )

        message = await interaction.channel.send(
            text
        )

        await replace_temporary_message(
            user_id,
            "skip",
            message
        )


    # ========================================================
    # ANFANGSBUCHSTABE
    # ========================================================

    @discord.ui.button(
        label="Anfangsbuchstabe",
        emoji="💡",
        style=discord.ButtonStyle.primary,
        custom_id="emoji_quiz_hint"
    )
    async def hint(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        global current_quiz
        global current_quiz_message

        if (
            current_quiz_message is None
            or interaction.message.id
            != current_quiz_message.id
        ):

            await interaction.response.send_message(
                "❌ Dieses Quiz ist nicht mehr aktuell.",
                ephemeral=True
            )

            return

        user_id = interaction.user.id

        used = hint_counts.get(
            user_id,
            0
        )

        if used >= 3:

            await interaction.response.defer()

            message = await interaction.channel.send(
                f"💡 {interaction.user.mention} "
                f"Du hast schon **3/3 mal den "
                f"Anfangsbuchstaben aufgedeckt**."
            )

            await replace_temporary_message(
                user_id,
                "hint",
                message
            )

            return

        hint_counts[user_id] = used + 1

        answer = current_quiz[1]

        first_letter = answer[0].upper()

        await interaction.response.defer()

        if hint_counts[user_id] == 3:

            text = (
                f"💡 {interaction.user.mention} "
                f"hat den Anfangsbuchstaben "
                f"**{first_letter}** aufgedeckt! "
                f"**3/3**"
            )

        else:

            text = (
                f"💡 {interaction.user.mention} "
                f"hat den Anfangsbuchstaben "
                f"**{first_letter}** aufgedeckt! "
                f"**{hint_counts[user_id]}/3**"
            )

        message = await interaction.channel.send(
            text
        )

        await replace_temporary_message(
            user_id,
            "hint",
            message
        )


# ============================================================
# RLP NAMETAG SYSTEM
# ============================================================

def get_base_name(member):

    current_name = member.nick or member.name

    # Entfernt vorhandene RLP-Präfixe.
    # Verhindert:
    # RLP RLP Max
    # RLP RLP RLP Max
    while current_name.startswith(NAMETAG):

        current_name = current_name[
            len(NAMETAG):
        ]

    return current_name.strip()


async def set_nametag(
    member,
    force=False
):

    if member.bot:
        return

    if member.guild is None:
        return

    if member.guild.id != GUILD_ID:
        return

    role = member.guild.get_role(
        NAMETAG_ROLE_ID
    )

    if role is None:

        print(
            "❌ RLP-Rolle nicht gefunden."
        )

        return

    # Ohne RLP-Rolle nichts machen
    if role not in member.roles:
        return

    # Wenn der Benutzer RLP selbst entfernt hat,
    # bleibt es auch beim Neustart entfernt.
    #
    # force=True wird nur verwendet,
    # wenn die Rolle gerade neu vergeben wurde
    # oder der Benutzer neu beigetreten ist.
    if (
        member.id in nametag_removed_users
        and not force
    ):

        return

    current_name = member.nick or member.name

    base_name = get_base_name(
        member
    )

    # RLP + Name
    new_nickname = (
        NAMETAG + base_name
    )[:32]

    # Wenn bereits exakt richtig:
    # NICHTS machen.
    if current_name == new_nickname:

        return

    try:

        await member.edit(
            nick=new_nickname,
            reason="Automatischer RLP Nametag"
        )

        # User ist nicht mehr im Opt-Out,
        # weil RLP jetzt wieder gesetzt wurde.
        nametag_removed_users.discard(
            member.id
        )

        save_nametag_data()

        print(
            f"✅ RLP gesetzt: {member} → {new_nickname}"
        )

    except discord.Forbidden:

        print(
            f"❌ Keine Berechtigung, Nickname von "
            f"{member} zu ändern."
        )

    except discord.HTTPException as error:

        print(
            f"❌ Nickname-Fehler bei {member}: {error}"
        )


# ============================================================
# ALLE RLP NAMETAGS BEIM BOT-START
# ============================================================

async def update_all_nametags():

    guild = bot.get_guild(
        GUILD_ID
    )

    if guild is None:

        print(
            "❌ Server für RLP-System nicht gefunden."
        )

        return

    role = guild.get_role(
        NAMETAG_ROLE_ID
    )

    if role is None:

        print(
            "❌ RLP-Rolle nicht gefunden."
        )

        return

    print(
        f"🔄 Prüfe RLP-Nametags für "
        f"{len(role.members)} Mitglieder..."
    )

    for member in role.members:

        # force=False!
        #
        # Dadurch werden Benutzer,
        # die RLP selbst entfernt haben,
        # NICHT wieder zurückgesetzt.
        await set_nametag(
            member,
            force=False
        )

        await asyncio.sleep(
            0.2
        )

    print(
        "✅ Alle RLP-Nametags wurden überprüft."
    )


# ============================================================
# NICKNAME PANEL VIEW
# ============================================================

class NicknamePanelView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )


    @discord.ui.button(
        label="RLP entfernen",
        emoji="✏️",
        style=discord.ButtonStyle.primary,
        custom_id="nickname_change_button"
    )
    async def change_nickname(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ Dieser Button funktioniert nur auf dem Server.",
                ephemeral=True
            )

            return

        if interaction.guild.id != GUILD_ID:

            await interaction.response.send_message(
                "❌ Dieser Button funktioniert auf diesem Server nicht.",
                ephemeral=True
            )

            return

        member = interaction.guild.get_member(
            interaction.user.id
        )

        if member is None:

            await interaction.response.send_message(
                "❌ Du konntest nicht gefunden werden.",
                ephemeral=True
            )

            return

        role = interaction.guild.get_role(
            NAMETAG_ROLE_ID
        )

        if role is None:

            await interaction.response.send_message(
                "❌ Die RLP-Rolle wurde nicht gefunden.",
                ephemeral=True
            )

            return

        # User muss die Rolle besitzen
        if role not in member.roles:

            await interaction.response.send_message(
                "❌ Du hast die RLP-Rolle nicht.",
                ephemeral=True
            )

            return

        current_nickname = member.nick

        # ====================================================
        # AKTUELLER NAME
        # ====================================================

        current_name = (
            current_nickname
            or member.name
        )

        # ====================================================
        # RLP NICHT VORHANDEN
        # ====================================================

        if not current_name.startswith(NAMETAG):

            # Trotzdem dauerhaft speichern,
            # damit der Bot RLP beim nächsten Start
            # nicht automatisch hinzufügt.
            nametag_removed_users.add(
                member.id
            )

            save_nametag_data()

            await interaction.response.send_message(
                "ℹ️ Dein Nickname enthält aktuell kein **RLP**.\n\n"
                "Ich werde **RLP** nicht automatisch wieder hinzufügen.",
                ephemeral=True
            )

            return

        # ====================================================
        # RLP ENTFERNEN
        # ====================================================

        new_nickname = current_name[
            len(NAMETAG):
        ].strip()

        # Falls nach RLP nichts mehr übrig bleibt
        if not new_nickname:

            new_nickname = None

        try:

            await member.edit(
                nick=new_nickname,
                reason="RLP Nametag durch Benutzer entfernt"
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Ich kann deinen Nickname nicht ändern.\n\n"
                "Bitte prüfe:\n"
                "• **Nickname verwalten** für den Bot\n"
                "• Die Bot-Rolle muss über der Rolle des Benutzers stehen.",
                ephemeral=True
            )

            return

        except discord.HTTPException as error:

            print(
                f"❌ Fehler beim Entfernen von RLP: {error}"
            )

            await interaction.response.send_message(
                "❌ Beim Ändern deines Nicknames ist ein Fehler aufgetreten.",
                ephemeral=True
            )

            return

        # ====================================================
        # USER DAUERHAFT SPEICHERN
        # ====================================================

        nametag_removed_users.add(
            member.id
        )

        save_nametag_data()

        await interaction.response.send_message(
            "✅ **RLP wurde entfernt!**\n\n"
            "Dein Nickname bleibt jetzt ohne **RLP**.\n"
            "Auch nach einem Neustart des Bots wird RLP "
            "nicht automatisch wieder hinzugefügt.",
            ephemeral=True
        )


# ============================================================
# NICKNAME PANEL SENDEN
# ============================================================

async def send_nickname_panel():

    channel = bot.get_channel(
        NICKNAME_CHANNEL_ID
    )

    if channel is None:

        print(
            "❌ Nickname-Kanal nicht gefunden."
        )

        return

    try:

        async for message in channel.history(
            limit=100
        ):

            if message.author != bot.user:
                continue

            if not message.embeds:
                continue

            if (
                message.embeds[0].title
                == "Nickname Ändern!"
            ):

                await safe_delete(
                    message
                )

    except discord.Forbidden:

        print(
            "❌ Keine Berechtigung im Nickname-Kanal."
        )

        return

    embed = discord.Embed(
        title="Nickname Ändern!",
        description=(
            "Hier kannst du **RLP** vor deinem Namen "
            "entfernen.\n\n"
            "Wenn du **RLP** entfernst, bleibt dein "
            "Nickname auch nach einem Bot-Neustart "
            "ohne RLP.\n\n"
            "Wenn dir die RLP-Rolle später neu gegeben "
            "wird, wird **RLP** wieder vor deinen Namen gesetzt."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="RLP Nickname-System"
    )

    await channel.send(
        embed=embed,
        view=NicknamePanelView()
    )

    print(
        "✅ Neues Nickname-Panel gesendet."
    )


# ============================================================
# DEVELOPER BEWERBUNG VIEW
# ============================================================

class DeveloperApplicationView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )


    @discord.ui.button(
        label="Bewerben",
        emoji="👨‍💻",
        style=discord.ButtonStyle.primary,
        custom_id="developer_apply"
    )
    async def apply(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        user = interaction.user

        if user.id in active_applications:

            await interaction.response.send_message(
                "⏳ Deine Developer-Bewerbung läuft bereits.",
                ephemeral=True
            )

            return

        active_applications.add(
            user.id
        )

        try:

            try:

                await user.send(
                    "👨‍💻 **Developer-Bewerbung**\n\n"
                    "Vielen Dank für dein Interesse an unserem "
                    "Developer-Team!\n\n"
                    "Die Bewerbung besteht aus **9 Fragen**.\n"
                    "Die Fragen kommen einzeln.\n\n"
                    "Schreibe **abbrechen**, wenn du "
                    "die Bewerbung beenden möchtest."
                )

            except discord.Forbidden:

                await interaction.response.send_message(
                    "❌ Ich kann dir keine DM schicken.\n\n"
                    "Bitte aktiviere deine Direktnachrichten "
                    "für diesen Server.",
                    ephemeral=True
                )

                return

            await interaction.response.send_message(
                "✅ Deine Developer-Bewerbung wurde per DM gestartet.",
                ephemeral=True
            )

            await start_developer_application(
                user
            )

        finally:

            active_applications.discard(
                user.id
            )


# ============================================================
# DEVELOPER BEWERBUNG
# ============================================================

async def start_developer_application(user):

    answers = []

    def check(message):

        return (
            message.author.id == user.id
            and isinstance(
                message.channel,
                discord.DMChannel
            )
        )

    for number, question in enumerate(
        DEVELOPER_QUESTIONS,
        start=1
    ):

        await user.send(
            f"**Frage {number}/9**\n\n"
            f"{question}"
        )

        try:

            answer_message = await bot.wait_for(
                "message",
                timeout=900,
                check=check
            )

        except asyncio.TimeoutError:

            await user.send(
                "⏰ Deine Bewerbung wurde beendet, "
                "weil du zu lange nicht geantwortet hast."
            )

            return

        answer = answer_message.content.strip()

        if normalize(answer) == "abbrechen":

            await user.send(
                "❌ Deine Developer-Bewerbung wurde abgebrochen."
            )

            return

        answers.append(
            answer
        )

    await user.send(
        "✅ **Developer-Bewerbung abgeschlossen!**\n\n"
        "Vielen Dank für deine Bewerbung.\n"
        "Deine Antworten wurden erfolgreich übermittelt."
    )

    await send_application_to_team(
        user,
        answers
    )


# ============================================================
# BEWERBUNG AN REVIEW KANAL
# ============================================================

async def send_application_to_team(
    user,
    answers
):

    channel = bot.get_channel(
        REVIEW_CHANNEL_ID
    )

    if channel is None:

        print(
            "❌ Review-Kanal nicht gefunden."
        )

        return

    embed = discord.Embed(
        title="👨‍💻 Neue Developer-Bewerbung",
        description=(
            f"**Bewerber:** {user.mention}\n"
            f"**Benutzer:** {user}\n"
            f"**User-ID:** `{user.id}`"
        ),
        color=discord.Color.blurple()
    )

    for number, answer in enumerate(
        answers,
        start=1
    ):

        question = DEVELOPER_QUESTIONS[
            number - 1
        ]

        value = (
            f"**{question}**\n"
            f"{answer}"
        )

        if len(value) > 1024:

            value = value[:1021] + "..."

        embed.add_field(
            name=f"Frage {number}",
            value=value,
            inline=False
        )

    embed.set_footer(
        text="Developer Bewerbungssystem"
    )

    await channel.send(
        embed=embed
    )


# ============================================================
# BEWERBUNGS PANEL
# ============================================================

async def send_application_panel():

    channel = bot.get_channel(
        APPLICATION_CHANNEL_ID
    )

    if channel is None:

        print(
            "❌ Bewerbungs-Kanal nicht gefunden."
        )

        return

    try:

        async for message in channel.history(
            limit=100
        ):

            if message.author != bot.user:
                continue

            if not message.embeds:
                continue

            if (
                message.embeds[0].title
                == "👨‍💻 Developer Bewerbung"
            ):

                await safe_delete(
                    message
                )

    except discord.Forbidden:

        print(
            "❌ Keine Berechtigung für Bewerbungs-Kanal."
        )

        return

    embed = discord.Embed(
        title="👨‍💻 Developer Bewerbung",
        description=(
            "**Hier Bewerben Als Developer!**\n\n"
            "Viel Glück!\n\n"
            "Du möchtest unser Developer-Team unterstützen?\n"
            "Klicke unten auf **Bewerben**, "
            "um deine Bewerbung zu starten."
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="Developer Bewerbungssystem"
    )

    await channel.send(
        embed=embed,
        view=DeveloperApplicationView()
    )

    print(
        "✅ Neues Developer-Bewerbungspanel gesendet."
    )


# ============================================================
# BOT KLASSE
# ============================================================

class QuizBot(
    discord.Client
):

    async def setup_hook(self):

        self.add_view(
            QuizView()
        )

        self.add_view(
            DeveloperApplicationView()
        )

        self.add_view(
            NicknamePanelView()
        )

        self.loop.create_task(
            temporary_message_cleaner()
        )


bot = QuizBot(
    intents=intents
)


# ============================================================
# READY
# ============================================================

@bot.event
async def on_ready():

    global startup_finished

    print(
        f"✅ Bot ist online als {bot.user}"
    )

    if startup_finished:
        return

    startup_finished = True

    # ========================================================
    # EMOJI QUIZ
    # ========================================================

    quiz_channel = bot.get_channel(
        QUIZ_CHANNEL_ID
    )

    if quiz_channel is not None:

        await cleanup_old_quizzes(
            quiz_channel
        )

        await send_new_quiz()

    else:

        print(
            "❌ Quiz-Kanal nicht gefunden."
        )

    # ========================================================
    # DEVELOPER PANEL
    # ========================================================

    await send_application_panel()

    # ========================================================
    # NICKNAME PANEL
    # ========================================================

    await send_nickname_panel()

    # ========================================================
    # RLP NAMETAGS
    # ========================================================

    # Beim Start werden ALLE Mitglieder mit der
    # RLP-Rolle überprüft.
    #
    # Personen, die RLP vorher selbst entfernt haben,
    # werden durch die JSON-Datei übersprungen.
    await update_all_nametags()


# ============================================================
# MEMBER JOIN
# ============================================================

@bot.event
async def on_member_join(member):

    if member.guild.id != GUILD_ID:
        return

    await asyncio.sleep(2)

    # Neues Mitglied:
    # Wenn es die RLP-Rolle besitzt,
    # soll RLP gesetzt werden.
    await set_nametag(
        member,
        force=True
    )


# ============================================================
# ROLE UPDATE
# ============================================================

@bot.event
async def on_member_update(
    before,
    after
):

    if after.guild.id != GUILD_ID:
        return

    role = after.guild.get_role(
        NAMETAG_ROLE_ID
    )

    if role is None:
        return

    # ========================================================
    # ROLLE WURDE NEU VERGEBEN
    # ========================================================

    if (
        role not in before.roles
        and role in after.roles
    ):

        # Wenn die Rolle neu vergeben wird,
        # darf RLP wieder gesetzt werden.
        nametag_removed_users.discard(
            after.id
        )

        save_nametag_data()

        await set_nametag(
            after,
            force=True
        )


# ============================================================
# NACHRICHTEN
# ============================================================

@bot.event
async def on_message(message):

    global current_quiz
    global current_quiz_message

    if message.author == bot.user:
        return

    if message.channel.id != QUIZ_CHANNEL_ID:
        return

    if current_quiz is None:
        return

    answer = normalize(
        message.content
    )

    correct_answer = normalize(
        current_quiz[1]
    )

    user_id = message.author.id

    # ========================================================
    # RICHTIG
    # ========================================================

    if answer == correct_answer:

        async with quiz_lock:

            if current_quiz is None:
                return

            for key, temp_message in list(
                temporary_messages.items()
            ):

                await safe_delete(
                    temp_message
                )

                temporary_messages.pop(
                    key,
                    None
                )

            old_quiz = current_quiz_message

            current_quiz = None
            current_quiz_message = None

            await safe_delete(
                old_quiz
            )

            result_message = await message.channel.send(
                f"✅ {message.author.mention} **Richtig!**"
            )

            await replace_temporary_message(
                user_id,
                "result",
                result_message
            )

            await send_new_quiz()

        return

    # ========================================================
    # FALSCH
    # ========================================================

    result_message = await message.channel.send(
        f"❌ {message.author.mention} "
        f"Leider falsch! Nächster Versuch, vielleicht wird's dann!"
    )

    await replace_temporary_message(
        user_id,
        "result",
        result_message
    )


# ============================================================
# TOKEN
# ============================================================

TOKEN = os.environ.get(
    "DISCORD_TOKEN"
)

if not TOKEN:

    raise RuntimeError(
        "❌ DISCORD_TOKEN wurde nicht gefunden. "
        "Prüfe dein GitHub Secret."
    )


# ============================================================
# BOT STARTEN
# ============================================================

bot.run(
    TOKEN
)
```
