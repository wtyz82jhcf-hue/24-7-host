import os
import random
import re
import asyncio
import discord


# ============================================================
# KANÄLE
# ============================================================

QUIZ_CHANNEL_ID = 1533409789256925185

APPLICATION_CHANNEL_ID = 1541391365219295343

REVIEW_CHANNEL_ID = 1548404201493762181


# ============================================================
# EMOJI-QUIZZE
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
    (["☕", "🥐"], "Frühstück"),

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
# DEVELOPER-BEWERBUNG - 9 FRAGEN
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


# ============================================================
# GLOBALE VARIABLEN
# ============================================================

current_quiz = None
current_quiz_message = None

last_result_messages = {}

active_applications = set()

quiz_lock = asyncio.Lock()

quiz_bag = []

last_quiz_emojis = set()

startup_finished = False

# Für jeden User eigene Zähler
skip_counts = {}
hint_counts = {}


# ============================================================
# HILFSFUNKTIONEN
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
            f"❌ Fehler beim Löschen: {error}"
        )


async def delete_previous_result(
    user,
    channel
):

    user_id = user.id

    old_message = last_result_messages.get(
        user_id
    )

    if old_message is not None:

        await safe_delete(
            old_message
        )

        last_result_messages.pop(
            user_id,
            None
        )

        return

    try:

        async for message in channel.history(
            limit=100
        ):

            if message.author != bot.user:
                continue

            if user.mention not in message.content:
                continue

            if (
                message.content.startswith("✅")
                or message.content.startswith("❌")
            ):

                await safe_delete(
                    message
                )

                return

    except discord.Forbidden:

        print(
            "❌ Keine Berechtigung zum Lesen des Verlaufs."
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

    # Möglichst keine Emojis aus dem letzten Quiz wiederverwenden.
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

    # Falls kein komplett anderes Quiz verfügbar ist:
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
            "❌ Emoji-Quiz-Kanal wurde nicht gefunden."
        )

        return

    # Neues Quiz auswählen
    current_quiz = get_next_quiz()

    # Jeder User bekommt beim neuen Quiz
    # wieder 3 Übersprünge und 3 Hinweise.
    skip_counts.clear()
    hint_counts.clear()

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
# ALTE QUIZ-NACHRICHTEN LÖSCHEN
# ============================================================

async def cleanup_old_quizzes(
    channel
):

    try:

        async for message in channel.history(
            limit=100
        ):

            if message.author != bot.user:
                continue

            if not message.embeds:
                continue

            embed = message.embeds[0]

            if embed.title == "🎯 Emoji-Quiz":

                await safe_delete(
                    message
                )

    except discord.Forbidden:

        print(
            "❌ Keine Berechtigung, alte Quizze zu löschen."
        )


# ============================================================
# QUIZ BUTTONS
# ============================================================

