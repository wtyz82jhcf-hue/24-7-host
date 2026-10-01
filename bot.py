```python
import os
import random
import discord

# Discord-Kanal
CHANNEL_ID = 1533409789256925185

# Emoji-Rätsel
QUIZZES = [
    (["🍕", "👨‍🍳", "🔥", "🍅", "🧀", "🍴"], "Pizza"),
    (["🌧️", "☀️", "🌈", "☁️", "💧", "🌤️"], "Regenbogen"),
    (["🐶", "🏠", "🦴", "🚪", "🐕", "🌳"], "Hundehütte"),
    (["🍎", "📱", "💻", "⌚", "🎧", "📲"], "Apple"),
    (["🌙", "⭐", "🌌", "😴", "🛏️", "🌃"], "Nacht"),
    (["🔥", "🚒", "👨‍🚒", "🏠", "💦", "🚨"], "Feuerwehr"),
    (["🎬", "🍿", "🥤", "🪑", "🎟️", "📽️"], "Kino"),
    (["✈️", "🌴", "🏖️", "☀️", "🧳", "🌊"], "Urlaub"),
    (["⚽", "🥅", "👟", "🏟️", "🏆", "🧑‍⚽"], "Fußball"),
    (["🐟", "🌊", "🎣", "🐠", "🪝", "⛵"], "Fischen"),
    (["🍔", "🍟", "🥤", "🍗", "🌭", "🍕"], "Fast Food"),
    (["🚗", "🛣️", "⛽", "🚦", "🗺️", "🚙"], "Autofahrt"),
    (["📚", "✏️", "🏫", "🎒", "🧑‍🏫", "📖"], "Schule"),
    (["🎄", "🎁", "⭐", "❄️", "🔔", "🎅"], "Weihnachten"),
    (["🎃", "👻", "🕷️", "🍬", "🦇", "🕸️"], "Halloween"),
    (["❤️", "💌", "🌹", "🥰", "💘", "💐"], "Liebe"),
    (["🐱", "🐭", "🧀", "🏠", "🐾", "😺"], "Katze"),
    (["🚀", "🌕", "👨‍🚀", "🪐", "⭐", "🌌"], "Weltraum"),
    (["🏴‍☠️", "💰", "🚢", "🗺️", "⚓", "☠️"], "Piraten"),
    (["👑", "🏰", "⚔️", "🐉", "🛡️", "🤴"], "König"),
    (["🍿", "📺", "🛋️", "🎮", "🥤", "🏠"], "Gamingabend"),
    (["🏖️", "🌴", "🥥", "🌊", "🩴", "😎"], "Strandurlaub"),
    (["☕", "🥐", "🍞", "🌅", "📰", "🍳"], "Frühstück"),
    (["🎂", "🎈", "🎁", "🥳", "🕯️", "🎉"], "Geburtstag"),
    (["🚂", "🎫", "🧳", "🛤️", "🏙️", "🚉"], "Zugfahrt"),
    (["🏀", "🏟️", "⛹️", "🏆", "👟", "🔥"], "Basketball"),
    (["🎸", "🎤", "🥁", "🎹", "🎶", "🎵"], "Musik"),
    (["🍦", "☀️", "🏖️", "😋", "🍓", "🍫"], "Eis"),
    (["🐝", "🌼", "🌸", "🍯", "🌻", "🦋"], "Bienen"),
    (["🌲", "🏕️", "🔥", "🌙", "🥾", "🏞️"], "Camping"),
]

# Discord-Berechtigungen
intents = discord.Intents.default()
intents.message_content = True

# Bot erstellen
bot = discord.Client(intents=intents)

# Aktuelles Rätsel
current_quiz = None


def normalize(text):
    return text.lower().strip()


async def send_new_quiz():
    global current_quiz

    channel = bot.get_channel(CHANNEL_ID)

    if channel is None:
        print("Kanal wurde nicht gefunden.")
        return

    current_quiz = random.choice(QUIZZES)

    emojis = " ".join(current_quiz[0])

    await channel.send(
        "**Emoji-Quiz - was bedeutet diese Emoji-Kombination?**\n\n"
        "Bitte errate die Bedeutung folgender Emojis, "
        "indem du eine Nachricht in diesen Kanal sendest!\n\n"
        f"{emojis}"
    )


@bot.event
async def on_ready():
    print(f"Bot ist online als {bot.user}")

    if current_quiz is None:
        await send_new_quiz()


@bot.event
async def on_message(message):
    global current_quiz

    # Nachrichten vom Bot ignorieren
    if message.author == bot.user:
        return

    # Nur den gewünschten Kanal verwenden
    if message.channel.id != CHANNEL_ID:
        return

    # Falls noch kein Rätsel vorhanden ist
    if current_quiz is None:
        return

    answer = normalize(message.content)
    correct_answer = normalize(current_quiz[1])

    # Richtige Antwort
    if answer == correct_answer:
        await message.channel.send(
            f"✅ Richtig, {message.author.mention}!"
        )

        # Neues Rätsel senden
        await send_new_quiz()


# Token aus GitHub Secret holen
TOKEN = os.environ["DISCORD_TOKEN"]

# Bot starten
bot.run(TOKEN)
```
