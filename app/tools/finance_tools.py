from datetime import date
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.agents.context import require_run_user
from app.services import invoice_store
from app.services.invoice_pdf import load_finance_config, money


class LineItem(BaseModel):
    description: str = Field(default="", description="What is billed, e.g. 'Frontend development'")
    quantity: float = Field(default=1, description="Hours or units")
    unit_price: Optional[float] = Field(default=None, description="Rate per hour/unit")
    amount: Optional[float] = Field(default=None, description="Use instead of unit_price for a fixed amount")


def _items(line_items: list) -> list[dict]:
    return [i.model_dump() if isinstance(i, BaseModel) else dict(i) for i in line_items]


def _date(value: Optional[str]) -> Optional[date]:
    return date.fromisoformat(value) if value else None


def bank_accounts_text() -> str:
    return "\n".join(f"- {a['id']}: {a['label']} ({a['currency']})" for a in load_finance_config()["bank_accounts"])


@tool
def list_clients(query: str = "") -> str:
    """List known clients (optionally filtered by name) with their default currency and bank account."""
    clients = invoice_store.list_clients(query)
    if not clients:
        return "No matching clients."
    return "\n".join(
        f"- {c.name} | currency {c.default_currency} | bank {c.default_bank_account or '-'}"
        + (f" | rate {c.default_rate}" if c.default_rate else "") + (f" | {c.email}" if c.email else "")
        for c in clients
    )


@tool
def add_client(name: str, contact_name: str = "", email: str = "", address: str = "",
               default_currency: str = "USD", default_rate: Optional[float] = None) -> str:
    """Add a new client. Only call after the user confirmed the details."""
    if invoice_store.find_client(name) and invoice_store.find_client(name).name.lower() == name.lower():
        return f"Client {name} already exists."
    c = invoice_store.add_client(name=name.strip(), contact_name=contact_name, email=email, address=address,
                                 default_currency=default_currency.upper(), default_rate=default_rate)
    return f"Client {c.name} added."


@tool
def list_bank_accounts() -> str:
    """List the company bank accounts invoices can be paid into (id, label, currency)."""
    return bank_accounts_text()


@tool
def calculate_invoice(line_items: list[LineItem], tax_pct: float = 0, discount: float = 0, currency: str = "USD") -> str:
    """Compute line amounts, subtotal, tax and total. Always use this instead of doing arithmetic yourself."""
    try:
        calc = invoice_store.calculate(_items(line_items), tax_pct, discount)
    except ValueError as e:
        return f"ERROR: {e}"
    lines = [f"- {i['description'] or 'Services'}: {i['quantity']:g} × {money(i['unit_price'], currency)} = "
             f"{money(i['amount'], currency)}" for i in calc["line_items"]]
    lines.append(f"Subtotal: {money(calc['subtotal'], currency)}")
    if calc["tax_amount"]:
        lines.append(f"Tax ({calc['tax_pct']:g}%): {money(calc['tax_amount'], currency)}")
    if calc["discount"]:
        lines.append(f"Discount: -{money(calc['discount'], currency)}")
    lines.append(f"TOTAL payable: {money(calc['total'], currency)}")
    return "\n".join(lines)


@tool(response_format="content_and_artifact")
def create_invoice(
    client_name: str,
    service_description: str,
    line_items: list[LineItem],
    currency: str = "",
    bank_account_id: str = "",
    issue_date: str = "",
    due_date: str = "",
    tax_pct: float = 0,
    discount: float = 0,
) -> tuple[str, Optional[dict]]:
    """Generate and save the invoice PDF.
    service_description completes the sentence 'services provided to <client> for ...', e.g. 'the development of the website'.
    For a single fixed amount pass one line item with amount set and empty description.
    Dates are ISO (YYYY-MM-DD); issue_date defaults to today."""
    try:
        inv = invoice_store.create_invoice(
            client_name=client_name, service_description=service_description, line_items=_items(line_items),
            currency=currency or None, bank_account_id=bank_account_id or None, issue_date=_date(issue_date),
            due_date=_date(due_date), tax_pct=tax_pct, discount=discount, created_by=require_run_user().id,
        )
    except (ValueError, KeyError) as e:
        return f"ERROR: {e}", None
    summary = (f"Invoice {inv.invoice_no} created for {client_name}: total {money(inv.total, inv.currency)}, "
               f"bank account {inv.bank_account_id}, issue date {inv.issue_date}, due {inv.due_date or '-'}.")
    return summary, {"type": "file", "file_id": inv.file_id, "filename": f"{inv.invoice_no}.pdf",
                     "mime": "application/pdf", "invoice_no": inv.invoice_no}


@tool
def list_invoices(client_name: str = "", limit: int = 10) -> str:
    """List recent invoices, optionally for one client."""
    rows = invoice_store.list_invoices(client_name, limit)
    if not rows:
        return "No invoices found."
    return "\n".join(
        f"- {inv.invoice_no} | {name} | {inv.issue_date} | {money(inv.total, inv.currency)} | {inv.service_description}"
        f" | items: {', '.join(i['description'] or 'amount' for i in inv.line_items)}"
        for inv, name in rows
    )


@tool(response_format="content_and_artifact")
def duplicate_invoice(invoice_no: str, issue_date: str = "", service_description: str = "",
                      line_items: Optional[list[LineItem]] = None) -> tuple[str, Optional[dict]]:
    """Create a new invoice copied from an existing one (e.g. monthly retainer), optionally changing date,
    description or line items."""
    found = invoice_store.get_invoice(invoice_no)
    if not found:
        return f"ERROR: invoice {invoice_no} not found", None
    old, client = found
    return create_invoice.func(
        client_name=client,
        service_description=service_description or old.service_description,
        line_items=_items(line_items) if line_items else old.line_items,
        currency=old.currency, bank_account_id=old.bank_account_id, issue_date=issue_date,
        tax_pct=old.tax_pct, discount=old.discount,
    )


FINANCE_TOOLS = [list_clients, add_client, list_bank_accounts, calculate_invoice, create_invoice, list_invoices,
                 duplicate_invoice]
