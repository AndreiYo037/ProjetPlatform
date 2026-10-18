"""The testimonial letter, typeset as a real business letter.

Letterhead (logo and company name), the date, an addressee, a Re: line naming
the person and the work, the body, and a signature block. Built on ReportLab:
the earlier hand-written writer could only place one size of Helvetica and no
images, so a letterhead or a signature was impossible.

A letter that has been signed carries the signature and a one-line record of
who signed it and when. An unsigned one is typeset the same way, with a blank
signature line, so the layout never changes shape on signing.
"""

from __future__ import annotations

import io
import re
from datetime import UTC, datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Flowable,
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

PAGE_W, PAGE_H = A4
MARGIN = 25.4 * mm  # one inch, as business-letter guidance asks
LOGO_BOX = (46 * mm, 16 * mm)
SIGNATURE_WIDTH = 52 * mm
SIGNATURE_MAX_HEIGHT = 22 * mm

INK = colors.HexColor("#1b1f27")
MUTED = colors.HexColor("#5d6674")
RULE = colors.HexColor("#c9ced6")

_CLOSING = re.compile(
    r"^\s*(yours\s+(sincerely|faithfully|truly)|sincerely|best\s+regards|kind\s+regards|"
    r"warm\s+regards|regards|best\s+wishes|with\s+thanks)\b",
    re.IGNORECASE,
)


def _safe(text: str) -> str:
    """The built-in fonts are Latin-1 (cp1252). Anything outside it would
    print as a black box, so it becomes a question mark instead."""
    return text.encode("cp1252", "replace").decode("cp1252")


def _p(text: str) -> str:
    return escape(_safe(text))


def has_closing(body: str) -> bool:
    """Did the writer already type their own sign-off ("Yours sincerely, ...")?

    If so the letter does not add a second one; it only places the signature."""
    lines = [line for line in body.strip().splitlines() if line.strip()]
    return any(_CLOSING.match(line) for line in lines[-12:])


def split_at_closing(body: str) -> tuple[str, str] | None:
    """Split the body just after the writer's own closing line, so the signature
    can sit between "Yours sincerely," and their typed name.

    Returns (up to and including the closing, everything after it), or None if
    there is no closing line near the end."""
    lines = body.strip().splitlines()
    for index in range(len(lines) - 1, max(len(lines) - 13, -1), -1):
        if _CLOSING.match(lines[index]):
            return "\n".join(lines[: index + 1]), "\n".join(lines[index + 1 :]).strip("\n")
    return None


def format_date(moment: datetime) -> str:
    """The day in Singapore, where the programme runs, not the server's UTC."""
    from projet.services.schedule import in_programme_tz

    local = in_programme_tz(moment)
    return f"{local.day} {local.strftime('%B %Y')}"


class _Letterhead(Flowable):
    """Logo on the left, company name on the right, a rule beneath."""

    def __init__(self, company_name: str, logo_png: bytes | None, width: float) -> None:
        super().__init__()
        self.company_name = company_name
        self.logo = logo_png
        self.width = width
        self.height = LOGO_BOX[1] + 5 * mm

    def draw(self) -> None:
        canvas = self.canv
        if self.logo:
            try:
                reader = ImageReader(io.BytesIO(self.logo))
                iw, ih = reader.getSize()
                scale = min(LOGO_BOX[0] / iw, LOGO_BOX[1] / ih)
                canvas.drawImage(
                    reader,
                    0,
                    5 * mm + (LOGO_BOX[1] - ih * scale) / 2,
                    width=iw * scale,
                    height=ih * scale,
                    mask="auto",
                )
            except Exception:
                pass  # a logo we cannot read must not stop the letter
        canvas.setFillColor(INK)
        canvas.setFont("Helvetica-Bold", 13)
        canvas.drawRightString(self.width, 5 * mm + LOGO_BOX[1] / 2 - 4, _safe(self.company_name))
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.8)
        canvas.line(0, 1 * mm, self.width, 1 * mm)


