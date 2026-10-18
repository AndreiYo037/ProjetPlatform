"""The testimonial letter is typeset as a business letter."""

from __future__ import annotations

import io
from datetime import UTC, datetime

from PIL import Image, ImageDraw

from projet.services.testimonial_pdf import format_date, has_closing, render_testimonial_pdf


def _png(draw_line: bool = False) -> bytes:
    image = Image.new("RGBA", (200, 80), (0, 0, 0, 0))
    if draw_line:
        ImageDraw.Draw(image).line([(5, 60), (100, 10), (195, 60)], fill=(0, 0, 90, 255), width=3)
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def _render(**overrides: object) -> bytes:
    args: dict = {
        "body": "Sam read the data properly.\n\nAnd explained it clearly.",
        "author_name": "Mo Manager",
        "author_title": "Head of Data",
        "company_name": "Acme Pte Ltd",
        "programme_title": "Churn analysis",
        "recipient_name": "Sam Student",
    }
    args.update(overrides)
    return render_testimonial_pdf(**args)


def test_a_letter_is_a_valid_pdf_with_the_letter_parts():
    pdf = _render(signed_at=datetime(2026, 10, 18, tzinfo=UTC), signature_typed=True)
    assert pdf.startswith(b"%PDF-")
    assert pdf.rstrip().endswith(b"%%EOF")


def test_a_logo_and_a_drawn_signature_are_embedded():
    plain = _render()
    dressed = _render(logo_png=_png(True), signature_png=_png(True))
    assert len(dressed) > len(plain), "images add to the file"


def test_an_unreadable_logo_does_not_stop_the_letter():
    assert _render(logo_png=b"not an image").startswith(b"%PDF-")


def test_text_outside_latin_one_does_not_break_the_letter():
    pdf = _render(body="Wonderful work from 王小明 and Zoë — truly excellent.")
    assert pdf.startswith(b"%PDF-")


def test_a_long_letter_runs_onto_a_second_page():
    pdf = _render(body="\n\n".join(["A full paragraph of praise. " * 30] * 12))
    assert pdf.count(b"/Type /Page\n") + pdf.count(b"/Type /Page ") >= 2


def test_a_typed_sign_off_is_recognised_so_it_is_not_repeated():
    assert has_closing("Great work.\n\nYours sincerely,\nJeffrey Chen\nBlueNexus")
    assert has_closing("Great work.\nBest regards,\nMo")
    assert not has_closing("Great work, and a sincere thank you for the effort.")


def test_the_date_is_written_out_in_full():
    assert format_date(datetime(2026, 10, 8, tzinfo=UTC)) == "8 October 2026"


def test_the_letter_is_dated_in_singapore_not_utc():
    # 16:43 UTC on the 18th is 00:43 on the 19th in Singapore.
    assert format_date(datetime(2026, 10, 18, 16, 43, tzinfo=UTC)) == "19 October 2026"


def test_a_signature_goes_between_the_writers_closing_and_their_name():
    from projet.services.testimonial_pdf import split_at_closing

    head, tail = split_at_closing("Thank you.\n\nYours sincerely,\nJeffrey Chen\nBlueNexus") or (
        "",
        "",
    )
    assert head.endswith("Yours sincerely,")
    assert tail.startswith("Jeffrey Chen")
    assert split_at_closing("Just praise, no sign-off.") is None


def test_a_teams_names_read_as_a_sentence():
    from projet.services.testimonial_pdf import join_names

    assert join_names(["Ada"]) == "Ada"
    assert join_names(["Ada", "Ben"]) == "Ada and Ben"
    assert join_names(["Ada", " Ben ", "", "Cy"]) == "Ada, Ben and Cy"
    assert join_names([]) == ""


def test_a_team_letter_with_company_details_renders():
    pdf = _render(
        recipients=["Sam Student", "Ada Analyst", "Bo Builder"],
        company_details="51 Goldhill Plaza, #07-07\nhttps://bluenexus.tech\ninfo@bluenexus.tech",
    )
    assert pdf.startswith(b"%PDF-")
