from scrapy.exceptions import CloseSpider

from ..core.language_service import LanguageService
from .base_pdf_spider import BasePdfLanguageSpider


class LanguagePdfSpider(BasePdfLanguageSpider):
    """
    This is the unified, data-driven PDF spider.
    It inherits from BasePdfLanguageSpider and uses the LanguageService
    to perform all language-related configuration and validation.

    Usage:
    scrapy crawl language_pdf -a lang=filipino -a seed_file=urls.txt
    scrapy crawl language_pdf -a lang=malay -a seed_file=urls.txt
    """

    name = "language_pdf"

    def __init__(self, *args, **kwargs):

        lang = kwargs.pop("lang", None)
        lang_file_arg = kwargs.pop("language_file", None)
        cache_dir_arg = kwargs.pop("model_cache_dir", None)

        if not lang:
            raise CloseSpider("Missing 'lang' argument. (e.g., -a lang=filipino)")
        if not lang_file_arg or not cache_dir_arg:
            raise CloseSpider("Missing 'language_file' or 'model_cache_dir' arguments.")

        try:
            self.lang_service = LanguageService(
                language_file=lang_file_arg, model_cache_dir=cache_dir_arg
            )
        except Exception as e:
            raise CloseSpider(f"Failed to initialize LanguageService: {e}")

        config = self.lang_service.get_config(lang)

        self.target_language_name = config["name"]
        self.download_dir = config["download_dir"]
        self.target_codes = config["glotlid_codes"]

        self.stats_counter = {
            "pdfs_found": 0,
            "pdfs_downloaded": 0,
            "target_language_pdfs": 0,
            "other_language_pdfs": 0,
            "languages_detected": {},
        }

        super().__init__(*args, **kwargs)

    def detect_language(self, text):
        """
        This method is required by BasePdfLanguageSpider.
        It passes the text to our LanguageService for validation.
        """
        is_target, detected_lang, confidence = self.lang_service.validate(
            text, self.target_codes
        )

        return is_target, {"language": detected_lang, "confidence": confidence}
