import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from datetime import datetime


def validate_webmention(source, target):
    """Validate and extract data from a webmention source."""
    # Verify URLs
    if not all(urlparse(url).scheme in ["http", "https"] for url in [source, target]):
        raise ValueError("Invalid URL scheme")

    # Fetch source page
    try:
        response = requests.get(source, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        raise ValueError(f"Could not fetch source: {str(e)}")

    # Parse the page
    soup = BeautifulSoup(response.text, "html.parser")

    # Verify source links to target
    if not any(a["href"] == target for a in soup.find_all("a", href=True)):
        raise ValueError("Source does not link to target")

    # Extract microformats data
    entry = soup.find(class_="h-entry")
    if not entry:
        # Basic extraction if no microformats
        return {
            "source": source,
            "target": target,
            "content": soup.find("title").text if soup.find("title") else "",
            "published": datetime.now().isoformat(),
            "type": "mention",
        }

    # Extract structured data
    author = entry.find(class_="p-author")
    return {
        "source": source,
        "target": target,
        "author": {
            "name": author.find(class_="p-name").text if author else None,
            "photo": (
                author.find(class_="u-photo")["src"]
                if author and author.find(class_="u-photo")
                else None
            ),
        },
        "content": (
            entry.find(class_="e-content").text
            if entry.find(class_="e-content")
            else ""
        ),
        "published": (
            entry.find(class_="dt-published")["datetime"]
            if entry.find(class_="dt-published")
            else datetime.now().isoformat()
        ),
        "type": "entry",
    }
