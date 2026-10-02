
import random
import re
import asyncio
import discord


# ============================================================
# KANÄLE
# ============================================================

# Emoji-Quiz
QUIZ_CHANNEL_ID = 1533409789256925185

# Developer-Bewerbung
APPLICATION_CHANNEL_ID = 1541391365219295343

# Hier kommen die fertigen Bewerbungen rein
REVIEW_CHANNEL_ID = 1548404201493762181


# ============================================================
# EMOJI-QUIZZE
# ============================================================

QUIZZES = [
    (["🍕", "🧀"], "Pizza"),
    (["🍔", "🍟"], "Fast Food"),
    (["🍎", "🍏"], "Apfel"),
    (["🍌", "🍓"], "Obst"),
    (["🍓", "🍒"], "Beeren"),
    (["🍉", "☀️"], "Wassermelone"),
    (["🍋", "🥤"], "Limonade"),
    (["🍫", "🥛"], "Schokolade"),
    (["🍩", "☕"], "Donut"),
    (["🍰", "🧁"], "Backen"),
    (["🍝", "🍅"], "Nudeln"),
    (["🍣", "🥢"], "Sushi"),
    (["🌮", "🌶️"], "Taco"),
    (["🍦", "☀️"], "Eis"),
    (["🥪", "🥤"], "Mittagessen"),
    (["☕", "🥐"], "Frühstück"),
    (["🎂", "🎈"], "Geburtstag"),
    (["🎁", "🎀"], "Geschenk"),
    (["🎈", "🎉"], "Party"),
    (["🍿", "📺"], "Fernsehen"),
    (["📖", "🔦"], "Lesen"),
    (["✏️", "📓"], "Schreiben"),
    (["🎨", "🖌️"], "Malen"),
    (["📷", "🤳"], "Foto"),
    (["📱", "💬"], "Chat"),
    (["📞", "📱"], "Anruf"),
    (["💻", "⌨️"], "Computer"),
    (["📧", "💻"], "E-Mail"),
    (["🎮", "🕹️"], "Gaming"),
    (["🎧", "🎵"], "Musik"),
    (["🎤", "🎶"], "Sänger"),
    (["🎹", "🎼"], "Klavier"),
    (["🥁", "🎵"], "Schlagzeug"),
    (["🎸", "🥁"], "Band"),
    (["🎬", "🎟️"], "Film"),
    (["🎨", "🖼️"], "Kunst"),
    (["⚽", "🥅"], "Fußball"),
    (["🏀", "⛹️"], "Basketball"),
    (["🏐", "🏆"], "Volleyball"),
    (["🎾", "🏟️"], "Tennis"),
    (["🥊", "🏆"], "Boxen"),
    (["🏎️", "🏁"], "Rennsport"),
    (["🚴", "🏆"], "Radrennen"),
    (["🏊", "🌊"], "Schwimmen"),
    (["👟", "🏃"], "Laufen"),
    (["🏋️", "💪"], "Fitness"),
    (["🎯", "🏆"], "Gewinnen"),
    (["🥇", "🏆"], "Sieger"),
    (["🚗", "⛽"], "Auto"),
    (["🚲", "🛣️"], "Fahrrad"),
    (["🏍️", "🛣️"], "Motorrad"),
    (["🚕", "🏙️"], "Taxi"),
    (["🚌", "🚏"], "Bus"),
    (["🚓", "👮"], "Polizei"),
    (["🚑", "🏥"], "Krankenwagen"),
    (["🚒", "🔥"], "Feuerwehr"),
    (["🚁", "🚨"], "Hubschrauber"),
    (["🚢", "⚓"], "Schiff"),
    (["🚆", "🚉"], "Zug"),
    (["🛫", "🛬"], "Flugzeug"),
    (["🚂", "🎫"], "Zugfahrt"),
    (["✈️", "🧳"], "Reise"),
    (["🗺️", "🧳"], "Urlaub"),
    (["🏨", "🛏️"], "Hotel"),
    (["🌍", "✈️"], "Weltreise"),
    (["🏖️", "☀️"], "Strand"),
    (["🌊", "🏝️"], "Insel"),
    (["🏕️", "🔥"], "Camping"),
    (["🏔️", "❄️"], "Berg"),
    (["🏜️", "🐪"], "Wüste"),
    (["🌲", "🏡"], "Wald"),
    (["🌋", "🔥"], "Vulkan"),
    (["🌞", "🌻"], "Sommer"),
    (["❄️", "⛄"], "Winter"),
    (["🍂", "🌳"], "Herbst"),
    (["🌷", "🌸"], "Frühling"),
    (["🌧️", "☔"], "Regen"),
    (["☁️", "💧"], "Wolke"),
    (["🌈", "☀️"], "Regenbogen"),
    (["🌙", "⭐"], "Mond"),
    (["🌙", "😴"], "Nacht"),
    (["🌞", "🔥"], "Hitze"),
    (["🌊", "🐚"], "Meer"),
    (["⭐", "🌌"], "Sterne"),
    (["🐶", "🦴"], "Hund"),
    (["🐱", "🐭"], "Katze"),
    (["🐭", "🧀"], "Maus"),
    (["🐰", "🥕"], "Hase"),
    (["🐮", "🥛"], "Kuh"),
    (["🐷", "🌾"], "Schwein"),
    (["🐔", "🥚"], "Huhn"),
    (["🐴", "🏇"], "Pferd"),
    (["🐵", "🍌"], "Affe"),
    (["🦊", "🌲"], "Fuchs"),
    (["🐻", "🍯"], "Bär"),
    (["🐼", "🎋"], "Panda"),
    (["🦒", "🌳"], "Giraffe"),
    (["🐘", "🌍"], "Elefant"),
    (["🦁", "👑"], "Löwe"),
    (["🐯", "🌴"], "Tiger"),
    (["🐺", "🌙"], "Wolf"),
    (["🦉", "🌙"], "Eule"),
    (["🦅", "☁️"], "Adler"),
    (["🐬", "🌊"], "Delfin"),
    (["🦈", "🌊"], "Hai"),
    (["🐙", "🌊"], "Oktopus"),
    (["🦀", "🏖️"], "Krabbe"),
    (["🐸", "💧"], "Frosch"),
    (["🐢", "🏁"], "Schildkröte"),
    (["🐍", "🌿"], "Schlange"),
    (["🐊", "🌊"], "Krokodil"),
    (["🐧", "❄️"], "Pinguin"),
    (["🦄", "✨"], "Einhorn"),
    (["🐲", "🔥"], "Drache"),
    (["🦋", "🌸"], "Schmetterling"),
    (["🐝", "🌼"], "Biene"),
    (["🐞", "🌿"], "Marienkäfer"),
    (["🌻", "🌞"], "Sonnenblume"),
    (["🌹", "❤️"], "Rose"),
    (["🌲", "🎄"], "Tannenbaum"),
    (["🎄", "🎁"], "Weihnachten"),
    (["🎃", "👻"], "Halloween"),
    (["🏴‍☠️", "🚢"], "Piraten"),
    (["👑", "🏰"], "König"),
    (["❤️", "🌹"], "Liebe"),
    (["❤️", "😊"], "Glück"),
    (["😂", "🤣"], "Lachen"),
    (["😭", "💧"], "Weinen"),
    (["😡", "🔥"], "Wut"),
    (["😎", "🕶️"], "Cool"),
    (["😴", "🛏️"], "Schlafen"),
    (["⏰", "😴"], "Wecker"),
    (["🚿", "🧼"], "Duschen"),
    (["🪥", "😁"], "Zähneputzen"),
    (["🧠", "💡"], "Idee"),
    (["🎓", "📚"], "Abschluss"),
    (["🔬", "🧪"], "Wissenschaft"),
    (["🧑‍🍳", "🍳"], "Kochen"),
    (["💰", "🏦"], "Geld"),
    (["💎", "💰"], "Reichtum"),
    (["🔑", "🚪"], "Schlüssel"),
    (["🔒", "🔑"], "Schloss"),
    (["🔍", "🕵️"], "Detektiv"),
    (["📦", "📬"], "Paket"),
    (["📅", "🗓️"], "Kalender"),
    (["⏱️", "⌛"], "Zeit"),
    (["🔔", "📣"], "Alarm"),
    (["🔦", "🌙"], "Taschenlampe"),
    (["☂️", "🌧️"], "Regenschirm"),
    (["🧤", "❄️"], "Handschuhe"),
    (["🧣", "❄️"], "Schal"),
    (["👟", "⚽"], "Fußballschuhe"),
    (["👕", "👖"], "Kleidung"),
    (["🧢", "🧒"], "Mütze"),
    (["🕶️", "☀️"], "Sonnenbrille"),
    (["👑", "💎"], "Krone"),
    (["💍", "❤️"], "Ehering"),
    (["🎒", "📚"], "Schultasche"),
    (["🏫", "👨‍🏫"], "Schule"),
    (["🏠", "🔑"], "Haus"),
    (["🛏️", "🏠"], "Schlafzimmer"),
    (["🛋️", "📺"], "Wohnzimmer"),
    (["🍳", "🥚"], "Ei"),
    (["🍞", "🧈"], "Brot"),
    (["🧀", "🐭"], "Käse"),
    (["🍯", "🐝"], "Honig"),
    (["🥕", "🐰"], "Karotte"),
    (["🌽", "🐔"], "Mais"),
    (["🍉", "🔪"], "Obstschneiden"),
    (["🥤", "🧊"], "Getränk"),
    (["🍵", "🌿"], "Tee"),
    (["🥛", "🥣"], "Milch"),
    (["🧊", "🥤"], "Eiswürfel"),
    (["🍪", "🥛"], "Kekse"),
    (["🍬", "🍭"], "Süßigkeiten"),
    (["🍭", "🎪"], "Jahrmarkt"),
    (["🎡", "🎢"], "Freizeitpark"),
    (["🎠", "🎪"], "Karussell"),
    (["🎳", "🎯"], "Bowling"),
    (["🏓", "🏆"], "Tischtennis"),
    (["🏸", "🏆"], "Badminton"),
    (["🏹", "🎯"], "Bogenschießen"),
    (["⛳", "🏌️"], "Golf"),
    (["🎣", "🐟"], "Angeln"),
    (["⛸️", "❄️"], "Eislaufen"),
    (["🎿", "🏔️"], "Skifahren"),
    (["🏂", "❄️"], "Snowboarden"),
    (["🛷", "⛄"], "Rodeln"),
    (["🏄", "🌊"], "Surfen"),
    (["🤿", "🌊"], "Tauchen"),
    (["🛶", "🌊"], "Kanufahren"),
    (["🚤", "🌊"], "Motorboot"),
    (["⛵", "🌊"], "Segeln"),
    (["🚦", "🚗"], "Verkehr"),
    (["⛽", "🚗"], "Tanken"),
    (["🅿️", "🚗"], "Parkplatz"),
    (["🚧", "🚗"], "Baustelle"),
    (["🛣️", "🚗"], "Straße"),
    (["🌐", "💻"], "Internet"),
    (["📡", "📶"], "WLAN"),
    (["🔋", "📱"], "Akku"),
    (["🔌", "⚡"], "Strom"),
    (["💡", "🔌"], "Lampe"),
    (["🖨️", "📄"], "Drucker"),
    (["⌨️", "🖥️"], "Tastatur"),
    (["🖱️", "💻"], "Maus"),
    (["📺", "🎮"], "Konsole"),
    (["📻", "🎵"], "Radio"),
    (["🎧", "📱"], "Kopfhörer"),
    (["📹", "🎥"], "Video"),
    (["🎞️", "🎬"], "Filmrolle"),
    (["📡", "📺"], "Fernsehen"),
    (["📚", "📖"], "Bücher"),
    (["📝", "✏️"], "Notiz"),
    (["📌", "📋"], "Plan"),
    (["📍", "🗺️"], "Standort"),
    (["✂️", "📄"], "Schere"),
    (["📎", "📄"], "Büro"),
    (["🖍️", "🎨"], "Malen"),
    (["🧩", "🧠"], "Puzzle"),
    (["🎲", "🎯"], "Spiel"),
    (["♟️", "♟️"], "Schach"),
    (["🃏", "🎲"], "Karten"),
    (["🎁", "🎉"], "Feier"),
    (["🎂", "🕯️"], "Geburtstag"),
    (["💌", "❤️"], "Liebesbrief"),
    (["📮", "✉️"], "Post"),
    (["✉️", "📬"], "Brief"),
    (["📦", "🚚"], "Lieferung"),
    (["🛒", "🛍️"], "Einkaufen"),
    (["🏪", "🛒"], "Supermarkt"),
    (["💳", "🏦"], "Bezahlen"),
    (["💵", "💰"], "Geld"),
    (["🏧", "💳"], "Geldautomat"),
    (["🏦", "💰"], "Bank"),
    (["🏥", "🩺"], "Arzt"),
    (["💊", "🏥"], "Medizin"),
    (["🚑", "🩹"], "Erste Hilfe"),
    (["🦷", "🪥"], "Zahnarzt"),
    (["👓", "👀"], "Brille"),
    (["👂", "🎧"], "Ohren"),
    (["👃", "🌸"], "Nase"),
    (["👟", "🧦"], "Socken"),
    (["🧤", "🧣"], "Winterkleidung"),
    (["🧥", "❄️"], "Winterjacke"),
    (["👗", "👠"], "Kleid"),
    (["👔", "👞"], "Anzug"),
    (["🎩", "🧥"], "Hut"),
    (["💄", "🪞"], "Make-up"),
    (["🪞", "👀"], "Spiegel"),
    (["🧴", "🧼"], "Seife"),
    (["🧹", "🏠"], "Putzen"),
    (["🧺", "👕"], "Wäsche"),
    (["🧽", "🧼"], "Waschen"),
    (["🛁", "🫧"], "Badewanne"),
    (["🚽", "🧻"], "Toilette"),
    (["🧻", "🧼"], "Papier"),
    (["🪣", "💧"], "Eimer"),
    (["🔨", "🪚"], "Handwerk"),
    (["🪛", "🔩"], "Werkzeug"),
    (["🔧", "🚗"], "Reparatur"),
    (["🧰", "🔧"], "Werkzeugkasten"),
    (["🪜", "🏠"], "Leiter"),
    (["🧯", "🔥"], "Feuerlöscher"),
    (["🏠", "🌳"], "Garten"),
    (["🌱", "🌷"], "Pflanzen"),
    (["🌵", "🏜️"], "Kaktus"),
    (["🌳", "🍎"], "Apfelbaum"),
    (["🍁", "🍂"], "Blätter"),
    (["🌴", "🏖️"], "Palme"),
    (["🌾", "🌻"], "Feld"),
    (["🌧️", "🌱"], "Wachsen"),
    (["🌨️", "❄️"], "Schnee"),
    (["⛈️", "⚡"], "Gewitter"),
    (["🌪️", "☁️"], "Sturm"),
    (["☀️", "🌤️"], "Sonne"),
    (["🌅", "🌄"], "Sonnenaufgang"),
    (["🌇", "🌆"], "Sonnenuntergang"),
    (["🌌", "🔭"], "Sternenhimmel"),
    (["🔭", "🌙"], "Astronomie"),
    (["🏰", "🛡️"], "Burg"),
    (["🏯", "⛩️"], "Schloss"),
    (["🗼", "🇫🇷"], "Paris"),
    (["🗽", "🇺🇸"], "New York"),
    (["🕌", "🕌"], "Moschee"),
    (["⛪", "🔔"], "Kirche"),
    (["🕍", "🕯️"], "Synagoge"),
    (["🏛️", "📚"], "Museum"),
    (["🖼️", "🏛️"], "Galerie"),
    (["🎭", "🎟️"], "Theater"),
    (["🎪", "🤡"], "Zirkus"),
    (["🎁", "📦"], "Paket"),
    (["🏆", "🥇"], "Pokal"),
    (["🎖️", "🏅"], "Medaille"),
    (["🏅", "🏃"], "Sport"),
    (["🧑‍🎓", "🎓"], "Student"),
    (["🧑‍🏫", "📚"], "Lehrer"),
    (["👨‍🚒", "🚒"], "Feuerwehrmann"),
    (["👮", "🚓"], "Polizist"),
    (["🧑‍🍳", "🍴"], "Koch"),
    (["🧑‍🎤", "🎤"], "Sänger"),
    (["👨‍⚕️", "🏥"], "Arzt"),
    (["👨‍🔧", "🔧"], "Mechaniker"),
    (["👨‍🌾", "🌾"], "Bauer"),
    (["👩‍💻", "💻"], "Developer"),
    (["🧑‍🎨", "🎨"], "Künstler"),
    (["🕵️", "🔍"], "Detektiv"),
    (["👷", "🚧"], "Bauarbeiter"),
    (["🧑‍🚀", "🚀"], "Astronaut"),
    (["🧜", "🌊"], "Meerjungfrau"),
    (["🧚", "✨"], "Fee"),
    (["🧙", "🔮"], "Zauberer"),
    (["🧛", "🩸"], "Vampir"),
    (["🧟", "🧟"], "Zombie"),
    (["👻", "🏚️"], "Geist"),
    (["🤖", "⚙️"], "Roboter"),
    (["👽", "🛸"], "Alien"),
    (["🦸", "🦹"], "Superheld"),
    (["🤠", "🐎"], "Cowboy"),
    (["🥳", "🎉"], "Feier"),
    (["😇", "👼"], "Engel"),
    (["😈", "🔥"], "Teufel"),
    (["🤡", "🎪"], "Clown"),
    (["🧑‍🚀", "🌕"], "Mondmission"),
    (["🛰️", "🌍"], "Satellit"),
    (["🚀", "🪐"], "Rakete"),
    (["🌕", "🌊"], "Mond"),
    (["☀️", "🌍"], "Sonne"),
    (["🌎", "🌍"], "Erde"),
    (["🪐", "⭐"], "Planet"),
    (["⭐", "🌠"], "Sternschnuppe"),
]


