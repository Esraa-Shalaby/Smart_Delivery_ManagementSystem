 

from django.conf import settings
from django.db import models


class AIAction(models.Model):
   

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="ai_actions",
    )
    action = models.CharField(max_length=100, db_index=True)
    input = models.TextField(blank=True)
    result = models.TextField(blank=True)
    success = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        outcome = "OK" if self.success else "FAILED"
        return f"[{outcome}] {self.action} ({self.user})"