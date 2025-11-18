from urllib.parse import parse_qs, urlparse

import scrapy
from scrapy.exceptions import CloseSpider

from ..items import SearchResultItem


class DiscoverSpider(scrapy.Spider):
    """
    This spider finds seed URLs by scraping DuckDuckGo.
    It takes comma-separated search terms and a max URL count.

    Usage:
    scrapy crawl discover -a seed_terms="Filipino news,Tagalog articles" -a max_urls=10
    """

    name = "discover"

    def __init__(self, *args, **kwargs):
        super(DiscoverSpider, self).__init__(*args, **kwargs)

        self.seed_terms = kwargs.get("seed_terms")
        if not self.seed_terms:
            raise CloseSpider(
                "Missing 'seed_terms' argument. (e.g., -a seed_terms='term1,term2')"
            )

        self.max_urls = int(kwargs.get("max_urls", 20))

        self.found_urls = set()

        self.logger.info(
            f"DiscoverSpider initialized. Target: {self.max_urls} URLs for terms: {self.seed_terms}"
        )

    def start_requests(self):
        """
        Generates the initial search requests for DuckDuckGo.
        """
        base_url = "https://html.duckduckgo.com/html/?q="

        for term in self.seed_terms.split(","):
            term = term.strip()
            if not term:
                continue

            search_url = base_url + term
            self.logger.info(f"Searching for: {term} at {search_url}")

            yield scrapy.Request(
                search_url, callback=self.parse, meta={"keyword": term}
            )

    def parse(self, response):
        """
        Parses the DuckDuckGo results page.
        """
        keyword = response.meta["keyword"]

        for i, result in enumerate(response.css(".result")):

            if len(self.found_urls) >= self.max_urls:
                self.logger.info(
                    f"Hit max URL limit of {self.max_urls}. Stopping crawl."
                )
                return

            raw_url = result.css(".result__url::attr(href)").get()
            if not raw_url:
                continue

            parsed_url = urlparse(raw_url)
            real_url = parse_qs(parsed_url.query).get("uddg", [None])[0]

            if not real_url:
                continue

            if real_url not in self.found_urls:
                self.found_urls.add(real_url)

                item = SearchResultItem()
                item["keyword"] = keyword
                item["url"] = real_url
                item["title"] = result.css(".result__title *::text").get("").strip()
                item["snippet"] = result.css(".result__snippet *::text").get("").strip()
                item["rank"] = i + 1
                item["search_engine"] = "DuckDuckGo"

                self.logger.info(f"Found URL #{len(self.found_urls)}: {real_url}")
                yield item
