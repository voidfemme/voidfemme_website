# api/photos.py
from PIL import Image
import os
from pathlib import Path
from datetime import datetime, timezone
import secrets
from werkzeug.utils import secure_filename
from config import PHOTOS_DIR, THUMBNAIL_SIZE, MEDIUM_SIZE, ALLOWED_EXTENSIONS


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_unique_filename(original_filename):
    """Generate a unique filename while preserving extension."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    random_hex = secrets.token_hex(4)
    ext = Path(original_filename).suffix
    return f"{timestamp}-{random_hex}{ext}"


def create_thumbnail(image, size):
    """Create a thumbnail while maintaining aspect ratio."""
    thumbnail = image.copy()
    thumbnail.thumbnail(size, Image.Resampling.LANCZOS)
    return thumbnail


def create_square_thumbnail(image, size):
    """Create a square thumbnail by cropping to center."""
    width, height = image.size
    if width == height:
        return create_thumbnail(image, size)

    # Calculate dimensions for center crop
    new_dim = min(width, height)
    left = (width - new_dim) // 2
    top = (height - new_dim) // 2
    right = left + new_dim
    bottom = top + new_dim

    # Crop to square and resize
    square = image.crop((left, top, right, bottom))
    return create_thumbnail(square, size)


def process_photo(file, generate_square_thumb=True):
    """Process an uploaded photo, creating required sizes."""
    if not allowed_file(file.filename):
        raise ValueError("Invalid file type")

    # Generate unique filename
    filename = generate_unique_filename(secure_filename(file.filename))

    # Open image and convert to RGB if necessary
    image = Image.open(file)
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    # Prepare paths
    original_path = PHOTOS_DIR / "original" / filename
    thumbnail_path = PHOTOS_DIR / "thumbnail" / filename
    medium_path = PHOTOS_DIR / "medium" / filename

    # Save original
    image.save(original_path, quality=95, optimize=True)

    # Create and save thumbnail
    if generate_square_thumb:
        thumbnail = create_square_thumbnail(image, THUMBNAIL_SIZE)
    else:
        thumbnail = create_thumbnail(image, THUMBNAIL_SIZE)
    thumbnail.save(thumbnail_path, quality=85, optimize=True)

    # Create and save medium size
    medium = create_thumbnail(image, MEDIUM_SIZE)
    medium.save(medium_path, quality=90, optimize=True)

    return {
        "filename": filename,
        "original_path": str(original_path.relative_to(PHOTOS_DIR)),
        "thumbnail_path": str(thumbnail_path.relative_to(PHOTOS_DIR)),
        "medium_path": str(medium_path.relative_to(PHOTOS_DIR)),
    }


def delete_photo(filename):
    """Delete all versions of a photo."""
    paths = [
        PHOTOS_DIR / "original" / filename,
        PHOTOS_DIR / "thumbnail" / filename,
        PHOTOS_DIR / "medium" / filename,
    ]

    for path in paths:
        try:
            path.unlink()
        except FileNotFoundError:
            pass  # Ignore if file doesn't exist
