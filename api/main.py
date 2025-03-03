from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    send_file,
    abort,
    url_for,
    redirect,
    flash,
    send_from_directory,
)
from flask_mail import Mail, Message
from slugify import slugify
import markdown
import frontmatter
from datetime import datetime, date, timezone
import logging
import requests
import markdown
import os

from database import Database
from validators import validate_webmention
from templates import render_post, render_page
from zines import ZineManager
from feed_aggregator import FeedAggregator
from config import (
    POSTS_DIR,
    PAGES_DIR,
    ZINES_DIR,
    PHOTOS_DIR,
    PHOTOS_PER_PAGE,
    DB_PATH,
    TELEGRAM_BOT_TOKEN,
    ALLOWED_TELEGRAM_USERS,
)
from photos import process_photo, delete_photo
from telegram_bot import TelegramBot

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="../src/_includes", static_folder="../src/static")
db = Database("webmentions.db")
zine_manager = ZineManager("../src/zines")
bot = TelegramBot(TELEGRAM_BOT_TOKEN, db)
feed_aggregator = FeedAggregator(cache_duration=30)  # Cache for 30 minutes
mail = Mail(app)
port = int(os.getenv("PORT", 10000))

app.run(host="0.0.0.0", port=port)

# Load secret key from envrionment
app.secret_key = os.getenv("FLASK_SECRET_KEY")


@app.route("/static/images/posts/<path:filename>")
def serve_blog_image(filename):
    return send_from_directory("src/static/images/posts", filename)


# Test route to verify the server is working
@app.route("/webhook/test", methods=["GET"])
def test_webhook():
    """Test endpoint to verify the server is responding."""
    return jsonify({"status": "ok", "message": "Webhook endpoint is working"}), 200


