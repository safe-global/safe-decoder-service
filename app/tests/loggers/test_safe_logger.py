# SPDX-License-Identifier: FSL-1.1-MIT
import json
import logging
from unittest import TestCase

from app.loggers.safe_logger import SafeJsonFormatter


class TestSafeJsonFormatter(TestCase):
    def test_writes_datadog_trace_fields(self):
        """The dd.* attributes ddtrace adds to a record end up in a "dd" object."""
        record = logging.makeLogRecord(
            {
                "dd.trace_id": "6afad78300000000a4289ab1112176c0",
                "dd.span_id": "14239931113675422624",
                "dd.service": "safe-decoder-service-web",
                "dd.version": "v1.0.0",
                "dd.env": "production",
            }
        )

        log = json.loads(SafeJsonFormatter().format(record))

        self.assertEqual(
            log["dd"],
            {
                "trace_id": "6afad78300000000a4289ab1112176c0",
                "span_id": "14239931113675422624",
                "service": "safe-decoder-service-web",
                "version": "v1.0.0",
                "env": "production",
            },
        )

    def test_omits_datadog_trace_fields_without_tracer(self):
        """Without ddtrace the record has no dd.* attributes and the log no "dd" key."""
        log = json.loads(SafeJsonFormatter().format(logging.makeLogRecord({})))

        self.assertNotIn("dd", log)

    def test_writes_only_service_fields_outside_span(self):
        """Outside a span ddtrace sets trace_id "0", so only service, version and env are written."""
        record = logging.makeLogRecord(
            {
                "dd.trace_id": "0",
                "dd.span_id": "0",
                "dd.service": "safe-decoder-service-web",
                "dd.version": "v1.0.0",
                "dd.env": "production",
            }
        )

        log = json.loads(SafeJsonFormatter().format(record))

        self.assertEqual(
            log["dd"],
            {
                "service": "safe-decoder-service-web",
                "version": "v1.0.0",
                "env": "production",
            },
        )
