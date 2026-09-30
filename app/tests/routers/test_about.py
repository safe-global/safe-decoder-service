# SPDX-License-Identifier: FSL-1.1-MIT
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from ... import VERSION
from ...config import settings
from ...main import app


class TestRouterAbout(unittest.TestCase):
    client: TestClient

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_view_about(self):
        commit = "a618123e4f0c3b1d2e5f6a7b8c9d0e1f2a3b4c5d"
        with mock.patch.object(settings, "BUILD_COMMIT", commit):
            response = self.client.get("/api/v1/about")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"version": VERSION, "buildCommit": commit})

    def test_view_about_without_build_commit(self):
        with mock.patch.object(settings, "BUILD_COMMIT", ""):
            response = self.client.get("/api/v1/about")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"version": VERSION, "buildCommit": None})
