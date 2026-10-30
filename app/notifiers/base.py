from abc import ABC, abstractmethod
from typing import Dict, Any
from app.core.models import AlertEvent

class BaseNotifier(ABC):
    channel_name: str = "base"

    @abstractmethod
    def send(self, alert: AlertEvent) -> bool:
        """Send alert notification. Returns True if successful, False otherwise."""
        pass
