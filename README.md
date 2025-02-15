# voidfemme Website

This repository contains the code for the [voidfemme](https://voidfemme.com) website—a personal space for thoughts, code, and zines created by Rose Proctor. The site is built with Flask, Jinja2 templates, Markdown content, and several IndieWeb features (webmentions, micropub, etc.) plus integrations like a Telegram bot.

This README serves as both an overview of the project and a guide for making future changes and additions.

---

## Table of Contents

- [Project Structure](#project-structure)
- [Installation and Setup](#installation-and-setup)
- [Working with Content](#working-with-content)
  - [Blog Posts](#blog-posts)
  - [Pages](#pages)
  - [Zines](#zines)
  - [Photos](#photos)
- [Theming and Frontend](#theming-and-frontend)
- [Development Workflow](#development-workflow)
- [Telegram Bot & Webhooks](#telegram-bot--webhooks)
- [Database & Webmentions](#database--webmentions)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Additional Resources](#additional-resources)

---

## Project Structure

```
voidfemme/
├── api/
│   ├── config.py         # Application configuration & environment settings
│   ├── app.py            # Main Flask application & route definitions
│   ├── database.py       # Database helper functions (SQLite)
│   ├── telegram_bot.py   # Telegram bot integration & webhook handling
│   └── ...               # Other backend modules and utilities
├── src/
│   ├── posts/            # Markdown files for blog posts
│   ├── pages/            # Markdown files for static pages (e.g. About, Home)
│   ├── zines/            # Markdown/PDF files for digital zines
│   ├── _includes/        # Jinja templates (base, header, footer, etc.)
│   └── static/
│       ├── css/          # CSS files (theme and layout)
│       ├── js/           # JavaScript files (enhancements, dark mode, etc.)
│       ├── fonts/        # Font files (e.g., Playfair Display)
│       ├── images/       # Images for posts (auto-processed paths)
│       └── photos/       # Uploaded photos (subdirectories: original, thumbnail, medium)
└── README.md             # This file
```

---

## Installation and Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yourusername/voidfemme.git
   cd voidfemme
   ```

2. **Create and activate a virtual environment:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```
   *Ensure you have Flask, python-dotenv, Markdown, python-frontmatter, python-slugify, requests, and other required packages installed.*

4. **Configure Environment Variables:**

   Create a `.env` file in the project root with variables like:

   ```dotenv
   FLASK_ENV=development
   TELEGRAM_BOT_TOKEN=your-telegram-bot-token
   ALLOWED_TELEGRAM_USERS=username1,username2
   ```

5. **Database Setup:**

   The application uses SQLite. On first run the necessary tables are created automatically. See `api/config.py` for the database path (`webmentions.db`).

6. **Run the Server:**

   ```bash
   flask run
   ```
   or, if running directly:

   ```bash
   python api/app.py
   ```

   The site should now be accessible at [http://localhost:5000](http://localhost:5000).

---

## Working with Content

### Blog Posts

- **Location:** `src/posts/`
- **Format:** Markdown files with YAML frontmatter. For example:

  ```yaml
  ---
  title: "My New Post"
  date: "2025-02-14 20:04"
  tags: ["tech", "python"]
  ---
  
  Your blog post content in Markdown goes here...
  ```

- **How-to:**
  - Create a new Markdown file in `src/posts/` using a unique filename (this becomes the post’s slug).
  - Use proper YAML frontmatter (include at least a title and date).
  - For images referenced in your Markdown, if you use a relative path (e.g., `![Alt text](image.jpg)`), the backend automatically rewrites the path to `/static/images/posts/{post_slug}/image.jpg`.

### Pages

- **Location:** `src/pages/`
- **Format:** Similar to posts, pages are Markdown files (e.g., `about.md`, `home.md`).
- **Usage:** Static pages like “About” and “Home.”
- **How-to:**
  - Edit existing pages or add new ones. They will be available via `/pages/<slug>`.

### Zines

- **Location:** `src/zines/`
- **Format:** Markdown files (with frontmatter) and associated PDFs.
- **Usage:** Displayed on the `/zines` page with download options.
- **How-to:**
  - Follow the established format in the `src/zines/` folder.
  - Ensure that each zine has metadata (e.g., title, created_at, description, tags) and that the corresponding PDF is stored where the zine manager can locate it.
  - The download route is `/zines/<zine_id>/download`.

### Photos

- **Location:** `src/static/photos/`
- **Subdirectories:**
  - `original/` — Original uploaded files.
  - `thumbnail/` — Square thumbnails (e.g., 300×300).
  - `medium/` — Optimized medium-size images.
- **How-to:**
  - Use the `/photos/new` route to upload new photo posts.
  - Provide a caption, tags, and alt text for each photo.
  - For editing, use the `/photos/<slug>/edit` route.
  - To delete a photo post, use the `/photos/<slug>/delete` route.

---

## Theming and Frontend

- **CSS Customization:**
  - Main styles are located in `src/static/css/`.
  - Theme variables (colors, spacing, fonts) are defined in the `:root` block. Adjust these to change the overall look and feel.
- **Templates:**
  - The base template is `src/_includes/base.html`.
  - Other components (header, footer, etc.) are in `src/_includes/`.
  - Templates use Jinja2 syntax and include blocks like `{% block content %}` for dynamic content.
- **JavaScript Enhancements:**
  - Found in `src/static/js/main.js`.
  - Handles deferred loading, dark mode, lazy loading images, and enhances the webmention form.
- **Adding New Sections:**
  - To add or modify layouts, update the corresponding template in the `_includes` directory and adjust CSS/JS as needed.

---

## Development Workflow

- **Editor:** Use your preferred code editor (VSCode, PyCharm, etc.).
- **Live Reload:** The Flask development server supports live reloading when `FLASK_ENV=development`.
- **Version Control:** Commit changes regularly. Use feature branches for new functionality.
- **Debugging:** Monitor the terminal/log output for errors. Flask debug mode provides detailed error reports.

---

## Telegram Bot & Webhooks

- **Purpose:** The Telegram bot is used for notifications and handling incoming updates.
- **Configuration:**
  - Set your bot token in the `.env` file (`TELEGRAM_BOT_TOKEN`).
  - Configure allowed users with `ALLOWED_TELEGRAM_USERS`.
- **Webhook Endpoint:** `/webhook/telegram` is the endpoint for receiving updates.
- **Testing:**
  - Use the `/webhook/test` and `/webhook/debug` routes to verify that the bot and webhooks are working.
  - Check the logs for detailed information about incoming updates.

---

## Database & Webmentions

- **Database:** The site uses an SQLite database (located at `api/webmentions.db` by default) for storing webmentions and photo post data.
- **Webmentions:**
  - The endpoint `/webmention` accepts incoming webmentions.
  - Validated webmentions are stored in the `webmentions` table.
- **Modifications:**
  - Use the `Database` class (in `api/database.py`) to interact with the database.
  - To modify the schema, update the SQL statements in the initialization scripts.

---

## Deployment

- **Production Server:** For production, use a WSGI server like Gunicorn.
- **Static Files:** Make sure your server is configured to serve static assets from `src/static/`.
- **Environment Variables:** Set `FLASK_ENV=production` and provide any other required environment variables.
- **Database Backup:** Regularly back up your SQLite database.
- **Logging:** Ensure proper logging and error tracking in production.

---

## Troubleshooting

- **Server Errors:**
  - Check the terminal or log files for error messages.
  - Verify that all required packages are installed and that environment variables are set correctly.
- **Template Issues:**
  - Confirm that template file paths in `src/_includes/` are correct.
- **Static File Issues:**
  - Ensure images and other static assets are placed in the proper directories.
- **Webhook/Telegram Issues:**
  - Use the debug endpoints to check webhook functionality.
  - Review the logs for any issues with incoming requests.
- **Database Issues:**
  - If problems arise with the database, consider re-initializing or restoring from a backup.

---

## Additional Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [Markdown Guide](https://www.markdownguide.org/)
- [IndieWeb/Webmention Guidelines](https://indieweb.org/Webmention)
- [Telegram Bot API](https://core.telegram.org/bots/api)

---

*This README is a living document—please update it as the project evolves to keep your workflow and setup instructions current.*

Happy coding!

---

You can adjust and expand this guide as needed to cover new features or changes in your workflow. Enjoy working on voidfemme!
