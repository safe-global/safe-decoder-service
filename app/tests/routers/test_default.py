import unittest

from fastapi.testclient import TestClient

from ...main import app


class TestRouterDefault(unittest.TestCase):
    client: TestClient

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_view_home(self):
        response = self.client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 200)

    def test_view_redoc(self):
        response = self.client.get("/redoc", follow_redirects=False)
        self.assertEqual(response.status_code, 200)

    def test_view_swagger_ui(self):
        response = self.client.get("/docs", follow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertTrue(response.has_redirect_location)
        self.assertEqual(response.headers["location"], "/")

    def test_view_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), "OK")

    def test_redirect_middleware(self):
        """Test that redirects work correctly with or without proxy headers (x-forwarded-prefix and x-forwarded-host)"""
        # Test with the /docs endpoint which redirects to /
        response = self.client.get(
            "/docs",
            follow_redirects=False,
        )

        # Should be a redirect response
        self.assertEqual(response.status_code, 307)

        # The location header should be updated by the middleware to include proxy information
        location = response.headers.get("location")
        self.assertIsNotNone(location)
        # The location should be the default /
        self.assertEqual(location, "/")

        # Test setting prefix to "" to disable it
        response = self.client.get(
            "/docs",
            headers={
                "x-forwarded-prefix": "",
                "x-forwarded-host": "proxy.example.com",
                "x-forwarded-proto": "https",
            },
            follow_redirects=False,
        )

        # Should be a redirect response
        self.assertEqual(response.status_code, 307)

        # The location header should be updated by the middleware to include proxy information
        location = response.headers.get("location")
        self.assertIsNotNone(location)
        # The location should be the default /
        self.assertEqual(location, "/")

        # Test with proxy headers without port
        response = self.client.get(
            "/docs",
            headers={
                "x-forwarded-prefix": "/safe-decoder",
                "x-forwarded-host": "proxy.example.com",
                "x-forwarded-proto": "https",
            },
            follow_redirects=False,
        )

        # Should be a redirect response
        self.assertEqual(response.status_code, 307)

        # The location header should be updated by the middleware to include proxy information
        location = response.headers.get("location")
        self.assertIsNotNone(location)
        # The location should include the forwarded prefix, host, and protocol
        self.assertEqual(location, "https://proxy.example.com/safe-decoder/")

        # Test with proxy headers with port
        response = self.client.get(
            "/docs",
            headers={
                "x-forwarded-prefix": "/safe-decoder",
                "x-forwarded-host": "proxy.example.com",
                "x-forwarded-proto": "https",
                "x-forwarded-port": "8000",
            },
            follow_redirects=False,
        )

        # Should be a redirect response
        self.assertEqual(response.status_code, 307)

        # The location header should be updated by the middleware to include proxy information
        location = response.headers.get("location")
        self.assertIsNotNone(location)
        # The location should include the forwarded prefix, host, protocol and port
        self.assertEqual(location, "https://proxy.example.com:8000/safe-decoder/")
