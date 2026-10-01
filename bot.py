python
import os
import random
import discord

CHANNEL_ID = 1533409789256925185

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

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)

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

    if message.author == bot.user:
        return

    if message.channel.id != CHANNEL_ID:
        return

    if current_quiz is None:
        return

    answer = normalize(message.content)
    correct_answer = normalize(current_quiz[1])

    if answer == correct_answer:
        await message.channel.send(
            f"✅ Richtig, {message.author.mention}!"
        )

        await send_new_quiz()


TOKEN = os.environ["DISCORD_TOKEN"]

bot.run(TOKEN)
