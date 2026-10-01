import os
import random
import re
import asyncio
import discord

CHANNEL_ID = 1533409789256925185

QUIZZES = [
    (["🍕", "🧀"], "Pizza"),
    (["🌧️", "🌈"], "Regenbogen"),
    (["🐶", "🏠"], "Hundehütte"),
    (["🍎", "📱"], "Apple"),
    (["🌙", "😴"], "Nacht"),
    (["🔥", "🚒"], "Feuerwehr"),
    (["🎬", "🍿"], "Kino"),
    (["✈️", "🌴"], "Urlaub"),
    (["⚽", "🥅"], "Fußball"),
    (["🐟", "🎣"], "Fischen"),
    (["🍔", "🍟"], "Fast Food"),
    (["🚗", "⛽"], "Auto"),
    (["📚", "🏫"], "Schule"),
    (["🎄", "🎁"], "Weihnachten"),
    (["🎃", "👻"], "Halloween"),
    (["❤️", "🌹"], "Liebe"),
    (["🐱", "🧀"], "Katze"),
    (["🚀", "🌕"], "Weltraum"),
    (["🏴‍☠️", "🚢"], "Piraten"),
    (["👑", "🏰"], "König"),
    (["🎮", "🕹️"], "Gaming"),
    (["🏖️", "☀️"], "Strand"),
    (["☕", "🥐"], "Frühstück"),
    (["🎂", "🎁"], "Geburtstag"),
    (["🚂", "🎫"], "Zugfahrt"),
    (["🏀", "🏆"], "Basketball"),
    (["🎸", "🎤"], "Musik"),
    (["🍦", "☀️"], "Eis"),
    (["🐝", "🍯"], "Biene"),
    (["🏕️", "🔥"], "Camping"),
    (["🌊", "🏄"], "Surfen"),
    (["🐘", "🌍"], "Elefant"),
    (["🦁", "👑"], "Löwe"),
    (["🐍", "🌿"], "Schlange"),
    (["🐬", "🌊"], "Delfin"),
    (["🦈", "🌊"], "Hai"),
    (["🐧", "❄️"], "Pinguin"),
    (["🦄", "✨"], "Einhorn"),
    (["🐲", "🔥"], "Drache"),
    (["🕷️", "🕸️"], "Spinne"),
    (["🐢", "🏁"], "Schildkröte"),
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
    (["🐊", "🌊"], "Krokodil"),
    (["🦋", "🌸"], "Schmetterling"),
    (["🌞", "🌻"], "Sommer"),
    (["❄️", "⛄"], "Winter"),
    (["🍂", "🌳"], "Herbst"),
    (["🌷", "🌸"], "Frühling"),
    (["🌋", "🔥"], "Vulkan"),
    (["🏔️", "❄️"], "Berg"),
    (["🏜️", "🐪"], "Wüste"),
    (["🌲", "🏡"], "Wald"),
    (["🌊", "🏝️"], "Insel"),
    (["🌍", "✈️"], "Weltreise"),
    (["🗺️", "🧳"], "Reise"),
    (["🏨", "🛏️"], "Hotel"),
    (["🚕", "🏙️"], "Taxi"),
    (["🚌", "🚏"], "Bus"),
    (["🚲", "🛣️"], "Fahrrad"),
    (["🏍️", "🛣️"], "Motorrad"),
    (["🚓", "👮"], "Polizei"),
    (["🚑", "🏥"], "Krankenwagen"),
    (["🚁", "🚨"], "Hubschrauber"),
    (["🚢", "⚓"], "Schiff"),
    (["🚆", "🚉"], "Zug"),
    (["🛫", "🛬"], "Flugzeug"),
    (["📱", "💬"], "Chat"),
    (["💻", "⌨️"], "Computer"),
    (["📺", "🍿"], "Fernsehen"),
    (["📷", "🤳"], "Foto"),
    (["🎧", "🎵"], "Musik"),
    (["🎤", "🎶"], "Sänger"),
    (["🥁", "🎵"], "Schlagzeug"),
    (["🎹", "🎶"], "Klavier"),
    (["🎨", "🖌️"], "Malen"),
    (["📖", "🔦"], "Lesen"),
    (["✏️", "📓"], "Schreiben"),
    (["🔬", "🧪"], "Wissenschaft"),
    (["🧑‍🍳", "🍳"], "Kochen"),
    (["🍰", "🧁"], "Backen"),
    (["🥪", "🥤"], "Mittagessen"),
    (["🍝", "🍅"], "Nudeln"),
    (["🍣", "🥢"], "Sushi"),
    (["🌮", "🌶️"], "Taco"),
    (["🍩", "☕"], "Donut"),
    (["🍫", "🥛"], "Schokolade"),
    (["🍓", "🍒"], "Beeren"),
    (["🍉", "☀️"], "Wassermelone"),
    (["🎁", "🎀"], "Geschenk"),
    (["🎈", "🎉"], "Party"),
    (["💰", "🏦"], "Geld"),
    (["💎", "💰"], "Reichtum"),
    (["🔑", "🚪"], "Schlüssel"),
    (["🔒", "🔑"], "Schloss"),
    (["📧", "💻"], "E-Mail"),
    (["📞", "📱"], "Anruf"),
    (["⏰", "😴"], "Wecker"),
    (["🛏️", "😴"], "Schlafen"),
    (["🚿", "🧼"], "Duschen"),
    (["🪥", "😁"], "Zähneputzen"),
    (["👟", "🏃"], "Laufen"),
    (["🏊", "🌊"], "Schwimmen"),
    (["🚴", "🚲"], "Radfahren"),
    (["🏋️", "💪"], "Fitness"),
    (["🎯", "🏆"], "Gewinnen"),
    (["🥇", "🏆"], "Sieger"),
    (["🎓", "📚"], "Abschluss"),
    (["💡", "🧠"], "Idee"),
    (["❤️", "😊"], "Glück"),
    (["😂", "🤣"], "Lachen"),
    (["😡", "🔥"], "Wut"),
    (["😭", "💧"], "Weinen"),
    (["😎", "🕶️"], "Cool"),
]

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)

