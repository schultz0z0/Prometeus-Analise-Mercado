import base64
import io

import httpx
import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from prometeus.entrypoints.rest.app import app


def pdf_bytes(text: str | None = None) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=600, height=800)
    if text:
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
        )
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 50 700 Td ({text}) Tj ET".encode())
        page[NameObject("/Contents")] = stream
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.mark.parametrize(
    "raw,expected",
    [(pdf_bytes("MBA Seguros 360 horas"), 200), (pdf_bytes(), 422), (b"invalid pdf", 400)],
)
async def test_pdf_upload_extracts_real_text_or_returns_explicit_error(raw, expected):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/intake/extract-document",
            json={"filename": "programa.pdf", "content_base64": base64.b64encode(raw).decode()},
        )
    assert response.status_code == expected
    if expected == 200:
        assert response.json()["text"].strip() == "MBA Seguros 360 horas"
