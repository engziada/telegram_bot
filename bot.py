from io import BytesIO
import logging
import os
from telethon import TelegramClient, events
from PIL import Image
from telethon.errors.rpcerrorlist import FloodWaitError
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

# Store last processed message ID (initialize to 0 if not found)
LAST_PROCESSED_ID_FILE = "last_processed_id.txt"
try:
    with open(LAST_PROCESSED_ID_FILE, "r") as f:
        last_processed_id = int(f.read().strip())
except FileNotFoundError:
    last_processed_id = 0

# Initialize the client
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
            # Check if the message is from your bot (avoid infinite loop)
            if event.sender_id == me.id:
                logging.info(f"Skipping message {event.id} (sent by this bot)")
                return

            if event.id <= last_processed_id:
                logging.info(f"Skipping message {event.id} (already processed)")
                return

            if event.media:
                logging.info("Message contains media")

                try:
                    
                    # # Download media into memory as bytes
                    # image_bytes = await client.download_media(event.media, file=bytes)
                    # if image_bytes is not None:  # Check if bytes were downloaded
                    #     # Open the image from bytes
                    #     img = Image.open(BytesIO(image_bytes))
                        
                    #     # Create a BytesIO object to store the processed image
                    #     output = BytesIO()
                        
                    #     # Optionally process the image here (e.g., resize, watermark)
                        
                    #     # Save the processed image to the BytesIO object
                    #     img.save(output, format="JPEG")
                        
                    #     # Reset the stream position to the beginning
                    #     output.seek(0)
                        
                    #     await client.send_file(YOUR_CHANNEL, output, caption=event.text)
                    #     logging.info(f"Sent image from message {event.id}")

                    #     # Update last processed message ID
                    #     last_processed_id = event.id
                    #     with open(LAST_PROCESSED_ID_FILE, "w") as f:
                    #         f.write(str(last_processed_id))
                    
                    
                    # Download media on disk
                    downloaded_file = await client.download_media(event.media)
                    if downloaded_file.endswith((".jpg", ".jpeg", ".png")):
                        logging.info(f"Processing image: {downloaded_file}")
                        img = Image.open(downloaded_file)  # Use downloaded_file here

                        full_file_path = os.path.abspath(downloaded_file)
                        logging.info(f"Sending image: {full_file_path}")

                        await client.send_file(YOUR_CHANNEL, full_file_path, caption=event.text)

                        # Delete the downloaded file after sending
                        try:
                            os.remove(full_file_path)
                            logging.info(f"Deleted file: {full_file_path}")
                        except Exception as e:
                            logging.error(f"Error deleting file: {e}")

                        # Update last processed message ID
                        last_processed_id = event.id
                        with open(LAST_PROCESSED_ID_FILE, "w") as f:
                            f.write(str(last_processed_id))
                            
                    else:
                        logging.warning(f"Unsupported media type in message {event.id}: {downloaded_file}")
                except Exception as e:
                    logging.error(f"Error processing message {event.id}: {e}")
            else:
                logging.info(f"Message {event.id} does not contain media")

        while True:
            try:
                await client.run_until_disconnected()
            except FloodWaitError as e:
                logging.warning(f"Flood wait for {e.seconds} seconds")
                sleep(e.seconds)
            except Exception as e:  # Catching general exceptions
                logging.error(f"Error: {e}")
                await client.disconnect()  # Disconnect if there's an error
                await client.start(phone_number)  # Attempt to reconnect
                continue  # Retry the operation after reconnecting

    except Exception as e:
        logging.error(f"Error connecting to Telegram: {e}")


with client:
    client.loop.run_until_complete(main())