current_quiz = None
quiz_message = None

# Hier wird für JEDEN Nutzer die letzte Ergebnis-Nachricht gespeichert.
last_result_messages = {}

# Verhindert, dass mehrere richtige Antworten gleichzeitig
# mehrere neue Quizze erzeugen.
quiz_lock = asyncio.Lock()


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
        print("❌ Der Bot darf diese Nachricht nicht löschen!")
    except discord.HTTPException as error:
        print(f"❌ Fehler beim Löschen: {error}")


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

    embed.set_footer(text="Viel Glück! 🍀")
    return embed


async def send_new_quiz():
    global current_quiz, quiz_message

    channel = bot.get_channel(CHANNEL_ID)

    if channel is None:
        print("❌ Kanal wurde nicht gefunden!")
        return

    current_quiz = random.choice(QUIZZES)

    embed = create_quiz_embed(current_quiz[0])

    quiz_message = await channel.send(embed=embed)

    print(f"✅ Neues Quiz: {current_quiz[1]}")


@bot.event
async def on_ready():
    print(f"✅ Bot ist online als {bot.user}")

    if current_quiz is None:
        await send_new_quiz()


@bot.event
async def on_message(message):
    global current_quiz
    global quiz_message

    # Bot ignoriert seine eigenen Nachrichten
    if message.author == bot.user:
        return

    # Nur der Quiz-Kanal
    if message.channel.id != CHANNEL_ID:
        return

    # Wenn kein Quiz aktiv ist
    if current_quiz is None:
        return

    answer = normalize(message.content)
    correct_answer = normalize(current_quiz[1])

    user_id = message.author.id
    mention = message.author.mention

    # =====================================================
    # RICHTIGE ANTWORT
    # =====================================================

    if answer == correct_answer:

        # Die alte Ergebnis-Nachricht DIESES Nutzers löschen.
        old_result = last_result_messages.get(user_id)

        if old_result is not None:
            await safe_delete(old_result)

        # Neue Richtig-Nachricht senden.
        new_result = await message.channel.send(
            f"✅ {mention} Richtig!"
        )

        # Neue Nachricht für DIESEN Nutzer speichern.
        last_result_messages[user_id] = new_result

        # Das alte Quiz löschen.
        old_quiz = quiz_message

        quiz_message = None
        current_quiz = None

        await safe_delete(old_quiz)

        # Neues Quiz erstellen.
        async with quiz_lock:
            if current_quiz is None:
                await send_new_quiz()

    # =====================================================
    # FALSCHE ANTWORT
    # =====================================================

    else:

        # Die alte Ergebnis-Nachricht DIESES Nutzers löschen.
        old_result = last_result_messages.get(user_id)

        if old_result is not None:
            await safe_delete(old_result)

        # Neue Falsch-Nachricht senden.
        new_result = await message.channel.send(
            f"❌ {mention} Leider falsch! Nächster Versuch, vielleicht wird's dann!"
        )

        # Für DIESEN Nutzer speichern.
        last_result_messages[user_id] = new_result


TOKEN = os.environ["DISCORD_TOKEN"]

bot.run(TOKEN)
