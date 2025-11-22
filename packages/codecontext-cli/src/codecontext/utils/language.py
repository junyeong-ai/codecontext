"""Language detection utilities."""

import logging

from langdetect import LangDetectException, detect

logger = logging.getLogger(__name__)


class LanguageDetector:
    """Language detection using langdetect.

    Fast, accurate detection for 99+ languages.
    Based on Google's language-detection library.
    """

    def detect(self, text: str) -> str:
        """Detect language (ISO 639-1 code).

        Args:
            text: Text to detect language

        Returns:
            Language code (e.g., "ko", "en", "ja")
            Defaults to "en" on error or empty text

        Examples:
            >>> detector = LanguageDetector()
            >>> detector.detect("사용자 인증")
            'ko'
            >>> detector.detect("user authentication")
            'en'
            >>> detector.detect("")
            'en'
        """
        if not text or not text.strip():
            return "en"

        try:
            lang: str = detect(text)
            logger.debug(f"Detected language: {lang} for text: {text[:50]}...")
            return lang
        except LangDetectException:
            logger.warning("Failed to detect language, defaulting to 'en'")
            return "en"
