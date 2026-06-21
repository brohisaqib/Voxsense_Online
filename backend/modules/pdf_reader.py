"""
VoxSense — modules/pdf_reader.py
"""
from pathlib import Path
from loguru import logger


class PDFReader:
    async def read_pdf(self, file_name: str = "") -> str:
        try:
            import pypdf

            # Search locations
            search_dirs = [
                Path.home() / "Desktop",
                Path.home() / "Documents",
                Path.home() / "Downloads",
            ]

            found = None

            # Agar file_name mein "desktop" ya "pdf" jaise generic words hain
            # toh Desktop pe pehli PDF dhundho
            generic = ["pdf", "file", "document", "desktop", "the pdf", "pdf file"]
            is_generic = not file_name or any(
                file_name.lower().strip() == g for g in generic
            )

            if is_generic:
                # Desktop pe pehli PDF lo
                for d in search_dirs:
                    pdfs = list(d.glob("*.pdf"))
                    if pdfs:
                        found = pdfs[0]
                        break
            else:
                # Specific file dhundho
                clean = file_name.replace("pdf", "").replace("file", "").strip()
                for d in search_dirs:
                    matches = list(d.glob(f"*{clean}*.pdf"))
                    if not matches:
                        matches = list(d.glob(f"*{file_name}*.pdf"))
                    if matches:
                        found = matches[0]
                        break

            if not found:
                # Last resort — har jagah dhundho
                for d in search_dirs:
                    all_pdfs = list(d.glob("*.pdf"))
                    if all_pdfs:
                        found = all_pdfs[0]
                        break

            if not found:
                return "No PDF files found on Desktop, Documents, or Downloads."

            # Read PDF
            reader = pypdf.PdfReader(str(found))
            total  = len(reader.pages)
            text   = ""

            for page in reader.pages[:3]:
                text += page.extract_text() or ""

            if not text.strip():
                return f"Found {found.name} but could not extract text. It may be a scanned PDF."

            words   = text.split()[:200]
            preview = " ".join(words)

            return (
                f"Reading {found.name}. "
                f"Total {total} pages. "
                f"Content: {preview}"
            )

        except ImportError:
            return "PDF reader not installed. Run: pip install pypdf"
        except Exception as e:
            logger.error(f"PDF error: {e}")
            return f"Could not read PDF. {e}"