# SPDX-License-Identifier: FSL-1.1-MIT
from unittest import TestCase

from app.config import Settings


class TestSettings(TestCase):
    def test_blockscout_api_key_strips_whitespace(self):
        """
        A Blockscout API key secret with a trailing newline is stripped, since it is
        sent in an HTTP header where a newline is rejected.
        """
        settings = Settings(BLOCKSCOUT_API_KEY=" proapi_test\n")
        self.assertEqual(settings.BLOCKSCOUT_API_KEY, "proapi_test")
