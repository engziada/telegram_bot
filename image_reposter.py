import logging
import os
from telethon import TelegramClient, events
from PIL import Image
from telethon.errors.rpcerrorlist import FloodWaitError, AuthKeyDuplicatedError
from time import sleep
from dotenv import load_dotenv

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")
MONITORED_CHANNEL = os.getenv("MONITORED_CHANNEL") 
YOUR_CHANNEL = os.getenv("YOUR_CHANNEL")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logging.info("Monitoring channel: " + MONITORED_CHANNEL)
logging.info("Forwarding messages to: " + YOUR_CHANNEL)

# Store last processed message ID (initialize to 0 if not found)
LAST_PROCESSED_ID_FILE = "last_processed_id.txt"
try:
    with open(LAST_PROCESSED_ID_FILE, "r") as f:
        last_processed_id = int(f.read().strip())
except FileNotFoundError:
    last_processed_id = 0

client = TelegramClient("your_session_name", API_ID, API_HASH)

async def main():
    logging.info("Connecting to Telegram...")
    try:
        await client.start(PHONE_NUMBER)
        logging.info("Connected successfully.")

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
                    else:
                        logging.warning(f"Unsupported media type in message {event.id}: {downloaded_file}")
                except Exception as e:
                    logging.error(f"Error processing message {event.id}: {e}")
            else:
                logging.info(f"Message {event.id} does not contain media")

        await client.run_until_disconnected()
        
    except FloodWaitError as e:
        logging.warning(f'Flood wait for {e.seconds} seconds')
        sleep(e.seconds)
    except AuthKeyDuplicatedError as e:  # Catch the specific error
        logging.error("Session file is being used elsewhere. Deleting and restarting...")
        await client.disconnect()
        os.remove("your_session_name.session") # Delete the session file
        await client.start(PHONE_NUMBER)  # Reconnect
    except Exception as e:  # Catching general exceptions
        logging.error(f"Error: {e}")
        await client.disconnect()  # Disconnect if there's an error
        await client.start(PHONE_NUMBER)  # Attempt to reconnect 
        
with client:
    client.loop.run_until_complete(main())
