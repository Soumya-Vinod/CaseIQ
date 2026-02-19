from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model for CaseIQ with role-based access.
    """
    
    ROLE_CHOICES = (
        ("citizen", "Citizen"),
        ("officer", "Officer"),
        ("admin", "Admin"),
    )
    
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="citizen")
    is_verified = models.BooleanField(default=False)
    
    # Language preference for bilingual support
    LANGUAGE_CHOICES = (
        ("en", "English"),
        ("hi", "Hindi"),
    )
    preferred_language = models.CharField(
        max_length=2, 
        choices=LANGUAGE_CHOICES, 
        default="en"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["email"]),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"