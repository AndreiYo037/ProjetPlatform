"""The certificate, as a landscape A4 PDF.

Merit is gold, Completion is navy, and a placing ("3rd Place") swaps the gold
for the medal colour and adds a ribbon. The names of the whole team are printed
together on the one certificate.
"""

from __future__ import annotations

import io
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

W, H = landscape(A4)
NAVY = colors.HexColor("#0b1a5c")
GOLD = colors.HexColor("#b8892b")
SILVER = colors.HexColor("#7d8793")
BRONZE = colors.HexColor("#a9622b")
INK = colors.HexColor("#1d2530")
MUTED = colors.HexColor("#5d6877")
CREAM = colors.HexColor("#fffdf7")
MM = 2.83

_PROJET_MARK = Path(__file__).resolve().parent.parent / "assets" / "projet-mark.png"
_WORDS = {"1st": "first", "2nd": "second", "3rd": "third"}


def join_names(names: list[str]) -> str:
    names = [n.strip() for n in names if n and n.strip()]
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def _centre(c: canvas.Canvas, y: float, text: str, font: str, size: float, color=INK, spacing=0.0):
    c.setFont(font, size)
    c.setFillColor(color)
    if spacing:
        t = c.beginText()
        width = c.stringWidth(text, font, size) + spacing * (len(text) - 1)
        t.setTextOrigin((W - width) / 2, y)
        t.setFont(font, size)
        t.setCharSpace(spacing)
        t.textOut(text)
        t.setCharSpace(0)
        c.drawText(t)
    else:
        c.drawCentredString(W / 2, y, text)


def _wrap(c, y, text, font, size, color, maxw, leading) -> float:
    words, line, lines = text.split(), "", []
    for word in words:
        trial = (line + " " + word).strip()
        if c.stringWidth(trial, font, size) <= maxw:
            line = trial
        else:
            lines.append(line)
            line = word
    lines.append(line)
    for ln in lines:
        _centre(c, y, ln, font, size, color)
        y -= leading
    return y


def _frame(c, accent) -> None:
    c.setFillColor(CREAM)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setStrokeColor(NAVY)
    c.setLineWidth(3)
    c.rect(14 * MM, 14 * MM, W - 28 * MM, H - 28 * MM)
    c.setStrokeColor(accent)
    c.setLineWidth(0.9)
    c.rect(19 * MM, 19 * MM, W - 38 * MM, H - 38 * MM)
    c.setFillColor(accent)
    for x, y in [(24, 24), (W / MM - 24, 24), (24, H / MM - 24), (W / MM - 24, H / MM - 24)]:
        c.circle(x * MM, y * MM, 2.2, fill=1, stroke=0)


def _header(c, logo_png: bytes | None, event_name: str | None) -> None:
    if logo_png:
        try:
            img = ImageReader(io.BytesIO(logo_png))
            iw, ih = img.getSize()
            h = 40.0
            w = h * iw / ih
            if w > 150:
                w, h = 150.0, 150.0 * ih / iw
            c.drawImage(img, (W - w) / 2, H - 52 - h, w, h, mask="auto")
        except Exception:
            pass
    if event_name:
        _centre(c, H - 128, event_name.upper(), "Helvetica-Bold", 10, MUTED, spacing=3)


def _seal(c, x, y, label, accent) -> None:
    c.setFillColor(accent)
    c.circle(x, y, 38, fill=1, stroke=0)
    c.setStrokeColor(CREAM)
    c.setLineWidth(1.4)
    c.circle(x, y, 33, fill=0, stroke=1)
    c.circle(x, y, 29, fill=0, stroke=1)
    c.setFillColor(CREAM)
    c.setFont("Times-Bold", 11 if len(label) < 8 else 7.5)
    c.drawCentredString(x, y + 2, label)


def _ribbon(c, x, y, numeral, accent) -> None:
    c.setFillColor(accent)
    for sign in (-1, 1):
        p = c.beginPath()
        p.moveTo(x + sign * 22, y - 30)
        p.lineTo(x + sign * 36, y - 78)
        p.lineTo(x + sign * 14, y - 66)
        p.lineTo(x + sign * 2, y - 80)
        p.lineTo(x - sign * 6, y - 30)
        c.drawPath(p, fill=1, stroke=0)
    c.circle(x, y, 40, fill=1, stroke=0)
    c.setStrokeColor(CREAM)
    c.setLineWidth(1.4)
    c.circle(x, y, 35, fill=0, stroke=1)
    c.circle(x, y, 31, fill=0, stroke=1)
    c.setFillColor(CREAM)
    c.setFont("Times-Bold", 30)
    c.drawCentredString(x, y - 6, numeral)
    c.setFont("Times-Roman", 7)
    c.drawCentredString(x, y - 20, "PLACE")


