"""
Matter Storage

JSON-based persistence for legal matters (conversations).
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.config import DATA_DIR


class MatterStorage:
    """Handles persistence of legal matters to JSON files."""

    def __init__(self, data_dir: str | None = None):
        self.data_dir = Path(data_dir or DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _matter_path(self, matter_id: str) -> Path:
        """Get the file path for a matter."""
        return self.data_dir / f"{matter_id}.json"

    def create_matter(
        self,
        matter_name: str | None = None,
        practice_area: str | None = None,
        jurisdiction: str | None = None,
        client: str | None = None
    ) -> dict[str, Any]:
        """
        Create a new legal matter.

        Args:
            matter_name: Name/title of the matter
            practice_area: Type of law (e.g., "employment", "civil")
            jurisdiction: Applicable jurisdiction
            client: Client name/identifier

        Returns:
            The created matter dict
        """
        matter_id = f"matter_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow().isoformat() + "Z"

        matter = {
            "id": matter_id,
            "created_at": now,
            "updated_at": now,
            "metadata": {
                "matter_name": matter_name or "New Matter",
                "practice_area": practice_area or "civil",
                "jurisdiction": jurisdiction or "federal",
                "client": client
            },
            "messages": []
        }

        self._save_matter(matter)
        return matter

    def get_matter(self, matter_id: str) -> dict[str, Any] | None:
        """
        Retrieve a matter by ID.

        Args:
            matter_id: The matter identifier

        Returns:
            The matter dict or None if not found
        """
        path = self._matter_path(matter_id)
        if not path.exists():
            return None

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_matters(self) -> list[dict[str, Any]]:
        """
        List all matters with summary info.

        Returns:
            List of matter summaries (id, metadata, timestamps)
        """
        matters = []
        for path in sorted(self.data_dir.glob("matter_*.json"), reverse=True):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    matter = json.load(f)
                    matters.append({
                        "id": matter["id"],
                        "created_at": matter["created_at"],
                        "updated_at": matter["updated_at"],
                        "metadata": matter["metadata"],
                        "message_count": len(matter.get("messages", []))
                    })
            except (json.JSONDecodeError, KeyError):
                continue
        return matters

    def update_matter(self, matter_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        """
        Update a matter's metadata.

        Args:
            matter_id: The matter identifier
            updates: Dict of metadata fields to update

        Returns:
            The updated matter or None if not found
        """
        matter = self.get_matter(matter_id)
        if not matter:
            return None

        matter["metadata"].update(updates)
        matter["updated_at"] = datetime.utcnow().isoformat() + "Z"
        self._save_matter(matter)
        return matter

    def delete_matter(self, matter_id: str) -> bool:
        """
        Delete a matter.

        Args:
            matter_id: The matter identifier

        Returns:
            True if deleted, False if not found
        """
        path = self._matter_path(matter_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def add_message(
        self,
        matter_id: str,
        role: str,
        content: str | None = None,
        context: str | None = None,
        stage1: dict | None = None,
        stage2: dict | None = None,
        stage3: dict | None = None
    ) -> dict[str, Any] | None:
        """
        Add a message to a matter.

        Args:
            matter_id: The matter identifier
            role: "user" or "assistant"
            content: Message content (for user messages)
            context: Additional context (for user messages)
            stage1: Stage 1 analyses (for assistant messages)
            stage2: Stage 2 assessments (for assistant messages)
            stage3: Stage 3 strategy (for assistant messages)

        Returns:
            The updated matter or None if not found
        """
        matter = self.get_matter(matter_id)
        if not matter:
            return None

        now = datetime.utcnow().isoformat() + "Z"

        message: dict[str, Any] = {
            "role": role,
            "timestamp": now
        }

        if role == "user":
            message["content"] = content
            if context:
                message["context"] = context
        else:
            if stage1:
                message["stage1"] = stage1
            if stage2:
                message["stage2"] = stage2
            if stage3:
                message["stage3"] = stage3

        matter["messages"].append(message)
        matter["updated_at"] = now
        self._save_matter(matter)
        return matter

    def update_message_stage(
        self,
        matter_id: str,
        message_index: int,
        stage: str,
        data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Update a specific stage of an assistant message.

        Args:
            matter_id: The matter identifier
            message_index: Index of the message to update
            stage: "stage1", "stage2", or "stage3"
            data: The stage data to set

        Returns:
            The updated matter or None if not found
        """
        matter = self.get_matter(matter_id)
        if not matter or message_index >= len(matter["messages"]):
            return None

        matter["messages"][message_index][stage] = data
        matter["updated_at"] = datetime.utcnow().isoformat() + "Z"
        self._save_matter(matter)
        return matter

    def _save_matter(self, matter: dict[str, Any]) -> None:
        """Save a matter to disk."""
        path = self._matter_path(matter["id"])
        with open(path, "w", encoding="utf-8") as f:
            json.dump(matter, f, indent=2, ensure_ascii=False)


# Global storage instance
_storage: MatterStorage | None = None


def get_storage() -> MatterStorage:
    """Get the global storage instance."""
    global _storage
    if _storage is None:
        _storage = MatterStorage()
    return _storage
