from unittest.mock import patch

from rest_framework.test import APIRequestFactory
from django.test import SimpleTestCase

from vsc_wallet.views import VscNetworkView, rpc_error


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
        self.assertNotIn("rpc_error", response.data)
        self.assertNotIn("private-node", str(response.data))

    def test_rpc_error_response_is_sanitized(self):
        response = rpc_error(RuntimeError("secret endpoint credential"))
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret", str(response.data))
