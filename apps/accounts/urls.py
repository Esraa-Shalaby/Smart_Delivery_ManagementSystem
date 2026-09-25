"""
URL routing for the accounts app.
"""

from django.urls import path

from apps.accounts.views import (
    UserProfileUpdateView,
    UserProfileView,
    UserRegistrationView,
)

app_name = "accounts"

urlpatterns = [
    path("register/", UserRegistrationView.as_view(), name="register"),
    path("profile/", UserProfileView.as_view(), name="profile"),
    path("profile/update/", UserProfileUpdateView.as_view(), name="profile-update"),
]