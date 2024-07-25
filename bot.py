import asyncio
import logging
import os
import threading
import telebot
from telethon import TelegramClient, events
from telethon.errors.rpcerrorlist import FloodWaitError, AuthKeyDuplicatedError
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")
MONITORED_CHANNEL = int(os.getenv("MONITORED_CHANNEL"))
YOUR_CHANNEL = os.getenv("YOUR_CHANNEL")
LAST_PROCESSED_ID_FILE = "last_processed_id.txt"

# Logging for debugging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logging.info("Monitoring channel: " + str(MONITORED_CHANNEL))
logging.info("Forwarding messages to: " + YOUR_CHANNEL)

# Store last processed message ID (initialize to 0 if not found)
try:
    with open(LAST_PROCESSED_ID_FILE, "r") as f:
        last_processed_id = int(f.read().strip())
except FileNotFoundError:
    last_processed_id = 0

# Initialize the Telethon client
client = TelegramClient("your_session_name", API_ID, API_HASH)

# Initialize the Telebot bot
bot = telebot.TeleBot(BOT_TOKEN)

# Disable the webhook
bot.delete_webhook()

# -------------------------  BOT --------------------------------------------------
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


#-------------------------------- Monitor -------------------------------------------
async def run_telethon_client():
    global last_processed_id
    logging.info("Connecting to Telegram Listener...")

    try:
        await client.start(PHONE_NUMBER)
        logging.info("Connected successfully.")

        # Check if the monitored channel exists and is accessible
        try:
            channel_entity = await client.get_entity(MONITORED_CHANNEL)
            logging.info(f"Successfully accessed channel: {channel_entity.title}")
        except ValueError as e:
            logging.error(
                f"Error: The channel {MONITORED_CHANNEL} does not exist or is inaccessible."
            )
            logging.error(
                f"Please check your MONITORED_CHANNEL setting and ensure it's correct."
            )
            logging.error(f"Full error: {str(e)}")
            return  # Exit the function if the channel is not accessible
        except Exception as e:
            logging.error(
                f"An unexpected error occurred while trying to access the channel: {str(e)}"
            )
            return  # Exit the function on unexpected errors

    except Exception as e:
        logging.error(f"Error connecting to Telegram: {e}")
        return

    @client.on(events.NewMessage(chats=MONITORED_CHANNEL))
    async def new_message_handler(event):
        global last_processed_id

        logging.info(f"New message received: ID {event.id}")
        logging.info(
            f"Message content: {event.text[:100]}..."
        )  # Log first 100 chars of message

        me = await client.get_me()
        logging.info(f"Bot ID: {me.id}, Sender ID: {event.sender_id}")
        if event.sender_id == me.id:
            logging.info(f"Skipping message {event.id} (sent by this bot)")
            return

        if event.id <= last_processed_id:
            logging.info(f"Skipping message {event.id} (already processed)")
            return

        logging.info(f"Processing message {event.id}")

        if event.media:
            logging.info(
                f"Message {event.id} contains media of type: {type(event.media)}"
            )

            try:
                logging.info(f"Attempting to download media from message {event.id}")
                downloaded_file = await client.download_media(event.media)
                logging.info(f"Media downloaded to: {downloaded_file}")

                if downloaded_file and downloaded_file.endswith(
                    (".jpg", ".jpeg", ".png")
                ):
                    logging.info(f"Processing image: {downloaded_file}")
                    full_file_path = os.path.abspath(downloaded_file)
                    logging.info(f"Absolute file path: {full_file_path}")

                    logging.info(f"Attempting to send file to channel: {YOUR_CHANNEL}")
                    await client.send_file(
                        YOUR_CHANNEL, full_file_path, caption=event.text
                    )
                    logging.info(f"File sent successfully to {YOUR_CHANNEL}")

                    try:
                        os.remove(full_file_path)
                        logging.info(f"Deleted file: {full_file_path}")
                    except Exception as e:
                        logging.error(f"Error deleting file: {e}")

                    # Update last processed message ID
                    last_processed_id = event.id
                    with open(LAST_PROCESSED_ID_FILE, "w") as f:
                        f.write(str(last_processed_id))
                    logging.info(f"Updated last_processed_id to {last_processed_id}")
                else:
                    logging.warning(
                        f"Unsupported media type or download failed for message {event.id}"
                    )
            except Exception as e:
                logging.error(f"Error processing message {event.id}: {e}")
        else:
            logging.info(f"Message {event.id} does not contain media")

    try:
        logging.info(
            f"Starting to listen for new messages in channel: {MONITORED_CHANNEL}"
        )
        await client.run_until_disconnected()
    except FloodWaitError as e:
        logging.warning(f"Flood wait for {e.seconds} seconds")
        await asyncio.sleep(e.seconds)
    except AuthKeyDuplicatedError:
        logging.error(
            "Session file is being used elsewhere. Deleting and restarting..."
        )
        await client.disconnect()
        os.remove("your_session_name.session")
        await client.start(PHONE_NUMBER)
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
    # Run the Telebot bot in a separate thread
    telebot_thread = threading.Thread(target=run_telebot_bot)
    telebot_thread.start()

    # Create tasks to run both clients concurrently
    # telethon_task = asyncio.create_task(run_telethon_client())
    await run_telethon_client()


    # Wait for the Telethon task to complete (which will run indefinitely)
    # await telethon_task

if __name__ == "__main__":
    asyncio.run(main())