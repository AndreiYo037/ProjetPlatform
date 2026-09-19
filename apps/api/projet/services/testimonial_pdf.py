"""Placeholder letter PDF from the company testimonial text.

Layout, fonts, and letterhead will be specified later. This exists so a
published testimonial is already a downloadable PDF on the profile.
"""

from __future__ import annotations

_PUNCT = str.maketrans(
    {
        "\u2014": "-",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\xa0": " ",
    }
)

PAGE_W = 612
PAGE_H = 792
MARGIN = 72
CHARS = 88
LINES_PER_PAGE = 38


def render_testimonial_pdf(
    *,
    body: str,
    author_name: str,
    author_title: str | None = None,
    company_name: str = "",
    programme_title: str = "",
) -> bytes:
    lines = _wrap("Testimonial")
    if programme_title:
        lines.extend(_wrap(programme_title))
    if company_name:
        lines.extend(_wrap(company_name))
    lines.append("")
    lines.extend(_wrap(body.strip()))
    sign_off = [""]
    if author_name:
        sign_off.append(author_name)
    if author_title:
        sign_off.append(author_title)
    if company_name and author_name:
        sign_off.append(company_name)
    lines.extend(sign_off)

    pages: list[list[str]] = []
    for i in range(0, max(len(lines), 1), LINES_PER_PAGE):
        pages.append(lines[i : i + LINES_PER_PAGE])

    font = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    contents = [_content_stream(page) for page in pages]
    page_count = len(contents)
    # 1 Catalog, 2 Pages, 3 Font, then page + stream pairs.
    page_ids = [4 + i * 2 for i in range(page_count)]
    stream_ids = [5 + i * 2 for i in range(page_count)]
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode(),
        font,
    ]
    for stream_id, stream in zip(stream_ids, contents, strict=True):
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
                f"/Contents {stream_id} 0 R /Resources << /Font << /F1 3 0 R >> >> >>"
            ).encode()
        )
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
    return _assemble(objects)


def _wrap(text: str) -> list[str]:
    safe = text.translate(_PUNCT).encode("ascii", "replace").decode("ascii")
    out: list[str] = []
    paragraphs = safe.splitlines() or [""]
    for paragraph in paragraphs:
        words = paragraph.split()
        if not words:
            out.append("")
            continue
        current = ""
        for word in words:
            trial = f"{current} {word}".strip()
            if len(trial) <= CHARS:
                current = trial
            else:
                if current:
                    out.append(current)
                current = word
        if current:
            out.append(current)
    return out


def _pdf_string(text: str) -> bytes:
    escaped = (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\r", " ")
    )
    return f"({escaped})".encode("ascii")


def _content_stream(lines: list[str]) -> bytes:
    y = PAGE_H - MARGIN
    chunks = [b"BT\n/F1 12 Tf\n"]
    first = True
    for line in lines:
        if first:
            chunks.append(f"1 0 0 1 {MARGIN} {y} Tm\n".encode())
            first = False
        else:
            chunks.append(b"0 -16 Td\n")
        chunks.append(_pdf_string(line) + b" Tj\n")
    chunks.append(b"ET\n")
    return b"".join(chunks)


def _assemble(objects: list[bytes]) -> bytes:
    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    parts = [header]
    offsets: list[int] = []
    pos = len(header)
    for index, obj in enumerate(objects, start=1):
        chunk = f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
        offsets.append(pos)
        parts.append(chunk)
        pos += len(chunk)
    xref = [f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()]
    for offset in offsets:
        xref.append(f"{offset:010d} 00000 n \n".encode())
    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{pos}\n%%EOF\n"
    ).encode()
    return b"".join(parts) + b"".join(xref) + trailer
