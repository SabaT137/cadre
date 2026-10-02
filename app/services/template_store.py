"""File-based registry of .docx contract templates and generated outputs."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.services import docx_filler

DEFAULT_TEMPLATE_ID = "consultant_hourly_parttime"
DEFAULT_TEMPLATE_META = {
    "name": "Consultant Contract – Part-time, Hourly",
    "description": "Stixor contractor agreement paid in USD per hour, fixed term with auto-renewal, 7-day notice, "
    "NDA/IP clauses and Annexure A job description.",
}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:60] or "file"


class TemplateStore:
    def __init__(self, templates_dir: Path | None = None, outputs_dir: Path | None = None):
        s = get_settings()
        self.templates_dir = templates_dir or s.templates_dir
        self.outputs_dir = outputs_dir or s.outputs_dir
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_default_meta()

    def _ensure_default_meta(self) -> None:
        docx = self.templates_dir / f"{DEFAULT_TEMPLATE_ID}.docx"
        meta = self.templates_dir / f"{DEFAULT_TEMPLATE_ID}.json"
        if docx.exists() and not meta.exists():
            self._write_meta(DEFAULT_TEMPLATE_ID, DEFAULT_TEMPLATE_META["name"], DEFAULT_TEMPLATE_META["description"])

    def _write_meta(self, template_id: str, name: str, description: str) -> dict:
        path = self.template_path(template_id)
        meta = {
            "template_id": template_id,
            "name": name,
            "description": description,
            "placeholder_count": len(docx_filler.scan(path)),
            "uploaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        (self.templates_dir / f"{template_id}.json").write_text(json.dumps(meta, indent=2))
        return meta

    def template_path(self, template_id: str) -> Path:
        if not re.fullmatch(r"[a-z0-9_]+", template_id or ""):
            raise KeyError(f"Invalid template id: {template_id!r}")
        path = self.templates_dir / f"{template_id}.docx"
        if not path.exists():
            raise KeyError(f"Unknown template: {template_id}")
        return path

    def list(self) -> list[dict]:
        items = []
        for meta in sorted(self.templates_dir.glob("*.json")):
            items.append(json.loads(meta.read_text()))
        return items

    def get(self, template_id: str) -> dict:
        self.template_path(template_id)
        return json.loads((self.templates_dir / f"{template_id}.json").read_text())

    def add(self, filename: str, content: bytes, name: str | None = None, description: str = "") -> dict:
        base = _slug(name or Path(filename).stem)
        template_id = f"{base}_{uuid.uuid4().hex[:6]}"
        (self.templates_dir / f"{template_id}.docx").write_bytes(content)
        try:
            return self._write_meta(template_id, name or Path(filename).stem, description)
        except Exception:
            (self.templates_dir / f"{template_id}.docx").unlink(missing_ok=True)
            raise

    # --- generated outputs ---
    def new_output_path(self, output_name: str) -> tuple[str, Path]:
        file_id = f"{_slug(output_name)}_{uuid.uuid4().hex[:8]}"
        return file_id, self.outputs_dir / f"{file_id}.docx"

    def output_path(self, file_id: str) -> Path:
        if not re.fullmatch(r"[a-z0-9_]+", file_id or ""):
            raise KeyError(f"Invalid file id: {file_id!r}")
        matches = sorted(self.outputs_dir.glob(f"{file_id}.*"))
        if not matches:
            raise KeyError(f"Unknown file: {file_id}")
        return matches[0]


_store: TemplateStore | None = None


def get_store() -> TemplateStore:
    global _store
    if _store is None:
        _store = TemplateStore()
    return _store
