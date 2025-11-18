import json
from datetime import datetime
from pathlib import Path

import scrapy
from scrapy.exceptions import CloseSpider
from scrapy_playwright.page import PageMethod

from ..core.language_service import LanguageService
from ..items import ArticleItem


class MasterSpider(scrapy.Spider):
    name = "master"

    def __init__(self, *args, **kwargs):
        """
        Initialize the spider and accept all arguments from run.py.
        This is now responsible for loading the site_config_file.
        """
        super(MasterSpider, self).__init__(*args, **kwargs)

        self.language_key = kwargs.pop("language", None)
        self.site_config_path = kwargs.pop("site_config_file", None)
        lang_file_arg = kwargs.pop("language_file", None)
        cache_dir_arg = kwargs.pop("model_cache_dir", None)

        if not self.language_key:
            raise CloseSpider(
                "Missing 'language' argument. (e.g., -a language=filipino)"
            )
        if not self.site_config_path:
            raise CloseSpider("Missing 'site_config_file' argument.")
        if not lang_file_arg or not cache_dir_arg:
            raise CloseSpider("Missing 'language_file' or 'model_cache_dir' arguments.")

        try:
            self.lang_service = LanguageService(
                language_file=lang_file_arg, model_cache_dir=cache_dir_arg
            )
        except Exception as e:
            raise CloseSpider(f"Failed to initialize LanguageService: {e}")

        config = self.lang_service.get_config(self.language_key)
        self.target_codes = config["glotlid_codes"]

        self.logger.info(
            f"MasterSpider initialized for language: '{self.language_key}'"
        )
        self.logger.info(
            f"Will validate text against GlotLID codes: {self.target_codes}"
        )

        self.site_configs = []
        config_path = Path(self.site_config_path)
        try:
            self.logger.info(f"Loading site configs from {config_path.resolve()}")
            with open(config_path, "r") as f:
                self.site_configs = json.load(f)
            self.logger.info(
                f"Successfully loaded {len(self.site_configs)} site configs."
            )
        except FileNotFoundError:
            self.logger.error(f"Config file not found at {config_path.resolve()}")
            self.logger.error(
                "This file is created by Stage 2 of the 'run.py web' command."
            )

        except json.JSONDecodeError:
            self.logger.error(f"Error decoding JSON from {config_path.resolve()}")

    async def start(self):

        if not self.site_configs:
            self.logger.warning("No site configs were loaded. Spider will close.")
            return

        for config in self.site_configs:
            start_url = config.get("start_url")
            if not start_url:
                self.logger.warning(
                    f"Skipping config with missing 'start_url': {config.get('name')}"
                )
                continue

            meta_data = {"config": config, "language": self.language_key}

            if config.get("needs_js", False):
                meta_data["playwright"] = True
                if config.get("selectors", {}).get("wait_for"):
                    wait_selector = config["selectors"]["wait_for"]
                    meta_data["playwright_page_methods"] = [
                        PageMethod("wait_for_selector", wait_selector, timeout=15000)
                    ]

                yield scrapy.Request(
                    start_url,
                    callback=self.parse,
                    meta=meta_data,
                    errback=self.errback_handle,
                )
            else:
                yield scrapy.Request(
                    start_url,
                    callback=self.parse,
                    meta=meta_data,
                    errback=self.errback_handle,
                )

    def parse(self, response):
        config = response.meta["config"]
        language = response.meta["language"]
        selectors = config["selectors"]

        article_links = response.css(selectors["article_links"]).getall()
        self.logger.info(
            f"[{config['name']}] Found {len(article_links)} article links on {response.url}"
        )

        for link in article_links:
            yield response.follow(
                link,
                callback=self.parse_article,
                meta={"config": config, "language": language},
            )

        if selectors.get("pagination"):
            next_page_url = response.css(selectors["pagination"]).get()

            if next_page_url and not next_page_url.startswith("javascript:"):

                self.logger.info(f"[{config['name']}] Found next page: {next_page_url}")

                if config.get("needs_js", False):
                    meta_data = {
                        "config": config,
                        "language": language,
                        "playwright": True,
                    }
                    if config.get("selectors", {}).get("wait_for"):
                        wait_selector = config["selectors"]["wait_for"]
                        meta_data["playwright_page_methods"] = [
                            PageMethod(
                                "wait_for_selector", wait_selector, timeout=15000
                            )
                        ]
                    yield response.follow(
                        next_page_url,
                        callback=self.parse,
                        meta=meta_data,
                        errback=self.errback_handle,
                    )
                else:
                    yield response.follow(
                        next_page_url,
                        callback=self.parse,
                        meta={"config": config, "language": language},
                        errback=self.errback_handle,
                    )

            elif next_page_url:
                self.logger.debug(
                    f"[{config['name']}] Ignored invalid pagination link: {next_page_url}"
                )

    def validate_language(self, text):
        """
        Passes the text to our central LanguageService for validation.
        """
        is_target, detected_lang, confidence = self.lang_service.validate(
            text, self.target_codes
        )

        return is_target, detected_lang, confidence

    def parse_article(self, response):
        config = response.meta["config"]
        language_key = response.meta["language"]
        selectors = config["selectors"]

        title = response.css(selectors["article_title"]).get()
        body_paragraphs = response.xpath(selectors["article_body"]).getall()
        published_at = response.css(selectors["article_date"]).get()

        body_text = "\n".join(p.strip() for p in body_paragraphs if p.strip())

        full_text = ""
        if title:
            full_text = title.strip()
        if body_text:
            full_text += "\n\n" + body_text

        if not full_text:
            self.logger.debug(f"No text found on {response.url}")
            return

        is_target_lang, detected_lang, confidence = self.validate_language(full_text)

        if not is_target_lang:
            self.logger.info(
                f"✗ SKIPPING: Article language ({detected_lang}) "
                f"not target ({language_key}). URL: {response.url}"
            )
            return

        self.logger.info(
            f"✓ VALIDATED: Article language ({detected_lang}, conf: {confidence:.2f}) "
            f"is target ({language_key}). URL: {response.url}"
        )

        item = ArticleItem()
        item["site_name"] = config["name"]
        item["url"] = response.url
        item["language"] = detected_lang
        item["scraped_at"] = datetime.now().isoformat()
        item["published_at"] = published_at.strip() if published_at else None

        item["title"] = title.strip() if title else None
        item["body_text"] = body_text
        item["text"] = full_text

        yield item

    async def errback_handle(self, failure):
        request = failure.request
        config_name = request.meta.get("config", {}).get("name", "Unknown")
        self.logger.error(f"Request failed for {config_name} at {request.url}")
        self.logger.error(f"Failure details: {failure.value}")
