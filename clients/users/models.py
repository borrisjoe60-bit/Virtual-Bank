from django.db import models
from django.contrib.auth.models import AbstractUser
from PIL import Image
from uuid import uuid4
import os

class User(AbstractUser):
    email = models.EmailField(unique=True)
    date_of_birth = models.DateTimeField(null=True)
    profile_picture = models.ImageField(default="default.png", upload_to='profile_pics')
    phone_number = models.BigIntegerField(null=True)
    address = models.CharField(max_length=255, null=True)
    city = models.CharField(max_length=100, null=True)
    state = models.CharField(max_length=100, null=True)
    country = models.CharField(max_length=50, null=True)
    ip_address = models.GenericIPAddressField(unpack_ipv4=True, null=True)

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = f"users_{User.objects.count() + 1}"

        # Login updates last_login via save(update_fields=["last_login"]).
        # Do not reopen or resize the profile image for unrelated field updates.
        update_fields = kwargs.get("update_fields")
        should_process_image = update_fields is None or "profile_picture" in update_fields

        super().save(*args, **kwargs)

        if not should_process_image or not self.profile_picture:
            return

        # Render's container filesystem may not contain older uploaded media.
        # Missing profile files must never prevent login or other user updates.
        try:
            if not self.profile_picture.storage.exists(self.profile_picture.name):
                return
            with self.profile_picture.open("rb") as image_file:
                img = Image.open(image_file)
                img.load()
                if img.height > 300 or img.width > 300:
                    img.thumbnail((300, 300))
                    img_format = img.format or "JPEG"
                    with self.profile_picture.open("wb") as output_file:
                        img.save(output_file, format=img_format)
        except (FileNotFoundError, OSError, ValueError):
            # Keep the account usable if an uploaded image is missing or invalid.
            return