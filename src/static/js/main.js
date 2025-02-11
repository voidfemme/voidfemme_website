// Only execute if JavaScript is enabled
document.documentElement.classList.add("js-enabled");

// Webmention form enhancement
const enhanceWebmentionForm = () => {
  const form = document.querySelector(".webmention-form");
  if (!form) return;

  // Create status element
  const status = document.createElement("div");
  status.className = "webmention-status";
  form.appendChild(status);

  // Show status message
  const showStatus = (message, isError = false) => {
    status.textContent = message;
    status.style.background = isError
      ? "var(--primary-color)"
      : "var(--accent-color)";
    status.classList.add("visible");
    setTimeout(() => status.classList.remove("visible"), 3000);
  };

  // Enhanced form submission
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const sourceUrl = form.querySelector('[name="source"]').value;
    const targetUrl = form.querySelector('[name="target"]').value;

    try {
      const response = await fetch("/webmention", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ source: sourceUrl, target: targetUrl }),
      });

      if (!response.ok) throw new Error("Submission failed");

      showStatus("Webmention sent successfully!");
      form.reset();
    } catch (error) {
      showStatus("Failed to send webmention. Please try again.", true);
    }
  });
};

// Lazy loading images
const enhanceImages = () => {
  const images = document.querySelectorAll("img[data-src]");

  const imageObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const img = entry.target;
        img.src = img.dataset.src;
        img.removeAttribute("data-src");
        observer.unobserve(img);
      }
    });
  });

  images.forEach((img) => imageObserver.observe(img));
};

// Dark mode toggle (if user prefers)
const enhanceDarkMode = () => {
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)");
  const toggleDark = (e) => {
    document.documentElement.classList.toggle("dark-mode", e.matches);
  };

  prefersDark.addEventListener("change", toggleDark);
  toggleDark(prefersDark);
};

// Initialize enhancements when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  enhanceWebmentionForm();
  enhanceImages();
  enhanceDarkMode();
});
