from dataclasses import dataclass
from typing import Any

from . import gemini_client


@dataclass
class Agent:
    name: str
    system_prompt: str
    schema: dict[str, Any]

    def responder_json(self, prompt: str) -> dict:
        return gemini_client.call_tool(self.system_prompt, prompt, "responder", self.schema)