# ============================================================
# DEVELOPER-BEWERBUNG
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
quiz_order = []
quiz_order_position = 0

# Pro User wird nur die letzte Richtig-/Falsch-Nachricht gespeichert.
last_result_messages = {}

# Bewerbungen, die gerade laufen.
active_applications = set()

# Verhindert gleichzeitige Quiz-Wechsel.
quiz_lock = asyncio.Lock()


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

    text = re.sub(r"[^a-z0-9]+", "", text)

    return text


async def safe_delete(message):
    if message is None:
        return

    try:
        await message.delete()

    except discord.NotFound:
        pass

    except discord.Forbidden:
        print("❌ Keine Berechtigung zum Löschen!")

    except discord.HTTPException as error:
        print(f"❌ Fehler beim Löschen: {error}")


async def delete_previous_result(user, channel):
    """
    Löscht die letzte Ergebnis-Nachricht dieses Users.

    Wenn der Bot zwischenzeitlich neu gestartet wurde,
    wird zusätzlich im Kanal nach der letzten passenden
    Nachricht gesucht.
    """

    user_id = user.id

    # Gespeicherte Nachricht verwenden.
    old_message = last_result_messages.get(user_id)

    if old_message is not None:
        await safe_delete(old_message)

        last_result_messages.pop(
            user_id,
            None
        )

        return

    # Fallback nach Neustart.
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
                await safe_delete(message)
                return

    except discord.Forbidden:
        print(
            "❌ Keine Berechtigung, den Nachrichtenverlauf zu lesen."
        )


