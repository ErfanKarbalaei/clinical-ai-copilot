"""Test helpers: build real (tiny) PDF files with a text layer."""

import io


def pdf_with_text(text: str) -> bytes:
    """Build a minimal valid single-page PDF containing a text layer."""
    content = f"BT /F1 24 Tf 72 700 Td ({text}) Tj ET".encode("ascii")
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
        ),
        4: (
            b"<< /Length " + str(len(content)).encode()
            + b" >>\nstream\n" + content + b"\nendstream"
        ),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for number, body in objects.items():
        offsets[number] = out.tell()
        out.write(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")

    xref_position = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for number in range(1, len(objects) + 1):
        out.write(f"{offsets[number]:010d} 00000 n \n".encode())
    out.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_position}\n%%EOF".encode()
    )
    return out.getvalue()
