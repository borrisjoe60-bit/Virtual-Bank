from django.urls import path
from .views import VscApiRootView, VscNetworkView, VscWalletListCreateView, VscBalanceView, VscDepositView, VscWithdrawBroadcastView, VscHistoryView, VscRecordTransactionView

urlpatterns = [
    path("", VscApiRootView.as_view(), name="vsc-api-root"),
    path("network/", VscNetworkView.as_view(), name="vsc-network"),
    path("wallets/", VscWalletListCreateView.as_view(), name="vsc-wallets"),
    path("wallets/<int:wallet_id>/balance/", VscBalanceView.as_view(), name="vsc-balance"),
    path("wallets/<int:wallet_id>/deposit/", VscDepositView.as_view(), name="vsc-deposit"),
    path("wallets/<int:wallet_id>/withdraw/", VscWithdrawBroadcastView.as_view(), name="vsc-withdraw"),
    path("wallets/<int:wallet_id>/transactions/record/", VscRecordTransactionView.as_view(), name="vsc-record-transaction"),
    path("wallets/<int:wallet_id>/history/", VscHistoryView.as_view(), name="vsc-history"),
]
