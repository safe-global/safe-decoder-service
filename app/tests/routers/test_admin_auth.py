# SPDX-License-Identifier: FSL-1.1-MIT
import unittest

from app.routers.admin import AdminAuth


class TestAdminAuth(unittest.TestCase):
    def test_compare_credentials_rejects_non_ascii_without_raising(self):
        self.assertFalse(AdminAuth._compare_credentials("uxio", "uxío"))
        self.assertFalse(AdminAuth._compare_credentials("uxío", "admin"))
        self.assertFalse(AdminAuth._compare_credentials("🙂", "admin"))

    def test_compare_credentials_accepts_exact_match(self):
        self.assertTrue(AdminAuth._compare_credentials("admin", "admin"))
        self.assertTrue(AdminAuth._compare_credentials("uxío", "uxío"))
        self.assertTrue(AdminAuth._compare_credentials("🙂", "🙂"))
