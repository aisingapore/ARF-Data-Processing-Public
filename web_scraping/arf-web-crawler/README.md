# Modular Web Scraping Framework (ARF-WEB-CRAWLER)

This is a modular web scraping framework built on top of the powerful Scrapy library. It is designed for targeted scraping, allowing developers to quickly create new spiders for different websites while reusing a core set of data processing tools.

## 1. Architecture Overview

The framework is built on the principle of Separation of Concerns. The core logic is stable and reusable, while the site-specific scraping rules are isolated in their own components.

| Component | Location     | Role & Reusability                                                                                                                                                                                        |
| --------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Spider    | spiders/     | **Customized.** Contains the site-specific logic: where to start, how to find article links, and how to extract data from a page. You will create a new spider for each new website you want to scrape.   |
| Item      | items.py     | **Semi-Reusable.** Defines the structure (schema) of the data you want to collect (e.g., ArticleItem). You only create a new Item when you are scraping a fundamentally new category of data.             |
| Pipeline  | pipelines.py | **Highly Reusable.** These are generic data processing tools that clean, validate, and save your data. The SaveToJsonlPipeline, for example, will work for any Item from any spider without modification. |
| Settings  | settings.py  | **Project Control Panel.** This file configures the global behavior of the scraper, such as setting politeness delays and activating your chosen pipelines.                                               |

## 2. Onboarding & Installation

Follow these steps to set up your development environment and install all necessary dependencies.

### Prerequisites

- **Git:** To clone the repository.
- **Conda / Miniconda:** To manage the Python environment.

### Step-by-Step Installation

#### Clone the Repository:

Open your terminal, navigate to the directory where you want to store the project, and run:

```bash
git clone https://github.com/aisingapore/ARF-Data-Processing-Public.git
cd web_scraping/arf-web-crawler
```

#### Create and Activate the Conda Environment:

This command creates an isolated Python 3.13 environment named scraper_env.

```bash
conda create -n scraper_env python=3.13 -y
conda activate scraper_env
```

Your terminal prompt should now be prefixed with `(scraper_env)`.

#### Install Dependencies with uv:

We use uv for fast package management. First, install uv itself, then use it to install all project dependencies from the pyproject.toml file.

```bash
pip install uv
```

You are now ready to run the scraper.

## 3. How to Run the Scraper

All commands must be run from the project's root directory (the folder containing scrapy.cfg).

Example:
To run the existing spider for sinarharian.com.my:

```bash
uv run scrapy crawl sinarharian
```

### Expected Output:

You will see logs in your terminal showing the spider's progress as it discovers categories and scrapes articles. Upon completion, a new file named `sinarharian_output.jsonl` will be created in the project root, containing all the scraped data.

## 4. How to Create a New Spider (Your Use Case)

This is the main workflow for targeting a new website.

### Step 1: The Detective Work (Analyze Your Target)

Before you write any code, you must investigate the target website.

1. **Identify Target Pages:** Determine the URLs of the category pages you want to start from (e.g., https://examplenews.com/politics, https://examplenews.com/sports).

2. **Find Article Links:** On a category page, use your browser's "Inspect Element" tool to find a robust CSS selector that uniquely identifies the links to individual articles.

3. **Analyze Pagination:** Scroll to the bottom of the category page.

   - If there's a simple "Next" button with an href link, note its selector.
   - If it loads more articles automatically or via a button without a link, open the "Network" tab in your browser's developer tools, click the button, and look for an XHR or Fetch request. This is the API call you will need to mimic. Note its URL and any parameters.

4. **Analyze an Article Page:** Open a sample article. Use "Inspect Element" to find the CSS selectors for each piece of data you want (e.g., the title, author, publication date, and body text).

### Step 2: Define Your Data Structure (The Item)

Open `scraping_framework/items.py`.

Decide if an existing Item (like `ArticleItem`) fits your needs.

If you are scraping a new type of data (e.g., real estate listings), create a new Item class:

```python
# in scraping_framework/items.py
import scrapy

class RealEstateItem(scrapy.Item):
    url = scrapy.Field()
    address = scrapy.Field()
    price = scrapy.Field()
    num_bedrooms = scrapy.Field()
    scraped_at = scrapy.Field()
```

### Step 3: Create the New Spider

Create a new file in the `scraping_framework/spiders/` directory (e.g., `my_new_site_spider.py`).

Use the template below as a starting point. Copy and paste it into your new file.

Fill in the `[TODO]` sections with the information you gathered in Step 1.

#### Spider Template

```python
import scrapy
from datetime import datetime
# [TODO] Import the correct Item from your items.py file
from scraping_framework.items import ArticleItem

class MyNewSpider(scrapy.Spider):
    # [TODO] 1. Set a unique name for your spider
    name = "my_new_site"

    # [TODO] 2. Add the starting category page URLs
    start_urls = [
        'https://examplenews.com/politics',
        'https://examplenews.com/sports',
    ]

    def parse(self, response):
        """
        Parses a category page, extracts article links, and handles pagination.
        """
        self.logger.info(f"Parsing category page: {response.url}")

        # [TODO] 3. Replace with the selector for article links on a category page
        article_links = response.css('div.article-card a.headline::attr(href)').getall()
        for link in article_links:
            yield response.follow(link, callback=self.parse_article)

        # [TODO] 4. Add your pagination logic here (choose one)

        # --- Option A: For simple "Next Page" links ---
        next_page = response.css('a.next-page::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

        # --- Option B: For JavaScript/API pagination (more advanced) ---
        # (This part requires custom logic based on your findings from Step 1)

    def parse_article(self, response):
        """
        Parses an individual article page to extract data.
        """
        self.logger.info(f"Scraping article: {response.url}")

        # [TODO] 5. Replace these selectors with the ones for your target article page
        title = response.css('h1.main-title::text').get()
        body_text = response.css('div.article-content p::text').getall()
        published_date = response.css('span.publish-date::text').get()

        # Create and populate the Item
        if title and body_text:
            # [TODO] 6. Make sure you are creating an instance of the correct Item
            item = ArticleItem()
            item['url'] = response.url
            item['title'] = title.strip()
            item['body_text'] = "\n".join(p.strip() for p in body_text).strip()
            item['published_at'] = published_date.strip() if published_date else None
            item['scraped_at'] = datetime.now().isoformat()

            yield item
```

### Step 4: Configure the Pipeline

Open `scraping_framework/settings.py`.

Find the `ITEM_PIPELINES` dictionary.

Ensure your desired pipeline (e.g., `SaveToJsonlPipeline`) is active. You can have multiple active pipelines.

```python
ITEM_PIPELINES = {
   "scraping_framework.pipelines.SaveToJsonlPipeline": 300,
}
```

### Step 5: Run Your New Spider

Go to your terminal (in the project root) and run the crawl command using the unique name you set in your spider.

```bash
uv run scrapy crawl my_new_site
```
