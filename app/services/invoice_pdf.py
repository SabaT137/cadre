"""Render invoices on the Stixor letterhead with ReportLab.

Layout coordinates are taken from the original Word-exported invoice (US Letter, 612x792 pt).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path

import yaml
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from app.config import ROOT_DIR, get_settings

PAGE_W, PAGE_H = letter
LEFT = 71
RIGHT = PAGE_W - 71
ACCENT = colors.HexColor("#7B4FE0")
FONT, BOLD = "Helvetica", "Helvetica-Bold"  # metric-compatible with Arial used in the original


@lru_cache
def load_finance_config() -> dict:
    return yaml.safe_load(get_settings().finance_config.read_text())


def bank_account(account_id: str) -> dict:
    for acc in load_finance_config()["bank_accounts"]:
        if acc["id"] == account_id:
            return acc
    raise KeyError(f"Unknown bank account: {account_id}")


def money(amount: float, currency: str) -> str:
    sym = load_finance_config().get("currency_symbols", {}).get(currency, f"{currency} ")
    text = f"{abs(amount):,.2f}"
    if text.endswith(".00"):
        text = text[:-3]
    return f"{'-' if amount < 0 else ''}{sym}{text}"


@dataclass
class InvoiceDoc:
    invoice_no: str
    client: str
    service_description: str
    issue_date: date
    currency: str
    bank_account_id: str
    line_items: list[dict] = field(default_factory=list)  # description, quantity, unit_price, amount
    subtotal: float = 0.0
    tax_pct: float = 0.0
    tax_amount: float = 0.0
    discount: float = 0.0
    total: float = 0.0
    due_date: date | None = None


def _path(p: str) -> Path:
    path = Path(p)
    return path if path.is_absolute() else ROOT_DIR / path


def _letterhead(c: Canvas, cfg: dict) -> None:
    co = cfg["company"]
    logo = _path(co.get("logo", ""))
    if co.get("logo") and logo.exists():
        c.drawImage(ImageReader(str(logo)), 157, 691, width=63, height=70, mask="auto")
    c.setFillColor(colors.black)
    c.setFont(FONT, 19.5)
    c.drawString(252, 731, " ".join(co["wordmark"]))
    c.setFont(FONT, 11)
    c.drawString(266, 706, " ".join(co["tagline"]))
    c.setFont(FONT, 8.5)
    c.drawString(331, 687, co["suffix"])
    c.setFont(FONT, 10)
    c.drawCentredString(PAGE_W / 2, 650, co["address"])
    # Top band
    c.setFillColor(colors.HexColor("#8172E3"))
    c.rect(0, PAGE_H - 12, PAGE_W, 12, stroke=0, fill=1)
    c.setFillColor(colors.black)


def _footer(c: Canvas, cfg: dict) -> None:
    c.setFillColor(colors.HexColor("#7B68E2"))
    c.rect(0, 0, PAGE_W, 107, stroke=0, fill=1)
    c.setFillColor(colors.HexColor("#BFB9E4"))
    p = c.beginPath()
    p.moveTo(380, 107); p.lineTo(PAGE_W, 107); p.lineTo(PAGE_W, 0); p.lineTo(462, 0); p.close()
    c.drawPath(p, stroke=0, fill=1)
    c.setFillColor(colors.HexColor("#A99CF2"))
    p = c.beginPath()
    p.moveTo(290, 0); p.lineTo(396, 82); p.lineTo(462, 0); p.close()
    c.drawPath(p, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Times-Roman", 13)
    for i, line in enumerate(cfg["company"].get("footer_lines", [])[:3]):
        c.drawString(48, 82 - i * 30, line)
    c.setFillColor(colors.black)


def render_invoice(doc: InvoiceDoc, out_path: Path) -> Path:
    cfg = load_finance_config()
    inv_cfg = cfg["invoice"]
    acc = bank_account(doc.bank_account_id)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    c = Canvas(str(out_path), pagesize=letter)
    c.setTitle(f"Invoice {doc.invoice_no} – {doc.client}")
    c.setAuthor(cfg["company"]["legal_name"])

    _letterhead(c, cfg)

    # Invoice number (left) and date (right)
    c.setFont(FONT, 12)
    c.drawString(LEFT, 614, f"Invoice No: {doc.invoice_no}")
    c.drawRightString(RIGHT, 614, f"Date: {doc.issue_date.strftime(inv_cfg['date_format'])}")
    top = 588
    if doc.due_date:
        c.setFont(FONT, 10)
        c.drawRightString(RIGHT, 599, f"Due: {doc.due_date.strftime(inv_cfg['date_format'])}")
        top = 580

    # Intro paragraph
    body = ParagraphStyle("body", fontName=FONT, fontSize=11, leading=20, alignment=TA_JUSTIFY)
    intro = inv_cfg["intro"].format(client=doc.client, service=doc.service_description, beneficiary=acc["beneficiary"])
    para = Paragraph(intro.replace("\n", " "), body)
    _, h = para.wrap(RIGHT - LEFT, 200)
    para.drawOn(c, LEFT, top - h)
    y = top - h - 24

    # Bank details
    rows = [
        ("Bank Address:", acc["bank_address"]),
        ("Bank Name:", acc["bank_name"]),
        ("Beneficiary Name:", acc["beneficiary"]),
        ("Account Number:", acc["account_number"]),
        ("IBAN:", acc.get("iban", "")),
        ("Swift Code:", acc.get("swift", "")),
    ]
    rows = [r for r in rows if r[1]]
    t = Table(rows, colWidths=[110, RIGHT - LEFT - 110], rowHeights=18)
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), FONT, 11),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    _, th = t.wrap(RIGHT - LEFT, 300)
    t.drawOn(c, LEFT + 1, y - th)
    y = y - th - 32

    # Title
    c.setFont(BOLD, 14)
    c.drawCentredString(PAGE_W / 2, y, "INVOICE")
    y -= 26

    # Line items (optional) + totals
    has_items = len(doc.line_items) > 1 or (
        doc.line_items and (doc.line_items[0].get("quantity", 1) != 1 or doc.line_items[0].get("description"))
    )
    if has_items:
        data = [["Description", "Qty / Hours", "Rate", "Amount"]]
        for it in doc.line_items:
            data.append([
                Paragraph(it.get("description", ""), ParagraphStyle("cell", fontName=FONT, fontSize=10, leading=12)),
                f"{it.get('quantity', 1):g}",
                money(it.get("unit_price", it.get("amount", 0)), doc.currency),
                money(it["amount"], doc.currency),
            ])
        tbl = Table(data, colWidths=[(RIGHT - LEFT) - 250, 80, 80, 90], repeatRows=1)
        tbl.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, 0), BOLD, 10),
            ("FONT", (0, 1), (-1, -1), FONT, 10),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, ACCENT),
            ("LINEBELOW", (0, -1), (-1, -1), 0.4, colors.grey),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (0, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        _, h = tbl.wrap(RIGHT - LEFT, 400)
        tbl.drawOn(c, LEFT, y - h)
        y = y - h - 20

    c.setFont(FONT, 11)
    if doc.tax_amount or doc.discount or has_items:
        for label, val in (("Subtotal", doc.subtotal),
                           (f"Tax ({doc.tax_pct:g}%)", doc.tax_amount if doc.tax_amount else None),
                           ("Discount", -doc.discount if doc.discount else None)):
            if val is None:
                continue
            c.drawString(RIGHT - 210, y, label)
            c.drawRightString(RIGHT, y, money(val, doc.currency))
            y -= 18
        y -= 4
    c.setFont(BOLD if has_items else FONT, 12 if has_items else 11)
    c.drawString(LEFT, y, "Payable Now")
    c.setFont(BOLD if has_items else FONT, 12)
    c.drawRightString(RIGHT, y, money(doc.total, doc.currency))

    # Signature block: at its original position, lower if content ran long, next page if it can't fit.
    sig = cfg["signatory"]
    sig_y = min(180, y - 34 - (73 if sig.get("apply_signature_image") else 0))
    if sig_y < 150:
        _footer(c, cfg)
        c.showPage()
        _letterhead(c, cfg)
        sig_y = 560
    sig_img = _path(sig.get("signature_image", ""))
    if sig.get("apply_signature_image") and sig_img.exists():
        c.drawImage(ImageReader(str(sig_img)), 59, sig_y + 2, width=116, height=73, mask="auto")
    c.setFont(FONT, 12)
    c.drawString(55, sig_y, "_" * 16)
    c.drawString(55, sig_y - 19, f"{sig['name']},")
    c.drawString(52, sig_y - 42, sig["title"])

    _footer(c, cfg)

    c.showPage()
    c.save()
    return out_path
