from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """Common interface every specialized research agent implements."""

    name: str = "base_agent"
    description: str = ""

    @abstractmethod
    async def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute the agent against a query and return a structured result.

        `context` carries data handed off from the Research Planner or from
        upstream agents (e.g. retrieved documents, prior agent outputs).
        """
        raise NotImplementedError
