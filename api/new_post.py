# api/new_post.py
from datetime import datetime
from pathlib import Path
import subprocess
import os


def create_new_post():
    # Get post details
    title = input("Enter post title: ")
    tags = input("Enter tags (comma-separated): ").split(",")
    tags = [tag.strip() for tag in tags if tag.strip()]
    summary = input("Enter brief summary: ")

    # Create current datetime in the desired format
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Create filename
    date_for_filename = current_time.split()[0]
    slug = title.lower().replace(" ", "-")
    filename = f"{date_for_filename}-{slug}.md"

    # Create post content
    content = f"""---
title: {title}
date: {current_time}
tags: {tags}
summary: {summary}
---

Write your post here...
"""

    # Save the file
    posts_dir = Path(__file__).parent.parent / "src" / "posts"
    post_path = posts_dir / filename

    with open(post_path, "w") as f:
        f.write(content)

    print(f"\nPost created at {post_path}")

    # Try to open the file in the default editor
    try:
        if os.name == "nt":  # Windows
            os.startfile(post_path)
        else:  # macOS and Linux
            editor = os.environ.get("EDITOR", "nvim")
            subprocess.call([editor, post_path])
    except:
        print("Couldn't open editor automatically. Please open the file manually.")


if __name__ == "__main__":
    create_new_post()
