const {
    Client,
    GatewayIntentBits,
    Events
} = require("discord.js");

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent
    ]
});

// ===============================
// EINSTELLUNGEN
// ===============================

const TOKEN = process.env.DISCORD_TOKEN;

const CHANNEL_ID = "1533409789256925185";

// Wie lange gewartet werden soll, bevor das erste Quiz erscheint
const START_DELAY = 3000;

// Emoji-Fragen
// emoji = das, was angezeigt wird
// answers = mögliche richtige Schreibweisen
const quizzes = [
    {
        emoji: "🌧️☀️",
        answers: ["regenbogen", "regenbogen"]
    },
    {
        emoji: "🐝🍯",
        answers: ["honig", "bienenhonig"]
    },
    {
        emoji: "🌙⭐",
        answers: ["nacht", "sternennacht"]
    },
    {
        emoji: "🔥🚒",
        answers: ["feuerwehr", "feuerwehrmann"]
    },
    {
        emoji: "🍎📱",
        answers: ["iphone", "apple"]
    },
    {
        emoji: "🐟🌊",
        answers: ["fisch", "fisch im meer"]
    },
    {
        emoji: "☀️🌻",
        answers: ["sonne", "sonnenblume"]
    },
    {
        emoji: "❄️☃️",
        answers: ["winter", "schnee"]
    },
    {
        emoji: "🚗💨",
        answers: ["schnelles auto", "rasendes auto"]
    },
    {
        emoji: "🎂🎉",
        answers: ["geburtstag", "geburtstagsfeier"]
    },
    {
        emoji: "📚🏫",
        answers: ["schule", "schulunterricht"]
    },
    {
        emoji: "⚽🥅",
        answers: ["fußball", "fussball"]
    }
];

// ===============================
// STATUS
// ===============================

let currentQuiz = null;
let currentQuizIndex = -1;

// ===============================
// HILFSFUNKTIONEN
// ===============================

function normalize(text) {
    return text
        .toLowerCase()
        .trim()
        .replace(/[.!?,;:]/g, "");
}

function getRandomQuiz() {
    let index;

    // Verhindert, dass direkt dasselbe Quiz nochmal kommt
    do {
        index = Math.floor(Math.random() * quizzes.length);
    } while (index === currentQuizIndex && quizzes.length > 1);

    currentQuizIndex = index;
    return quizzes[index];
}

async function sendQuiz(channel) {
    currentQuiz = getRandomQuiz();

    await channel.send(
        `**Emoji-Quiz - was bedeutet diese Emoji-Kombination?**\n\n` +
        `Bitte errate die Bedeutung folgender Emojis, indem du eine Nachricht in diesen Kanal sendest!\n\n` +
        `${currentQuiz.emoji}`
    );
}

// ===============================
// BOT START
// ===============================

client.once(Events.ClientReady, async (bot) => {
    console.log(`Bot ist online als ${bot.user.tag}`);

    const channel = await bot.channels.fetch(CHANNEL_ID);

    if (!channel) {
        console.error("Kanal wurde nicht gefunden.");
        return;
    }

    if (!channel.isTextBased()) {
        console.error("Der angegebene Kanal ist kein Textkanal.");
        return;
    }

    setTimeout(() => {
        sendQuiz(channel);
    }, START_DELAY);
});

// ===============================
// NACHRICHTEN ÜBERPRÜFEN
// ===============================

client.on(Events.MessageCreate, async (message) => {

    // Eigene Nachrichten ignorieren
    if (message.author.bot) return;

    // Nur den angegebenen Kanal überwachen
    if (message.channel.id !== CHANNEL_ID) return;

    // Falls noch kein Quiz aktiv ist
    if (!currentQuiz) return;

    const answer = normalize(message.content);

    const isCorrect = currentQuiz.answers.some(
        correctAnswer => normalize(correctAnswer) === answer
    );

    if (!isCorrect) return;

    // Aktuelles Quiz abschließen
    const solvedQuiz = currentQuiz;
    currentQuiz = null;

    await message.channel.send(
        `🎉 **Richtig!** ${message.author} hat die Lösung gefunden!`
    );

    // Kurz warten und neues Quiz senden
    setTimeout(() => {
        sendQuiz(message.channel);
    }, 2000);
});

// ===============================
// LOGIN
// ===============================

const TOKEN = process.env.DISCORD_TOKEN;

client.login(TOKEN);
