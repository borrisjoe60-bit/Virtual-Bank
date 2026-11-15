from django.conf import settings
from django.db import models


class VscWallet(models.Model):
    """Non-custodial wallet address registered by an authenticated user."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vsc_wallets")
    address = models.CharField(max_length=42)
    chain_id = models.PositiveIntegerField(default=420042)
    label = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("user", "chain_id", "address"), name="unique_user_vsc_wallet")]
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.address} (VSC)"


class VscTransaction(models.Model):
    wallet = models.ForeignKey(VscWallet, on_delete=models.CASCADE, related_name="transactions")
    tx_hash = models.CharField(max_length=66, unique=True)
    direction = models.CharField(max_length=10, choices=(("IN", "Incoming"), ("OUT", "Outgoing")))
    amount_wei = models.DecimalField(max_digits=78, decimal_places=0, null=True, blank=True)
    status = models.CharField(max_length=20, default="SUBMITTED")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
