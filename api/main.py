from flask import Flask, request, jsonify, render_template, send_file, abort
from pathlib import Path
import markdown
import frontmatter
from datetime import datetime
from database import Database
from validators import validate_webmention
from templates import render_post, render_page
from zines import ZineManager

app = Flask(__name__, template_folder="../src/_includes", static_folder="../src/static")


# Add date filter to Jinja
@app.template_filter("date")
def date_filter(value, format="%B %d, %Y"):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    return value.strftime(format) if value else ""


db = Database("webmentions.db")
zine_manager = ZineManager("../src/zines")

# File path configurations
CONTENT_DIR = Path(__file__).parent.parent / "src"
POSTS_DIR = CONTENT_DIR / "posts"
PAGES_DIR = CONTENT_DIR / "pages"
ZINES_DIR = CONTENT_DIR / "zines"

# Ensure directories exist
POSTS_DIR.mkdir(parents=True, exist_ok=True)
PAGES_DIR.mkdir(parents=True, exist_ok=True)
ZINES_DIR.mkdir(parents=True, exist_ok=True)


def get_post_data(post_path):
    """Load and parse a post file with frontmatter."""
    with open(post_path) as f:
        post = frontmatter.load(f)

    # Convert date string to datetime if needed
    date = post.metadata.get("date", datetime.now())
    if isinstance(date, str):
        try:
            # Handle the format: "2025-02-08 04:36"
            date = datetime.strptime(date, "%Y-%m-%d %H:%M")
        except ValueError:
            try:
                # Fallback for ISO format
                date = datetime.fromisoformat(date)
            except ValueError:
                date = datetime.now()

    content = markdown.markdown(post.content)
    return {
        "title": post.metadata.get("title", ""),
        "date": date,
        "content": content,
        "url": f"/posts/{post_path.stem}",
        **post.metadata,
    }


@app.route("/")
def home():
    """Render the home page."""
    return render_template("index.html")


@app.route("/blog")
def blog():
    """Render the blog page with all posts."""
    posts = []
    for post_path in sorted(POSTS_DIR.glob("*.md"), reverse=True):
        posts.append(get_post_data(post_path))

    return render_template("blog.html", posts=posts)


@app.route("/about")
def about():
    """Render the about page."""
    page_path = PAGES_DIR / "about.md"
    if not page_path.exists():
        return "About page not found", 404

    page_data = get_post_data(page_path)
    return render_page(page_data)


@app.route("/posts/<slug>")
def post(slug):
    """Render an individual post."""
    post_path = POSTS_DIR / f"{slug}.md"
    if not post_path.exists():
        return "Post not found", 404

    post_data = get_post_data(post_path)
    webmentions = db.get_webmentions(f"/posts/{slug}")

    return render_post(post_data, webmentions)


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


if __name__ == "__main__":
    app.run(debug=True)
