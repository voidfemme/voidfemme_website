# api/add_zine.py
from zines import ZineManager
import shutil
from pathlib import Path


def add_zine():
    zine_manager = ZineManager("../src/zines")

    # Get zine information from user
    title = input("Enter zine title: ")
    description = input("Enter zine description: ")
    tags = input("Enter tags (comma-separated): ").split(",")
    tags = [tag.strip() for tag in tags if tag.strip()]

    # Get PDF file path
    while True:
        pdf_path = input("Enter path to your PDF file: ")
        pdf_path = Path(pdf_path)
        if pdf_path.exists() and pdf_path.suffix.lower() == ".pdf":
            break
        print("File not found or not a PDF. Please try again.")

    # Create a sanitized filename
    safe_filename = "".join(c for c in title.lower() if c.isalnum() or c in (" ", "-"))
    safe_filename = safe_filename.replace(" ", "-") + ".pdf"

    # Copy PDF to zines directory
    destination = zine_manager.pdfs_dir / safe_filename
    shutil.copy2(pdf_path, destination)

    # Add zine to collection
    zine = zine_manager.add_zine(
        title=title, description=description, pdf_filename=safe_filename, tags=tags
    )

    print(f"\nZine added successfully!")
    print(f"Title: {zine['title']}")
    print(f"ID: {zine['id']}")
    print(f"Tags: {', '.join(zine['tags'])}")


if __name__ == "__main__":
    add_zine()
