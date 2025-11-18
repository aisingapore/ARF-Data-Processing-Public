import argparse
import json
import re
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from lxml import html as lxml_html


class ScraperConfigGenerator:
    """
    Automated pipeline to generate scraper configurations for websites.
    This version includes deep validation by testing selectors
    on a sample article page.
    """

    def __init__(self, min_links=3, min_body_length=100):
        """
        Args:
            min_links: Minimum number of article links to find for validation
            min_body_length: Minimum body text length for validation
        """
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self.min_links = min_links
        self.min_body_length = min_body_length

        # Advanced CMS patterns
        self.cms_patterns = {
            "wordpress": {
                "article_links": [
                    "h2.entry-title a::attr(href)",
                    "h3.entry-title a::attr(href)",
                    "h1.entry-title a::attr(href)",
                    "article h2 a::attr(href)",
                    "article h3 a::attr(href)",
                    ".post-title a::attr(href)",
                    ".entry-header a::attr(href)",
                    "article.post a[rel='bookmark']::attr(href)",
                    ".post .entry-title a::attr(href)",
                    ".hentry h2 a::attr(href)",
                    ".type-post h2 a::attr(href)",
                    ".post-grid article a::attr(href)",
                    ".blog-post a.post-link::attr(href)",
                    ".posts-list .post-item a::attr(href)",
                    "article .post-thumbnail a::attr(href)",
                    ".entry-featured-image-url::attr(href)",
                ],
                "pagination": [
                    "a.next.page-numbers::attr(href)",
                    ".nav-previous a::attr(href)",
                    ".nav-next a::attr(href)",
                    'a[rel="next"]::attr(href)',
                    ".pagination .next::attr(href)",
                    ".wp-pagenavi a.nextpostslink::attr(href)",
                    ".navigation .nav-links a.next::attr(href)",
                    ".nav-links a[rel='next']::attr(href)",
                    'a:contains("Older posts")::attr(href)',
                    'a:contains("Next")::attr(href)',
                    ".older-posts a::attr(href)",
                ],
                "article_title": [
                    "h1.entry-title::text",
                    "h1.post-title::text",
                    "article h1::text",
                    "h1.single-title::text",
                    ".article-title h1::text",
                    "header.entry-header h1::text",
                    'meta[property="og:title"]::attr(content)',
                ],
                "article_body": [
                    '//div[contains(@class, "entry-content")]//p//text()',
                    '//div[contains(@class, "post-content")]//p//text()',
                    '//div[contains(@class, "article-content")]//p//text()',
                    "//article//p//text()",
                    '//div[contains(@class, "entry-content")]//li//text()',
                    '//div[contains(@class, "entry-content")]//blockquote//text()',
                    '//div[contains(@class, "single-content")]//p//text()',
                    '//main[contains(@class, "site-main")]//p//text()',
                ],
                "article_date": [
                    'meta[property="article:published_time"]::attr(content)',
                    'meta[name="publish_date"]::attr(content)',
                    "time::attr(datetime)",
                    "time.entry-date::attr(datetime)",
                    ".entry-date::attr(datetime)",
                    ".post-date::attr(datetime)",
                    ".published::attr(datetime)",
                    "span.posted-on time::attr(datetime)",
                    'meta[property="article:published"]::attr(content)',
                ],
            },
            "drupal": {
                "article_links": [
                    ".node-title a::attr(href)",
                    ".views-field-title a::attr(href)",
                    "article h2 a::attr(href)",
                    ".field-name-title a::attr(href)",
                    ".node-article h2 a::attr(href)",
                ],
                "pagination": [
                    "li.pager-next a::attr(href)",
                    ".pager-next a::attr(href)",
                    'a[rel="next"]::attr(href)',
                    ".pagination a.next::attr(href)",
                ],
                "article_title": [
                    "h1.page-title::text",
                    ".node-title::text",
                    "article h1::text",
                    'meta[property="og:title"]::attr(content)',
                ],
                "article_body": [
                    '//div[contains(@class, "field-type-text-with-summary")]//p//text()',
                    '//div[contains(@class, "field-name-body")]//p//text()',
                    "//article//p//text()",
                    '//div[contains(@class, "node-content")]//p//text()',
                ],
                "article_date": [
                    'meta[property="article:published_time"]::attr(content)',
                    ".submitted time::attr(datetime)",
                    ".field-name-post-date::attr(datetime)",
                    "time::attr(datetime)",
                ],
            },
            "joomla": {
                "article_links": [
                    ".item-title a::attr(href)",
                    ".blog-item h2 a::attr(href)",
                    "article h2 a::attr(href)",
                    ".category-list .list-title a::attr(href)",
                ],
                "pagination": [
                    ".pagination .next a::attr(href)",
                    'a[rel="next"]::attr(href)',
                    ".pagenav .pagenav-next a::attr(href)",
                ],
                "article_title": [
                    "h1.page-header::text",
                    ".item-page h2::text",
                    "article h1::text",
                ],
                "article_body": [
                    '//div[contains(@class, "item-page")]//p//text()',
                    "//article//p//text()",
                    '//div[@itemprop="articleBody"]//p//text()',
                ],
                "article_date": [
                    'time[itemprop="datePublished"]::attr(datetime)',
                    ".create::attr(datetime)",
                    'meta[property="article:published_time"]::attr(content)',
                ],
            },
            "medium": {
                "article_links": [
                    "article h2 a::attr(href)",
                    "div[data-post-id] a::attr(href)",
                    '.streamItem a[data-action="open-post"]::attr(href)',
                ],
                "pagination": [
                    'a:contains("Load more")::attr(href)',
                ],
                "article_title": [
                    "h1::text",
                    'meta[property="og:title"]::attr(content)',
                    "article h1::text",
                ],
                "article_body": [
                    "//article//section//p//text()",
                    '//div[@class="section-content"]//p//text()',
                ],
                "article_date": [
                    'meta[property="article:published_time"]::attr(content)',
                    "time::attr(datetime)",
                ],
            },
            "ghost": {
                "article_links": [
                    ".post-card-title a::attr(href)",
                    "article.post-card a.post-card-content-link::attr(href)",
                    ".post-feed article a::attr(href)",
                ],
                "pagination": [
                    'link[rel="next"]::attr(href)',
                    ".pagination-next::attr(href)",
                    'a[rel="next"]::attr(href)',
                ],
                "article_title": [
                    "h1.post-title::text",
                    ".article-title::text",
                    'meta[property="og:title"]::attr(content)',
                ],
                "article_body": [
                    '//div[contains(@class, "post-content")]//p//text()',
                    "//article//p//text()",
                ],
                "article_date": [
                    "time.post-date::attr(datetime)",
                    'meta[property="article:published_time"]::attr(content)',
                ],
            },
            "generic": {
                "article_links": [
                    "article h2 a::attr(href)",
                    "article h3 a::attr(href)",
                    "article header a::attr(href)",
                    ".post h2 a::attr(href)",
                    ".article h2 a::attr(href)",
                    ".blog-post h2 a::attr(href)",
                    ".entry h2 a::attr(href)",
                    ".post-title a::attr(href)",
                    ".article-title a::attr(href)",
                    ".entry-title a::attr(href)",
                    ".title a::attr(href)",
                    "h2 a::attr(href)",
                    "h3 a::attr(href)",
                    ".card h2 a::attr(href)",
                    ".card-title a::attr(href)",
                    ".grid-item a::attr(href)",
                    ".post-list article a::attr(href)",
                    ".article-list .item a::attr(href)",
                    'article[itemtype*="Article"] a::attr(href)',
                    'div[itemtype*="BlogPosting"] a::attr(href)',
                ],
                "pagination": [
                    'a[rel="next"]::attr(href)',
                    'link[rel="next"]::attr(href)',
                    ".pagination a.next::attr(href)",
                    ".pagination .next a::attr(href)",
                    ".pager .next a::attr(href)",
                    "a.next::attr(href)",
                    ".next-page::attr(href)",
                    'a:contains("Next")::attr(href)',
                    'a:contains("Older")::attr(href)',
                    'a:contains("More")::attr(href)',
                    'a:contains("→")::attr(href)',
                    ".nav-next a::attr(href)",
                    ".navigation-next::attr(href)",
                    'nav a[aria-label="Next"]::attr(href)',
                    ".pagination a:last-child::attr(href)",
                ],
                "article_title": [
                    "h1::text",
                    "article h1::text",
                    "main h1::text",
                    "header h1::text",
                    ".article-title::text",
                    ".post-title::text",
                    ".entry-title::text",
                    ".title h1::text",
                    ".headline::text",
                    'meta[property="og:title"]::attr(content)',
                    'meta[name="title"]::attr(content)',
                    'meta[property="twitter:title"]::attr(content)',
                    'h1[itemprop="headline"]::text',
                ],
                "article_body": [
                    "//article//p//text()",
                    "//main//p//text()",
                    '//div[contains(@class, "content")]//p//text()',
                    '//div[contains(@class, "article")]//p//text()',
                    '//div[contains(@class, "post")]//p//text()',
                    '//div[contains(@class, "entry")]//p//text()',
                    '//div[contains(@class, "body")]//p//text()',
                    '//div[contains(@class, "text")]//p//text()',
                    '//div[@itemprop="articleBody"]//p//text()',
                    "//article//li//text()",
                    "//article//blockquote//text()",
                    '//div[contains(@class, "content")]//li//text()',
                    "//p//text()",
                ],
                "article_date": [
                    'meta[property="article:published_time"]::attr(content)',
                    'meta[property="article:published"]::attr(content)',
                    'meta[name="publish_date"]::attr(content)',
                    'meta[name="date"]::attr(content)',
                    'meta[property="og:updated_time"]::attr(content)',
                    "time::attr(datetime)",
                    'time[itemprop="datePublished"]::attr(datetime)',
                    "time[datetime]::attr(datetime)",
                    ".date::attr(datetime)",
                    ".publish-date::attr(datetime)",
                    ".published::attr(datetime)",
                    ".post-date::attr(datetime)",
                    ".entry-date::attr(datetime)",
                    ".article-date::attr(datetime)",
                    ".date::text",
                    ".published::text",
                    'time[itemprop="datePublished"]::text',
                ],
            },
        }

    def extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain

    def generate_name(self, domain: str) -> str:
        """Generate site name from domain."""
        return domain.split(".")[0]

    def detect_cms(self, html: str) -> str:
        """Detect CMS platform from HTML content."""
        html_lower = html.lower()

        if "wp-content" in html_lower or "wordpress" in html_lower:
            return "wordpress"
        if "drupal.js" in html_lower or "data-drupal-selector" in html_lower:
            return "drupal"
        if "joomla-favicon.svg" in html_lower or "com_content" in html_lower:
            return "joomla"
        if "ghost-search-field" in html_lower or "/ghost/api/" in html_lower:
            return "ghost"
        if 'property="al:android:app_name" content="Medium"' in html_lower:
            return "medium"

        return "generic"

    def needs_javascript(self, html: str) -> bool:
        """Detect if page needs JavaScript rendering."""
        soup = BeautifulSoup(html, "html.parser")
        scripts = soup.find_all("script")
        for script in scripts:
            if script.get("src"):
                src = script["src"].lower()
                if any(
                    framework in src
                    for framework in ["react", "vue", "angular", "next"]
                ):
                    return True
        text_length = len(soup.get_text(strip=True))
        if text_length < 500:
            return True
        return False

    def is_valid_article_url(self, url: str, base_domain: str) -> bool:
        """Check if URL looks like an article (not homepage, category, etc.)."""
        if not url:
            return False

        parsed = urlparse(url)

        if base_domain not in parsed.netloc:
            return False

        path = parsed.path.lower()

        exclude_patterns = [
            "/category/",
            "/tag/",
            "/author/",
            "/page/",
            "/archive/",
            "/search/",
            "/feed/",
            "/wp-json/",
            "/wp-admin/",
            "/wp-content/",
            "/login",
            "/register",
            "/about",
            "/contact",
            "/privacy",
            "/terms",
        ]

        if any(pattern in path for pattern in exclude_patterns):
            return False

        if path in ["", "/"]:
            return False

        return True

    def test_css_selector(
        self, soup: BeautifulSoup, selector: str, base_url: str = None
    ) -> Tuple[bool, int, List]:
        """
        Test a CSS selector and return success status, count, and sample results.
        """
        try:
            test_selector = re.split(r"::(attr|text)", selector)[0]
            elements = soup.select(test_selector)

            if not elements:
                return False, 0, []

            results = []
            if "::attr(href)" in selector:
                attr_name = "href"
                for el in elements[:10]:  # Sample first 10
                    value = el.get(attr_name)
                    if value:
                        if base_url and not value.startswith("http"):
                            value = urljoin(base_url, value)
                        results.append(value)
            elif "::attr" in selector:
                attr_match = re.search(r"::attr\((\w+)\)", selector)
                if attr_match:
                    attr_name = attr_match.group(1)
                    for el in elements[:5]:
                        value = el.get(attr_name)
                        if value:
                            results.append(value)
            elif "::text" in selector:
                for el in elements[:5]:
                    text = el.get_text(strip=True)
                    if text:
                        results.append(text)

            # Fallback if no specific :: part, but elements found
            if not results and elements:
                return True, len(elements), []

            return len(results) > 0, len(results), results

        except Exception as e:
            return False, 0, []

    def test_xpath_selector(
        self, html_content: str, xpath: str
    ) -> Tuple[bool, int, List]:
        """
        Test an XPath selector and return success status, count, and sample results.
        """
        try:
            tree = lxml_html.fromstring(html_content)
            elements = tree.xpath(xpath)

            if not elements:
                return False, 0, []

            results = []
            for el in elements[:20]:  # Sample first 20
                if isinstance(el, str):
                    text = el.strip()
                    if len(text) > 10:  # Meaningful text
                        results.append(text)

            return len(results) > 0, len(results), results

        except Exception as e:
            return False, 0, []

    def find_best_selector(
        self,
        soup: BeautifulSoup,
        html_content: str,
        selector_list: List[str],
        selector_type: str,
        base_url: str = None,
        base_domain: str = None,
    ) -> Tuple[Optional[str], int, List]:
        """
        Find the best working selector from a list with validation.
        Returns: (selector, count, sample_results)
        """
        best_selector = None
        best_count = 0
        best_results = []

        for selector in selector_list:
            if selector.startswith("//"):  # XPath
                success, count, results = self.test_xpath_selector(
                    html_content, selector
                )
            else:  # CSS
                success, count, results = self.test_css_selector(
                    soup, selector, base_url
                )

            if success:
                # Additional validation for article links
                if selector_type == "article_links" and base_domain:
                    valid_results = [
                        r for r in results if self.is_valid_article_url(r, base_domain)
                    ]
                    count = len(valid_results)
                    results = valid_results

                    if count < self.min_links:
                        continue

                # Additional validation for body text
                if selector_type == "article_body":
                    total_length = sum(len(r) for r in results)
                    if total_length < self.min_body_length:
                        continue

                # Keep track of best selector
                if count > best_count:
                    best_selector = selector
                    best_count = count
                    best_results = results

                # Early exit if we found a really good selector
                if selector_type == "article_links" and count >= 10:
                    break
                if (
                    selector_type == "article_body"
                    and sum(len(r) for r in results) >= 500
                ):
                    break

        # Fallback to first selector if none worked
        if not best_selector and selector_list:
            best_selector = selector_list[0]

        return best_selector, best_count, best_results

    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch page content."""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"  Error fetching {url}: {e}")
            return None

    def generate_config(
        self, url: str, analyze_page: bool = True, deep_validation: bool = True
    ) -> Dict:
        """
        Generate scraper configuration for a URL.

        Args:
            url: The URL to analyze
            analyze_page: Whether to fetch and analyze the page
            deep_validation: Whether to test selectors on an actual article page
        """
        domain = self.extract_domain(url)
        name = self.generate_name(domain)

        config = {
            "name": name,
            "allowed_domain": domain,
            "start_url": url,
            "needs_js": False,
            "selectors": {},
            "validation": {},
        }

        if not analyze_page:
            # Quick mode: use generic defaults
            patterns = self.cms_patterns["generic"]
            config["selectors"] = {
                "article_links": patterns["article_links"][0],
                "pagination": patterns["pagination"][0],
                "wait_for": None,
                "article_title": patterns["article_title"][0],
                "article_body": patterns["article_body"][0],
                "article_date": patterns["article_date"][0],
            }
            return config

        # Fetch and analyze the page
        html = self.fetch_page(url)
        if not html:
            print("  ⚠ Could not fetch page, using generic defaults")
            patterns = self.cms_patterns["generic"]
            config["selectors"] = {
                "article_links": patterns["article_links"][0],
                "pagination": patterns["pagination"][0],
                "wait_for": None,
                "article_title": patterns["article_title"][0],
                "article_body": patterns["article_body"][0],
                "article_date": patterns["article_date"][0],
            }
            return config

        soup = BeautifulSoup(html, "html.parser")
        cms = self.detect_cms(html)
        config["needs_js"] = self.needs_javascript(html)

        print(f"  Detected CMS: {cms}")
        if config["needs_js"]:
            print("  ⚠ JavaScript rendering may be required")

        patterns = self.cms_patterns.get(cms, self.cms_patterns["generic"])

        # Find best selectors with validation
        article_links_sel, links_count, sample_links = self.find_best_selector(
            soup, html, patterns["article_links"], "article_links", url, domain
        )
        print(f"  Found {links_count} article links with: {article_links_sel}")

        pagination_sel, pag_count, sample_pag = self.find_best_selector(
            soup, html, patterns["pagination"], "pagination", url
        )
        if pag_count > 0:
            print(f"  Found pagination: {pagination_sel}")
        else:
            print("  ⚠ No pagination found (single page?)")

        config["selectors"] = {
            "article_links": article_links_sel,
            "pagination": pagination_sel,
            "wait_for": None,
            "article_title": None,
            "article_body": None,
            "article_date": None,
        }

        config["validation"] = {
            "article_links_found": links_count,
            "pagination_found": pag_count > 0,
        }

        # Deep validation: test on actual article page
        if deep_validation and sample_links:
            print("  Testing selectors on sample article...")
            test_article_url = sample_links[0]

            article_html = self.fetch_page(test_article_url)
            if article_html:
                article_soup = BeautifulSoup(article_html, "html.parser")

                # Find best selectors for article page
                title_sel, title_count, title_samples = self.find_best_selector(
                    article_soup,
                    article_html,
                    patterns["article_title"],
                    "article_title",
                )

                body_sel, body_count, body_samples = self.find_best_selector(
                    article_soup, article_html, patterns["article_body"], "article_body"
                )

                date_sel, date_count, date_samples = self.find_best_selector(
                    article_soup, article_html, patterns["article_date"], "article_date"
                )

                config["selectors"]["article_title"] = title_sel
                config["selectors"]["article_body"] = body_sel
                config["selectors"]["article_date"] = date_sel

                # Update validation info
                config["validation"].update(
                    {
                        "title_works": title_count > 0,
                        "title_sample": title_samples[0] if title_samples else None,
                        "body_works": body_count > 0,
                        "body_paragraphs": body_count,
                        "body_length": sum(len(s) for s in body_samples),
                        "date_works": date_count > 0,
                        "date_sample": date_samples[0] if date_samples else None,
                        "test_url": test_article_url,
                    }
                )

                print(
                    f"    Title: {'✓' if title_count > 0 else '✗'} ({title_count} found)"
                )
                print(
                    f"    Body: {'✓' if body_count > 0 else '✗'} ({body_count} paragraphs)"
                )
                print(
                    f"    Date: {'✓' if date_count > 0 else '✗'} ({date_count} found)"
                )
            else:
                print("  ⚠ Could not fetch sample article for validation")
        else:
            # Use first match without deep validation
            config["selectors"]["article_title"] = patterns["article_title"][0]
            config["selectors"]["article_body"] = patterns["article_body"][0]
            config["selectors"]["article_date"] = patterns["article_date"][0]

        return config

    def process_urls(
        self,
        urls: List[str],
        analyze_pages: bool = True,
        deep_validation: bool = True,
        delay: float = 1.0,
    ) -> List[Dict]:
        """Process multiple URLs and generate configs."""
        configs = []
        for i, url in enumerate(urls, 1):
            url = url.strip()
            if not url:
                continue
            print(f"\n[{i}/{len(urls)}] Processing: {url}")
            try:
                config = self.generate_config(
                    url, analyze_page=analyze_pages, deep_validation=deep_validation
                )
                configs.append(config)

                # Success indicator
                if config.get("validation"):
                    val = config["validation"]
                    if val.get("article_links_found", 0) >= self.min_links:
                        print(f"  ✓ Config generated successfully")
                    else:
                        print(f"  ⚠ Config generated with warnings (few links found)")
                else:
                    print(f"  ✓ Config generated (basic mode)")

            except Exception as e:
                print(f"  ✗ Error: {e}")
                import traceback

                traceback.print_exc()
                configs.append({"error": True, "url": url, "message": str(e)})

            if i < len(urls):
                time.sleep(delay)
        return configs

    def save_configs(
        self, configs: List[Dict], output_file: str = "scraper_configs.json"
    ):
        """Save configs to JSON file."""
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(configs, f, indent=2, ensure_ascii=False)

        # Print summary
        successful = sum(1 for c in configs if not c.get("error"))
        print(f"\n✓ Saved {len(configs)} configs to {output_file}")
        print(f"  Successful: {successful}")
        print(f"  Failed: {len(configs) - successful}")

        # Print validation summary if available
        validated = [c for c in configs if c.get("validation")]
        if validated:
            print(f"\n  Validation Summary:")
            good_links = sum(
                1
                for c in validated
                if c["validation"].get("article_links_found", 0) >= self.min_links
            )
            good_titles = sum(
                1 for c in validated if c["validation"].get("title_works", False)
            )
            good_bodies = sum(
                1 for c in validated if c["validation"].get("body_works", False)
            )
            good_dates = sum(
                1 for c in validated if c["validation"].get("date_works", False)
            )

            print(f"    Article links working: {good_links}/{len(validated)}")
            print(f"    Titles working: {good_titles}/{len(validated)}")
            print(f"    Bodies working: {good_bodies}/{len(validated)}")
            print(f"    Dates working: {good_dates}/{len(validated)}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate Scrapy config files for a list of URLs."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to a .txt file containing a list of seed URLs.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to save the output site_configs.json file.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay (in seconds) between fetching pages.",
    )
    parser.add_argument(
        "--no-analyze",
        action="store_true",
        help="Quick mode: Use defaults without fetching/analyzing pages.",
    )
    parser.add_argument(
        "--no-deep-validation",
        action="store_true",
        help="Skip testing selectors on actual article pages (faster but less accurate).",
    )
    parser.add_argument(
        "--min-links",
        type=int,
        default=3,
        help="Minimum number of article links required for validation (default: 3).",
    )
    parser.add_argument(
        "--min-body-length",
        type=int,
        default=100,
        help="Minimum body text length for validation (default: 100).",
    )
    args = parser.parse_args()

    # Read URLs from the input file
    print(f"Reading URLs from {args.input}...")
    try:
        with open(args.input, "r") as f:
            urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"ERROR: Input file not found at {args.input}")
        return
    except Exception as e:
        print(f"ERROR: Could not read file: {e}")
        return

    if not urls:
        print("No URLs found in the input file.")
        return

    print(f"Found {len(urls)} URLs to process.")

    # Initialize and run the generator
    generator = ScraperConfigGenerator(
        min_links=args.min_links, min_body_length=args.min_body_length
    )

    analyze = not args.no_analyze
    deep_validation = not args.no_deep_validation

    if not analyze:
        print("Running in quick mode (no page analysis)")
    elif not deep_validation:
        print("Running with basic validation (no article page testing)")
    else:
        print("Running with deep validation (testing on actual article pages)")

    configs = generator.process_urls(
        urls, analyze_pages=analyze, deep_validation=deep_validation, delay=args.delay
    )

    # Save the configs to the specified output file
    generator.save_configs(configs, args.output)

    print("\n" + "=" * 50)
    print(f"Generated {len(configs)} configurations.")
    print("=" * 50)


if __name__ == "__main__":
    main()
