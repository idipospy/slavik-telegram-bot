import telebot
import os
import time
import random
from telebot.types import Message
from flask import Flask
from threading import Thread
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# ========== НАСТРОЙКИ (без секретов) ==========
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Не найдены переменные окружения TELEGRAM_TOKEN или GEMINI_API_KEY")

# Настройка Gemini
genai.configure(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-2.0-flash"  # можно заменить на gemini-1.5-pro или gemini-1.5-flash
model = genai.GenerativeModel(MODEL_NAME)

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Вероятность отправки стикера (5%)
STICKER_CHANCE = 0.05

# ========== ЛИЧНОСТЬ ==========
PERSONALITY_FILE = "personality.txt"

def load_personality() -> str:
    if os.path.exists(PERSONALITY_FILE):
        with open(PERSONALITY_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                return content
    return "Ты — Славик. Отвечай агрессивно и с матом."

PERSONALITY = load_personality()
print(f"✅ Личность загружена из {PERSONALITY_FILE}")

# ========== ХРАНИЛИЩЕ ИСТОРИЙ ==========
user_histories = {}

# ========== СПИСОК СТИКЕРОВ (ВАШИ ID) ==========
STICKERS = [  # полный список оставляем как есть, он очень длинный, для краткости оставлю ссылку
    "CAACAgIAAxkBAAIsoGotFLzIjtQ4i9t2WEQebPAXC61_AALFmwACYNzRS9UuG2zTQo7XPAQ",
    # ... здесь все ваши 30+ стикеров (я не стал копировать их для краткости, но вы вставите свои)
    # Убедитесь, что список STICKERS полностью скопирован из вашего предыдущего кода.
]
# Если вы хотите, чтобы стикеры работали, вставьте сюда все 32 ID из вашего сообщения.

# ========== КОМАНДЫ ==========
@bot.message_handler(commands=['start'])
def cmd_start(message: Message):
    user_id = message.chat.id
    user_histories[user_id] = []
    bot.reply_to(message, "Че надо? Пиши давай, не тяни.")

@bot.message_handler(commands=['reset'])
def cmd_reset(message: Message):
    user_id = message.chat.id
    if user_id in user_histories:
        user_histories[user_id] = []
    bot.reply_to(message, "Историю очистил, мудила. Теперь начинай сначала.")

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
    # иначе игнорируем

def process_message(message: Message, user_text: str):
    # Редко отправляем стикер вместе с ответом
    if random.random() < STICKER_CHANCE and STICKERS:
        try:
            bot.send_sticker(message.chat.id, random.choice(STICKERS))
        except Exception as e:
            print(f"Ошибка отправки стикера: {e}")

    answer_user(message, user_text)

def answer_user(message: Message, user_text: str):
    user_id = message.chat.id
    bot.send_chat_action(user_id, "typing")

    if user_id not in user_histories:
        user_histories[user_id] = []

    # Склеиваем промпт с личностью и историей (костыль для Gemini)
    full_prompt = PERSONALITY + "\n\nИстория диалога:\n"
    for msg in user_histories[user_id]:
        if msg["role"] == "user":
            full_prompt += f"Пользователь: {msg['parts'][0]}\n"
        else:
            full_prompt += f"Бот: {msg['parts'][0]}\n"
    full_prompt += f"Пользователь: {user_text}\nБот:"

    try:
        response = model.generate_content(full_prompt)
        ai_response = response.text.strip()
        if not ai_response:
            ai_response = "Чё молчишь? Я не понял, дебил."

        # Сохраняем историю (ручное управление)
        user_histories[user_id].append({"role": "user", "parts": [user_text]})
        user_histories[user_id].append({"role": "model", "parts": [ai_response]})
        if len(user_histories[user_id]) > 10:
            user_histories[user_id] = user_histories[user_id][-10:]

        bot.reply_to(message, ai_response[:500])

    except Exception as e:
        print(f"❌ Ошибка Gemini: {e}")
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
    keep_alive()
    print("🤖 Бот с Gemini (gemini-2.0-flash) запущен!")
    print(f"🎲 Вероятность стикера: {STICKER_CHANCE*100}%")
    print("💬 В группах отвечает только на упоминания @slovik568_bot")
    print(f"📦 Загружено стикеров: {len(STICKERS)}")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен.")
