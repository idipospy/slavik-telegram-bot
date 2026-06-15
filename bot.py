import telebot
import os
import random
from telebot.types import Message
from flask import Flask
from threading import Thread
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ========== НАСТРОЙКИ ==========
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("Не найдены TELEGRAM_TOKEN или GROQ_API_KEY")

# Модель: мощная 70B с отличной памятью
MODEL_NAME = "llama-3.3-70b-versatile"

client = Groq(api_key=GROQ_API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Вероятность отправки стикера дополнительно к тексту (15%)
STICKER_CHANCE = 0.15

# ========== ЛИЧНОСТЬ ==========
PERSONALITY_FILE = "personality.txt"

def load_personality() -> str:
    if os.path.exists(PERSONALITY_FILE):
        with open(PERSONALITY_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                return content
    return "Ты — Славик. ."

PERSONALITY = load_personality()
print(f"✅ Личность загружена из {PERSONALITY_FILE}")

# ========== ХРАНИЛИЩЕ ИСТОРИЙ ==========
user_histories = {}

# ========== ПОЛНЫЙ СПИСОК СТИКЕРОВ (31 шт) ==========
STICKERS = [
    "CAACAgIAAxkBAAIsoGotFLzIjtQ4i9t2WEQebPAXC61_AALFmwACYNzRS9UuG2zTQo7XPAQ",
    "CAACAgIAAxkBAAIsomotFMIm9LqoEVUtVAaVe8HsaAF-AAJYRQACXBlISLj-sZAiG5BxPAQ",
    "CAACAgIAAxUAAWotFVJeDGSKQK6-bB25X7UlOIClAALkiAACgsbRS5wOg98jieXfPAQ",
    "CAACAgIAAxUAAWotFVLKsTVh8WA5X3W6fGcbVcU4AAJlbQACsIJoSAFi7Z6nGPaJPAQ",
    "CAACAgIAAxUAAWotFVJwPdGaSbjpfZqItTHdpROaAALTiwAC4fS4S813QUtk_b4WPAQ",
    "CAACAgIAAxUAAWotFVIDpX1eVJMdTJ4WE15WruZ1AAIXcwACSGcBSQGmZ5xGtKMfPAQ",
    "CAACAgIAAxUAAWotFVKYvp-GW9SEnGLxTrai7p3LAAJ1SAACfi8YSB6tzDLQ03r7PAQ",
    "CAACAgIAAxUAAWotFVLaTFaNYKD85o0AAQbLVB9Z0gACcHMAApkeQEmJvhl8s1i0IjwE",
    "CAACAgIAAxUAAWotFVKelziTn7FrCPGmsinkzTRlAAK6hgACRm_RSo-NSwslQDgePAQ",
    "CAACAgIAAxUAAWotFVIqz7AmOIj7av9Fpi4pQ_klAAJNhQACWJYJS7Uuu9pMjJ_YPAQ",
    "CAACAgIAAxUAAWotFVJwScD0_vGegQABxolBBbEOhAAC6kQAAmo9GEjORn6qgYEIZTwE",
    "CAACAgIAAxUAAWotFVLnQjigN19YxQtef0ApAAHizQACclAAAsSmGUhlKow7bD_x2DwE",
    "CAACAgIAAxUAAWotFVIdX3SwyZ1q6ZlqdnnD6nglAAJRgAACC5ZBS2B_xx-QUkhjPAQ",
    "CAACAgIAAxUAAWotFVIYiydayte3_roTFhkwI5cnAALjhwACijJYS5x_5zPckadSPAQ",
    "CAACAgIAAxUAAWotFVKqU33BGiyr6RsIRCI-W4f5AAKQhwACChOwS6GUYXM_MJsgPAQ",
    "CAACAgIAAxUAAWotFVI6Iyv8oRuwI83tHuB73VaiAAKFSAACFioYSDoherJoG2J1PAQ",
    "CAACAgIAAxUAAWotFVKKJJ-QnAr3iRtOwPhEVKwMAAI0SQACEMAZSBuLm2-_1SK2PAQ",
    "CAACAgIAAxUAAWotFVIM-f2ZkD9gVhgF9eOokD5fAALphgACZR5JSNF70QteHtsOPAQ",
    "CAACAgIAAxUAAWotFVISAioK1RhJEVgMC-boAjdvAAJ6kwACy7PYSIVu7FyylZCVPAQ",
    "CAACAgIAAxUAAWotFVL2vQI2tnS1epwfavCUh3mTAAJplAAC4zvZSWNUnbla9dA3PAQ",
    "CAACAgIAAxUAAWotFVJnFvQ0cyFWTVBCNrfD3phuAAL1fwACKXvpSffIurdC9bhrPAQ",
    "CAACAgIAAxUAAWotFVKrVxCPDZtzYfhTwN8FEj27AAI4hQACHAm4Sm8KlPo3JvcpPAQ",
    "CAACAgIAAxUAAWotFVKsMFy7ej-7ewZ34w4x4w7tAALboAACncZoShgrsL0h_MpPPAQ",
    "CAACAgIAAxUAAWotFVJuAAFlQV6QJIbZ_4zIdfBsiwACKY8AAv8eEEutzGJbPoFk2TwE",
    "CAACAgIAAxUAAWotFVIujwokua0SzvK147nn4kcVAALaowAC7xBIS11Rx7OzNKFnPAQ",
    "CAACAgIAAxUAAWotFVIMkVadXYACWyMler8cHhUnAAJangACu-VJS13Spp8fGtpDPAQ",
    "CAACAgIAAxUAAWotFVLyYXdZZLLngDHMSctlPcOXAAJdogACYUqAS9ymhAVSwKNXPAQ",
    "CAACAgIAAxUAAWotFVKmHl2T4hhKNCVEyB04nFZeAAIKmwACvn_gS0A4SLjvGsw8PAQ",
    "CAACAgIAAxUAAWotFVJSNCgMUcev0yeYRYxDWisyAAK9owACih1xSBo7ETg_Pp3-PAQ",
    "CAACAgIAAxUAAWotFVK-blslX77LWErvr4NXyfI9AAJ0ngACsdp5SAfEXKXbWWYpPAQ",
    "CAACAgIAAxUAAWotFVKMA4HWO_gzb3u51yILInyPAAJBnwAC61nASO9JO701qVABPAQ"
]

# ========== КОМАНДЫ ==========
@bot.message_handler(commands=['start'])
def cmd_start(message: Message):
    user_id = message.chat.id
    if user_id in user_histories:
        del user_histories[user_id]
    bot.reply_to(message, "Че надо? Пиши давай, не тяни.")

@bot.message_handler(commands=['reset'])
def cmd_reset(message: Message):
    user_id = message.chat.id
    if user_id in user_histories:
        del user_histories[user_id]
    bot.reply_to(message, "Историю очистил. Теперь начинай сначала.")

@bot.message_handler(commands=['sticker'])
def send_random_sticker(message: Message):
    if not STICKERS:
        bot.reply_to(message, "Стикеры закончились.")
        return
    chosen = random.choice(STICKERS)
    try:
        bot.send_sticker(message.chat.id, chosen)
    except Exception as e:
        print(f"Ошибка отправки стикера: {e}")

# ========== ОСНОВНОЙ ОБРАБОТЧИК ==========
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message: Message):
    user_id = message.chat.id
    user_text = message.text or ""

    if user_text.startswith('/'):
        return

    if message.chat.type == "private":
        process_message(message, user_text)
        return

    bot_username = bot.get_me().username
    is_mentioned = f"@{bot_username}" in user_text if user_text else False
    is_reply_to_bot = (message.reply_to_message and
                       message.reply_to_message.from_user.id == bot.get_me().id)

    if is_mentioned or is_reply_to_bot:
        clean_text = user_text.replace(f"@{bot_username}", "").strip()
        if not clean_text:
            clean_text = "эй"
        process_message(message, clean_text)

def process_message(message: Message, user_text: str):
    # С вероятностью 15% отправляем стикер (дополнительно к тексту)
    if random.random() < STICKER_CHANCE and STICKERS:
        try:
            bot.send_sticker(message.chat.id, random.choice(STICKERS))
        except Exception as e:
            print(f"Ошибка отправки стикера: {e}")

    # Всегда отправляем текстовый ответ через Groq
    answer_user(message, user_text)

# ========== ОТВЕТ ЧЕРЕЗ GROQ С ПАМЯТЬЮ ==========
def answer_user(message: Message, user_text: str):
    user_id = message.chat.id
    bot.send_chat_action(user_id, "typing")

    if user_id not in user_histories:
        user_histories[user_id] = []

    # Добавляем новое сообщение пользователя
    user_histories[user_id].append({"role": "user", "content": user_text})

    # Формируем полный массив: system + вся история (последние 10 сообщений)
    messages = [{"role": "system", "content": PERSONALITY}]
    messages.extend(user_histories[user_id])

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.9,
            max_tokens=500
        )
        ai_response = response.choices[0].message.content.strip()
        if not ai_response:
            ai_response = "Чё молчишь? Я не понял, дебил."

        # Сохраняем ответ ассистента
        user_histories[user_id].append({"role": "assistant", "content": ai_response})

        # Ограничиваем историю последними 10 сообщениями
        if len(user_histories[user_id]) > 10:
            user_histories[user_id] = user_histories[user_id][-10:]

        bot.reply_to(message, ai_response[:500])
    except Exception as e:
        print(f"❌ Ошибка Groq: {e}")
        if user_id in user_histories:
            del user_histories[user_id]
        bot.reply_to(message, "Ошибка. /reset попробуй, чмо.")

# ==================== ВЕБ-СЕРВЕР ДЛЯ KEEP-ALIVE ====================
app = Flask('')

@app.route('/')
def home():
    return "🤖 Бот Славик жив и работает!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# ====================================================================

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    # ---- Сброс вебхука для предотвращения ошибки 409 ----
    try:
        bot.delete_webhook()
        print("✅ Вебхук успешно сброшен перед запуском.")
    except Exception as e:
        print(f"⚠️ Не удалось сбросить вебхук: {e}")
    # ----------------------------------------------------
    keep_alive()
    print("🤖 Бот с Groq запущен!")
    print(f"🎲 Вероятность стикера: {STICKER_CHANCE*100}%")
    print(f"🧠 Модель: {MODEL_NAME}")
    print("💬 В группах отвечает только на упоминания @slovik568_bot")
    print(f"📦 Загружено стикеров: {len(STICKERS)}")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен.")