import asyncio
import logging
import os
import threading
import telebot
from telethon import TelegramClient, events
from PIL import Image  
from telethon.errors.rpcerrorlist import FloodWaitError, AuthKeyDuplicatedError
from time import sleep
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")
MONITORED_CHANNEL = os.getenv("MONITORED_CHANNEL") 
YOUR_CHANNEL = os.getenv("YOUR_CHANNEL")

# Logging for debugging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logging.info("Monitoring channel: " + MONITORED_CHANNEL)
logging.info("Forwarding messages to: " + YOUR_CHANNEL)

# Store last processed message ID (initialize to 0 if not found)
LAST_PROCESSED_ID_FILE = "last_processed_id.txt"
try:
    with open(LAST_PROCESSED_ID_FILE, "r") as f:
        last_processed_id = int(f.read().strip())
except FileNotFoundError:
    last_processed_id = 0

# Initialize the Telethon client
client = TelegramClient("your_session_name", API_ID, API_HASH)

# Initialize the Telebot bot
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
    logging.info(f"Received purchase request: {items}")
    # Process the purchase request here

@bot.message_handler(func=lambda message: True)
def handle_inquiry(message):
    inquiry = message.text
    logging.info(f"Received inquiry: {inquiry}")
    # Process the inquiry here

# Set up the start command handler for the bot
bot.message_handler(commands=["start"])(handle_start)

async def run_telethon_client():
    logging.info("Connecting to Telegram Listener...")

    try:
        await client.start(PHONE_NUMBER)
        logging.info("Connected successfully.")
    except Exception as e:  # Catch any exceptions during the connection
        logging.error(f"Error connecting to Telegram: {e}")
        return  # Exit the script if the connection fails

    @client.on(events.NewMessage(chats=MONITORED_CHANNEL))
    async def new_message_handler(event):
        global last_processed_id

        logging.info(f"New message received: ID {event.id}")
        
        me = await client.get_me()
        if event.sender_id == me.id:  # Now access me.id
            logging.info(f"Skipping message {event.id} (sent by this bot)")
            return

        if event.id <= last_processed_id:
            logging.info(f"Skipping message {event.id} (already processed)")
            return

        if event.media:
            logging.info("Message contains media")

            try:
                downloaded_file = await client.download_media(event.media)

                if downloaded_file.endswith((".jpg", ".jpeg", ".png")):
                    logging.info(f"Processing image: {downloaded_file}")
                    img = Image.open(downloaded_file)

                    full_file_path = os.path.abspath(downloaded_file)
                    logging.info(f"Sending image: {full_file_path}")

                    await client.send_file(YOUR_CHANNEL, full_file_path, caption=event.text)

                    # Delete the downloaded file after sending (inside the try-except block)
                    try:
                        os.remove(full_file_path)
                        logging.info(f"Deleted file: {full_file_path}")
                    except Exception as e:
                        logging.error(f"Error deleting file: {e}")

                    # ... (Update last processed message ID)
                else:
                    logging.warning(
                        f"Unsupported media type in message {event.id}: {downloaded_file}"
                    )
            except Exception as e:
                logging.error(f"Error processing message {event.id}: {e}")
        else:
            logging.info(f"Message {event.id} does not contain media")

    try:
        # Run the Telethon client
        await client.run_until_disconnected()
    except FloodWaitError as e:
        logging.warning(f"Flood wait for {e.seconds} seconds")
        sleep(e.seconds)
    except AuthKeyDuplicatedError:  # Catch the specific error
        logging.error("Session file is being used elsewhere. Deleting and restarting...")
        await client.disconnect()
        os.remove("your_session_name.session") # Delete the session file
        await client.start(PHONE_NUMBER)  # Reconnect
    except Exception as e:
        logging.error(f"Error: {e}")
        await client.disconnect()
        await client.start(PHONE_NUMBER)
        
# Function to run the Telebot bot
def run_telebot_bot():
    try:
        bot.polling(none_stop=True)
        logging.info("Telebot bot started successfully.")
    except Exception as e:
        logging.error(f"Error in Telebot bot: {e}")
        
        
async def main():
    # Create tasks to run both clients concurrently
    telethon_task = asyncio.create_task(run_telethon_client())

    # Run the Telebot bot in a separate thread
    telebot_thread = threading.Thread(target=run_telebot_bot)
    telebot_thread.start()

    # Wait for the Telethon task to complete (which will run indefinitely)
    await telethon_task

if __name__ == "__main__":
    asyncio.run(main())