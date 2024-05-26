import telebot
from dotenv import load_dotenv
import os
from icecream import ic


load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(func=lambda message: True)
def handle_start(message):
    bot.send_message(message.chat.id, "مرحباً بك في القناة! هل ترغب في القيام بـ\n1- عملية شراء\n2- إستفسار")
    bot.register_next_step_handler(message, handle_choice)

@bot.message_handler(func=lambda message: True)
def handle_choice(message):
    if message.text == "1":
        bot.send_message(message.chat.id, "يرجى كتابة أكواد المنتجات التي ترغب في شرائها:")
        bot.register_next_step_handler(message, handle_purchase)
    elif message.text == "2":
        bot.send_message(message.chat.id, "يرجى كتابة استفسارك:")
        bot.register_next_step_handler(message, handle_inquiry)
    else:
        bot.send_message(message.chat.id, "خيار غير صحيح. يرجى اختيار 1 أو 2.")
        handle_start(message)  # Restart the conversation

@bot.message_handler(func=lambda message: True)
def handle_purchase(message):
    items = message.text.split()
    ic(f"Received purchase request: {items}")
    # Process the purchase request here


@bot.message_handler(func=lambda message: True)
def handle_inquiry(message):
    inquiry = message.text
    ic(f"Received inquiry: {inquiry}")
    # Process the inquiry here

# Set up the start command handler for the bot
bot.message_handler(commands=["start"])(handle_start)

if __name__ == "__main__":
    try:
        ic("Telebot bot started...")
        bot.polling(none_stop=True)
    except Exception as e:
        ic(f"Telebot bot stopped with error: {e}")
