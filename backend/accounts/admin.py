from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class AlphaPickUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("AlphaPick Profile", {"fields": ("nickname", "risk_type")}),
    )
    list_display = ("username", "email", "nickname", "risk_type", "is_staff")
