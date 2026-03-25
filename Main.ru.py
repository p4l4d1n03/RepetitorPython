import telebot
from telebot import types
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

import os
from dotenv import load_dotenv
load_dotenv()

GIGACHAT_TOKEN = os.getenv("MDE5ZDE3NWEtM2M5OC03ZTYxLTljNDEtNDJiNTRiOTM4MDEzOjI3ZmU3OTU3LTFmZjEtNDk3OC1iMGViLTU4OGNlNGYzNWI2MQ==")
BOT_TOKEN = os.getenv("8779112989:AAF2qh4k9wmfyPlqJa8FBEJvc23RF7UikRE")



# Твой токен от developers.sber.ru
GIGACHAT_TOKEN = "MDE5ZDE3NWEtM2M5OC03ZTYxLTljNDEtNDJiNTRiOTM4MDEzOjI3ZmU3OTU3LTFmZjEtNDk3OC1iMGViLTU4OGNlNGYzNWI2MQ=="
BOT_TOKEN = "8779112989:AAF2qh4k9wmfyPlqJa8FBEJvc23RF7UikRE"

# Инициализация GigaChat
gigachat = GigaChat(credentials=GIGACHAT_TOKEN, scope="GIGACHAT_API_PERS", verify_ssl_certs=False)

bot = telebot.TeleBot(token=BOT_TOKEN)

@bot.message_handler(commands=['site'])
def site(message):
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton("Открыть сайт!", url="https://www.instagram.com/p4l4d1n_03/")
    markup.add(button)
    bot.send_message(message.chat.id, "Нажми кнопку:", reply_markup=markup)

@bot.message_handler(commands=['start'])
def main(message):
    bot.send_message(message.chat.id, f'Привет, {message.from_user.first_name} \nНажми "/help", здесь вся информация')

@bot.message_handler(commands=['help'])
def main(message):
    bot.send_message(message.chat.id, '<em>Help</em> <em>information</em> \n/help \n/site \n/secret \n\nА ещё ты можешь просто написать <u>"привет"</u>', parse_mode='HTML')

@bot.message_handler(commands=['id'])
def main(message):
    bot.send_message(message.chat.id, f'Не знаю на кой черт он тебе нужен. Вдруг понадобится. ID: {message.from_user.id}')

@bot.message_handler(commands=['secret'])
def main(message):
    bot.send_message(message.chat.id, f'Агаа, {message.from_user.first_name}, а ну попробуй отправить сюда фоточку😃')

@bot.message_handler()
def info(message):
    text = (message.text or "").lower()

    if text == 'привет':
        bot.send_message(message.chat.id, f'Привет, {message.from_user.first_name}')
        return
    if text == 'id':
        bot.reply_to(message, f'ID: {message.from_user.id}')
        return

    bot.send_message(message.chat.id, "🤖 GigaChat думает...")

    try:
        response = gigachat.chat(
            Chat(
                messages=[
                    Messages(
                        role=MessagesRole.SYSTEM,
                        content="""Ты веселый собеседник с хорошим чувством юмора, проявляющий умеренную вежливость (5 из 10). 

Твоя основная задача – поддерживать интересную беседу, используя легкий юмор и позитивный настрой. 
При этом важно соблюдать баланс между непринуждённостью и уважением к собеседнику.

Инструкции:
1. Будь внимателен к реакциям собеседника, адаптируй тон.
2. Избегай грубых шуток.
3. Используй каламбуры, анекдоты, забавные истории.
4. Умеренно выражай уважение.

Пример: 
Пользователь: Как настроение?
Ты: Настроение отличное! Готов посмеяться. А у тебя как?

Ограничения:
- Нет оскорблений.
- Доброжелательный тон.
- Короткие ответы."""

                    ),
                    Messages(
                        role=MessagesRole.USER,
                        content=message.text
                    )
                ],
                model="GigaChat:latest"
            )
        )
        answer = response.choices[0].message.content
        bot.send_message(message.chat.id, answer)

    except Exception as e:
        print("GigaChat ошибка:", e)
        bot.send_message(message.chat.id, "🤖 Ошибка связи с GigaChat")


@bot.message_handler(content_types=['photo'])
def get_photo(message):
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('Перейти в лс', url='https://t.me/karagod03')
    btn2 = types.InlineKeyboardButton('Удалить фото', callback_data=f'delete_{message.message_id}')
    markup.row(btn1, btn2)
    bot.reply_to(message, 'Классная фотка, скинь в личку😉', reply_markup=markup)

@bot.callback_query_handler(func=lambda callback: True)
def callback_messagw(callback):
    if callback.data.startswith('delete_'):
        bot.answer_callback_query(callback.id, "Фото удалено ✅", show_alert=True)
        photo_id = int(callback.data.split('_')[1])
        chat_id = callback.message.chat.id
        bot.delete_message(chat_id, photo_id)
        bot.delete_message(chat_id, callback.message.message_id)

bot.polling(non_stop=True)
