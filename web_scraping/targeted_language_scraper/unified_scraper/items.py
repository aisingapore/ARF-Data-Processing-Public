import scrapy


class ArticleItem(scrapy.Item):
    """
    A unified item for scraped web articles.
    Combines fields from both 'multi_site_crawler' and 'scraping_framework copy'.
    """

    url = scrapy.Field()
    language = scrapy.Field()
    text = scrapy.Field()
    title = scrapy.Field()
    body_text = scrapy.Field()
    scraped_at = scrapy.Field()
    published_at = scrapy.Field()
    site_name = scrapy.Field()


class PdfItem(scrapy.Item):
    """
    A new, structured item for PDF data, based on the fields
    from your filipino_pdf_spider.py.
    """

    url = scrapy.Field()
    original_url = scrapy.Field()
    filename = scrapy.Field()
    source_page = scrapy.Field()
    size_bytes = scrapy.Field()
    size_mb = scrapy.Field()
    detected_language = scrapy.Field()
    confidence = scrapy.Field()
    text_length = scrapy.Field()
    saved_to = scrapy.Field()


class SearchResultItem(scrapy.Item):
    """
    From 'scraping_framework copy'. This will be used by our
    new 'discover' spider in Stage 1.
    """

    keyword = scrapy.Field()
    url = scrapy.Field()
    title = scrapy.Field()
    snippet = scrapy.Field()
    rank = scrapy.Field()
    search_engine = scrapy.Field()
