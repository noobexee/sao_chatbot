import os
from PIL import Image
import shutil

# Import handlers for different file types
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    import docx
except ImportError:
    docx = None

try:
    import typhoon_ocr
except ImportError:
    print("Warning: typhoon-ocr not found. Did you run 'pip install typhoon-ocr'?")
    typhoon_ocr = None

class TyphoonService:
    def __init__(self):
        print("Initializing Document Service...")

    def extract_text(self, file_path: str) -> str:
        """
        Determines file type and extracts text accordingly.
        Uses Typhoon OCR for images, and native extractors for docs/pdfs.
        """
        # Get file extension
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        print(f"Processing file type: {ext}")

        try:
            # --- CASE 1: Text File (.txt) ---
            if ext == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()

            # --- CASE 2: PDF (.pdf) ---
            elif ext == '.pdf':
                if not PdfReader:
                    return "Error: pypdf library not installed."
                
                reader = PdfReader(file_path)
                text = ""
                for page in reader.pages:
                    extract = page.extract_text()
                    if extract:
                        text += extract + "\n"
                return text if text.strip() else "No text found in PDF (might be scanned image PDF without OCR layer)."

            # --- CASE 3: Word Doc (.docx) ---
            elif ext in ['.docx', '.doc']:
                if not docx:
                    return "Error: python-docx library not installed."
                
                doc = docx.Document(file_path)
                return "\n".join([para.text for para in doc.paragraphs])

        except Exception as e:
            print(f"Extraction Failed: {e}")
            return f"Error reading file: {str(e)}"

typhoon_service = TyphoonService()