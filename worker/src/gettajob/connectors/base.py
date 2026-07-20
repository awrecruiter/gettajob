from abc import ABC, abstractmethod
from typing import Iterable

from gettajob.models import Job


class Connector(ABC):
    source: str

    @property
    @abstractmethod
    def identifier(self) -> str:
        """Human-readable identifier for logs (company slug or query summary)."""

    @abstractmethod
    def fetch(self) -> Iterable[Job]:
        """Yield Job records from the source."""
