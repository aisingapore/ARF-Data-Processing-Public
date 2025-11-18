import hashlib
import io
import os
import re
import traceback
from urllib.parse import urljoin, urlparse

import scrapy
from scrapy.exceptions import CloseSpider
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from ..items import PdfItem

try:
    import PyPDF2

    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    PyPDF2 = None

try:
    from scrapy_playwright.page import PageMethod

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    PageMethod = None


class BasePdfLanguageSpider(CrawlSpider):
    """
    This is the base class for our PDF language spiders.
    It contains all shared logic for CRAWLING and PDF EXTRACTION.

    It no longer contains any language detection logic itself.

    A child spider MUST:
    1. Define 'name', 'download_dir', 'target_language_name'.
    2. Implement the 'detect_language(self, text)' method.
    3. Initialize the 'stats_counter' dictionary.
    """

    download_dir = "downloaded_pdfs"
    target_language_name = "Unknown"
    rules = (
        Rule(
            LinkExtractor(deny_extensions=["pdf"]),
            callback="parse_page",
            follow=True,
            process_request="use_playwright_for_google_sites",
        ),
    )

    def __init__(
        self,
        seed_file=None,
        domain=None,
        max_depth=5,
        use_playwright=True,
        *args,
        **kwargs,
    ):

        super(BasePdfLanguageSpider, self).__init__(*args, **kwargs)

        self.custom_settings = {}

        if seed_file:
            try:
                with open(seed_file, "r") as f:
                    self.start_urls = [url.strip() for url in f if url.strip()]
            except FileNotFoundError:
                self.logger.error(f"ERROR: seed_file not found at {seed_file}")
                raise CloseSpider(f"Seed file not found: {seed_file}")
        else:
            self.logger.error(
                "Missing 'seed_file' argument. e.g., -a seed_file=urls.txt"
            )
            raise CloseSpider("Missing seed_file argument")

        if domain:
            self.allowed_domains = [domain]
        else:
            self.allowed_domains = list(
                set(urlparse(url).netloc for url in self.start_urls)
            )

        if max_depth:
            self.custom_settings["DEPTH_LIMIT"] = int(max_depth)

        self.use_playwright = use_playwright and PLAYWRIGHT_AVAILABLE
        if not self.use_playwright and use_playwright:
            self.logger.warning("Playwright dependencies not available.")

        if not PYPDF2_AVAILABLE:
            self.logger.error("PyPDF2 is not installed. PDF text extraction will fail.")
            raise CloseSpider("Missing required PyPDF2 dependency.")

        os.makedirs(self.download_dir, exist_ok=True)

        self.logger.info(f"Starting crawl on {len(self.start_urls)} seed URLs")
        self.logger.info(f"Allowed domains: {self.allowed_domains}")
        self.logger.info(f"PDFs will be saved to: {self.download_dir}")

        if not hasattr(self, "stats_counter"):
            self.stats_counter = {
                "pdfs_found": 0,
                "pdfs_downloaded": 0,
                "target_language_pdfs": 0,
                "other_language_pdfs": 0,
                "languages_detected": {},
            }

    def use_playwright_for_google_sites(self, request, response):
        if self.use_playwright and "sites.google.com" in request.url:
            request.meta["playwright"] = True
            request.meta["playwright_include_page"] = True
            request.meta["playwright_page_methods"] = [
                PageMethod("wait_for_timeout", 3000),
                PageMethod("wait_for_load_state", "networkidle"),
            ]
        return request

    def parse_page(self, response):
        """
        Parse each page and extract PDF links
        """
        try:
            content_type = response.headers.get("Content-Type", b"").decode().lower()

            if "pdf" in content_type or response.body.startswith(b"%PDF"):
                self.logger.info(f"Direct PDF download detected: {response.url}")
                yield from self.process_pdf(response)
                return

            if "html" not in content_type and "text" not in content_type:
                return

            pdf_links = set()
            pdf_links.update(response.css('a[href$=".pdf"]::attr(href)').getall())
            pdf_links.update(
                response.xpath('//a[contains(@href, ".pdf")]/@href').getall()
            )
            pdf_links.update(
                response.xpath(
                    '//a[contains(text(), "PDF") or contains(text(), "pdf")]/@href'
                ).getall()
            )
            pdf_links.update(
                response.xpath('//a[contains(@href, "/file")]/@href').getall()
            )
            pdf_links.update(response.xpath("//a[@download]/@href").getall())

            iframes = response.xpath("//iframe/@src").getall()
            for iframe_src in iframes:
                if "drive.google.com" in iframe_src:
                    direct_link = self.convert_gdrive_to_direct(iframe_src)
                    if direct_link:
                        pdf_links.add(direct_link)

            for pdf_url in pdf_links:
                full_url = urljoin(response.url, pdf_url)
                if full_url.startswith("mailto:") or full_url.startswith("javascript:"):
                    self.logger.debug(f"Ignored non-HTTP link: {full_url[:50]}...")
                    continue

                is_potential_pdf = (
                    full_url.lower().endswith(".pdf")
                    or ".pdf" in full_url.lower()
                    or full_url.endswith("/file")
                    or full_url.endswith("/download")
                    or "/download/" in full_url.lower()
                    or "drive.google.com" in full_url
                )

                if not is_potential_pdf:
                    continue

                self.stats_counter["pdfs_found"] += 1

                needs_playwright = (
                    "drive.google.com" in full_url
                    or "dropbox.com" in full_url
                    or full_url.endswith("/file")
                    or full_url.endswith("/download")
                )

                request_meta = {
                    "source_page": response.url,
                    "pdf_url": full_url,
                    "handle_httpstatus_list": [302, 303, 307, 308],
                }

                if needs_playwright and self.use_playwright:
                    request_meta["playwright"] = True
                    request_meta["playwright_include_page"] = True
                    request_meta["playwright_page_methods"] = [
                        PageMethod("wait_for_load_state", "networkidle"),
                    ]

                yield scrapy.Request(
                    full_url,
                    callback=self.process_pdf,
                    meta=request_meta,
                    dont_filter=True,
                    errback=self.handle_error,
                )
        except Exception as e:
            self.logger.error(f"Error parsing page {response.url}: {e}")

    def convert_gdrive_to_direct(self, url):
        patterns = [
            r"/file/d/([a-zA-Z0-9_-]+)",
            r"id=([a-zA-Z0-9_-]+)",
            r"/open\?id=([a-zA-Z0-9_-]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                file_id = match.group(1)
                return f"https://drive.google.com/uc?export=download&id={file_id}"
        return None

    def extract_text_from_pdf(self, pdf_content):
        if not PYPDF2_AVAILABLE:
            return ""
        try:
            pdf_file = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            max_pages = min(10, len(pdf_reader.pages))
            for page_num in range(max_pages):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
            return text
        except Exception as e:
            self.logger.debug(f"PyPDF2 extraction failed: {e}")
            try:
                sample = pdf_content[:100000].decode("latin-1", errors="ignore")
                return sample
            except Exception as e:
                self.logger.error(f"Text extraction failed: {e}")
                return ""

    def get_safe_filename(self, url):
        try:
            parsed = urlparse(url)
            path = parsed.path
            if path.endswith("/file"):
                path_parts = [p for p in path.split("/") if p and p != "file"]
                filename = path_parts[-1] + ".pdf" if path_parts else "document.pdf"
            else:
                filename = os.path.basename(path)

            if not filename or filename == ".pdf":
                path_parts = [p for p in parsed.path.split("/") if p and p != "file"]
                base_name = path_parts[-1][:50] if path_parts else "document"
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                filename = f"{base_name}_{url_hash}.pdf"

            if not filename.lower().endswith(".pdf"):
                filename += ".pdf"

            filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
            filename = filename.strip()

            filepath = os.path.join(self.download_dir, filename)
            counter = 1
            base, ext = os.path.splitext(filename)
            while os.path.exists(filepath):
                filename = f"{base}_{counter}{ext}"
                filepath = os.path.join(self.download_dir, filename)
                counter += 1

            return filename
        except Exception as e:
            self.logger.error(f"Error creating filename for {url}: {e}")
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            return f"error_{url_hash}.pdf"

    def handle_error(self, failure):
        self.logger.error(f"Failed to download: {failure.request.url}")
        self.logger.error(f"Error: {failure.value}")

    def detect_language(self, text):
        """
        This is an abstract method.
        The child spider (e.g., LanguagePdfSpider) MUST implement
        this and return (bool is_target, str detected_lang).
        """
        raise NotImplementedError(
            "Child spider must implement 'detect_language' method."
        )

    def process_pdf(self, response):
        try:
            content_type = response.headers.get("Content-Type", b"").decode().lower()
            is_pdf_url = (
                response.url.lower().endswith(".pdf") or ".pdf" in response.url.lower()
            )
            is_pdf_content = "pdf" in content_type

            if (
                not is_pdf_url
                and not is_pdf_content
                and not response.body.startswith(b"%PDF")
            ):
                self.logger.warning(
                    f"Not a PDF: {response.url} (content-type: {content_type})"
                )
                return

            if not response.body or len(response.body) < 100:
                self.logger.warning(f"Empty or too small response from: {response.url}")
                return

            if not response.body.startswith(b"%PDF"):
                self.logger.debug(
                    f"Invalid PDF file (missing PDF header): {response.url}"
                )
                return

            self.stats_counter["pdfs_downloaded"] += 1
            text_content = self.extract_text_from_pdf(response.body)

            if not text_content or len(text_content.strip()) < 100:
                self.logger.warning(
                    f"Could not extract enough text from PDF: {response.url}"
                )
                return

            is_target, lang_info = self.detect_language(text_content)

            detected_lang = lang_info.get("language", "unknown")
            confidence = lang_info.get("confidence", 0)

            lang_key = detected_lang
            if lang_key not in self.stats_counter["languages_detected"]:
                self.stats_counter["languages_detected"][lang_key] = 0
            self.stats_counter["languages_detected"][lang_key] += 1

            if is_target:
                self.stats_counter["target_language_pdfs"] += 1
                status = f"✓ {self.target_language_name.upper()}"
            else:
                self.stats_counter["other_language_pdfs"] += 1
                status = f"✗ NOT {self.target_language_name.upper()}"

            self.logger.info(
                f"{status} PDF (lang: {detected_lang}, conf: {confidence:.2f}): {response.url}"
            )

            if is_target:
                filename = self.get_safe_filename(
                    response.meta.get("pdf_url", response.url)
                )
                filepath = os.path.join(self.download_dir, filename)

                with open(filepath, "wb") as f:
                    f.write(response.body)

                item = PdfItem()
                item["url"] = response.url
                item["original_url"] = response.meta.get("pdf_url")
                item["filename"] = filename
                item["source_page"] = response.meta.get("source_page")
                item["size_bytes"] = len(response.body)
                item["size_mb"] = round(len(response.body) / (1024 * 1024), 2)
                item["detected_language"] = detected_lang
                item["confidence"] = confidence
                item["text_length"] = len(text_content)
                item["saved_to"] = filepath
                yield item

        except Exception as e:
            self.logger.error(f"Error processing PDF {response.url}: {e}")
            self.logger.debug(traceback.format_exc())

    def closed(self, reason):
        self.logger.info("=" * 60)
        self.logger.info("CRAWL STATISTICS")
        self.logger.info("=" * 60)
        self.logger.info(f"PDFs found: {self.stats_counter['pdfs_found']}")
        self.logger.info(f"PDFs downloaded: {self.stats_counter['pdfs_downloaded']}")
        self.logger.info(
            f"{self.target_language_name} PDFs: {self.stats_counter['target_language_pdfs']} ✓"
        )
        self.logger.info(
            f"Other Language PDFs: {self.stats_counter['other_language_pdfs']} ✗"
        )
        self.logger.info(f"Files saved to: {os.path.abspath(self.download_dir)}")

        if self.stats_counter["languages_detected"]:
            self.logger.info("-" * 60)
            self.logger.info("Languages Detected:")
            for lang, count in sorted(
                self.stats_counter["languages_detected"].items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                self.logger.info(f"  {lang}: {count}")
        self.logger.info("=" * 60)
