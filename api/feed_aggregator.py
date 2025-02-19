"""Enhanced feed aggregator with debugging"""

import feedparser
import requests
from datetime import datetime, timedelta
import email.utils
from dateutil import parser
from pathlib import Path
import yaml
import mf2py
import logging
import os


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FeedAggregator:
    def __init__(self, cache_duration=30):
        # Get the absolute path to the project root
        self.project_root = Path(__file__).parent.parent
        self.data_dir = self.project_root / "src" / "data"
        self.feeds_path = self.data_dir / "feeds.yaml"
        self.cache_path = self.data_dir / "feed_cache.json"
        self.cache_duration = timedelta(minutes=cache_duration)

        # Create data directory if it doesn't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Log the paths we're using
        logger.info(f"Project root: {self.project_root}")
        logger.info(f"Data directory: {self.data_dir}")
        logger.info(f"Feeds file path: {self.feeds_path}")

    def load_feed_urls(self):
        """Load feed URLs from YAML file."""
        try:
            if not self.feeds_path.exists():
                logger.error(f"Feeds file not found at {self.feeds_path}")
                logger.error(f"Current working directory: {os.getcwd()}")
                return []

            with open(self.feeds_path) as f:
                logger.info(f"Successfully opened feeds file at {self.feeds_path}")
                data = yaml.safe_load(f)
                if not data:
                    logger.error("YAML file is empty or invalid")
                    return []

                feeds = data.get("feeds", [])
                logger.info(f"Loaded {len(feeds)} feeds from config")
                logger.info(f"Feed data: {feeds}")
                return feeds

        except Exception as e:
            logger.error(f"Error loading feeds: {str(e)}")
            logger.error(f"Current working directory: {os.getcwd()}")
            logger.error(f"Attempted to load from: {self.feeds_path}")
            return []

    def parse_date(self, date_str):
        """Parse a date string into a consistent format."""
        if not date_str:
            return datetime.now().isoformat()

        try:
            # Try parsing as RFC 2822 (common in RSS feeds)
            parsed_date = email.utils.parsedate_to_datetime(date_str)
            return parsed_date.isoformat()
        except:
            try:
                # Try parsing as ISO format
                parsed_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                return parsed_date.isoformat()
            except:
                try:
                    # Try parsing with dateutil as a fallback
                    parsed_date = parser.parse(date_str)
                    return parsed_date.isoformat()
                except:
                    logger.warning(f"Could not parse date: {date_str}")
                    return datetime.now().isoformat()

    def parse_h_feed(self, url):
        """Parse an h-feed from a URL with enhanced debugging."""
        try:
            logger.info(f"Fetching h-feed from {url}")
            response = requests.get(url)
            response.raise_for_status()

            # Parse the page
            parsed = mf2py.parse(doc=response.text, url=url)

            # Debug the overall structure
            logger.info("Found microformat types:")
            all_types = set()
            for item in parsed["items"]:
                all_types.update(item["type"])
            logger.info(f"All types found: {all_types}")

            items = []
            # First try to find h-feed
            feed_items = []

            # Look for h-feed container
            feeds = [item for item in parsed["items"] if "h-feed" in item["type"]]
            if feeds:
                logger.info("Found h-feed container")
                # Get entries from the feed
                for feed in feeds:
                    if "children" in feed:
                        feed_items.extend(
                            [
                                child
                                for child in feed["children"]
                                if "h-entry" in child["type"]
                            ]
                        )

            # If no h-feed found or no entries in h-feed, look for h-entries directly
            if not feed_items:
                logger.info("No entries found in h-feed, looking for direct h-entries")
                feed_items = [
                    item for item in parsed["items"] if "h-entry" in item["type"]
                ]

            logger.info(f"Found {len(feed_items)} potential entries")

            for item in feed_items:
                try:
                    if "properties" not in item:
                        logger.warning(f"No properties found in item: {item}")
                        continue

                    properties = item["properties"]

                    # Debug properties
                    logger.info(f"Properties found in entry: {list(properties.keys())}")

                    # Get title (try different possible properties)
                    title = None
                    for title_prop in ["name", "title"]:
                        if title_prop in properties and properties[title_prop]:
                            title = properties[title_prop][0]
                            break

                    # If no title found but content exists, use first few words
                    if not title and "content" in properties:
                        content_text = properties["content"][0]["value"]
                        title = " ".join(content_text.split()[:7]) + "..."

                    # Get URL
                    url = None
                    if "url" in properties and properties["url"]:
                        url = properties["url"][0]

                    # Get date
                    published = None
                    for date_prop in ["published", "updated", "date"]:
                        if date_prop in properties and properties[date_prop]:
                            published = properties[date_prop][0]
                            break

                    # Get summary/content
                    summary = None
                    if "summary" in properties and properties["summary"]:
                        summary = properties["summary"][0]
                    elif "content" in properties and properties["content"]:
                        content = properties["content"][0]
                        if isinstance(content, dict):
                            summary = content.get("value", "")
                        else:
                            summary = content

                    if title and url:  # Only add if we have at least a title and URL
                        entry = {
                            "title": title,
                            "url": url,
                            "date": (
                                self.parse_date(published)
                                if published
                                else datetime.now().isoformat()
                            ),
                            "summary": summary,
                            "author": None,  # We'll handle author below
                        }

                        # Handle author
                        if "author" in properties:
                            author_data = properties["author"][0]
                            if isinstance(author_data, dict):
                                if "properties" in author_data:
                                    entry["author"] = author_data["properties"].get(
                                        "name", [None]
                                    )[0]
                                else:
                                    entry["author"] = author_data.get("value", None)
                            else:
                                entry["author"] = author_data

                        items.append(entry)
                        logger.info(f"Successfully parsed entry: {title}")
                    else:
                        logger.warning(
                            f"Skipping entry - missing title or URL. Title: {title}, URL: {url}"
                        )

                except Exception as e:
                    logger.error(f"Error parsing individual entry: {str(e)}")
                    continue

            logger.info(f"Successfully parsed {len(items)} entries from h-feed")
            return items

        except Exception as e:
            logger.error(f"Error parsing h-feed {url}: {str(e)}")
            return []

    def parse_rss_feed(self, url):
        """Parse an RSS feed from a URL."""
        try:
            logger.info(f"Fetching RSS feed from {url}")
            feed = feedparser.parse(url)

            if feed.bozo:
                logger.error(f"Feed parsing error: {feed.bozo_exception}")

            items = []
            for entry in feed.entries:
                published = entry.get("published") or entry.get("updated")

                item = {
                    "title": entry.get("title"),
                    "url": entry.get("link"),
                    "author": entry.get("author"),
                    "date": self.parse_date(published),
                    "summary": entry.get("summary", entry.get("description")),
                }

                if (
                    item["title"] and item["url"]
                ):  # Only add if we have at least title and URL
                    items.append(item)

            return items

        except Exception as e:
            logger.error(f"Error parsing RSS feed {url}: {str(e)}")
            return []

    def fetch_feeds(self):
        """Fetch and aggregate all feeds."""
        try:
            feeds = self.load_feed_urls()
            if not feeds:
                logger.error("No feeds found in configuration")
                return []

            all_items = []
            for feed in feeds:
                logger.info(f"Processing feed: {feed['url']} (type: {feed['type']})")

                if feed.get("type") == "h-feed":
                    items = self.parse_h_feed(feed["url"])
                else:  # assume RSS
                    items = self.parse_rss_feed(feed["url"])

                all_items.extend(items)

            # Filter out items with no date or invalid data
            valid_items = [
                item for item in all_items if item.get("date") and item.get("url")
            ]

            # Sort by date
            valid_items.sort(key=lambda x: x["date"] if x["date"] else "", reverse=True)

            logger.info(f"Total valid items found: {len(valid_items)}")
            return valid_items

        except Exception as e:
            logger.error(f"Error in fetch_feeds: {str(e)}")
            return []
