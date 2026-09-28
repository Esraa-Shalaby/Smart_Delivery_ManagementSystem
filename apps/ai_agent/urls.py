"""
URL routing for the ai_agent app.
"""

from django.urls import path

from apps.ai_agent.views import ChatbotView

app_name = "ai_agent"

urlpatterns = [
    path("chat/", ChatbotView.as_view(), name="chat"),
]
