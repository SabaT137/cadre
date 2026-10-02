from fastapi import APIRouter, Depends

from app.auth.deps import CurrentUser, current_user
from app.services import invoice_store
from app.services.invoice_pdf import load_finance_config

router = APIRouter(tags=["finance"])


@router.get("/clients")
def clients(user: CurrentUser = Depends(current_user)):
    return [{"id": c.id, "name": c.name, "default_currency": c.default_currency, "email": c.email}
            for c in invoice_store.list_clients()]


@router.get("/invoices")
def invoices(client: str = "", limit: int = 20, user: CurrentUser = Depends(current_user)):
    return [{"invoice_no": inv.invoice_no, "client": name, "issue_date": inv.issue_date.isoformat(),
             "total": inv.total, "currency": inv.currency, "file_id": inv.file_id,
             "service_description": inv.service_description} for inv, name in invoice_store.list_invoices(client, limit)]


@router.get("/finance/bank-accounts")
def bank_accounts(user: CurrentUser = Depends(current_user)):
    return [{"id": a["id"], "label": a["label"], "currency": a["currency"]} for a in load_finance_config()["bank_accounts"]]
