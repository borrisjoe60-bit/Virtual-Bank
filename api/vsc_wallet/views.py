import re
from decimal import Decimal

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
WEI = Decimal(10**18)


def rpc(method, params=None):
    primary = getattr(settings, "VSC_RPC_URL", "")
    endpoints = ([primary] if primary else []) + list(getattr(settings, "VSC_RPC_FALLBACK_URLS", []))
    if not endpoints:
        raise RuntimeError("No VSC RPC endpoint configured")
    errors = []
    for endpoint in dict.fromkeys(endpoints):
        try:
            if method != "eth_chainId":
                check = requests.post(endpoint, json={"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []}, timeout=8)
                check.raise_for_status()
                chain_data = check.json()
                if chain_data.get("error") or int(chain_data.get("result", "0x0"), 16) != CHAIN_ID:
                    raise RuntimeError("RPC chain ID mismatch")
            response = requests.post(endpoint, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}, timeout=8)
            response.raise_for_status()
            payload = response.json()
            if payload.get("error"):
                raise RuntimeError("RPC method returned an error")
            if "result" not in payload:
                raise RuntimeError("RPC response did not contain a result")
            return payload["result"]
        except Exception as exc:
            errors.append(exc)
    raise RuntimeError("All configured VSC RPC endpoints failed")


def rpc_error(exc):
    return Response({"detail": "Vector Smart Chain RPC is temporarily unavailable. Please retry shortly."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


def get_user_wallet(request, wallet_id):
    return VscWallet.objects.filter(id=wallet_id, user=request.user, chain_id=CHAIN_ID).first()


class VscNetworkView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        data = {"name": "Vector Smart Chain", "symbol": "VSG", "chain_id": CHAIN_ID, "chain_id_hex": hex(CHAIN_ID), "explorer_url": EXPLORER, "rpc_configured": bool(getattr(settings, "VSC_RPC_URL", ""))}
        try:
            data["latest_block"] = int(rpc("eth_blockNumber"), 16)
            data["rpc_status"] = "online"
        except Exception:
            data["latest_block"] = None
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
            return Response({"detail": "A valid 0x wallet address is required. Connect a wallet app; never enter a seed phrase or private key."}, status=400)
        wallet, created = VscWallet.objects.get_or_create(user=request.user, chain_id=CHAIN_ID, address=address, defaults={"label": label})
        return Response({"id": wallet.id, "address": wallet.address, "label": wallet.label, "chain_id": CHAIN_ID, "created": created, "explorer_url": f"{EXPLORER}/address/{wallet.address}"}, status=201 if created else 200)


class VscBalanceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, wallet_id):
        wallet = get_user_wallet(request, wallet_id)
        if not wallet:
            return Response({"detail": "Wallet not found"}, status=404)
        try:
            wei = int(rpc("eth_getBalance", [wallet.address, "latest"]), 16)
            return Response({"address": wallet.address, "chain_id": CHAIN_ID, "symbol": "VSG", "balance_wei": str(wei), "balance_vsg": str(Decimal(wei) / WEI), "explorer_url": f"{EXPLORER}/address/{wallet.address}"})
        except Exception as exc:
            return rpc_error(exc)


class VscDepositView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, wallet_id):
        wallet = get_user_wallet(request, wallet_id)
        if not wallet:
            return Response({"detail": "Wallet not found"}, status=404)
        return Response({"network": "Vector Smart Chain", "chain_id": CHAIN_ID, "asset": "VSG", "deposit_address": wallet.address, "explorer_url": f"{EXPLORER}/address/{wallet.address}", "instructions": "Send VSG on Vector Smart Chain only. Sending assets on another network may result in permanent loss. Deposits are on-chain and are not credited to a simulated bank balance."})


class VscRecordTransactionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, wallet_id):
        wallet = get_user_wallet(request, wallet_id)
        if not wallet:
            return Response({"detail": "Wallet not found"}, status=404)
        tx_hash = str(request.data.get("tx_hash", "")).strip()
        if not HASH_RE.fullmatch(tx_hash):
            return Response({"detail": "A valid transaction hash is required."}, status=400)
        try:
            tx = rpc("eth_getTransactionByHash", [tx_hash])
            if not tx:
                return Response({"detail": "Transaction is not yet visible on the VSC network. Retry shortly."}, status=404)
            if str(tx.get("from", "")).lower() != wallet.address.lower():
                return Response({"detail": "Transaction sender does not match this registered wallet."}, status=403)
            receipt = rpc("eth_getTransactionReceipt", [tx_hash])
            tx_status = "CONFIRMED" if receipt and receipt.get("status") == "0x1" else "FAILED" if receipt and receipt.get("status") == "0x0" else "SUBMITTED"
            value = int(tx.get("value", "0x0"), 16)
            VscTransaction.objects.update_or_create(wallet=wallet, tx_hash=tx_hash, defaults={"direction": "OUT", "status": tx_status, "amount_wei": value})
            return Response({"tx_hash": tx_hash, "status": tx_status, "amount_vsg": str(Decimal(value) / WEI), "explorer_url": f"{EXPLORER}/tx/{tx_hash}"}, status=200)
        except Exception as exc:
            return rpc_error(exc)