class QuizView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )


    # --------------------------------------------------------
    # ÜBERSPRINGEN
    # --------------------------------------------------------

    @discord.ui.button(
        label="Überspringen",
        emoji="⏭️",
        style=discord.ButtonStyle.secondary,
        custom_id="quiz_skip_button"
    )
    async def skip(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        global current_quiz
        global current_quiz_message

        user_id = interaction.user.id

        used = skip_counts.get(
            user_id,
            0
        )

        # Schon 3/3
        if used >= 3:

            await interaction.response.send_message(
                "Du hast schon **3/3 mal übersprungen**.",
                ephemeral=True
            )

            return

        # Zähler erhöhen
        skip_counts[user_id] = used + 1

        # Altes Quiz sichern
        old_message = current_quiz_message

        # Altes Quiz löschen
        await safe_delete(
            old_message
        )

        # Neues Quiz für alle
        current_quiz = get_next_quiz()

        embed = create_quiz_embed(
            current_quiz[0]
        )

        channel = interaction.channel

        current_quiz_message = await channel.send(
            embed=embed,
            view=QuizView()
        )

        await interaction.response.send_message(
            f"⏭️ Übersprungen!\n\n"
            f"Du hast noch "
            f"**{3 - skip_counts[user_id]}/3** "
            f"Übersprünge.",
            ephemeral=True
        )


    # --------------------------------------------------------
    # ANFANGSBUCHSTABE
    # --------------------------------------------------------

    @discord.ui.button(
        label="Anfangsbuchstabe",
        emoji="💡",
        style=discord.ButtonStyle.primary,
        custom_id="quiz_hint_button"
    )
    async def hint(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        global current_quiz

        user_id = interaction.user.id

        used = hint_counts.get(
            user_id,
            0
        )

        # Schon 3/3
        if used >= 3:

            await interaction.response.send_message(
                "Du hast schon **3/3 mal den Anfangsbuchstaben aufgedeckt**.",
                ephemeral=True
            )

            return

        # Zähler erhöhen
        hint_counts[user_id] = used + 1

        answer = current_quiz[1]

        first_letter = answer[0].upper()

        # Für ALLE sichtbar
        await interaction.response.send_message(
            f"💡 **Anfangsbuchstabe:** `{first_letter}`\n\n"
            f"Verwendet: "
            f"**{hint_counts[user_id]}/3**",
            ephemeral=False
        )


# ============================================================
# DEVELOPER-BEWERBUNG BUTTON
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
        custom_id="developer_application_button"
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

            # DM testen
            try:

                await user.send(
                    "👨‍💻 **Developer-Bewerbung**\n\n"
                    "Vielen Dank für dein Interesse an unserem "
                    "Developer-Team!\n\n"
                    "Die Bewerbung besteht aus **9 Fragen**.\n"
                    "Die Fragen kommen **einzeln**.\n\n"
                    "Du beantwortest Frage 1 → "
                    "danach kommt Frage 2 → "
                    "bis Frage 9.\n\n"
                    "Schreibe **abbrechen**, wenn du die "
                    "Bewerbung beenden möchtest."
                )

            except discord.Forbidden:

                await interaction.response.send_message(
                    "❌ Ich kann dir keine DM schicken.\n\n"
                    "Bitte aktiviere deine Direktnachrichten "
                    "für diesen Server und versuche es erneut.",
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
# DEVELOPER-BEWERBUNG DURCHFÜHREN
# ============================================================

async def start_developer_application(
    user
):

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

    # Bewerbung fertig
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
# BEWERBUNG AN REVIEW-KANAL
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
            "❌ Bewerbungs-Review-Kanal wurde nicht gefunden."
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

            value = (
                value[:1021]
                + "..."
            )

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

    print(
        f"✅ Bewerbung von {user} wurde gesendet."
    )


# ============================================================
# DEVELOPER PANEL
# ============================================================

async def send_application_panel():

    channel = bot.get_channel(
        APPLICATION_CHANNEL_ID
    )

    if channel is None:

        print(
            "❌ Developer-Bewerbungskanal wurde nicht gefunden."
        )

        return

    # Prüfen, ob Panel schon existiert
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

                print(
                    "✅ Developer-Panel existiert bereits."
                )

                return

    except discord.Forbidden:

        print(
            "❌ Keine Berechtigung zum Lesen des Kanals."
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
        "✅ Developer-Panel erstellt."
    )


# ============================================================
# BOT KLASSE
# ============================================================

class QuizBot(
    discord.Client
):

    async def setup_hook(self):

        # Developer-Button nach Neustart registrieren
        self.add_view(
            DeveloperApplicationView()
        )

        # Quiz-Buttons nach Neustart registrieren
        self.add_view(
            QuizView()
        )


bot = QuizBot(
    intents=intents
)


# ============================================================
# BOT READY
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
    # QUIZ
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
            "❌ Quiz-Kanal wurde nicht gefunden."
        )

    # ========================================================
    # DEVELOPER BEWERBUNG
    # ========================================================

    await send_application_panel()


# ============================================================
# NACHRICHTEN
# ============================================================

@bot.event
async def on_message(
    message
):

    global current_quiz
    global current_quiz_message

    # Eigene Nachrichten ignorieren
    if message.author == bot.user:
        return

    # Nur Quiz-Kanal
    if message.channel.id != QUIZ_CHANNEL_ID:
        return

    # Kein aktives Quiz
    if current_quiz is None:
        return

    answer = normalize(
        message.content
    )

    correct_answer = normalize(
        current_quiz[1]
    )

    user = message.author

    # ========================================================
    # RICHTIG
    # ========================================================

    if answer == correct_answer:

        async with quiz_lock:

            if current_quiz is None:
                return

            # Alte Ergebnis-Nachricht dieses Users löschen
            await delete_previous_result(
                user,
                message.channel
            )

            # Neue Richtig-Nachricht
            result_message = await message.channel.send(
                f"✅ {user.mention} Richtig!"
            )

            last_result_messages[
                user.id
            ] = result_message

            # Altes Quiz sichern
            old_quiz_message = (
                current_quiz_message
            )

            # Quiz deaktivieren
            current_quiz = None
            current_quiz_message = None

            # Altes Quiz löschen
            await safe_delete(
                old_quiz_message
            )

            # Neues Quiz
            await send_new_quiz()

        return

    # ========================================================
    # FALSCH
    # ========================================================

    await delete_previous_result(
        user,
        message.channel
    )

    result_message = await message.channel.send(
        f"❌ {user.mention} Leider falsch! "
        "Nächster Versuch, vielleicht wird's dann!"
    )

    last_result_messages[
        user.id
    ] = result_message


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
