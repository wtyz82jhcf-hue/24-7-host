import os
import random
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
    (["🐢", "🐢"], "Schildkröte"),
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
    (["🍓", "🍰"], "Erdbeerkuchen"),
    (["🍉", "☀️"], "Wassermelone"),
    (["🍌", "🥛"], "Bananenmilch"),
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


def normalize(text):
    return text.lower().strip()


async def send_new_quiz():
    global current_quiz, quiz_message

    channel = bot.get_channel(CHANNEL_ID)

    if channel is None:
        print("Kanal wurde nicht gefunden.")
        return

    current_quiz = random.choice(QUIZZES)

    emojis = " ".join(current_quiz[0])

    quiz_message = await channel.send(
        "**Emoji-Quiz - was bedeutet diese Emoji-Kombination?**\n\n"
        "Bitte errate die Bedeutung der Emojis!\n\n"
        f"{emojis}"
    )


@bot.event
async def on_ready():
    print(f"Bot ist online als {bot.user}")

    if current_quiz is None:
        await send_new_quiz()


@bot.event
async def on_message(message):
    global current_quiz, quiz_message

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

        if quiz_message is not None:
            try:
                await quiz_message.delete()
            except discord.NotFound:
                pass
            except discord.Forbidden:
                print("Keine Berechtigung zum Löschen.")

        current_quiz = None
        quiz_message = None

        await send_new_quiz()

    else:
        await message.channel.send(
            "❌ Leider falsch! Nächster Versuch, vielleicht wird's dann!"
        )


TOKEN = os.environ["DISCORD_TOKEN"]

bot.run(TOKEN)
