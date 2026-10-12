import unittest

from src.youtube_client import (
    YouTubeAPIError,
    YouTubeAuthenticationError,
    YouTubeClient,
    YouTubeRateLimitError,
)


class YouTubeClientErrorClassificationTests(unittest.TestCase):
    def test_http_401_is_authentication_error(self):
        with self.assertRaises(YouTubeAuthenticationError):
            YouTubeClient._raise_api_error(
                401,
                {"error": {"message": "Invalid credentials", "errors": []}},
            )

    def test_invalid_api_key_reason_is_authentication_error(self):
        with self.assertRaises(YouTubeAuthenticationError):
            YouTubeClient._raise_api_error(
                403,
                {
                    "error": {
                        "message": "Invalid API key",
                        "errors": [{"reason": "keyInvalid"}],
                    }
                },
            )

    def test_quota_exceeded_reason_is_rate_limit_error(self):
        with self.assertRaises(YouTubeRateLimitError):
            YouTubeClient._raise_api_error(
                403,
                {
                    "error": {
                        "message": "Quota exceeded",
                        "errors": [{"reason": "quotaExceeded"}],
                    }
                },
            )

    def test_http_429_is_rate_limit_error(self):
        with self.assertRaises(YouTubeRateLimitError):
            YouTubeClient._raise_api_error(429, {"error": {"errors": []}})

    def test_unclassified_http_403_remains_generic_api_error(self):
        with self.assertRaises(YouTubeAPIError) as context:
            YouTubeClient._raise_api_error(
                403,
                {
                    "error": {
                        "message": "Access forbidden",
                        "errors": [{"reason": "forbidden"}],
                    }
                },
            )

        self.assertNotIsInstance(context.exception, YouTubeAuthenticationError)
        self.assertNotIsInstance(context.exception, YouTubeRateLimitError)


if __name__ == "__main__":
    unittest.main()
