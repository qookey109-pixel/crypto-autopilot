from __future__ import annotations

import io
import json
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.cloud_pionex_client_v0_1 import (
    CLOUD_PAPER_PATHS,
    MAX_RESPONSE_BYTES,
    CloudPaperPionexPublicClient,
    CloudPaperTransportBlocked,
    _NoRedirect,
)

MODULE = "crypto_autopilot.paper.cloud_pionex_client_v0_1"


class Response:
    def __init__(self, body, *, code=200, encoding=None):
        self.body = body
        self.code = code
        self.headers = {} if encoding is None else {"Content-Encoding": encoding}
        self.read_limits = []
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def getcode(self):
        return self.code

    def read(self, size):
        self.read_limits.append(size)
        return self.body[:size]


class CloudPaperPionexTransportTests(unittest.TestCase):
    def request(self, response, *, method=None):
        events = []
        client = CloudPaperPionexPublicClient(
            before_send=lambda: events.append("evidence"),
        )
        opener = Mock()
        opener.open.side_effect = lambda *args, **kwargs: (
            events.append("send") or response
        )
        with patch.object(client, "_pace", side_effect=lambda: events.append("pace")):
            with patch(f"{MODULE}.build_opener", return_value=opener) as factory:
                value = (method or client.list_perpetual_symbols)()
        factory.assert_called_once_with(_NoRedirect)
        self.assertEqual(events, ["pace", "evidence", "send"])
        self.assertEqual(opener.open.call_count, 1)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.get_header("Accept-encoding"), "identity")
        self.assertEqual(opener.open.call_args.kwargs["timeout"], 10.0)
        self.assertTrue(response.closed)
        return value, request

    def test_existing_symbol_parser_fixed_host_and_bounded_read(self):
        response = Response(json.dumps({
            "result": True,
            "data": {"symbols": [{"symbol": "BTC_USDT_PERP"}]},
        }).encode())
        value, request = self.request(response)
        self.assertEqual(value, ["BTC_USDT_PERP"])
        self.assertTrue(request.full_url.startswith("https://api.pionex.com/"))
        self.assertEqual(response.read_limits, [MAX_RESPONSE_BYTES + 1])

    def test_legacy_kline_parser_retains_sorting(self):
        client = CloudPaperPionexPublicClient(before_send=lambda: None)
        rows = [
            {"time": 2, "open": "2", "high": "3", "low": "1",
             "close": "2.5", "volume": "20"},
            {"time": 1, "open": "1", "high": "2", "low": "0.5",
             "close": "1.5", "volume": "10"},
        ]
        response = Response(json.dumps({"result": True, "data": {"klines": rows}}).encode())
        opener = Mock()
        opener.open.return_value = response
        # Changing the inherited host cannot change this transport's authority.
        client.BASE_URL = "https://invalid.example"
        with patch.object(client, "_pace"), patch(
            f"{MODULE}.build_opener", return_value=opener,
        ):
            value = client.get_klines("BTC_USDT_PERP", "15M", limit=2)
        self.assertEqual([c.time_ms for c in value], [1, 2])
        self.assertTrue(opener.open.call_args.args[0].full_url.startswith(
            "https://api.pionex.com/api/v1/market/klines?",
        ))

    def test_all_cloud_paper_endpoints_are_public_and_inherited_extra_paths_stop(self):
        self.assertEqual(len(CLOUD_PAPER_PATHS), 6)
        client = CloudPaperPionexPublicClient(before_send=lambda: None)
        with patch(f"{MODULE}.build_opener") as opener, patch.object(client, "_pace"):
            for call in (client.list_open_interests, client.list_derivative_indexes):
                with self.assertRaisesRegex(CloudPaperTransportBlocked, "ENDPOINT_NOT_ALLOWED"):
                    call()
            with self.assertRaisesRegex(CloudPaperTransportBlocked, "ENDPOINT_NOT_ALLOWED"):
                client._get_json("https://invalid.example", {})
        opener.assert_not_called()

    def test_all_redirect_statuses_stop_without_another_request(self):
        client = CloudPaperPionexPublicClient(before_send=lambda: None)
        for status in (301, 302, 303, 307, 308):
            for target in ("https://api.pionex.com/other", "https://invalid.example"):
                with self.subTest(status=status, target=target):
                    opener = Mock()
                    opener.open.side_effect = lambda request, **kwargs: _NoRedirect().redirect_request(
                        request, io.BytesIO(b"redirect"), status, "redirect", {}, target,
                    )
                    with patch.object(client, "_pace"), patch(
                        f"{MODULE}.build_opener", return_value=opener,
                    ):
                        with self.assertRaisesRegex(
                            CloudPaperTransportBlocked, "^PIONEX_REDIRECT_REJECTED$",
                        ):
                            client.list_perpetual_symbols()
                    self.assertEqual(opener.open.call_count, 1)

    def test_budget_expires_during_pacing_before_transport_is_created(self):
        events = []
        def check():
            events.append("check")
            raise BudgetBlocked("BLOCKED_BUDGET_EVIDENCE_STALE")
        client = CloudPaperPionexPublicClient(before_send=check)
        with patch.object(client, "_pace", side_effect=lambda: events.append("pace")):
            with patch(f"{MODULE}.build_opener") as opener:
                with self.assertRaisesRegex(BudgetBlocked, "EVIDENCE_STALE"):
                    client.list_perpetual_symbols()
        self.assertEqual(events, ["pace", "check"])
        opener.assert_not_called()

    def test_oversize_and_encoded_responses_stop_before_json_parsing(self):
        client = CloudPaperPionexPublicClient(before_send=lambda: None)
        for response, code in (
            (Response(b"x" * (MAX_RESPONSE_BYTES + 2)), "RESPONSE_TOO_LARGE"),
            (Response(b"{}", encoding="gzip"), "CONTENT_ENCODING_REJECTED"),
            (Response(b"{}", code=503), "HTTP_STATUS_REJECTED"),
        ):
            opener = Mock()
            opener.open.return_value = response
            with patch.object(client, "_pace"), patch(
                f"{MODULE}.build_opener", return_value=opener,
            ):
                with self.assertRaisesRegex(CloudPaperTransportBlocked, code):
                    client.list_perpetual_symbols()
            self.assertEqual(opener.open.call_count, 1)
            self.assertTrue(response.closed)

    def test_transport_and_invalid_payload_errors_do_not_retry_or_echo_details(self):
        client = CloudPaperPionexPublicClient(before_send=lambda: None)
        for error in (
            HTTPError("https://invalid.example/detail", 429, "provider-detail", {}, None),
            URLError("provider-detail"), TimeoutError("provider-detail"),
        ):
            opener = Mock()
            opener.open.side_effect = error
            with patch.object(client, "_pace"), patch(
                f"{MODULE}.build_opener", return_value=opener,
            ):
                with self.assertRaisesRegex(
                    CloudPaperTransportBlocked, "^PIONEX_REQUEST_FAILED$",
                ):
                    client.list_perpetual_symbols()
            self.assertEqual(opener.open.call_count, 1)
        for body in (b"not-json", b"[]", b'{"result":1,"data":{}}',
                     b'{"result":true,"data":[]}', b'{"result":true,"data":{"x":NaN}}'):
            opener = Mock()
            opener.open.return_value = Response(body)
            with patch.object(client, "_pace"), patch(
                f"{MODULE}.build_opener", return_value=opener,
            ):
                with self.assertRaises(CloudPaperTransportBlocked):
                    client.list_perpetual_symbols()
            self.assertEqual(opener.open.call_count, 1)

    def test_constructor_limits_and_missing_guard(self):
        for kwargs in (
            {"before_send": None}, {"timeout_seconds": 11},
            {"timeout_seconds": float("nan")}, {"requests_per_second": 4},
            {"requests_per_second": float("inf")}, {"timeout_seconds": True},
        ):
            values = {"before_send": lambda: None, **kwargs}
            with self.assertRaises(ValueError):
                CloudPaperPionexPublicClient(**values)


if __name__ == "__main__":
    unittest.main()
