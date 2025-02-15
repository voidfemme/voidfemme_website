import sqlite3
from datetime import datetime, timezone
import json


class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize the database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            # Existing webmentions table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS webmentions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    target TEXT NOT NULL,
                    author_name TEXT,
                    author_photo TEXT,
                    content TEXT,
                    published TIMESTAMP,
                    type TEXT,
                    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # New photo posts table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS photo_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    caption TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    tags TEXT,  -- Stored as JSON array
                    slug TEXT UNIQUE NOT NULL,
                    activitypub_id TEXT UNIQUE,
                    visibility TEXT DEFAULT 'public'
                )
            """
            )

            # Table for individual photos within posts
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS photos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    original_path TEXT NOT NULL,
                    thumbnail_path TEXT NOT NULL,
                    medium_path TEXT NOT NULL,
                    alt_text TEXT,
                    order_index INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (post_id) REFERENCES photo_posts(id) ON DELETE CASCADE
                )
            """
            )

            # Create indexes for better query performance
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_photos_post_id ON photos(post_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_photo_posts_created ON photo_posts(created_at)"
            )

    def create_photo_post(self, caption, tags, slug):
        """Create a new photo post."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO photo_posts (caption, tags, slug, created_at)
                VALUES (?, ?, ?, ?)
            """,
                (caption, json.dumps(tags), slug, datetime.now(timezone.utc)),
            )
            return cursor.lastrowid

    def update_photo_post(self, post_id, caption, tags):
        """Update an existing photo post."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE photo_posts 
                SET caption = ?, tags = ?
                WHERE id = ?
            """,
                (caption, json.dumps(tags), post_id),
            )

    def delete_photo_post(self, post_id):
        """Delete a photo post and all associated photos."""
        with sqlite3.connect(self.db_path) as conn:
            # Photos will be deleted automatically due to ON DELETE CASCADE
            conn.execute("DELETE FROM photo_posts WHERE id = ?", (post_id,))

    def update_photo_alt_text(self, photo_id, alt_text):
        """Update the alt text for a specific photo."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE photos 
                SET alt_text = ?
                WHERE id = ?
            """,
                (alt_text, photo_id),
            )

    def add_photo_to_post(
        self,
        post_id,
        filename,
        original_path,
        thumbnail_path,
        medium_path,
        alt_text,
        order_index,
    ):
        """Add a photo to an existing post."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO photos (
                    post_id, filename, original_path, thumbnail_path, 
                    medium_path, alt_text, order_index
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    post_id,
                    filename,
                    original_path,
                    thumbnail_path,
                    medium_path,
                    alt_text,
                    order_index,
                ),
            )

    def get_photo_posts(self, page=1, per_page=12):
        """Get paginated photo posts with their first photo."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            offset = (page - 1) * per_page
            cursor = conn.execute(
                """
                SELECT 
                    pp.*,
                    p.thumbnail_path,
                    p.alt_text
                FROM photo_posts pp
                LEFT JOIN photos p ON p.post_id = pp.id 
                WHERE p.order_index = 0
                ORDER BY pp.created_at DESC
                LIMIT ? OFFSET ?
            """,
                (per_page, offset),
            )
            posts = []
            for row in cursor:
                post = dict(row)
                post["tags"] = json.loads(post["tags"])
                posts.append(post)
            return posts

    def get_photo_post(self, slug):
        """Get a specific photo post and all its photos."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get the post data
            cursor = conn.execute(
                """
                SELECT * FROM photo_posts WHERE slug = ?
            """,
                (slug,),
            )
            post = cursor.fetchone()

            if not post:
                return None

            post = dict(post)
            post["tags"] = json.loads(post["tags"])

            # Get all photos for this post
            cursor = conn.execute(
                """
                SELECT * FROM photos 
                WHERE post_id = ? 
                ORDER BY order_index
            """,
                (post["id"],),
            )

            post["photos"] = [dict(row) for row in cursor.fetchall()]
            return post

    def get_posts_by_tag(self, tag, page=1, per_page=12):
        """Get photo posts with a specific tag."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            offset = (page - 1) * per_page
            cursor = conn.execute(
                """
                SELECT 
                    pp.*,
                    p.thumbnail_path,
                    p.alt_text
                FROM photo_posts pp
                LEFT JOIN photos p ON p.post_id = pp.id 
                WHERE p.order_index = 0
                AND pp.tags LIKE ?
                ORDER BY pp.created_at DESC
                LIMIT ? OFFSET ?
            """,
                (f"%{tag}%", per_page, offset),
            )
            posts = []
            for row in cursor:
                post = dict(row)
                post["tags"] = json.loads(post["tags"])
                posts.append(post)
            return posts

    def store_webmention(self, mention_data):
        """Store a validated webmention."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO webmentions 
                (source, target, author_name, author_photo, content, published, type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    mention_data["source"],
                    mention_data["target"],
                    mention_data.get("author", {}).get("name"),
                    mention_data.get("author", {}).get("photo"),
                    mention_data.get("content"),
                    mention_data.get("published"),
                    mention_data.get("type"),
                ),
            )

    def get_webmentions(self, target_url):
        """Retrieve webmentions for a target URL."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM webmentions 
                WHERE target = ? 
                ORDER BY published DESC
            """,
                (target_url,),
            )
            return [dict(row) for row in cursor.fetchall()]