# ============================================================
# QUIZ
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


async def send_new_quiz():
    global current_quiz
    global current_quiz_message
    global quiz_order
    global quiz_order_position

    channel = bot.get_channel(
        QUIZ_CHANNEL_ID
    )

    if channel is None:
        print(
            "❌ Emoji-Quiz-Kanal wurde nicht gefunden."
        )
        return

    # Alle Quizze werden zuerst gemischt.
    # Dadurch erscheint kein Rätsel erneut, bevor
    # einmal alle anderen Quizze benutzt wurden.
    if not quiz_order or quiz_order_position >= len(quiz_order):
        quiz_order = list(range(len(QUIZZES)))
        random.shuffle(quiz_order)
        quiz_order_position = 0

    quiz_index = quiz_order[quiz_order_position]
    quiz_order_position += 1

    current_quiz = QUIZZES[quiz_index]

    embed = create_quiz_embed(
        current_quiz[0]
    )

    current_quiz_message = await channel.send(
        embed=embed
    )

    print(
        f"✅ Neues Quiz: {current_quiz[1]}"
    )


# ============================================================
# DEVELOPER BUTTON
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

            # DM öffnen
            try:
                await user.send(
                    "👨‍💻 **Developer-Bewerbung**\n\n"
                    "Vielen Dank für dein Interesse an unserem Developer-Team!\n\n"
                    "Die Bewerbung besteht aus **9 Fragen**.\n"
                    "Die Fragen werden **einzeln** gestellt.\n\n"
                    "Du beantwortest Frage 1 → "
                    "danach kommt Frage 2 → "
                    "bis Frage 9.\n\n"
                    "Schreibe **abbrechen**, wenn du die Bewerbung beenden möchtest."
                )

            except discord.Forbidden:

                await interaction.response.send_message(
                    "❌ Ich kann dir keine DM schicken.\n\n"
                    "Bitte aktiviere deine Direktnachrichten für diesen Server "
                    "und klicke danach erneut auf **Bewerben**.",
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
# BEWERBUNG DURCHFÜHREN
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

        # Nur die aktuelle Frage senden.
        await user.send(
            f"**Frage {number}/9**\n\n"
            f"{question}"
        )

        # Auf die Antwort warten.
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

        # Abbrechen.
        if normalize(answer) == "abbrechen":

            await user.send(
                "❌ Deine Developer-Bewerbung wurde abgebrochen."
            )

            return

        # Antwort speichern.
        answers.append(
            answer
        )

        # Danach geht es automatisch
        # mit der nächsten Frage weiter.

    # Bewerbung abgeschlossen.
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
# BEWERBUNG INS TEAM-KANAL SENDEN
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
            "❌ Bewerbungs-Review-Kanal wurde nicht gefunden!"
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

        # Discord-Feldlimit beachten.
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

    print(
        f"✅ Developer-Bewerbung von {user} wurde gesendet."
    )


# ============================================================
# BEWERBUNGS-PANEL
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

    # Prüfen, ob bereits ein Panel vorhanden ist.
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
                    "✅ Developer-Bewerbungs-Panel existiert bereits."
                )
                return

    except discord.Forbidden:

        print(
            "❌ Keine Berechtigung, den Bewerbungskanal zu lesen."
        )

        return

    embed = discord.Embed(
        title="👨‍💻 Developer Bewerbung",
        description=(
            "**Hier Bewerben Als Developer!**\n\n"
            "Viel Glück!\n\n"
            "Du möchtest unser Developer-Team unterstützen?\n"
            "Klicke unten auf **Bewerben**, um deine Bewerbung zu starten."
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
        "✅ Developer-Bewerbungs-Panel erstellt."
    )


# ============================================================
# BOT KLASSE
# ============================================================

class QuizBot(
    discord.Client
):

    async def setup_hook(self):

        # Wichtig für den Button nach Neustarts.
        self.add_view(
            DeveloperApplicationView()
        )


bot = QuizBot(
    intents=intents
)


# ============================================================
# BOT READY
# ============================================================

started = False


@bot.event
async def on_ready():

    global started

    print(
        f"✅ Bot ist online als {bot.user}"
    )

    # on_ready kann bei einer Verbindung erneut aufgerufen werden.
    if started:
        return

    started = True

    # ========================================================
    # EMOJI-QUIZ STARTEN
    # ========================================================

    quiz_channel = bot.get_channel(
        QUIZ_CHANNEL_ID
    )

    if quiz_channel is not None:

        await send_new_quiz()

    else:

        print(
            "❌ Emoji-Quiz-Kanal nicht gefunden."
        )

    # ========================================================
    # DEVELOPER-PANEL
    # ========================================================

    await send_application_panel()


# ============================================================
# NACHRICHTEN
# ============================================================

@bot.event
async def on_message(message):

    global current_quiz
    global current_quiz_message

    # Eigene Nachrichten ignorieren.
    if message.author == bot.user:
        return

    # Nur im Quiz-Kanal auswerten.
    if message.channel.id != QUIZ_CHANNEL_ID:
        return

    # Kein Quiz aktiv.
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

            # Prüfen, ob das Quiz noch aktiv ist.
            if current_quiz is None:
                return

            # Alte Ergebnis-Nachricht des Users löschen.
            await delete_previous_result(
                user,
                message.channel
            )

            # Neue Richtig-Nachricht.
            result_message = await message.channel.send(
                f"✅ {user.mention} Richtig!"
            )

            last_result_messages[
                user.id
            ] = result_message

            # Altes Quiz speichern.
            old_quiz = current_quiz_message

            # Status löschen.
            current_quiz = None
            current_quiz_message = None

            # Altes Quiz löschen.
            await safe_delete(
                old_quiz
            )

            # Neues Quiz.
            await send_new_quiz()

        return

    # ========================================================
    # FALSCH
    # ========================================================

    # Alte Ergebnis-Nachricht des Users löschen.
    await delete_previous_result(
        user,
        message.channel
    )

    # Neue Falsch-Nachricht.
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
# START
# ============================================================

bot.run(
    TOKEN
)
