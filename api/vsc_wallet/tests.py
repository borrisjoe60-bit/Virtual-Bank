from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory

from vsc_wallet.views import VscNetworkView, rpc, rpc_error


class VscNetworkViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    @patch("vsc_wallet.views.rpc", return_value="0x10")
    def test_network_reports_chain_and_latest_block(self, mock_rpc):
        response = VscNetworkView.as_view()(self.factory.get("/vsc/network/"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["chain_id"], 420042)
        self.assertEqual(response.data["latest_block"], 16)
        self.assertEqual(response.data["rpc_status"], "online")

    @patch("vsc_wallet.views.rpc", side_effect=RuntimeError("https://private-node.example/token"))
    def test_network_does_not_leak_rpc_error_details(self, mock_rpc):
        response = VscNetworkView.as_view()(self.factory.get("/vsc/network/"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["rpc_status"], "unavailable")
        self.assertNotIn("private-node", str(response.data))

    def test_rpc_error_response_is_sanitized(self):
        response = rpc_error(RuntimeError("secret endpoint credential"))
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret", str(response.data))

    @override_settings(VSC_RPC_URL="https://primary.invalid", VSC_RPC_FALLBACK_URLS=["https://fallback.invalid"])
    @patch("vsc_wallet.views.requests.post")
    def test_rpc_fails_over_to_secondary_after_primary_failure(self, post):
        def reply(result):
            response = Mock()
            response.raise_for_status.return_value = None
            response.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": result}
            return response
        post.side_effect = [
            requests.Timeout("primary timeout"),
            reply("0x668ca"),
            reply("0x2a"),
        ]
        self.assertEqual(rpc("eth_blockNumber"), "0x2a")
        self.assertEqual(post.call_count, 3)
        self.assertEqual(post.call_args_list[1].args[0], "https://fallback.invalid")
