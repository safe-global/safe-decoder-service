# SPDX-License-Identifier: FSL-1.1-MIT
import unittest

from ...config import settings
from ...main import app


class TestOpenApi(unittest.TestCase):
    def test_data_decoder_data_limit_is_expressed_in_hex_characters(self):
        data = app.openapi()["components"]["schemas"]["DataDecoderInput"]["properties"][
            "data"
        ]
        self.assertEqual(data["type"], "string")
        self.assertEqual(data["maxLength"], 2 + 2 * settings.DECODER_MAX_DATA_BYTES)
