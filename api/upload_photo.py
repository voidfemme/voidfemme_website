# api/upload_photo.py
from io import BufferedReader
import sys
import re
from pathlib import Path
from datetime import datetime, timezone
import click
from unicodedata import normalize
from database import Database
from photos import process_photo
from config import DB_PATH

db = Database(DB_PATH)


def slugify(text):
    """Create a URL-friendly slug from the given text."""
    text = text.lower()
    text = normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    return text


class FileWrapper:
    """Wrapper class to make file objects compatible with process_photo."""

    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.filename = str(self.file_path.name)  # Ensure filename is str
        self._file = None

    def read(self, size=-1):
        """Read and return the file contents."""
        if self._file is None:
            self._file = open(self.file_path, "rb")
        return self._file.read(size)

    def seek(self, offset):
        """Reset file pointer."""
        if self._file is None:
            self._file = open(self.file_path, "rb")
        return self._file.seek(offset)

    def tell(self):
        """Return current file position."""
        if self._file is None:
            self._file = open(self.file_path, "rb")
        return self._file.tell()

    def close(self):
        """Close the file."""
        if self._file is not None:
            self._file.close()
            self._file = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


@click.command()
@click.argument("photo_paths", nargs=-1, type=click.Path(exists=True))
@click.option("--caption", "-c", help="Caption for the photo post")
@click.option("--tags", "-t", help="Comma-separated list of tags")
@click.option(
    "--alt-text",
    "-a",
    help="Alt text for the photos (will be used for all photos if multiple)",
)
def upload_photos(photo_paths, caption, tags, alt_text):
    """Upload one or more photos with optional caption and tags."""
    if not photo_paths:
        click.echo("Please provide at least one photo path")
        sys.exit(1)

    # Convert tags string to list
    tag_list = [tag.strip() for tag in (tags or "").split(",") if tag.strip()]

    # Create slug from caption or timestamp
    if caption:
        base_slug = slugify(caption)
    else:
        base_slug = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    # Initialize database
    db = Database("webmentions.db")

    # Process photos first to ensure they're valid before creating database entry
    processed_photos = []

    try:
        for photo_path in photo_paths:
            click.echo(f"Processing {Path(photo_path).name}...")

            with FileWrapper(photo_path) as file_wrapper:
                try:
                    photo_data = process_photo(file_wrapper)
                    processed_photos.append(photo_data)
                    click.echo(f"Successfully processed {Path(photo_path).name}")
                except Exception as e:
                    click.echo(f"Error processing {photo_path}: {str(e)}", err=True)
                    raise

        # If we get here, all photos were processed successfully
        # Create the post
        post_id = db.create_photo_post(caption, tag_list, base_slug)

        # Add all processed photos to the database
        for i, photo_data in enumerate(processed_photos):
            db.add_photo_to_post(
                post_id=post_id,
                filename=photo_data["filename"],
                original_path=photo_data["original_path"],
                thumbnail_path=photo_data["thumbnail_path"],
                medium_path=photo_data["medium_path"],
                alt_text=alt_text,
                order_index=i,
            )

        click.echo(f"\nSuccessfully created post with {len(processed_photos)} photo(s)")
        click.echo(f"View at: /photos/{base_slug}")

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        # Clean up processed photos if anything fails
        for processed in processed_photos:
            try:
                for path_type in ["original_path", "thumbnail_path", "medium_path"]:
                    if path_type in processed:
                        full_path = Path("src/static/photos") / processed[path_type]
                        if full_path.exists():
                            full_path.unlink()
            except Exception as cleanup_error:
                click.echo(f"Error during cleanup: {str(cleanup_error)}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    upload_photos()
