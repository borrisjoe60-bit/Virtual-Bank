from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="VscWallet",
            fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("address", models.CharField(max_length=42)), ("chain_id", models.PositiveIntegerField(default=420042)), ("label", models.CharField(blank=True, max_length=80)), ("created_at", models.DateTimeField(auto_now_add=True)), ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="vsc_wallets", to=settings.AUTH_USER_MODEL))],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddConstraint(model_name="vscwallet", constraint=models.UniqueConstraint(fields=("user", "chain_id", "address"), name="unique_user_vsc_wallet")),
        migrations.CreateModel(
            name="VscTransaction",
            fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("tx_hash", models.CharField(max_length=66, unique=True)), ("direction", models.CharField(choices=[("IN", "Incoming"), ("OUT", "Outgoing")], max_length=10)), ("amount_wei", models.DecimalField(blank=True, decimal_places=0, max_digits=78, null=True)), ("status", models.CharField(default="SUBMITTED", max_length=20)), ("created_at", models.DateTimeField(auto_now_add=True)), ("wallet", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="transactions", to="vsc_wallet.vscwallet"))],
            options={"ordering": ("-created_at",)},
        ),
    ]