def render_testimonial_pdf(
    *,
    body: str,
    author_name: str,
    author_title: str | None = None,
    company_name: str = "",
    programme_title: str = "",
    recipient_name: str = "",
    logo_png: bytes | None = None,
    signature_png: bytes | None = None,
    signature_typed: bool = False,
    signed_at: datetime | None = None,
    letter_date: datetime | None = None,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=18 * mm,
        bottomMargin=22 * mm,
        title=f"Testimonial for {recipient_name}" if recipient_name else "Testimonial",
        author=author_name or company_name or "Projet",
    )
    width = PAGE_W - 2 * MARGIN

    base = ParagraphStyle(
        "body", fontName="Times-Roman", fontSize=11, leading=15.5, textColor=INK, alignment=TA_LEFT
    )
    small = ParagraphStyle("small", parent=base, fontSize=9, leading=12, textColor=MUTED)
    re_style = ParagraphStyle("re", parent=base, fontName="Times-Bold")
    typed_style = ParagraphStyle(
        "typed", parent=base, fontName="Times-Italic", fontSize=24, leading=28
    )

    story: list[Flowable] = [_Letterhead(company_name, logo_png, width), Spacer(1, 9 * mm)]
    story.append(Paragraph(_p(format_date(letter_date or signed_at or datetime.now(UTC))), base))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("To whom it may concern", base))
    story.append(Spacer(1, 5 * mm))

    subject = recipient_name or "Participant"
    re_line = f"Re: {_p(subject)}"
    if programme_title:
        re_line += f"<br/>{_p(programme_title)}"
    story.append(Paragraph(re_line, re_style))
    story.append(Spacer(1, 5 * mm))

    split = split_at_closing(body)
    own_closing = split is not None
    head, tail = split if split else (body, "")

    def add_paragraphs(text: str) -> None:
        for paragraph in re.split(r"\n\s*\n", text.strip()):
            joined = "<br/>".join(_p(line.rstrip()) for line in paragraph.splitlines())
            if joined.strip():
                story.append(Paragraph(joined, base))
                story.append(Spacer(1, 3.2 * mm))

    add_paragraphs(head)
    sign: list[Flowable] = [Spacer(1, 1 * mm)]
    if not own_closing:
        sign.append(Paragraph("Sincerely,", base))
        sign.append(Spacer(1, 2 * mm))
    if signature_png:
        try:
            reader = ImageReader(io.BytesIO(signature_png))
            iw, ih = reader.getSize()
            scale = min(SIGNATURE_WIDTH / iw, SIGNATURE_MAX_HEIGHT / ih)
            sign.append(
                Image(io.BytesIO(signature_png), width=iw * scale, height=ih * scale, hAlign="LEFT")
            )
        except Exception:
            sign.append(Spacer(1, 14 * mm))
    elif signature_typed and author_name:
        sign.append(Paragraph(_p(author_name), typed_style))
    else:
        sign.append(Spacer(1, 14 * mm))
    if not own_closing:
        sign.append(Spacer(1, 1.5 * mm))
        sign.append(Paragraph(f"<b>{_p(author_name)}</b>", base))
        if author_title:
            sign.append(Paragraph(_p(author_title), base))
        if company_name:
            sign.append(Paragraph(_p(company_name), base))
    record: list[Flowable] = []
    if signed_at and author_name:
        record = [
            Spacer(1, 4 * mm),
            Paragraph(
                f"Signed electronically by {_p(author_name)} on {_p(format_date(signed_at))}.",
                small,
            ),
        ]
    if own_closing:
        # Signature right under their own "Yours sincerely,", their typed name
        # and details after it, and the signing record at the very end.
        story.append(KeepTogether(sign))
        if tail.strip():
            story.append(Spacer(1, 2 * mm))
            add_paragraphs(tail)
        story.extend(record)
    else:
        story.append(KeepTogether(sign + record))

    def footer(canvas, _doc) -> None:  # type: ignore[no-untyped-def]
        canvas.saveState()
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.6)
        canvas.line(MARGIN, 16 * mm, PAGE_W - MARGIN, 16 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, 11.5 * mm, "Issued through Projet")
        canvas.drawRightString(PAGE_W - MARGIN, 11.5 * mm, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
