# --- Core Scrapy Identification ---
BOT_NAME = "scraping_framework"

SPIDER_MODULES = ["scraping_framework.spiders"]

# --- "Good Bot" Behavior Settings ---
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36"
ROBOTSTXT_OBEY = True

# --- Concurrency and Delay Settings ---
DOWNLOAD_DELAY = 3

# --- Crawl Configuration ---
# DEPTH_LIMIT = 4

# --- Optional Settings ---
# Disable cookies (enabled by default)
# Cookies are often not needed for scraping public data and can be used for tracking.
# COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
# TELNETCONSOLE_ENABLED = False


# --- Item Pipeline Configuration ---
ITEM_PIPELINES = {
    # "scraping_framework.pipelines.SaveToCsvPipeline": 300,
    "scraping_framework.pipelines.SaveToJsonlPipeline": 300,
}

# Set settings whose default value is deprecated to a future-proof value
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"

# --- Playwright Settings ---
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
