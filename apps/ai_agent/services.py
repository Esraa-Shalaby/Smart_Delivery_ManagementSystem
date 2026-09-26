 

import json

from django.db import transaction

from apps.ai_agent.models import AIAction

_MAX_STORED_LENGTH = 2000


def _safe_json(value):
    
    try:
        text = json.dumps(value, default=str)
    except TypeError:
        text = str(value)
    return text[:_MAX_STORED_LENGTH]


@transaction.atomic
def log_ai_action(*, user, action, input_data, result, success):
   
    return AIAction.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        action=action,
        input=_safe_json(input_data),
        result=_safe_json(result),
        success=success,
    )


def get_ai_action_history(*, user=None, limit=50):
    
    queryset = AIAction.objects.all()
    if user is not None:
        queryset = queryset.filter(user=user)
    return queryset.order_by("-created_at")[:limit]