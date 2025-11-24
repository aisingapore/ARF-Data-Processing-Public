from urllib.parse import quote_plus

import scrapy
from scraping_framework.items import SearchResultItem


class BingSearchSpider(scrapy.Spider):
    """
    A spider to discover seed URLs by scraping bing search results.
    This version uses the 'lr' URL parameter to filter results by language.

    How to run:
    1. Edit keywords.txt:
       - First line: lang: <language_code> (e.g., lang: ms, lang: en, lang: ja)
       - Subsequent lines: your keywords
    2. Run the spider:
       scrapy crawl bing_search -a pages=2
    """

    name = "bing_search"

    custom_settings = {
        "JOBDIR": f"crawls/bing_search",
        "ROBOTSTXT_OBEY": False,
        "DOWNLOAD_DELAY": 5,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36",
    }

    base_url = "https://www.bing.com/search?q="

    def start_requests(self):
        """
        Reads language and keywords from a .txt file and generates targeted searches.
        """
        keyword_file = getattr(self, "file", "keywords.txt")
        pages_to_crawl = int(getattr(self, "pages", 1))

        try:
            with open(keyword_file, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            self.logger.error(f"Keyword file not found: '{keyword_file}'.")
            return

        if not lines:
            self.logger.error(f"Keyword file '{keyword_file}' is empty.")
            return

        # Language parsing logic
        language = "en"
        keyword_lines = lines

        if lines and lines[0].lower().startswith("lang:"):
            content_after_lang = lines[0].split(":", 1)[1].strip()
            parts = [p.strip() for p in content_after_lang.split(",") if p.strip()]
            if parts:
                language = parts[0]
                keyword_lines = parts[1:] + lines[1:]
            else:
                keyword_lines = lines[1:]
            self.logger.info(f"Using language filter: '{language}'")
        else:
            self.logger.warning(f"No language specified. Defaulting to '{language}'.")

        full_keyword_string = ",".join(keyword_lines)
        keywords = [k.strip() for k in full_keyword_string.split(",") if k.strip()]

        if not keywords:
            self.logger.error(f"No keywords could be parsed from '{keyword_file}'.")
            return

        self.logger.info(f"Found {len(keywords)} keywords to process.")
        for keyword in keywords:
            search_term = keyword
            self.logger.info(
                f"Starting search for: '{keyword}' in language '{language}'"
            )
            search_url = f"{self.base_url}{quote_plus(search_term)}&setlang={language}&mkt={language}"

            yield scrapy.Request(
                search_url,
                callback=self.parse,
                meta={"playwright": True},
                cb_kwargs={
                    "keyword": keyword,
                    "language": language,
                    "current_page": 1,
                    "pages_to_crawl": pages_to_crawl,
                },
            )

    def parse(self, response, keyword, language, current_page, pages_to_crawl):
        """
        Parses a Bing SERP and yields all found results.
        """
        self.logger.info(
            f"Parsing page {current_page}/{pages_to_crawl} for keyword: '{keyword}'"
        )

        results = response.css("ol#b_results > li.b_algo")

        if not results:
            self.logger.warning(
                f"No search results found on page {current_page} for keyword '{keyword}'."
            )

        for i, result in enumerate(results):
            item = SearchResultItem()
            item["keyword"] = keyword
            item["language"] = language
            item["search_engine"] = "Bing"
            item["rank"] = i + 1 + ((current_page - 1) * 10)
            item["title"] = result.css("h2 a::text").get()
            item["url"] = result.css("h2 a::attr(href)").get()
            item["snippet"] = "".join(
                result.css(".b_caption p ::text").getall()
            ).strip()

            if item["url"] and item["title"]:
                yield item

        if current_page < pages_to_crawl:
            next_page = response.css("a.sb_pagN::attr(href)").get()
            if next_page:
                yield response.follow(
                    next_page,
                    callback=self.parse,
                    meta={"playwright": True},
                    cb_kwargs={
                        "keyword": keyword,
                        "language": language,
                        "current_page": current_page + 1,
                        "pages_to_crawl": pages_to_crawl,
                    },
                )
