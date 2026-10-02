from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.api.schemas import TemplateInfo
from app.auth.deps import CurrentUser, current_user
from app.config import get_settings
from app.services import docx_filler, usage
from app.services.template_store import get_store

router = APIRouter(tags=["templates & files"], dependencies=[Depends(current_user)])
MIME = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pdf": "application/pdf",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
    ".md": "text/markdown",
}


@router.get("/templates", response_model=list[TemplateInfo])
def list_templates():
    return get_store().list()


@router.post("/templates", response_model=TemplateInfo, status_code=201)
async def upload_template(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    description: str = Form(""),
):
    if not (file.filename or "").lower().endswith(".docx"):
        raise HTTPException(400, "Only .docx templates are supported.")
    content = await file.read()
    if len(content) > get_settings().max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "File too large.")
    try:
        return get_store().add(file.filename, content, name=name, description=description)
    except Exception as e:
        raise HTTPException(400, f"Could not read the .docx file: {e}")


@router.get("/templates/{template_id}/placeholders")
def template_placeholders(template_id: str):
    try:
        path = get_store().template_path(template_id)
    except KeyError as e:
        raise HTTPException(404, str(e))
    return docx_filler.scan(path)


@router.get("/files/{file_id}")
def download_file(file_id: str, inline: bool = False, user: CurrentUser = Depends(current_user)):
    if not usage.can_access_file(file_id, user.id, user.is_admin, user.allowed_agents):
        raise HTTPException(404, "Unknown file")
    try:
        path = get_store().output_path(file_id)
    except KeyError as e:
        raise HTTPException(404, str(e))
    return FileResponse(path, media_type=MIME.get(path.suffix, "application/octet-stream"), filename=path.name,
                        content_disposition_type="inline" if inline else "attachment")
