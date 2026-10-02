"""Clients, invoice maths, numbering and persistence."""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select

from app.db.models import Client, Invoice
from app.db.session import session_scope
from app.services.invoice_pdf import InvoiceDoc, bank_account, load_finance_config, render_invoice
from app.services.template_store import get_store


def calculate(line_items: list[dict], tax_pct: float = 0.0, discount: float = 0.0) -> dict:
    items = []
    for it in line_items:
        qty = float(it.get("quantity", 1) or 1)
        if it.get("unit_price") is not None:
            price = float(it["unit_price"])
        elif it.get("amount") is not None:
            price = float(it["amount"]) / qty
        else:
            raise ValueError(f"Line item needs unit_price or amount: {it}")
        items.append({
            "description": str(it.get("description", "")).strip(),
            "quantity": qty,
            "unit_price": round(price, 2),
            "amount": round(qty * price, 2),
        })
    if not items:
        raise ValueError("At least one line item or amount is required")
    subtotal = round(sum(i["amount"] for i in items), 2)
    tax_amount = round(subtotal * float(tax_pct or 0) / 100, 2)
    total = round(subtotal + tax_amount - float(discount or 0), 2)
    if total < 0:
        raise ValueError("Total cannot be negative")
    return {"line_items": items, "subtotal": subtotal, "tax_pct": float(tax_pct or 0),
            "tax_amount": tax_amount, "discount": float(discount or 0), "total": total}


def seed_clients() -> None:
    with session_scope() as s:
        if s.scalar(select(func.count()).select_from(Client)) == 0:
            s.add(Client(name="Isekaiverse", default_currency="USD", default_bank_account="usd_first_century"))


def find_client(name: str) -> Client | None:
    with session_scope() as s:
        exact = s.scalar(select(Client).where(func.lower(Client.name) == name.strip().lower()))
        if exact:
            return exact
        return s.scalar(select(Client).where(Client.name.ilike(f"%{name.strip()}%")))


def list_clients(query: str = "") -> list[Client]:
    with session_scope() as s:
        stmt = select(Client).order_by(Client.name)
        if query:
            stmt = stmt.where(Client.name.ilike(f"%{query}%"))
        return list(s.scalars(stmt))


def add_client(**fields) -> Client:
    with session_scope() as s:
        client = Client(**fields)
        s.add(client)
        s.flush()
        return client


def _next_number(s, issue: date) -> str:
    fmt = load_finance_config()["invoice"]["number_format"]
    prefix = fmt.split("{seq")[0].format(year=issue.year)
    count = s.scalar(select(func.count()).select_from(Invoice).where(Invoice.invoice_no.like(f"{prefix}%")))
    return fmt.format(year=issue.year, seq=count + 1)


def create_invoice(
    *, client_name: str, service_description: str, line_items: list[dict], currency: str | None,
    bank_account_id: str | None, issue_date: date | None, due_date: date | None, tax_pct: float, discount: float,
    created_by: int,
) -> Invoice:
    cfg = load_finance_config()
    client = find_client(client_name)
    if client is None:
        raise ValueError(f"Unknown client {client_name!r}; add the client first.")
    currency = (currency or client.default_currency or cfg["invoice"]["default_currency"]).upper()
    if not bank_account_id:
        bank_account_id = client.default_bank_account or next(
            (a["id"] for a in cfg["bank_accounts"] if a["currency"] == currency), cfg["bank_accounts"][0]["id"])
    acc = bank_account(bank_account_id)
    if acc["currency"] != currency:
        raise ValueError(f"Bank account {bank_account_id} is {acc['currency']}, invoice currency is {currency}.")
    calc = calculate(line_items, tax_pct, discount)
    issue = issue_date or date.today()
    terms = int(cfg["invoice"].get("payment_terms_days") or 0)
    due = due_date or (issue + timedelta(days=terms) if terms else None)

    store = get_store()
    with session_scope() as s:
        number = _next_number(s, issue)
        file_id, _ = store.new_output_path(f"invoice_{number}_{client.name}")
        pdf_path = store.outputs_dir / f"{file_id}.pdf"
        render_invoice(InvoiceDoc(
            invoice_no=number, client=client.name, service_description=service_description, issue_date=issue,
            currency=currency, bank_account_id=bank_account_id, due_date=due, **calc,
        ), pdf_path)
        inv = Invoice(
            invoice_no=number, client_id=client.id, service_description=service_description, issue_date=issue,
            due_date=due, currency=currency, bank_account_id=bank_account_id, file_id=file_id, created_by=created_by,
            **calc,
        )
        s.add(inv)
        s.flush()
        return inv


def list_invoices(client_name: str = "", limit: int = 20) -> list[tuple[Invoice, str]]:
    with session_scope() as s:
        stmt = select(Invoice, Client.name).join(Client, Client.id == Invoice.client_id).order_by(Invoice.id.desc()).limit(limit)
        if client_name:
            stmt = stmt.where(Client.name.ilike(f"%{client_name}%"))
        return [(inv, name) for inv, name in s.execute(stmt)]


def get_invoice(invoice_no: str) -> tuple[Invoice, str] | None:
    with session_scope() as s:
        row = s.execute(select(Invoice, Client.name).join(Client, Client.id == Invoice.client_id)
                        .where(Invoice.invoice_no == invoice_no)).first()
        return (row[0], row[1]) if row else None