@app.route("/webhook/debug", methods=["GET"])
def debug_webhook():
    """Debug endpoint to verify database and bot configuration."""
    try:
        # Test database connection
        db_status = "OK" if db else "Not initialized"

        # Test bot configuration
        bot_status = "OK" if bot and bot.token else "Not initialized"

        return (
            jsonify(
                {
                    "status": "running",
                    "database": db_status,
                    "bot": bot_status,
                    "allowed_users": ALLOWED_TELEGRAM_USERS,
                    "webhook_url": request.url_root + "webhook/telegram",
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/webhook/telegram", methods=["POST"])
def telegram_webhook():
    """Handle incoming updates from Telegram."""
    logger.info("Webhook called")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request headers: {dict(request.headers)}")

    try:
        # Log raw data
        raw_data = request.get_data()
        logger.info(f"Raw request data: {raw_data}")

        if not request.is_json:
            logger.error("Request is not JSON")
            return jsonify({"error": "Request must be JSON"}), 400

        update = request.get_json()
        logger.info(f"Parsed update data: {update}")

        if not update:
            logger.error("Empty update received")
            return jsonify({"error": "No data received"}), 400

        # Add more context about the update
        if "message" in update:
            msg = update["message"]
            logger.info(f"Received message: {msg.get('text', '(no text)')}")
            logger.info(f"From user: {msg.get('from', {}).get('username', 'unknown')}")

        # Handle the update
        bot.handle_update(update)
        logger.info("Update handled successfully")
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logger.error(f"Error in webhook: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


print("Available routes:")
for rule in app.url_map.iter_rules():
    print(f"{rule.endpoint}: {rule.rule}")


# Add date filter to Jinja
@app.template_filter("date")
def date_filter(value, format="%B %d, %Y"):
    """Convert a date to a formatted string."""
    if not value:
        return ""

    if isinstance(value, str):
        try:
            # Try parsing ISO format first
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                # Try parsing standard format
                value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return value

    if isinstance(value, date) and not isinstance(value, datetime):
        value = datetime.combine(value, datetime.min.time())

    return value.strftime(format)


# Ensure directories exist
POSTS_DIR.mkdir(parents=True, exist_ok=True)
PAGES_DIR.mkdir(parents=True, exist_ok=True)
ZINES_DIR.mkdir(parents=True, exist_ok=True)


def register_photo_routes(app):
    @app.route("/photos")
    def photos():
        """Display the photo grid/gallery view."""
        page = request.args.get("page", 1, type=int)
        tag = request.args.get("tag")

        if tag:
            posts = db.get_posts_by_tag(tag, page, PHOTOS_PER_PAGE)
        else:
            posts = db.get_photo_posts(page, PHOTOS_PER_PAGE)

        print("Debug - Photos route:")
        print(f"Number of posts: {len(posts)}")
        if posts:
            print(f"First post: {posts[0]}")

        return render_template("photos/index.html", posts=posts, page=page, tag=tag)

    @app.route("/photos/<slug>")
    def photo_detail(slug):
        """Display a single photo post."""
        post = db.get_photo_post(slug)
        if not post:
            abort(404)
        return render_template("photos/detail.html", post=post)

    @app.route("/photos/new", methods=["GET", "POST"])
    def new_photo():
        """Handle new photo post creation."""
        if request.method == "POST":
            caption = request.form.get("caption", "").strip()
            tags = [
                tag.strip()
                for tag in request.form.get("tags", "").split(",")
                if tag.strip()
            ]
            files = request.files.getlist("photos")

            if not files or not files[0].filename:
                flash("Please select at least one photo.", "error")
                return redirect(request.url)

            # Create slug from caption or timestamp if no caption
            if caption:
                base_slug = slugify(caption)
            else:
                base_slug = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

            try:
                # Create the post
                post_id = db.create_photo_post(caption, tags, base_slug)

                # Process each uploaded photo
                for i, file in enumerate(files):
                    photo_data = process_photo(file)
                    db.add_photo_to_post(
                        post_id=post_id,
                        filename=photo_data["filename"],
                        original_path=photo_data["original_path"],
                        thumbnail_path=photo_data["thumbnail_path"],
                        medium_path=photo_data["medium_path"],
                        alt_text=request.form.get(f"alt_text_{i}", ""),
                        order_index=i,
                    )
            except Exception as e:
                flash(f"Error processing photo: {str(e)}", "error")
                return redirect(request.url)

            return redirect(url_for("photos"))

        return render_template("photos/new.html")

    @app.route("/photos/<path:filename>")
    def serve_photo(filename):
        """Serve photo files."""
        try:
            # Extract size from query parameter
            size = request.args.get("size", "medium")
            if size not in ["original", "medium", "thumbnail"]:
                size = "medium"  # Default to medium if invalid size

            # If filename includes the directory, strip it
            if "/" in filename:
                filename = filename.split("/")[-1]

            # Construct the file path
            photo_path = PHOTOS_DIR / size / filename

            if not photo_path.exists():
                print(f"Photo not found at path: {photo_path}")
                abort(404)

            # Get the directory and filename
            directory = str(PHOTOS_DIR / size)

            print(f"Serving photo from: {directory}, filename: {filename}")
            return send_from_directory(directory, filename)
        except Exception as e:
            print(f"Error serving photo: {str(e)}")
            abort(404)

    @app.route("/photos/<slug>/edit", methods=["GET", "POST"])
    def edit_photo(slug):
        """Edit a photo post."""
        post = db.get_photo_post(slug)
        if not post:
            abort(404)

        if request.method == "POST":
            caption = request.form.get("caption", "").strip()
            tags = [
                tag.strip()
                for tag in request.form.get("tags", "").split(",")
                if tag.strip()
            ]

            # Update post in database
            db.update_photo_post(post["id"], caption, tags)

            # Update alt text for existing photos
            for photo in post["photos"]:
                new_alt_text = request.form.get(f"alt_text_{photo['id']}", "")
                if new_alt_text != photo["alt_text"]:
                    db.update_photo_alt_text(photo["id"], new_alt_text)

            return redirect(url_for("photo_detail", slug=slug))

        return render_template("photos/edit.html", post=post)

    @app.route("/photos/<slug>/delete", methods=["POST"])
    def delete_photo_post(slug):
        """Delete a photo post and all associated files."""
        post = db.get_photo_post(slug)
        if not post:
            abort(404)

        # Delete all photo files
        for photo in post["photos"]:
            delete_photo(photo["filename"])

        # Delete from database
        db.delete_photo_post(post["id"])

        flash("Photo post deleted successfully.", "success")
        return redirect(url_for("photos"))

    @app.route("/photos/tag/<tag>")
    def photos_by_tag(tag):
        """Display photos filtered by tag."""
        page = request.args.get("page", 1, type=int)
        posts = db.get_posts_by_tag(tag, page, PHOTOS_PER_PAGE)
        return render_template("photos/index.html", posts=posts, page=page, tag=tag)

    @app.route("/debug/photos")
    def debug_photos():
        """Debug endpoint to check photo posts."""
        posts = db.get_photo_posts()
        return jsonify(
            {"posts": posts, "photos_dir": str(PHOTOS_DIR), "db_path": str(DB_PATH)}
        )

    @app.route("/debug/photo/<path:filename>")
    def debug_photo(filename):
        """Debug endpoint to check photo paths."""
        size = request.args.get("size", "medium")
        if size not in ["original", "medium", "thumbnail"]:
            size = "medium"

        # If filename includes the directory, strip it
        if "/" in filename:
            filename = filename.split("/")[-1]

        photo_path = PHOTOS_DIR / size / filename

        return jsonify(
            {
                "requested_filename": filename,
                "size": size,
                "full_path": str(photo_path),
                "exists": photo_path.exists(),
                "photos_dir": str(PHOTOS_DIR),
                "is_file": photo_path.is_file() if photo_path.exists() else None,
            }
        )


# Register the photo routes
register_photo_routes(app)


def get_post_data(post_path):
    """Load and parse a post file with frontmatter."""
    try:
        with open(post_path) as f:
            content = f.read()

        try:
            post = frontmatter.loads(content)
        except Exception as e:
            print(f"Error parsing frontmatter in {post_path}: {str(e)}")
            return {
                "title": post_path.stem,
                "date": datetime.now(),
                "content": content,
                "url": f"/posts/{post_path.stem}",
                "tags": [],
            }

        # Convert date string to datetime if needed
        post_date = post.metadata.get("date", datetime.now())
        if isinstance(post_date, str):
            try:
                post_date = datetime.strptime(post_date, "%Y-%m-%d %H:%M")
            except ValueError:
                try:
                    post_date = datetime.fromisoformat(post_date)
                except ValueError:
                    post_date = datetime.now()
        elif isinstance(post_date, date) and not isinstance(post_date, datetime):
            post_date = datetime.combine(post_date, datetime.min.time())

        # Configure Markdown extensions
        md = markdown.Markdown(
            extensions=[
                "fenced_code",
                "codehilite",
                "tables",
                "footnotes",
                "attr_list",
                "toc",
                "md_in_html",  # Allow Markdown inside HTML tags
            ]
        )

        # Process the content to handle image paths
        processed_content = process_image_paths(post.content, post_path.stem)
        content = md.convert(processed_content)

        # Extract and normalize tags
        tags = post.metadata.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]

        # Ensure tags are a list even if missing or wrongly formatted
        if not isinstance(tags, list):
            tags = []

        # Determine the post status (default to "draft" if missing)
        status = post.metadata.get("status", "draft").lower()
        if status not in ["published", "draft"]:  # Fallback if invalid
            status = "draft"

        return {
            "title": post.metadata.get("title", ""),
            "date": post_date,
            "content": content,
            "url": f"/posts/{post_path.stem}",
            "tags": tags,
            "status": status,
            **post.metadata,
        }
    except Exception as e:
        print(f"Error processing {post_path}: {str(e)}")
        return {
            "title": post_path.stem,
            "date": datetime.now(),
            "content": "Error loading post",
            "url": f"/posts/{post_path.stem}",
            "tags": [],
        }


def process_image_paths(content, post_slug):
    """Process image paths in markdown content to point to the correct static directory."""
    import re

    # Regular expression to find markdown image syntax
    img_pattern = r"!\[(.*?)\]\((.*?)\)"

    def replace_path(match):
        alt_text = match.group(1)
        img_path = match.group(2)

        # If it's already a full URL, leave it unchanged
        if img_path.startswith(("http://", "https://", "/")):
            return f"![{alt_text}]({img_path})"

        # Otherwise, construct the path to the static directory
        new_path = f"/static/images/posts/{post_slug}/{img_path}"
        return f"![{alt_text}]({new_path})"

    return re.sub(img_pattern, replace_path, content)


def get_home_content():
    """Load and parse the home page content."""
    home_path = PAGES_DIR / "home.md"
    if home_path.exists():
        with open(home_path) as f:
            post = frontmatter.load(f)
            return markdown.markdown(post.content)
    return ""


@app.route("/")
def home():
    """Render the home page with recent posts and zines."""
    # Get latest 3 posts
    posts = []
    for post_path in sorted(POSTS_DIR.glob("*.md"), reverse=True):
        post_data = get_post_data(post_path)
        # Ensure date is datetime
        if isinstance(post_data["date"], date) and not isinstance(
            post_data["date"], datetime
        ):
            post_data["date"] = datetime.combine(post_data["date"], datetime.min.time())
        posts.append(post_data)

    # Debug print
    for post in posts:
        print(
            f"Post: {post['title']}, Date type: {type(post['date'])}, Value: {post['date']}"
        )

    recent_posts = sorted(posts, key=lambda x: x["date"], reverse=True)[:3]

    # Get latest 3 zines
    all_zines = zine_manager.get_all_zines()
    recent_zines = sorted(
        all_zines, key=lambda x: datetime.fromisoformat(x["created_at"]), reverse=True
    )[:3]

    # Get home page content
    home_content = get_home_content()

    # Load the links content
    homelinks_content = get_homelinks_content()

    return render_template(
        "index.html",
        recent_posts=recent_posts,
        recent_zines=recent_zines,
        home_content=home_content,
        homelinks=homelinks_content,
    )


@app.route("/blog")
def blog():
    """Render the blog page with all posts."""
    posts = []
    for post_path in sorted(POSTS_DIR.glob("*.md"), reverse=True):
        post_data = get_post_data(post_path)

        # Ensure date is datetime
        if isinstance(post_data["date"], date) and not isinstance(
            post_data["date"], datetime
        ):
            post_data["date"] = datetime.combine(post_data["date"], datetime.min.time())

        if (
            post_data and post_data["status"] == "published"
        ):  # Only show published posts
            posts.append(post_data)

    posts = sorted(
        posts, key=lambda x: x["date"], reverse=True
    )  # Now all dates are datetime objects

    return render_template("blog.html", posts=posts)


@app.route("/about")
def about():
    """Render the about page."""
    page_path = PAGES_DIR / "about.md"
    if not page_path.exists():
        return "About page not found", 404

    page_data = get_post_data(page_path)
    return render_template(
        "about.html", title=page_data["title"], content=page_data["content"]
    )


@app.route("/tags/<tag>")
def posts_by_tag(tag):
    """Display posts filtered by a specific tag."""
    page = request.args.get("page", 1, type=int)
    posts = []

    for post_path in sorted(POSTS_DIR.glob("*.md"), reverse=True):
        post_data = get_post_data(post_path)

        if (
            post_data
            and tag in post_data.get("tags", [])
            and post_data["status"] == "published"
        ):
            posts.append(post_data)

    return render_template("tag_archive.html", tag=tag, posts=posts)


@app.route("/posts/<slug>")
def post(slug):
    """Render an individual post."""
    post_path = POSTS_DIR / f"{slug}.md"
    if not post_path.exists():
        return "Post not found", 404

    post_data = get_post_data(post_path)

    # If the post is a draft, show a warning message
    if post_data["status"] == "draft":
        flash("This post is a draft and not publicly visible.", "warning")

    webmentions = db.get_webmentions(f"/posts/{slug}")

    return render_template("post.html", **post_data, webmentions=webmentions)


@app.route("/pages/<slug>")
def page(slug):
    """Render a static page."""
    page_path = PAGES_DIR / f"{slug}.md"
    if not page_path.exists():
        return "Page not found", 404

    page_data = get_post_data(page_path)
    return render_page(page_data)


@app.route("/webmention", methods=["POST"])
def receive_webmention():
    """Handle incoming webmentions."""
    source = request.form.get("source")
    target = request.form.get("target")

    if not source or not target:
        return jsonify({"error": "Missing source or target"}), 400

    # Validate the webmention
    try:
        mention_data = validate_webmention(source, target)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Store the validated webmention
    db.store_webmention(mention_data)

    return jsonify({"status": "Webmention received"}), 202


@app.route("/zines")
def zines():
    """Render the zines page."""
    all_zines = zine_manager.get_all_zines()
    return render_template("zines.html", zines=all_zines)


@app.route("/zines/<int:zine_id>")
def zine_detail(zine_id):
    """Show details for a specific zine."""
    zine = zine_manager.get_zine(zine_id)
    if not zine:
        abort(404)
    return render_template("zine_detail.html", zine=zine)


@app.route("/zines/<int:zine_id>/download")
def download_zine(zine_id):
    """Download a zine PDF."""
    zine = zine_manager.get_zine(zine_id)
    if not zine:
        abort(404)

    try:
        pdf_path = zine_manager.get_pdf_path(zine["pdf_filename"])
        zine_manager.increment_downloads(zine_id)
        return send_file(pdf_path, as_attachment=True)
    except FileNotFoundError:
        abort(404)


def get_homelinks_content():
    links_path = PAGES_DIR / "homelinks.md"
    if links_path.exists():
        with open(links_path) as f:
            post = frontmatter.load(f)
            return markdown.markdown(post.content)
    return ""


@app.route("/debug/feeds")
def debug_feeds():
    """Debug endpoint to check feed parsing."""
    aggregator = feed_aggregator  # Your existing feed_aggregator instance

    results = {
        "paths": {
            "project_root": str(aggregator.project_root),
            "data_dir": str(aggregator.data_dir),
            "feeds_file": str(aggregator.feeds_path),
            "current_working_dir": os.getcwd(),
        },
        "file_exists": aggregator.feeds_path.exists(),
        "feed_config": aggregator.load_feed_urls(),
        "parsing_results": {},
    }

    if results["feed_config"]:
        for feed in results["feed_config"]:
            if feed["type"] == "h-feed":
                items = aggregator.parse_h_feed(feed["url"])
            else:
                items = aggregator.parse_rss_feed(feed["url"])

            results["parsing_results"][feed["url"]] = {
                "type": feed["type"],
                "item_count": len(items),
                "sample_items": items[:2] if items else None,
                "success": bool(items),
            }

    return jsonify(results)


@app.route("/feed")
def feed():
    """Render the feed page with indieweb content."""
    feed_path = PAGES_DIR / "feed.md"

    # Get the page content (description, etc.)
    if feed_path.exists():
        with open(feed_path) as f:
            page = frontmatter.load(f)
            content = markdown.markdown(page.content)
    else:
        content = ""

    # Get the feed items
    feed_items = feed_aggregator.fetch_feeds()

    return render_template("feed.html", content=content, feed_items=feed_items)


@app.route("/contact", methods=["POST"])
def contact():
    # Check the honeypot field
    if request.form.get("website"):
        # This is likely a bot submission since the honeypot field was filled
        # Just silently redirect to avoid letting the bot know it was detected
        return redirect(url_for("about"))

    # Process legitimate form submissions
    name = request.form.get("name")
    email = request.form.get("email")
    message = request.form.get("message")

    # Validate the form data
    if not all([name, email, message]):
        flash("Please fill out all required fields", "error")
        return redirect(url_for("about"))

    try:
        # Save to database or send email notification
        db.store_contact_message(name, email, message)
        flash("Thank you for your message! I'll get back to you soon.", "success")
    except Exception as e:
        flash(
            "There was an error sending your message. Please try again later.", "error"
        )
        app.logger.error(f"Contact form error: {str(e)}")

    return redirect(url_for("about"))


if __name__ == "__main__":
    # Test the bot token on startup
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
        )
        if response.status_code == 200:
            logger.info("Telegram bot token is valid")
            logger.info(f"Bot info: {response.json()}")
        else:
            logger.error(f"Invalid Telegram bot token: {response.text}")
    except Exception as e:
        logger.error(f"Error testing bot token: {str(e)}")

    # Print startup information
    logger.info(f"Server starting on port 5000")
    logger.info(f"Debug mode: {app.debug}")
    logger.info(f"TELEGRAM_BOT_TOKEN set: {bool(TELEGRAM_BOT_TOKEN)}")
    logger.info(f"ALLOWED_TELEGRAM_USERS: {ALLOWED_TELEGRAM_USERS}")

    # Run the app
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=True)
