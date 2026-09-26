
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_agent.agent import Agent


class ChatbotView(APIView):
    

    permission_classes = [IsAuthenticated]

    def post(self, request):
        message = request.data.get("message")
        if not isinstance(message, str) or not message.strip():
            return Response(
                {"success": False, "reply": "A non-empty 'message' field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        extra_params = request.data.get("params")
        if extra_params is not None and not isinstance(extra_params, dict):
            return Response(
                {"success": False, "reply": "'params' must be an object."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        agent = Agent()
        outcome = agent.handle_message(message=message, user=request.user, extra_params=extra_params)
        return Response(outcome, status=status.HTTP_200_OK)