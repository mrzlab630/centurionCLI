import argparse
import importlib.util
from pathlib import Path
import socket
import unittest
from unittest.mock import patch


RECON_PATH = Path(__file__).parents[1] / "skills/velites/scripts/recon.py"
SPEC = importlib.util.spec_from_file_location("velites_recon", RECON_PATH)
recon = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recon)


class ParseTargetTests(unittest.TestCase):
    @patch.object(recon.urllib.request, "urlopen")
    @patch.object(recon, "check_port")
    @patch.object(recon.socket, "getaddrinfo")
    def test_rejects_malformed_http_prefix_without_network(self, getaddrinfo, check_port, urlopen):
        with self.assertRaisesRegex(ValueError, "http:// or https://"):
            recon.main.__wrapped__(argparse.Namespace(target="http-malformed"))
        getaddrinfo.assert_not_called()
        check_port.assert_not_called()
        urlopen.assert_not_called()

    @patch.object(recon.urllib.request, "urlopen")
    @patch.object(recon, "check_port")
    @patch.object(recon.socket, "getaddrinfo")
    def test_rejects_urls_without_hostname_without_network(self, getaddrinfo, check_port, urlopen):
        for target in ("https://", "https:///path", "ftp://example.com"):
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    recon.main.__wrapped__(argparse.Namespace(target=target))
        getaddrinfo.assert_not_called()
        check_port.assert_not_called()
        urlopen.assert_not_called()

    def test_parses_hostname_instead_of_netloc(self):
        url, host = recon.parse_target("https://user@example.test:8443/path")
        self.assertEqual(url, "https://user@example.test:8443/path")
        self.assertEqual(host, "example.test")
        self.assertEqual(recon.parse_target("example.test"), ("https://example.test", "example.test"))


class ReconTargetTests(unittest.TestCase):
    @patch.object(recon.urllib.request, "urlopen")
    @patch.object(recon, "check_port", return_value=None)
    @patch.object(recon.socket, "getaddrinfo", return_value=[
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("203.0.113.10", 0))
    ])
    def test_resolves_parsed_host_and_requests_url(self, getaddrinfo, check_port, urlopen):
        response = urlopen.return_value.__enter__.return_value
        response.headers = {"Server": "test"}
        response.status = 200

        report = recon.main.__wrapped__(
            argparse.Namespace(target="https://user@example.test:8443/path")
        )

        self.assertEqual(report["target"], "example.test")
        self.assertEqual(report["url"], "https://user@example.test:8443/path")
        self.assertEqual(report["ip"], "203.0.113.10")
        getaddrinfo.assert_called_once_with("example.test", None, type=socket.SOCK_STREAM)
        self.assertEqual(check_port.call_count, len(recon.COMMON_PORTS))
        self.assertEqual(urlopen.call_args.args[0].full_url, report["url"])

    @patch.object(recon.urllib.request, "urlopen")
    @patch.object(recon, "check_port")
    @patch.object(recon.socket, "getaddrinfo", side_effect=OSError("not found"))
    def test_unresolved_target_stops_before_port_or_http_calls(self, getaddrinfo, check_port, urlopen):
        with self.assertRaisesRegex(ValueError, "Unable to resolve"):
            recon.main.__wrapped__(argparse.Namespace(target="example.test"))

        getaddrinfo.assert_called_once_with("example.test", None, type=socket.SOCK_STREAM)
        check_port.assert_not_called()
        urlopen.assert_not_called()

    @patch.object(recon.urllib.request, "urlopen")
    @patch.object(recon, "check_port", return_value=None)
    @patch.object(recon.socket, "getaddrinfo", return_value=[
        (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("2001:db8::1", 0, 0, 0))
    ])
    def test_ipv6_only_target_continues_to_http(self, getaddrinfo, check_port, urlopen):
        response = urlopen.return_value.__enter__.return_value
        response.headers = {"Server": "test"}
        response.status = 200

        report = recon.main.__wrapped__(argparse.Namespace(target="https://[2001:db8::1]"))

        self.assertEqual(report["ip"], "2001:db8::1")
        self.assertEqual(report["status"], 200)
        getaddrinfo.assert_called_once_with("2001:db8::1", None, type=socket.SOCK_STREAM)
        self.assertEqual(check_port.call_count, len(recon.COMMON_PORTS))
        urlopen.assert_called_once()


if __name__ == "__main__":
    unittest.main()
