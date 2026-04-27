from django.db import models


class UserProfile(models.Model):
    """Recommendation-side profile for a user owned by another service.

    user_id is opaque (UUID, integer-as-string, etc) — whatever the user
    service uses. Indexed and unique.
    """

    class Language(models.TextChoices):
        EN = "en", "English"
        RU = "ru", "Русский"
        RO = "ro", "Română"

    user_id = models.CharField(max_length=64, unique=True, db_index=True)

    preferred_categories = models.JSONField(default=list, blank=True)
    preferred_raw_categories = models.JSONField(default=list, blank=True)
    home_city = models.CharField(max_length=128, default="Кишинёв")
    language = models.CharField(max_length=2, choices=Language.choices, default=Language.RU)
    max_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    free_only = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_profiles"
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self) -> str:
        return f"UserProfile({self.user_id})"
