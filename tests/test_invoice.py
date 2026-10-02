from datetime import date

import pytest
from pypdf import PdfReader

from app.db.session import init_db
from app.services import invoice_store
from app.services.template_store import get_store


@pytest.fixture(scope="module", autouse=True)
def db():
    init_db()
    invoice_store.seed_clients()


def test_calculate_hours_tax_discount():
    calc = invoice_store.calculate(
        [{"description": "FE", "quantity": 40, "unit_price": 15}, {"description": "BE", "quantity": 25, "unit_price": 18}],
        tax_pct=5, discount=50,
    )
    assert calc["subtotal"] == 1050 and calc["tax_amount"] == 52.5 and calc["total"] == 1052.5


def test_calculate_fixed_amount_and_validation():
    assert invoice_store.calculate([{"amount": 100}])["total"] == 100
    with pytest.raises(ValueError):
        invoice_store.calculate([])
    with pytest.raises(ValueError):
        invoice_store.calculate([{"amount": 10}], discount=50)


def test_create_invoice_pdf_and_numbering():
    a = invoice_store.create_invoice(
        client_name="isekai", service_description="the development of the website", line_items=[{"amount": 100}],
        currency=None, bank_account_id=None, issue_date=date(2026, 1, 5), due_date=None, tax_pct=0, discount=0, created_by=1,
    )
    b = invoice_store.create_invoice(
        client_name="Isekaiverse", service_description="maintenance", line_items=[{"description": "Support", "quantity": 10, "unit_price": 20}],
        currency="USD", bank_account_id="usd_first_century", issue_date=date(2026, 2, 1), due_date=None, tax_pct=0,
        discount=0, created_by=1,
    )
    assert a.invoice_no == "STX-2026-0001" and b.invoice_no == "STX-2026-0002"
    text = PdfReader(get_store().output_path(a.file_id)).pages[0].extract_text()
    for needle in ("Isekaiverse", "the development of the website", "INVOICE", "Payable Now", "$100", "FCSSUS32",
                   "Stixor Technologies Private Limited", "STX-2026-0001", "05/01/2026"):
        assert needle in text, needle


def test_currency_mismatch_and_unknown_client():
    with pytest.raises(ValueError):
        invoice_store.create_invoice(client_name="Isekaiverse", service_description="x", line_items=[{"amount": 1}],
                                     currency="EUR", bank_account_id="usd_first_century", issue_date=None, due_date=None,
                                     tax_pct=0, discount=0, created_by=1)
    with pytest.raises(ValueError):
        invoice_store.create_invoice(client_name="Nobody Ltd", service_description="x", line_items=[{"amount": 1}],
                                     currency=None, bank_account_id=None, issue_date=None, due_date=None, tax_pct=0,
                                     discount=0, created_by=1)
