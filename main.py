import asyncio
import logging
import random
import sqlite3
import os
import pandas as pd
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties

# ================= НАСТРОЙКИ =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения!")


EXCEL_FILE = "For_BD.xlsx"
ADMIN_ID = 369162989
# =============================================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect("tarot_cards.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY,
            file_key TEXT,
            card_name TEXT,
            meaning_1 TEXT,
            meaning_2 TEXT,
            meaning_3 TEXT,
            advice_1 TEXT,
            advice_2 TEXT,
            advice_3 TEXT,
            vibe_1 TEXT,
            vibe_2 TEXT,
            vibe_3 TEXT,
            photo_id TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_activity TEXT,
            total_cards INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

async def save_user(message: types.Message):
    conn = sqlite3.connect("tarot_cards.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, username, first_name, last_activity, total_cards)
        VALUES (?, ?, ?, ?, COALESCE((SELECT total_cards FROM users WHERE user_id = ?), 0))
    """, (
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.first_name or "",
        datetime.now().isoformat(),
        message.from_user.id
    ))
    conn.commit()
    conn.close()

async def increment_card_count(user_id: int):
    conn = sqlite3.connect("tarot_cards.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET total_cards = total_cards + 1, last_activity = ?
        WHERE user_id = ?
    """, (datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()

def create_db_from_excel():
    if not os.path.exists(EXCEL_FILE):
        logging.error(f"Файл {EXCEL_FILE} не найден!")
        return
    try:
        df = pd.read_excel(EXCEL_FILE)
        conn = sqlite3.connect("tarot_cards.db")
        cursor = conn.cursor()
        for _, row in df.iterrows():
            cursor.execute("""
                INSERT OR REPLACE INTO cards (
                    id, file_key, card_name,
                    meaning_1, meaning_2, meaning_3,
                    advice_1, advice_2, advice_3,
                    vibe_1, vibe_2, vibe_3,
                    photo_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row['ID'], row['File_key'], row['Card_name'],
                row['Meaning 1'], row['Meaning 2'], row['Meaning 3'],
                row['Advice 1'], row['Advice 2'], row['Advice 3'],
                row['Vibe 1'], row['Vibe 2'], row['Vibe 3'],
                row['photo_id']
            ))
        conn.commit()
        conn.close()
        logging.info("База данных создана из Excel")
    except Exception as e:
        logging.error(f"Ошибка при создании базы: {e}")

# ============ ВСЕ КОМАНДЫ ============

# --- /START ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await save_user(message)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎴 Получить карту", callback_data="card")],
            [InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")],
            [InlineKeyboardButton(text="📩 Поддержка", callback_data="support")],
            [InlineKeyboardButton(text="🔒 Политика", callback_data="privacy")]
        ]
    )
    await message.answer(
        "✨ <b>Tarot Magerie — Карта дня</b>\n\n"
        "Привет.\n\n"
        "Каждый день я выбираю для тебя одну карту Таро.\n"
        "Короткое толкование и совет, который не требует особых усилий.\n\n"
        "Попробуй — это просто способ остановиться на пару минут.",
        reply_markup=keyboard
    )

# --- /CARD ---
@dp.message(Command("card"))
async def card_command(message: types.Message):
    await send_card_to_user(message)

# --- /ABOUT ---
@dp.message(Command("about"))
async def about_command(message: types.Message):
    await message.answer(
        "ℹ️ <b>О боте</b>\n\n"
        "Tarot Magerie — это бот для тех, кто хочет получить совет дня.\n\n"
        "📖 <b>Как это работает:</b>\n"
        "Бот берёт случайную карту Таро и даёт её толкование, совет и настроение.\n\n"
        "🔮 <b>Зачем это?</b>\n"
        "Просто способ остановиться, задуматься и посмотреть на день под другим углом.\n\n"
        "✉️ Вопросы / идеи: /support\n"
        "🔒 Политика конфиденциальности: /privacy"
    )

# --- /SUPPORT ---
@dp.message(Command("support"))
async def support_command(message: types.Message):
    await message.answer(
        "📩 <b>Служба поддержки</b>\n\n"
        "Опишите вашу проблему, идею или предложение.\n"
        "Просто напишите сообщение в этот чат — я передам его разработчику.\n\n"
        "<i>Обычно ответ приходит в течение 24 часов.</i>"
    )

# --- /PRIVACY ---
@dp.message(Command("privacy"))
async def privacy_command(message: types.Message):
    await message.answer(
        "🔒 <b>Политика конфиденциальности</b>\n\n"
         "Полный текст политики конфиденциальности доступен по ссылке:\n"
        "https://telegra.ph/Politika-konfidencialnosti-bota-Tarot-Magerie-07-25\n\n"
        "1. <b>Какие данные собираются:</b>\n"
        "   • Ваш Telegram ID (уникальный номер)\n"
        "   • Ваше имя и никнейм (из профиля)\n"
        "   • Количество запрошенных карт\n"
        "   • Дата последнего обращения\n\n"
        "2. <b>Зачем это нужно:</b>\n"
        "   • Для подсчёта активных пользователей\n"
        "   • Для улучшения работы бота\n"
        "   • Для предотвращения спама\n\n"
        "3. <b>Кто имеет доступ:</b>\n"
        "   • Только разработчик бота\n"
        "   • Данные не передаются третьим лицам\n\n"
        "4. <b>Как удалить данные:</b>\n"
        "   • Напишите команду /delete_data\n"
        "   • Все ваши данные будут удалены навсегда\n\n"
        "5. <b>Срок хранения:</b>\n"
        "   • Данные хранятся, пока вы не удалите их сами\n"
        "   • Или пока бот активен\n\n"
        "📌 <i>Используя бота, вы соглашаетесь с этой политикой.</i>"
    )

# --- /DELETE_DATA ---
@dp.message(Command("delete_data"))
async def delete_data_command(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("tarot_cards.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE user_id = ?", (user_id,))
    count = cursor.fetchone()[0]
    
    if count == 0:
        await message.answer("❌ Ваши данные уже удалены или вас нет в базе.")
        conn.close()
        return
    
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    await message.answer("✅ Ваши данные успешно удалены. Если захотите снова пользоваться ботом — просто нажмите /start.")

# ============ КНОПКИ ============

# --- КНОПКА "О БОТЕ" ---
@dp.callback_query(lambda c: c.data == "about")
async def about_callback(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "ℹ️ <b>О боте</b>\n\n"
        "Tarot Magerie — это бот для тех, кто хочет получить совет дня.\n\n"
        "📖 <b>Как это работает:</b>\n"
        "Бот берёт случайную карту Таро и даёт её толкование, совет и настроение.\n\n"
        "🔮 <b>Зачем это?</b>\n"
        "Просто способ остановиться, задуматься и посмотреть на день под другим углом.\n\n"
        "✉️ Вопросы / идеи: /support\n"
        "🔒 Политика конфиденциальности: /privacy",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔒 Политика", callback_data="privacy")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
            ]
        )
    )

# --- КНОПКА "ПОДДЕРЖКА" ---
@dp.callback_query(lambda c: c.data == "support")
async def support_callback(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "📩 <b>Служба поддержки</b>\n\n"
        "Опишите вашу проблему, идею или предложение.\n"
        "Просто напишите сообщение в этот чат — я передам его разработчику.\n\n"
        "<i>Обычно ответ приходит в течение 24 часов.</i>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
            ]
        )
    )

# --- КНОПКА "ПОЛИТИКА" ---
@dp.callback_query(lambda c: c.data == "privacy")
async def privacy_callback(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "🔒 <b>Политика конфиденциальности</b>\n\n"
        "1. <b>Какие данные собираются:</b>\n"
        "   • Ваш Telegram ID (уникальный номер)\n"
        "   • Ваше имя и никнейм (из профиля)\n"
        "   • Количество запрошенных карт\n"
        "   • Дата последнего обращения\n\n"
        "2. <b>Зачем это нужно:</b>\n"
        "   • Для подсчёта активных пользователей\n"
        "   • Для улучшения работы бота\n"
        "   • Для предотвращения спама\n\n"
        "3. <b>Кто имеет доступ:</b>\n"
        "   • Только разработчик бота\n"
        "   • Данные не передаются третьим лицам\n\n"
        "4. <b>Как удалить данные:</b>\n"
        "   • Напишите команду /delete_data\n"
        "   • Все ваши данные будут удалены навсегда\n\n"
        "5. <b>Срок хранения:</b>\n"
        "   • Данные хранятся, пока вы не удалите их сами\n"
        "   • Или пока бот активен\n\n"
        "📌 <i>Используя бота, вы соглашаетесь с этой политикой.</i>"
    )

# --- КНОПКА "НАЗАД" ---
@dp.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await callback.answer()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎴 Получить карту", callback_data="card")],
            [InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")],
            [InlineKeyboardButton(text="📩 Поддержка", callback_data="support")],
            [InlineKeyboardButton(text="🔒 Политика", callback_data="privacy")]
        ]
    )
    await callback.message.answer(
        "✨ <b>Tarot Magerie — Карта дня</b>\n\n"
        "Привет.\n\n"
        "Каждый день я выбираю для тебя одну карту Таро.\n"
        "Короткое толкование и совет, который не требует особых усилий.\n\n"
        "Попробуй — это просто способ остановиться на пару минут.",
        reply_markup=keyboard
    )

# --- ОБРАБОТЧИК ТЕКСТА (для поддержки) ---
@dp.message(F.text)
async def handle_support(message: types.Message):
    if not message.text.startswith('/') and not message.text.startswith('📩'):
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"💬 <b>Новое обращение</b>\n\n"
                 f"👤 @{message.from_user.username or 'без юзернейма'} (ID: {message.from_user.id})\n"
                 f"📝 Сообщение: {message.text}"
        )
        await message.answer("✅ Ваше сообщение отправлено разработчику. Спасибо!")

# ============ ФУНКЦИЯ ДЛЯ /CARD ============
async def send_card_to_user(message: types.Message):
    await save_user(message)
    await increment_card_count(message.from_user.id)
    
    conn = sqlite3.connect("tarot_cards.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT card_name, meaning_1, meaning_2, meaning_3,
               advice_1, advice_2, advice_3,
               vibe_1, vibe_2, vibe_3, photo_id
        FROM cards
        WHERE photo_id IS NOT NULL AND photo_id != ''
        ORDER BY RANDOM() LIMIT 1
    """)
    card = cursor.fetchone()
    conn.close()
    
    if not card:
        await message.answer("❌ Карта не найдена. Попробуй позже.")
        return
    
    (name, m1, m2, m3, a1, a2, a3, v1, v2, v3, photo_id) = card
    
    meaning = random.choice([m1, m2, m3])
    advice = random.choice([a1, a2, a3])
    vibe = random.choice([v1, v2, v3])
    
    caption = (
        f"🌟 <b>{name}</b>\n\n"
        f"📖 <b>Толкование:</b> {meaning}\n\n"
        f"✨ <b>Совет:</b> {advice}\n\n"
        f"🎯 <b>Вайб:</b> {vibe}\n\n"
        f"———\n"
        f"<i>Нажми на кнопку, чтобы получить другую карту</i>"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Другую карту", callback_data="card")],
            [InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")],
            [InlineKeyboardButton(text="📩 Поддержка", callback_data="support")],
            [InlineKeyboardButton(text="🔒 Политика", callback_data="privacy")]
        ]
    )
    
    await message.answer_photo(
        photo=photo_id,
        caption=caption,
        reply_markup=keyboard
    )

# --- ПОЛУЧЕНИЕ КАРТЫ ПО КНОПКЕ ---
@dp.callback_query(lambda c: c.data == "card")
async def send_card_callback(callback: types.CallbackQuery):
    await callback.answer()
    await send_card_to_user(callback.message)

# ============ ЗАПУСК ============
async def main():
    init_db()
    create_db_from_excel()
    logging.info("🚀 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