def _projet_footer(c, y) -> None:
    label = "Issued through"
    c.setFont("Helvetica", 8)
    lw = c.stringWidth(label, "Helvetica", 8)
    try:
        img = ImageReader(str(_PROJET_MARK))
        iw, ih = img.getSize()
        h = 16.0
        w = h * iw / ih
    except Exception:
        img, w, h = None, 0.0, 0.0
    total = lw + (6 + w if img else 0)
    x = (W - total) / 2
    c.setFillColor(MUTED)
    c.drawString(x, y + 3, label if img else "Issued through Projet")
    if img:
        c.drawImage(img, x + lw + 6, y - 1, w, h, mask="auto")


def _medal(place_label: str | None):
    label = (place_label or "").lower()
    if label.startswith("1st"):
        return GOLD
    if label.startswith("2nd"):
        return SILVER
    return BRONZE


def render_certificate_pdf(
    *,
    names: list[str],
    tier: str,
    programme_title: str,
    company_name: str,
    logo_png: bytes | None = None,
    place_label: str | None = None,
    rank: int | None = None,
    entries: int | None = None,
    applied_teams: int | None = None,
    submitted_teams: int | None = None,
    event_name: str | None = None,
    event_date: str | None = None,
    joint: bool = False,
) -> bytes:
    merit = tier == "merit"
    placed = merit and bool(place_label)
    accent = (_medal(place_label) if placed else GOLD) if merit else NAVY
    heading = "CERTIFICATE OF MERIT" if merit else "CERTIFICATE OF COMPLETION"

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(W, H))
    c.setTitle(heading.title())
    _frame(c, accent)
    _header(c, logo_png, event_name)

    _centre(c, H - 172, heading, "Times-Bold", 32 if not merit else 34, NAVY, spacing=2)
    c.setStrokeColor(accent)
    c.setLineWidth(1.2)
    c.line(W / 2 - 60, H - 186, W / 2 + 60, H - 186)
    _centre(c, H - 217, "This certificate is awarded to", "Times-Italic", 14, MUTED)

    name = join_names(names)
    size = 38.0
    while c.stringWidth(name, "Times-BoldItalic", size) > W - 220 and size > 18:
        size -= 1
    _centre(c, H - 264, name, "Times-BoldItalic", size, INK)
    half = max(190.0, c.stringWidth(name, "Times-BoldItalic", size) / 2 + 20)
    c.setStrokeColor(INK)
    c.setLineWidth(0.5)
    c.line(W / 2 - half, H - 274, W / 2 + half, H - 274)

    if placed:
        first = (place_label or "").split()[0].lower()
        lead = f"in recognition of {_WORDS.get(first, (place_label or '').lower())} place with"
    elif merit:
        lead = "for a strong solution to"
    else:
        lead = "for completing"
    _centre(c, H - 302, lead, "Times-Roman", 14, INK)
    y = _wrap(c, H - 328, programme_title, "Times-Bold", 16, NAVY, W - 300, 21)
    _centre(c, y - 4, f"set by {company_name}", "Times-Roman", 14, INK)
    y -= 4

    if placed:
        _centre(c, y - 40, place_label or "", "Times-Bold", 22, accent)
        c.setStrokeColor(accent)
        c.setLineWidth(0.8)
        c.line(W / 2 - 230, y - 33, W / 2 - 150, y - 33)
        c.line(W / 2 + 150, y - 33, W / 2 + 230, y - 33)
    elif merit and rank and entries:
        text = f"Ranked {'joint ' if joint else ''}{ordinal(rank)} of {entries} entries"
        _centre(c, y - 40, text, "Times-Bold", 20, GOLD)
    elif not merit:
        _centre(
            c,
            y - 20,
            "by submitting a solution and presenting it to the company's judges",
            "Times-Roman",
            12,
            INK,
        )
        if applied_teams and submitted_teams:
            who = "Your team was" if len(names) > 1 else "You were"
            _wrap(
                c,
                y - 54,
                f"{applied_teams} teams applied for this challenge. Only {submitted_teams} "
                f"submitted a solution. {who} one of them.",
                "Times-BoldItalic",
                14,
                NAVY,
                W - 300,
                19,
            )

    line = "  ·  ".join(part for part in (event_name, event_date) if part)
    if line:
        _centre(c, 98, line, "Times-Roman", 11, MUTED)
    if merit:
        _centre(c, 83, f"Assessed and awarded by {company_name}", "Times-Roman", 11, MUTED)
    _projet_footer(c, 62)

    if placed:
        numeral = (place_label or "").split()[0]
        _ribbon(c, W - 110, 128, numeral, accent)
    else:
        _seal(c, W - 110, 105, "MERIT" if merit else "COMPLETION", accent)
        c.setFillColor(CREAM)
        c.setFont("Times-Roman", 6.5)
        if event_name:
            c.drawCentredString(W - 110, 105 - 9, event_name.upper()[:18])
    c.showPage()
    c.save()
    return buffer.getvalue()
