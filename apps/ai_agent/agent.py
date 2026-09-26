
import re
from dataclasses import dataclass, field

from apps.ai_agent.tools import TOOL_REGISTRY, execute_tool


@dataclass
class ToolCall:
    tool_name: str
    params: dict = field(default_factory=dict)


class AgentProvider:
    """
    Base interface for anything that turns a user message into a
    ToolCall.
    """

    def decide(self, *, message: str, user) -> ToolCall:
        raise NotImplementedError


class KeywordAgentProvider(AgentProvider):
    """
    Deterministic, dependency-free default provider. Matches simple
    keywords/patterns in the message to a known tool. Makes no
    network calls, so it's safe to run with no external API key
    configured.
    """

    TRACKING_PATTERN = re.compile(r"\bSD[0-9A-F]{6,}\b", re.IGNORECASE)
    ID_PATTERN = re.compile(r"\b(\d+)\b")

    def decide(self, *, message: str, user) -> ToolCall:
        text = message.lower().strip()
        tracking_match = self.TRACKING_PATTERN.search(message)
        id_match = self.ID_PATTERN.search(message)

        if "delayed" in text:
            return ToolCall("get_delayed_deliveries")

        if "available driver" in text or "available drivers" in text or "who is free" in text:
            return ToolCall("get_available_drivers")

        if "my shipment" in text or "my order" in text or "my delivery" in text:
            return ToolCall("get_customer_shipments")

        if "reassign" in text:
            return ToolCall(
                "reassign_driver",
                {
                    "shipment_id": int(id_match.group(1)) if id_match else None,
                    "driver_id": None,
                },
            )

        if "assign" in text:
            return ToolCall(
                "assign_driver",
                {
                    "shipment_id": int(id_match.group(1)) if id_match else None,
                    "driver_id": None,
                },
            )

        if "status" in text and "update" in text:
            return ToolCall(
                "update_shipment_status",
                {
                    "shipment_id": int(id_match.group(1)) if id_match else None,
                    "status": None,
                },
            )

        if "driver" in text and id_match:
            return ToolCall("get_driver_details", {"driver_profile_id": int(id_match.group(1))})

        if tracking_match or "track" in text or "status" in text:
            return ToolCall(
                "get_delivery_status",
                {
                    "tracking_number": tracking_match.group(0) if tracking_match else None,
                    "shipment_id": int(id_match.group(1)) if (id_match and not tracking_match) else None,
                },
            )

        return ToolCall("unrecognized")


class Agent:
    """
    Orchestrates a single chat turn. Never touches the database
    directly — only delegates to the tools layer.
    """

    def __init__(self, provider: AgentProvider = None):
        self.provider = provider or KeywordAgentProvider()

    def handle_message(self, *, message: str, user, extra_params: dict = None) -> dict:
        if not message or not message.strip():
            return {"success": False, "reply": "Please enter a message.", "tool": None}

        tool_call = self.provider.decide(message=message, user=user)

        if extra_params:
            tool_call.params.update({k: v for k, v in extra_params.items() if v is not None})

        if tool_call.tool_name not in TOOL_REGISTRY:
            return {
                "success": False,
                "reply": "Sorry, I couldn't understand that request.",
                "tool": tool_call.tool_name,
            }

        return execute_tool(
            tool_name=tool_call.tool_name,
            params=tool_call.params,
            user=user,
            raw_message=message,
        )