import sqlite3


class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize the database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
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
