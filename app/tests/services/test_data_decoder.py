import unittest

from ...services.data_decoder import DataDecoderService


class TestRouterAbout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_decoder = DataDecoderService()

    def test_view_about(self):
        response = self.client.get("/api/v1/about")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"version": VERSION})