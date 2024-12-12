import unittest

from fastapi.testclient import TestClient

from ...main import app


class TestRouterAdmin(unittest.TestCase):
    client: TestClient

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_admin(self):
        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 200)
        self.assertIn("DOCTYPE html", response.text)
