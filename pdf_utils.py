# Copyright (c) 2026 Isaiah Williams / DrawingIQ
# All rights reserved. Unauthorized copying, modification,
# or distribution of this software is strictly prohibited.



"""
pdf_utils.py — PDF handling for DrawingIQ
Converts PDF pages to high-res images for GPT-4o vision analysis.
Uses pdf2image (poppler) with fallback to PyMuPDF (fitz).
"""

import io
import base64
from typing import Generator


def pdf_to_images(pdf_bytes: bytes, dpi: int = 200, max_pages: int = 20) -> list[dict]:
    """
    Convert PDF bytes to a list of base64-encoded images.
    Returns: [{"page": int, "b64": str, "mime": "image/png", "width": int, "height": int}]
    Tries pdf2image first, falls back to PyMuPDF.
    """
    try:
        return _convert_with_pdf2image(pdf_bytes, dpi, max_pages)
    except ImportError:
        pass
    try:
        return _convert_with_pymupdf(pdf_bytes, dpi, max_pages)
    except ImportError:
        raise RuntimeError(
            "PDF support requires either pdf2image+poppler or PyMuPDF.\n"
            "Install with:  pip install pdf2image pymupdf\n"
            "Also install poppler: brew install poppler  OR  apt install poppler-utils"
        )


def _convert_with_pdf2image(pdf_bytes: bytes, dpi: int, max_pages: int) -> list[dict]:
    from pdf2image import convert_from_bytes
    images = convert_from_bytes(
        pdf_bytes,
        dpi=dpi,
        first_page=1,
        last_page=max_pages,
        fmt="png",
        thread_count=2,
    )
    result = []
    for i, img in enumerate(images):
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        result.append({
            "page": i + 1,
            "b64": b64,
            "mime": "image/png",
            "width": img.width,
            "height": img.height,
        })
    return result


def _convert_with_pymupdf(pdf_bytes: bytes, dpi: int, max_pages: int) -> list[dict]:
    import fitz  # PyMuPDF
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    result = []
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    for i in range(min(len(doc), max_pages)):
        page = doc[i]
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_bytes = pix.tobytes("png")
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        result.append({
            "page": i + 1,
            "b64": b64,
            "mime": "image/png",
            "width": pix.width,
            "height": pix.height,
        })
    doc.close()
    return result


def get_pdf_page_count(pdf_bytes: bytes) -> int:
    """Quick page count without full conversion."""
    try:
        from pdf2image.pdf2image import pdfinfo_from_bytes
        info = pdfinfo_from_bytes(pdf_bytes)
        return info.get("Pages", 0)
    except Exception:
        pass
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        count = len(doc)
        doc.close()
        return count
    except Exception:
        return 0


def image_file_to_b64(file_bytes: bytes, filename: str) -> tuple[str, str]:
    """Convert uploaded image bytes to b64 + mime type."""
    ext = filename.rsplit(".", 1)[-1].lower()
    mime_map = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}
    mime = mime_map.get(ext, "image/jpeg")
    b64 = base64.b64encode(file_bytes).decode("utf-8")
    return b64, mime
