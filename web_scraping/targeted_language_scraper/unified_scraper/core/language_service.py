import json
import warnings
from pathlib import Path

from scrapy.exceptions import CloseSpider

try:
    import fasttext
    from huggingface_hub import hf_hub_download

    GLOTLID_AVAILABLE = True
except ImportError:
    GLOTLID_AVAILABLE = False
    fasttext = None
    hf_hub_download = None


class LanguageService:
    """
    A single, centralized service for all language-related tasks.
    It loads the model and config file *once* and provides
    validation methods to any spider that uses it.
    """

    def __init__(
        self,
        language_file=None,
        model_cache_dir="language_models",
        model_path=None,
        min_text_length=20,
        sample_size=1000,
        confidence_threshold=0.5,
    ):
        """
        Initializes the service by loading the GlotLID model
        and the language configuration file.

        - language_file (str): Path to languages.json
        - model_cache_dir (str): Path to cache the model
        - model_path (str): Optional path to a local model.bin
        - min_text_length (int): Minimum text length for validation (default: 20)
        - sample_size (int): Size of text sample to analyze (default: 1000)
        - confidence_threshold (float): Minimum confidence for validation (default: 0.5)
        """
        print("Initializing LanguageService...")

        if not language_file:
            raise CloseSpider("LanguageService requires 'language_file' argument.")

        config_path = Path(language_file)
        if not config_path.exists():
            raise CloseSpider(f"Language file not found at {config_path.resolve()}")
        try:
            with open(config_path, "r") as f:
                self.lang_configs = json.load(f)
        except Exception as e:
            raise CloseSpider(f"Error reading {language_file}: {e}")

        if not GLOTLID_AVAILABLE:
            raise CloseSpider(
                "Missing required GlotLID dependencies (fasttext, huggingface_hub)."
            )

        self.min_text_length = min_text_length
        self.sample_size = sample_size
        self.confidence_threshold = confidence_threshold

        self.glotlid_model = None
        try:
            if model_path:
                glotlid_model_path = model_path
            else:
                glotlid_model_path = hf_hub_download(
                    repo_id="cis-lmu/glotlid",
                    filename="model.bin",
                    cache_dir=model_cache_dir,
                )

            self.glotlid_model = fasttext.load_model(glotlid_model_path)
            print("✓ LanguageService: GlotLID model loaded successfully.")
            print(f"  - Min text length: {self.min_text_length}")
            print(f"  - Sample size: {self.sample_size}")
            print(f"  - Confidence threshold: {self.confidence_threshold}")

        except Exception as e:
            print(f"✗ LanguageService: FAILED to load GlotLID model: {e}")
            raise CloseSpider(f"Failed to load GlotLID model: {e}")

    def get_config(self, lang_key):
        """
        Gets the configuration block for a specific language.
        """
        config = self.lang_configs.get(lang_key.lower())
        if not config:
            raise CloseSpider(
                f"Language '{lang_key}' not found in languages.json. Available: {list(self.lang_configs.keys())}"
            )
        return config

    def _extract_text_sample(self, text, sample_size):
        """
        Intelligently extracts a representative text sample.
        Takes text from multiple positions to handle cases where
        important content isn't at the beginning.
        """
        text = text.strip().replace("\n", " ").replace("\t", " ")

        while "  " in text:
            text = text.replace("  ", " ")

        if len(text) <= sample_size:
            return text

        chunk_size = sample_size // 3
        start = text[:chunk_size]
        middle_pos = len(text) // 2 - chunk_size // 2
        middle = text[middle_pos : middle_pos + chunk_size]
        end = text[-chunk_size:]

        return f"{start} {middle} {end}"

    def validate(self, text, target_lang_codes, lenient_mode=False):
        """
        Uses the loaded GlotLID model to check if the text
        is in the list of target languages.

        Args:
            text (str): The text to validate
            target_lang_codes (list): List of acceptable language codes
            lenient_mode (bool): If True, uses lower thresholds for edge cases

        Returns:
            tuple: (is_valid (bool), detected_lang (str), confidence (float))
        """

        if not text:
            print("Warning: Empty text provided for validation")
            return False, "empty", 0.0

        text_stripped = text.strip()
        text_length = len(text_stripped)

        effective_min_length = (
            self.min_text_length // 2 if lenient_mode else self.min_text_length
        )

        if text_length < effective_min_length:
            print(
                f"Warning: Text too short ({text_length} chars, min: {effective_min_length})"
            )
            return False, "too_short", 0.0

        try:
            text_sample = self._extract_text_sample(text_stripped, self.sample_size)

            if not text_sample:
                print("Warning: Text sample extraction failed")
                return False, "extraction_failed", 0.0

            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=DeprecationWarning)
                warnings.filterwarnings("ignore", category=FutureWarning)

                predictions = self.glotlid_model.predict(text_sample, k=3)

            lang_label = predictions[0][0]
            detected_lang = lang_label.replace("__label__", "")
            confidence = float(predictions[1][0])

            is_target = detected_lang in target_lang_codes

            if not is_target and len(predictions[0]) > 1:
                for i in range(1, len(predictions[0])):
                    alt_lang = predictions[0][i].replace("__label__", "")
                    alt_confidence = float(predictions[1][i])

                    if (
                        alt_lang in target_lang_codes
                        and alt_confidence >= self.confidence_threshold * 0.8
                    ):
                        print(
                            f"Info: Using secondary prediction - {alt_lang} (confidence: {alt_confidence:.3f})"
                        )
                        return True, alt_lang, alt_confidence

            effective_threshold = (
                self.confidence_threshold * 0.7
                if lenient_mode
                else self.confidence_threshold
            )

            if is_target:
                if confidence >= effective_threshold:
                    print(
                        f"✓ Validation passed: {detected_lang} (confidence: {confidence:.3f}, length: {text_length})"
                    )
                else:
                    print(
                        f"⚠ Low confidence match: {detected_lang} (confidence: {confidence:.3f}, threshold: {effective_threshold:.3f})"
                    )
            else:
                print(
                    f"✗ Language mismatch: detected={detected_lang} (confidence: {confidence:.3f}), expected={target_lang_codes}"
                )

            final_is_valid = is_target and (
                confidence >= effective_threshold or lenient_mode
            )

            return final_is_valid, detected_lang, confidence

        except Exception as e:
            print(f"Error: GlotLID validation failed: {e}")
            import traceback

            traceback.print_exc()
            return False, "error", 0.0

    def validate_multiple_samples(self, text, target_lang_codes, num_samples=3):
        """
        Validates using multiple random samples from the text for better accuracy.
        Useful for long documents where language might vary.

        Args:
            text (str): The text to validate
            target_lang_codes (list): List of acceptable language codes
            num_samples (int): Number of samples to check

        Returns:
            tuple: (is_valid (bool), detected_lang (str), avg_confidence (float))
        """
        if len(text.strip()) < self.min_text_length * num_samples:
            return self.validate(text, target_lang_codes)

        results = []
        text_len = len(text)
        sample_positions = [0, text_len // 3, 2 * text_len // 3][:num_samples]

        for pos in sample_positions:
            sample = text[pos : pos + self.sample_size]
            is_valid, lang, conf = self.validate(sample, target_lang_codes)
            if is_valid:
                results.append((lang, conf))

        if not results:
            return False, "no_valid_samples", 0.0

        from collections import Counter

        lang_counts = Counter([r[0] for r in results])
        most_common_lang = lang_counts.most_common(1)[0][0]
        avg_confidence = sum(r[1] for r in results if r[0] == most_common_lang) / len(
            results
        )

        return True, most_common_lang, avg_confidence
