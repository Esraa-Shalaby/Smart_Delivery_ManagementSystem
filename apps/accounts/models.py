"""
Models for the accounts app.

Defines the project's single, scalable custom User model.
Role-specific profile data belongs in separate models/files, not here.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model shared by all roles (customer, driver, manager).

    Authentication still uses username + password (Django defaults);
    email is kept unique so it can double as a secondary identifier.
    """

    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        DRIVER = "DRIVER", "Driver"
        MANAGER = "MANAGER", "Manager"

    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.role})"