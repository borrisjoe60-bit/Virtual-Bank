import json
import re
from decimal import Decimal
from urllib.parse import urlencode

import requests
from eth_account import Account
from django.conf import settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import VscWallet, VscTransaction

CHAIN_ID = 420042
EXPLORER = "https://explorer.vscblockchain.org"
ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
HASH_RE = re.compile(r"^0x[a-fA-F0-9]{64}$")


def rpc(method, params=None):
    endpoint = getattr(settings, "VSC_RPC_URL", "")
    if not endpoint:
        raise RuntimeError("VSC_RPC_URL is not configured")
    response = requests.post(endpoint, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}, timeout=15)
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(payload["error"].get("message", "VSC RPC error"))
    return payload.get("result")


def rpc_error(exc):
    # Do not expose RPC hostnames, credentials, or upstream response bodies to clients.
    return Response({"detail": "Vector Smart Chain RPC is temporarily unavailable."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class VscNetworkView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        data = {"name": "Vector Smart Chain", "symbol": "VSG", "chain_id": CHAIN_ID, "chain_id_hex": hex(CHAIN_ID), "explorer_url": EXPLORER, "rpc_configured": bool(getattr(settings, "VSC_RPC_URL", ""))}
        try:
            data["latest_block"] = int(rpc("eth_blockNumber", []), 16)
            data["rpc_status"] = "online"
        except Exception as exc:
            data["rpc_status"] = "unavailable"
        return Response(data)


class VscWalletListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        rows = VscWallet.objects.filter(user=request.user, chain_id=CHAIN_ID)
        return Response([{"id": w.id, "address": w.address, "label": w.label, "chain_id": w.chain_id, "created_at": w.created_at, "explorer_url": f"{EXPLORER}/address/{w.address}"} for w in rows])

    def post(self, request):
        address = str(request.data.get("address", "")).strip()
        label = str(request.data.get("label", ""))[:80]
        if not ADDRESS_RE.fullmatch(address):
            return Response({"detail": "A valid 0x wallet address is required. Create/import the wallet in a trusted wallet app; this API never receives private keys or seed phrases."}, status=400)
        wallet, created = VscWallet.objects.get_or_create(user=request.user, chain_id=CHAIN_ID, address=address, defaults={"label": label})
        return Response({"id": wallet.id, "address": wallet.address, "label": wallet.label, "chain_id": CHAIN_ID, "created": created, "explorer_url": f"{EXPLORER}/address/{wallet.address}"}, status=201 if created else 200)


class VscBalanceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, wallet_id):
        wallet = VscWallet.objects.filter(id=wallet_id, user=request.user, chain_id=CHAIN_ID).first()
        if not wallet:
            return Response({"detail": "Wallet not found"}, status=404)
        try:
            raw = rpc("eth_getBalance", [wallet.address, "latest"])
            wei = int(raw, 16)
            return Response({"address": wallet.address, "chain_id": CHAIN_ID, "symbol": "VSG", "balance_wei": str(wei), "balance_vsg": str(Decimal(wei) / Decimal(10**18)), "explorer_url": f"{EXPLORER}/address/{wallet.address}"})
        except Exception as exc:
            return rpc_error(exc)


class VscDepositView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, wallet_id):
        wallet = VscWallet.objects.filter(id=wallet_id, user=request.user, chain_id=CHAIN_ID).first()
        if not wallet:
            return Response({"detail": "Wallet not found"}, status=404)
        return Response({"network": "Vector Smart Chain", "chain_id": CHAIN_ID, "asset": "VSG", "deposit_address": wallet.address, "explorer_url": f"{EXPLORER}/address/{wallet.address}", "instructions": "Send VSG on Vector Smart Chain only. Sending assets on another network may result in permanent loss."})


class VscWithdrawBroadcastView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, wallet_id):
        wallet = VscWallet.objects.filter(id=wallet_id, user=request.user, chain_id=CHAIN_ID).first()
        if not wallet:
            return Response({"detail": "Wallet not found"}, status=404)
        raw_tx = str(request.data.get("signed_raw_transaction", ""))
        if not raw_tx.startswith("0x") or len(raw_tx) < 20:
            return Response({"detail": "Provide a wallet-signed raw transaction. Never send a seed phrase or private key."}, status=400)
        try:
            signer = Account.recover_transaction(raw_tx)
            if signer.lower() != wallet.address.lower():
                return Response({"detail": "The signed transaction sender does not match this registered wallet."}, status=400)
            tx_hash = rpc("eth_sendRawTransaction", [raw_tx])
            if not HASH_RE.fullmatch(str(tx_hash)):
                raise RuntimeError("RPC returned an invalid transaction hash")
            VscTransaction.objects.get_or_create(wallet=wallet, tx_hash=tx_hash, defaults={"direction": "OUT", "status": "SUBMITTED"})
            return Response({"tx_hash": tx_hash, "status": "SUBMITTED", "explorer_url": f"{EXPLORER}/tx/{tx_hash}"}, status=202)
        except Exception as exc:
            return rpc_error(exc)


class VscHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, wallet_id):
        wallet = VscWallet.objects.filter(id=wallet_id, user=request.user, chain_id=CHAIN_ID).first()
        if not wallet:
            return Response({"detail": "Wallet not found"}, status=404)
        indexer = getattr(settings, "VSC_HISTORY_API_URL", "")
        if not indexer:
            local = VscTransaction.objects.filter(wallet=wallet)
            return Response({"items": [{"tx_hash": t.tx_hash, "direction": t.direction, "status": t.status, "created_at": t.created_at, "explorer_url": f"{EXPLORER}/tx/{t.tx_hash}"} for t in local], "history_complete": False, "message": "Configure VSC_HISTORY_API_URL to enable indexed incoming and outgoing transaction history. The explorer link remains available."})
        try:
            response = requests.get(indexer, params={"address": wallet.address, "chain_id": CHAIN_ID}, timeout=15)
            response.raise_for_status()
            payload = response.json()
            items = payload if isinstance(payload, list) else payload.get("items", []) if isinstance(payload, dict) else None
            if not isinstance(items, list):
                return Response({"detail": "The configured VSC history service returned an unsupported response."}, status=502)
            # Only accept transaction objects with a valid hash; do not blindly proxy arbitrary upstream data.
            safe_items = []
            for item in items[:100]:
                if not isinstance(item, dict) or not HASH_RE.fullmatch(str(item.get("tx_hash", item.get("hash", "")))):
                    continue
                tx_hash = str(item.get("tx_hash", item.get("hash")))
                safe_items.append({"tx_hash": tx_hash, "direction": item.get("direction"), "status": item.get("status"), "amount": item.get("amount"), "timestamp": item.get("timestamp"), "explorer_url": f"{EXPLORER}/tx/{tx_hash}"})
            return Response({"items": safe_items, "history_complete": True})
        except Exception as exc:
            return rpc_error(exc)
