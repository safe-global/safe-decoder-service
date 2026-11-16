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

    def test_omits_empty_datadog_trace_fields(self):
        """Version and env are empty without DD_VERSION and DD_ENV, so they are not written."""
        record = logging.makeLogRecord(
            {
                "dd.trace_id": "6afad78300000000a4289ab1112176c0",
                "dd.span_id": "14239931113675422624",
                "dd.service": "safe-decoder-service-web",
                "dd.version": "",
                "dd.env": "",
            }
        )

        log = json.loads(SafeJsonFormatter().format(record))

        self.assertEqual(
            log["dd"],
            {
                "trace_id": "6afad78300000000a4289ab1112176c0",
                "span_id": "14239931113675422624",
                "service": "safe-decoder-service-web",
            },
        )

    def test_writes_only_present_datadog_trace_fields(self):
        """A record with dd.trace_id but no other dd.* attribute writes only the trace id."""
        record = logging.makeLogRecord(
            {"dd.trace_id": "6afad78300000000a4289ab1112176c0"}
        )

        log = json.loads(SafeJsonFormatter().format(record))

        self.assertEqual(log["dd"], {"trace_id": "6afad78300000000a4289ab1112176c0"})

    def test_omits_dd_key_when_all_datadog_fields_are_empty(self):
        """Outside a span with empty service, version and env there is nothing to write."""
        record = logging.makeLogRecord(
            {
                "dd.trace_id": "0",
                "dd.span_id": "0",
                "dd.service": "",
                "dd.version": "",
                "dd.env": "",
            }
        )

        log = json.loads(SafeJsonFormatter().format(record))

        self.assertNotIn("dd", log)
