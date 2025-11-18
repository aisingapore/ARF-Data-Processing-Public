# -----------------------------------------------------------------------------
# CORE PROJECT SETTINGS
# -----------------------------------------------------------------------------

# New bot and module names for our unified project
BOT_NAME = "unified_scraper"
SPIDER_MODULES = ["unified_scraper.spiders"]
NEWSPIDER_MODULE = "unified_scraper.spiders"

# -----------------------------------------------------------------------------
# CRAWLER "POLITENESS" & ANTI-BAN SETTINGS
# -----------------------------------------------------------------------------
#
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
ROBOTSTXT_OBEY = False
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 30
AUTOTHROTTLE_TARGET_CONCURRENCY = 8.0
CONCURRENT_REQUESTS_PER_DOMAIN = 8
DOWNLOAD_DELAY = 0


# -----------------------------------------------------------------------------
# PLAYWRIGHT & DYNAMIC CONTENT SETTINGS
# -----------------------------------------------------------------------------

DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

PLAYWRIGHT_PAGE_SETTINGS = {
    "default_timeout": 60 * 1000,
}
PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "timeout": 60000,
}


# -----------------------------------------------------------------------------
# 4. ITEM PIPELINES
# -----------------------------------------------------------------------------
ITEM_PIPELINES = {
    "unified_scraper.pipelines.PerSiteJsonLinePipeline": 300,
    "unified_scraper.pipelines.SaveToJsonlPipeline": 301,
}

# -----------------------------------------------------------------------------
# 5. OTHER BEST-PRACTICE SETTINGS (MERGED)
# -----------------------------------------------------------------------------

DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]
COOKIES_ENABLED = True
DOWNLOAD_TIMEOUT = 60
REDIRECT_ENABLED = True
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
FEED_EXPORT_ENCODING = "utf-8"
LOG_LEVEL = "INFO"

# -----------------------------------------------------------------------------
# 6. NEW FRAMEWORK FEATURES (OUR PLAN)
# -----------------------------------------------------------------------------

# Setting for the stop/resume feature.
# We will override the path from the command line.
JOBDIR = None

# We can set a default crawl depth, which can be overridden
# by the spider if needed.
# DEPTH_LIMIT = 10
