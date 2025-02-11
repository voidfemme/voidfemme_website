from pathlib import Path
import json
from datetime import datetime


class ZineManager:
    def __init__(self, zines_dir):
        self.zines_dir = Path(zines_dir)
        self.metadata_file = self.zines_dir / "metadata.json"
        self.pdfs_dir = self.zines_dir / "pdfs"

        # Ensure directories exist
        self.pdfs_dir.mkdir(parents=True, exist_ok=True)

        # Initialize or load metadata
        if not self.metadata_file.exists():
            self._initialize_metadata()

    def _initialize_metadata(self):
        """Create an empty metadata file."""
        metadata = {"zines": []}
        self._save_metadata(metadata)

    def _load_metadata(self):
        """Load zine metadata from JSON file."""
        with open(self.metadata_file) as f:
            return json.load(f)

    def _save_metadata(self, metadata):
        """Save zine metadata to JSON file."""
        with open(self.metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

    def add_zine(self, title, description, pdf_filename, cover_image=None, tags=None):
        """Add a new zine to the collection."""
        metadata = self._load_metadata()

        new_zine = {
            "id": len(metadata["zines"]),
            "title": title,
            "description": description,
            "pdf_filename": pdf_filename,
            "cover_image": cover_image,
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
            "downloads": 0,
        }

        metadata["zines"].append(new_zine)
        self._save_metadata(metadata)
        return new_zine

    def get_all_zines(self):
        """Get all zines metadata."""
        metadata = self._load_metadata()
        return metadata["zines"]

    def get_zine(self, zine_id):
        """Get a specific zine by ID."""
        metadata = self._load_metadata()
        try:
            return next(z for z in metadata["zines"] if z["id"] == zine_id)
        except StopIteration:
            return None

    def increment_downloads(self, zine_id):
        """Increment the download count for a zine."""
        metadata = self._load_metadata()
        for zine in metadata["zines"]:
            if zine["id"] == zine_id:
                zine["downloads"] += 1
                break
        self._save_metadata(metadata)

    def get_pdf_path(self, filename):
        """Get the full path for a zine PDF file."""
        return self.pdfs_dir / filename
