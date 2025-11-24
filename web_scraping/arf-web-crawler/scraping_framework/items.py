import scrapy


class ArticleItem(scrapy.Item):
    """
    A structured container for scraped article data.
    This defines the schema for news articles.
    """

    url = scrapy.Field()
    language = scrapy.Field()
    title = scrapy.Field()
    body_text = scrapy.Field()
    scraped_at = scrapy.Field()
    published_at = scrapy.Field()


class SearchResultItem(scrapy.Item):
    """
    A structured container for search engine results.
    This will hold the seed URLs we discover.
    """

    keyword = scrapy.Field()
    language = scrapy.Field()
    url = scrapy.Field()
    title = scrapy.Field()
    snippet = scrapy.Field()
    rank = scrapy.Field()
    search_engine = scrapy.Field()
