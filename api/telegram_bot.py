import os
import requests
from pathlib import Path
import tempfile
from datetime import datetime, timezone
from config import ALLOWED_TELEGRAM_USERS
from photos import process_photo
import logging
import re
from unidecode import unidecode

logger = logging.getLogger(__name__)


def custom_slugify(text):
    """
    Convert a string to a URL-friendly slug.
    """
    # Convert to lowercase and normalize unicode characters
    text = text.lower()
    text = unidecode(text)

    # Replace any non-alphanumeric character with a dash
    text = re.sub(r"[^\w\s-]", "-", text)

    # Replace whitespace with a single dash
    text = re.sub(r"[-\s]+", "-", text)

    return text.strip("-")


class TelegramBot:
    def __init__(self, token, db):
        self.token = token
        self.db = db
        self.api_url = f"https://api.telegram.org/bot{token}"
        logger.info(f"Bot initialized with API URL: {self.api_url}")

    def get_file(self, file_id):
        """Get file info from Telegram."""
        response = requests.get(f"{self.api_url}/getFile", params={"file_id": file_id})
        return response.json()["result"]["file_path"]

    def download_file(self, file_path):
        """Download a file from Telegram."""
        url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
        response = requests.get(url)
        return response.content

    def send_message(self, chat_id, text):
        """Send a message to a chat."""
        logger.debug(f"Sending message to {chat_id}: {text}")
        try:
            response = requests.post(
                f"{self.api_url}/sendMessage", json={"chat_id": chat_id, "text": text}
            )
            response.raise_for_status()
            logger.debug(f"Message sent successfully: {response.json()}")
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")

    def handle_update(self, update_data):
        """Handle incoming Telegram update."""
        try:
            message = update_data.get("message", {})
            chat_id = message.get("chat", {}).get("id")
            username = message.get("from", {}).get("username")

            # Check if user is allowed
            if username not in ALLOWED_TELEGRAM_USERS:
                self.send_message(
                    chat_id, "Sorry, you're not authorized to use this bot."
                )
                return

            # Handle photo message
            if "photo" in message:
                return self.handle_photo(message)

            # Handle command message
            if "text" in message:
                return self.handle_command(message)

        except Exception as e:
            print(f"Error handling update: {str(e)}")
            if chat_id:
                self.send_message(chat_id, f"Error processing request: {str(e)}")

    def handle_photo(self, message):
        """Handle photo message."""
        chat_id = message["chat"]["id"]
        caption = message.get("caption", "")
        logger.info(f"Processing photo with caption: {caption}")

        try:
            # Get the largest photo version (last in array)
            photo = message["photo"][-1]
            file_id = photo["file_id"]
            logger.info(f"Processing file_id: {file_id}")

            # Download the photo
            file_path = self.get_file(file_id)
            photo_data = self.download_file(file_path)
            logger.info("Photo downloaded successfully")

            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
                temp_file.write(photo_data)
                temp_path = temp_file.name
                logger.info(f"Temporary file created at: {temp_path}")

            try:
                # Extract tags from caption (words starting with #)
                tags = [word[1:] for word in caption.split() if word.startswith("#")]
                # Remove tags from caption
                clean_caption = " ".join(
                    word for word in caption.split() if not word.startswith("#")
                ).strip()

                # Create slug
                if clean_caption:
                    base_slug = custom_slugify(clean_caption)
                else:
                    base_slug = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

                logger.info(f"Created slug: {base_slug}")

                # Create a FileWrapper for the temporary file
                class FileWrapper:
                    def __init__(self, file_path):
                        self.file_path = Path(file_path)
                        self.filename = str(self.file_path.name)
                        self._file = None

                    def read(self, size=-1):
                        if self._file is None:
                            self._file = open(self.file_path, "rb")
                        return self._file.read(size)

                    def seek(self, offset):
                        if self._file is None:
                            self._file = open(self.file_path, "rb")
                        return self._file.seek(offset)

                    def tell(self):
                        if self._file is None:
                            self._file = open(self.file_path, "rb")
                        return self._file.tell()

                    def close(self):
                        if self._file is not None:
                            self._file.close()
                            self._file = None

                # Process the photo
                file_wrapper = FileWrapper(temp_path)
                try:
                    # Create the post first
                    logger.info("Creating photo post in database")
                    post_id = self.db.create_photo_post(clean_caption, tags, base_slug)

                    # Then process and store the photo
                    logger.info("Processing photo")
                    photo_data = process_photo(file_wrapper)

                    logger.info("Adding photo to database")
                    self.db.add_photo_to_post(
                        post_id=post_id,
                        filename=photo_data["filename"],
                        original_path=photo_data["original_path"],
                        thumbnail_path=photo_data["thumbnail_path"],
                        medium_path=photo_data["medium_path"],
                        alt_text=clean_caption,
                        order_index=0,
                    )

                    # Send success message with URL
                    self.send_message(
                        chat_id,
                        f"Photo uploaded successfully!\nView at: /photos/{base_slug}",
                    )
                    logger.info("Photo processing completed successfully")

                except Exception as e:
                    logger.error(f"Error processing photo: {str(e)}", exc_info=True)
                    self.send_message(chat_id, f"Error processing photo: {str(e)}")
                    raise
                finally:
                    file_wrapper.close()

            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                    logger.info("Temporary file cleaned up")
                except Exception as e:
                    logger.error(f"Error cleaning up temporary file: {str(e)}")

        except Exception as e:
            logger.error(f"Error in handle_photo: {str(e)}", exc_info=True)
            self.send_message(chat_id, f"Error processing photo: {str(e)}")

    def handle_command(self, message):
        """Handle command message."""
        chat_id = message["chat"]["id"]
        text = message["text"]
        logger.debug(f"Handling command: {text} from chat {chat_id}")

        if text == "/start":
            logger.debug("Sending start message")
            self.send_message(
                chat_id,
                "Welcome! Send me photos to upload to your website. "
                "You can include a caption and #tags with your photo.",
            )
        elif text == "/help":
            logger.debug("Sending help message")
            self.send_message(
                chat_id,
                "Send a photo with an optional caption and #tags.\n\n"
                "Example: A beautiful sunset #nature #photography",
            )
