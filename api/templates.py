from flask import render_template
from datetime import datetime


def render_post(post_data, webmentions=None):
    """Render a blog post with webmentions."""
    return render_template(
        "post.html",
        title=post_data["title"],
        content=post_data["content"],
        date=post_data["date"],
        webmentions=webmentions or [],
        page_url=post_data["url"],
    )


def render_page(page_data):
    """Render a static page."""
    return render_template(
        "page.html",
        title=page_data["title"],
        content=page_data["content"],
        page_url=page_data["url"],
    )
