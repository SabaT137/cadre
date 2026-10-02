from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.services import docx_filler
from app.services.template_store import get_store


class ClauseEdit(BaseModel):
    paragraph_idx: int = Field(description="Paragraph index from read_template_clauses")
    action: Literal["replace", "insert_after", "delete"] = "replace"
    text: str = Field(default="", description="New paragraph text (for replace / insert_after)")


@tool
def list_templates() -> str:
    """List the available contract templates (id, name, description, number of placeholders)."""
    items = get_store().list()
    if not items:
        return "No templates available."
    return "\n".join(
        f"- {t['template_id']}: {t['name']} ({t['placeholder_count']} placeholders). {t.get('description', '')}"
        for t in items
    )


@tool
def inspect_template(template_id: str) -> str:
    """Show every fillable placeholder in a template, numbered, with its section and surrounding text.
    <<HERE>> marks the exact spot of each placeholder. Use the numbers as keys for fill_contract."""
    try:
        path = get_store().template_path(template_id)
    except KeyError as e:
        return str(e)
    lines = [f"Template {template_id} placeholders (id | section | context):"]
    for ph in docx_filler.scan(path):
        lines.append(f"#{ph['id']} | {ph['section'][:40]} | {ph['context']}")
    return "\n".join(lines)


@tool
def read_template_clauses(template_id: str, keyword: str = "") -> str:
    """Read the clause text of a template with paragraph indices, for custom edits.
    keyword filters by section heading or text (e.g. 'TERMINATION', 'notice', 'salary'); empty returns an outline."""
    try:
        path = get_store().template_path(template_id)
    except KeyError as e:
        return str(e)
    paras = docx_filler.paragraphs(path)
    if not keyword:
        sections: list[str] = []
        for p in paras:
            if p["section"] and p["section"] not in sections:
                sections.append(p["section"])
        return "Sections: " + " | ".join(sections)
    kw = keyword.lower()
    hits = [p for p in paras if kw in p["section"].lower() or kw in p["text"].lower()][:40]
    if not hits:
        return f"No paragraphs match {keyword!r}."
    return "\n".join(f"[{p['paragraph_idx']}] ({p['section'][:30]}) {p['text'][:600]}" for p in hits)


@tool(response_format="content_and_artifact")
def fill_contract(
    template_id: str,
    values: dict[str, str],
    output_name: str,
    clause_edits: list[ClauseEdit] | None = None,
) -> tuple[str, dict | None]:
    """Generate the final .docx contract.
    values: map of placeholder id (as string, from inspect_template) to the text to insert, e.g. {"4": "Ali Khan"}.
    output_name: short file name, e.g. "contract_ali_khan".
    clause_edits: optional custom paragraph changes using indices from read_template_clauses."""
    store = get_store()
    try:
        path = store.template_path(template_id)
    except KeyError as e:
        return str(e), None
    file_id, out = store.new_output_path(output_name)
    edits = [e.model_dump() if isinstance(e, BaseModel) else dict(e) for e in (clause_edits or [])]
    result = docx_filler.fill(path, out, values, edits)
    # Signature/witness fields are routinely hand-filled; anything else left as [●] in the body is likely a mistake.
    hand_filled = [u for u in result["unfilled"] if u["kind"] == "blank_field" or "behalf" in u["section"].lower()]
    missed = [u for u in result["unfilled"] if u not in hand_filled]
    summary = (
        f"Contract generated: file_id={file_id}. Filled {result['filled']} placeholders; "
        f"signature/witness fields left blank: {', '.join('#' + str(u['id']) for u in hand_filled) or 'none'}; "
        f"empty list items removed: {result['removed_empty_items'] or 'none'}; "
        f"unknown ids ignored: {result['unknown_ids'] or 'none'}; "
        f"clause edits applied: {len(result['clause_edits_applied'])}."
    )
    if missed:
        summary += "\nWARNING – these body placeholders are still unfilled and will show as [●]:\n" + "\n".join(
            f"#{u['id']} | {u['context']}" for u in missed
        ) + "\nIf you know the values, call fill_contract again with ALL values (it creates a fresh file)."
    artifact = {"type": "file", "file_id": file_id, "filename": f"{file_id}.docx", "template_id": template_id}
    return summary, artifact


HR_TOOLS = [list_templates, inspect_template, read_template_clauses, fill_contract]
