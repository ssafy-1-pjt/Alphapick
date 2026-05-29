from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class RiskType(models.TextChoices):
        AGGRESSIVE = "aggressive", "Aggressive"
        NEUTRAL = "neutral", "Neutral"
        STABLE = "stable", "Stable"

    nickname = models.CharField(max_length=40, blank=True)
    risk_type = models.CharField(
        max_length=20,
        choices=RiskType.choices,
        default=RiskType.NEUTRAL,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def display_name(self):
        return self.nickname or self.username
