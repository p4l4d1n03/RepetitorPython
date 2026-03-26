import asyncio
import datetime
import logging
import sys
from os import getenv
import os
from dotenv import load_dotenv

import uuid
from yookassa import Configuration, Payment

# ЮKassa ОТКЛЮЧЕНА (нет ключей)
print("⚠️ ЮKassa отключена")

import aiosqlite
from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from bot_token import BOT_TOKEN  # твой файл с токеном

# Глобальный dp!
dp = Dispatcher(storage=MemoryStorage())

load_dotenv()

try:
    from gigachat import GigaChat
    from gigachat.models import Chat, Messages, MessagesRole

    gc = GigaChat(
        credentials=getenv("GIGACHAT_TOKEN"),  # имя переменной, а не сам токен!
        scope="GIGACHAT_API_PERS",
        verify_ssl_certs=False
    )
    GIGACHAT_AVAILABLE = True
    print("✅ GigaChat подключён")
except Exception as e:
    GIGACHAT_AVAILABLE = False
    print(f"❌ GigaChat ошибка: {e}")


SYSTEM_PROMPT = """
Ты ИИ-репетитор Python. Ответ структурой:
1. **Объяснение**
2. **Код-пример**
3. **Задание** (3 вопроса)
4. **Следующий шаг**
Для новичков, коротко.
"""

class LessonState(StatesGroup):
    waiting_topic = State()

async def add_to_database(telegram_id, username):
    async with aiosqlite.connect('telegram.db') as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (telegram_id BIGINT, username TEXT, date TEXT)")
        cursor = await db.execute('SELECT * from users where telegram_id = ?', (telegram_id,))
        data = await cursor.fetchone()
        if data is None:
            date = str(datetime.date.today())
            await db.execute("INSERT INTO users (telegram_id, username, date) VALUES (?, ?, ?)", (telegram_id, username, date))
            await db.commit()

async def init_repetitor_db():
    async with aiosqlite.connect('telegram.db') as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS repetitor_users (
                telegram_id BIGINT PRIMARY KEY, daily_requests INTEGER DEFAULT 5,
                premium_until TEXT DEFAULT NULL, lessons_done INTEGER DEFAULT 0
            )
        """)
        await db.commit()

async def get_repetitor_user(telegram_id):
    async with aiosqlite.connect('telegram.db') as db:
        cursor = await db.execute('SELECT * FROM repetitor_users WHERE telegram_id = ?', (telegram_id,))
        data = await cursor.fetchone()
        if data is None:
            await db.execute("INSERT INTO repetitor_users (telegram_id) VALUES (?)", (telegram_id,))
            await db.commit()
            return (telegram_id, 5, None, 0)
        return data

async def update_requests(telegram_id):
    async with aiosqlite.connect('telegram.db') as db:
        await db.execute("UPDATE repetitor_users SET daily_requests = daily_requests - 1 WHERE telegram_id = ?", (telegram_id,))
        await db.commit()

async def is_premium(telegram_id):
    user = await get_repetitor_user(telegram_id)
    if user[2]:  # premium_until
        return datetime.datetime.now() < datetime.datetime.fromisoformat(user[2])
    return False

async def gigachat_lesson(topic):
    if not GIGACHAT_AVAILABLE:
        return "🧑‍💻 <b>GigaChat недоступен.</b>\nПример: x = 5\nЗадание: y = 10"
    chat_compl = Chat(messages=[
        Messages(role=MessagesRole.SYSTEM, content=SYSTEM_PROMPT),
        Messages(role=MessagesRole.USER, content=topic)
    ])
    response = gc.chat(chat_compl)
    return response.choices[0].message.content

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Привет, {html.bold(message.from_user.full_name)}! /repetitor — Python-репетитор")
    telegram_id = message.from_user.id
    username = message.from_user.username or "no_username"
    await add_to_database(telegram_id, username)

@dp.message(Command("repetitor"))
async def repetitor_start(message: Message, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Урок Python", callback_data="python_lesson")],
        [InlineKeyboardButton(text="⭐ Премиум", callback_data="premium")]
    ])
    await message.answer("🎓 Python-репетитор!\nБесплатно: 5 уроков/день.", reply_markup=kb)

@dp.callback_query(F.data == "python_lesson")
async def lesson_callback(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    user = await get_repetitor_user(telegram_id)
    if user[1] <= 0 and not await is_premium(telegram_id):
        await callback.message.answer("❌ Лимит исчерпан. Купи премиум!")
        await callback.answer()
        return
    await callback.message.answer("💡 Тема урока? (пример: 'функции')")
    await state.set_state(LessonState.waiting_topic)
    await callback.answer()

@dp.message(LessonState.waiting_topic)
async def process_lesson(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    lesson = await gigachat_lesson(message.text)
    await message.answer(lesson)
    await update_requests(telegram_id)
    await state.clear()
    await message.answer("Готов к новому? /repetitor")

@dp.callback_query(F.data == "close")
async def close_handler(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()

@dp.callback_query(F.data == "premium")
async def premium_handler(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить 299₽ (скоро)", callback_data="premium_coming")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")]
    ])
    await callback.message.answer(
        "⭐ **ПРЕМИУМ 299₽/МЕСЯЦ** (ЮKassa подключается):\n\n"
        "• Неограниченные уроки\n"
        "• Статистика прогресса\n"
        "• Приоритет GigaChat\n\n"
        "⏳ Скоро заработает!",
        reply_markup=kb, parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "premium_coming")
async def premium_coming(callback: CallbackQuery):
    await callback.answer("Скоро! 💰", show_alert=True)

@dp.message()
async def echo_handler(message: Message) -> None:
    await message.answer("Используй /repetitor для уроков Python!")

async def main() -> None:
    await init_repetitor_db()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())

@dp.callback_query(F.data == "quiz")
async def quiz_start(callback: CallbackQuery):
    questions = [
        "Что выводит print('Hi')?",
        "x = 5; print(x)?",
        "len('Python')?"
    ]
    await callback.message.answer("🧠 **КВИЗ Python** (3 вопроса)\n\n1. " + questions[0])

@dp.message(Command("progress"))
async def progress(message: Message):
    user = await get_repetitor_user(message.from_user.id)
    await message.answer(f"📊 **Твой прогресс**:\nУроки: {user[3]}\nОсталось бесплатно: {user[1]}\nПремиум до: {user[2] or 'Нет'}")

@dp.callback_query(F.data == "quiz")
async def quiz_start(callback: CallbackQuery):
    await callback.answer("Квиз скоро! 🎯", show_alert=True)
