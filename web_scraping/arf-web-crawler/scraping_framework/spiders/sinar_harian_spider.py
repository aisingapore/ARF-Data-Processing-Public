from datetime import datetime

import scrapy
from scraping_framework.items import ArticleItem


class SinarHarianSpider(scrapy.Spider):
    """
    Performs a deep crawl of the Sinar Harian website by starting from a
    pre-defined list of main news categories and using the site's internal JSON API
    to handle pagination. This version is robust and handles multiple page layouts
    and dynamic API parameters.
    """

    name = "sinarharian"

    custom_settings = {
        "JOBDIR": f"crawls/{name}",
        "ROBOTSTXT_OBEY": False,
        "CONCURRENT_REQUESTS": 6,
        "DOWNLOAD_DELAY": 2,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 1,
        "AUTOTHROTTLE_MAX_DELAY": 10,
    }

    start_urls = ["https://www.sinarharian.com.my/terkini"]

    ajax_url = "https://www.sinarharian.com.my/ajax/loadMoreArticles"

    def parse(self, response):
        """
        Parses the first page of a category, scrapes its articles, and
        kicks off the API-based pagination with dynamic parameters.
        """
        self.logger.info(f"Parsing initial category page: {response.url}")

        universal_article_selector = """
            .sinarharian-pagination-all-articles .article-title a::attr(href),
            .sinarharian-three-articles-two-columns a.bigTitle::attr(href),
            .sinarharian-pagination-articles .article-title a::attr(href)
        """
        article_links = response.css(universal_article_selector).getall()

        unique_links = {link for link in article_links if "/article/" in link}
        self.logger.info(
            f"Found {len(unique_links)} unique initial article links on this page."
        )
        for link in unique_links:
            yield response.follow(link, callback=self.parse_article)

        offset = response.css(".more-articles-row::attr(data-offset)").get(default="10")
        limit = response.css(".more-articles-row::attr(data-limit)").get(default="10")
        section_id = response.css(".more-articles-row::attr(data-section)").get(
            default="0"
        )
        subsection_id = response.css(".more-articles-row::attr(data-sub-section)").get(
            default="0"
        )

        self.logger.info(
            f"Kicking off API pagination for section {section_id}/{subsection_id} starting at offset {offset}"
        )
        yield scrapy.FormRequest(
            url=self.ajax_url,
            method="POST",
            formdata={
                "sectionId": section_id,
                "subsectionId": subsection_id,
                "widgetLimit": limit,
                "widgetOffset": str(offset),
                "viewHtml": "theme::ajax.load_more_articles",
            },
            callback=self.parse_ajax,
            cb_kwargs={
                "offset": int(offset),
                "limit": int(limit),
                "section_id": section_id,
                "subsection_id": subsection_id,
            },
            dont_filter=True,
        )

    def parse_ajax(self, response, offset, limit, section_id, subsection_id):
        """
        Parses the JSON response from the pagination API and schedules the next call.
        """
        self.logger.info(
            f"Parsing API response for section {section_id}/{subsection_id} at offset: {offset}"
        )

        try:
            data = response.json()
        except Exception:
            self.logger.warning(
                f"Failed to parse JSON from API response for section {section_id}"
            )
            return

        if data.get("error") > 0 or not data.get("articlesHtml", "").strip():
            self.logger.info(
                f"No more articles found for section {section_id} at offset {offset}. Ending pagination."
            )
            return

        html_content = data["articlesHtml"]
        html_selector = scrapy.Selector(text=html_content)
        article_links = html_selector.css(".article-title a::attr(href)").getall()

        if not article_links:
            self.logger.info(
                f"API returned no new links for section {section_id} at offset {offset}."
            )
            return

        self.logger.info(f"Found {len(article_links)} new article links from API.")
        for link in set(article_links):
            if "/article/" in link:
                yield response.follow(link, callback=self.parse_article)

        next_offset = offset + limit
        yield scrapy.FormRequest(
            url=self.ajax_url,
            method="POST",
            formdata={
                "sectionId": section_id,
                "subsectionId": subsection_id,
                "widgetLimit": str(limit),
                "widgetOffset": str(next_offset),
                "viewHtml": "theme::ajax.load_more_articles",
            },
            callback=self.parse_ajax,
            cb_kwargs={
                "offset": next_offset,
                "limit": limit,
                "section_id": section_id,
                "subsection_id": subsection_id,
            },
            dont_filter=True,
        )

    def parse_article(self, response):
        """
        Parses an individual article page to extract data.
        """
        self.logger.info(f"Scraping article content from: {response.url}")

        title = response.css("h1.title::text").get()
        body_paragraphs = response.css("div#articleText p::text").getall()
        body_text = "\n".join(
            paragraph.strip() for paragraph in body_paragraphs
        ).strip()
        published_at_raw = response.css(
            ".byline-date-readingtime .timespan::text"
        ).get()

        if title and body_text:
            item = ArticleItem()
            item["url"] = response.url
            item["language"] = "ms"
            item["title"] = title.strip()
            item["body_text"] = body_text
            item["scraped_at"] = datetime.now().isoformat()

            if published_at_raw:
                item["published_at"] = published_at_raw.strip().split("\n")[0]
            else:
                item["published_at"] = None

            yield item
        else:
            self.logger.warning(f"Could not extract title or body from {response.url}")
