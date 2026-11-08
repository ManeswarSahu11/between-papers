import re
from io import BytesIO

from pypdf import PdfReader


REFERENCE_HEADING_PATTERN = re.compile(
    r"^\s*(?:\d+[.\s]+)?(references|bibliography)\s*[:.]?\s*$",
    flags=re.IGNORECASE,
)


def extract_pdf_text(pdf_bytes: bytes, exclude_references: bool = False) -> str:
    """
    Extract text from all pages, optionally stopping at a bibliography heading.
    """
    reader = PdfReader(BytesIO(pdf_bytes))
    chunks: list[str] = []

    for page in reader.pages:
        page_text = page.extract_text() or ""
        lines = page_text.splitlines()

        cutoff_index = None
        for i, line in enumerate(lines):
            if exclude_references and REFERENCE_HEADING_PATTERN.match(line.strip()):
                cutoff_index = i
                break

        if cutoff_index is not None:
            valid_lines = lines[:cutoff_index]
            if valid_lines:
                chunks.append("\n".join(valid_lines))
            break

        chunks.append(page_text)

    return "\n".join(chunks).strip()


def extract_text_without_references(pdf_bytes: bytes) -> str:
    """Keep the original reference-excluding helper for existing callers."""
    return extract_pdf_text(pdf_bytes, exclude_references=True)