class VscWithdrawBroadcastView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, wallet_id):
        wallet = get_user_wallet(request, wallet_id)
        if not wallet:
            return Response({"detail": "Wallet not found"}, status=404)
        raw_tx = str(request.data.get("signed_raw_transaction", "")).strip()
        if not raw_tx.startswith("0x") or len(raw_tx) < 20:
            return Response({"detail": "Provide a wallet-signed raw transaction. Never send a seed phrase or private key."}, status=400)
        try:
            signer = Account.recover_transaction(raw_tx)
        except Exception:
            return Response({"detail": "The signed transaction could not be verified."}, status=400)
        if signer.lower() != wallet.address.lower():
            return Response({"detail": "The signed transaction sender does not match this registered wallet."}, status=400)
        try:
            tx_hash = rpc("eth_sendRawTransaction", [raw_tx])
            if not HASH_RE.fullmatch(str(tx_hash)):
                raise RuntimeError("Invalid transaction hash from RPC")
            VscTransaction.objects.update_or_create(wallet=wallet, tx_hash=tx_hash, defaults={"direction": "OUT", "status": "SUBMITTED"})
            return Response({"tx_hash": tx_hash, "status": "SUBMITTED", "explorer_url": f"{EXPLORER}/tx/{tx_hash}"}, status=202)
        except Exception as exc:
            return rpc_error(exc)


class VscHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, wallet_id):
        wallet = get_user_wallet(request, wallet_id)
        if not wallet:
            return Response({"detail": "Wallet not found"}, status=404)
        endpoint = getattr(settings, "VSC_HISTORY_API_URL", "") or f"{EXPLORER}/api"
        try:
            response = requests.get(endpoint, params={"module": "account", "action": "txlist", "address": wallet.address, "startblock": 0, "endblock": 99999999, "page": 1, "offset": 100, "sort": "desc"}, timeout=12)
            response.raise_for_status()
            payload = response.json()
            result = payload.get("result", []) if isinstance(payload, dict) else []
            if not isinstance(result, list):
                return Response({"detail": "The VSC explorer returned an unsupported transaction-history response."}, status=502)
            if payload.get("status") == "0" and "no transactions" not in str(payload.get("message", "")).lower():
                return Response({"detail": "The VSC explorer history service is temporarily unavailable."}, status=502)
            items = []
            for item in result[:100]:
                if not isinstance(item, dict) or not HASH_RE.fullmatch(str(item.get("hash", ""))):
                    continue
                value = int(str(item.get("value", "0")) or "0")
                sender = str(item.get("from", ""))
                recipient = str(item.get("to", ""))
                failed = str(item.get("isError", "0")) == "1" or str(item.get("txreceipt_status", "1")) == "0"
                items.append({"tx_hash": item["hash"], "direction": "OUT" if sender.lower() == wallet.address.lower() else "IN", "status": "FAILED" if failed else "CONFIRMED", "from": sender, "to": recipient, "amount_vsg": str(Decimal(value) / WEI), "timestamp": item.get("timeStamp"), "block_number": item.get("blockNumber"), "explorer_url": f"{EXPLORER}/tx/{item['hash']}"})
            return Response({"items": items, "history_complete": True, "source": "VSC Explorer API", "asset": "native VSG"})
        except Exception as exc:
            return Response({"detail": "VSC transaction history is temporarily unavailable. Use the explorer link to inspect this wallet."}, status=503)
