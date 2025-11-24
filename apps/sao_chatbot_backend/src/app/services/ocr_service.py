import os
import fitz 
import tempfile
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders.base import BaseLoader
from typhoon_ocr import ocr_document

class TyphoonOCRLoader(BaseLoader):
    def __init__(self, file_path: str, api_key: str = None):
        self.file_path = file_path
        self.api_key = api_key or os.getenv("TYPHOON_API_KEY")
        
        if not self.api_key:
            raise ValueError("Typhoon API Key is missing")

    def load(self) -> List[Document]:
        file_name = self.file_path.split("/")[-1]
        print(f"🌪️  [Typhoon OCR] Starting: {file_name}")

        documents = []
        
        try:
            doc = fitz.open(self.file_path)
            total_pages = len(doc)
            print(f"📄 Found {total_pages} pages. Processing page by page...")

            for page_num, page in enumerate(doc):
                real_page_num = page_num + 1
                print(f"Processing Page {real_page_num}/{total_pages}...")
                pix = page.get_pixmap(dpi=300)
                
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=True) as temp_img:
                    pix.save(temp_img.name)
                    try:
                        markdown_text = ocr_document(
                            pdf_or_image_path=temp_img.name,
                            api_key=self.api_key,
                            base_url="https://api.opentyphoon.ai/v1",
                            model="typhoon-ocr"
                        )
                        
                        if markdown_text:
                            meta = {
                                "source": self.file_path,
                                "page": real_page_num,  
                                "engine": "typhoon-ocr"
                            }
                            documents.append(Document(page_content=markdown_text, metadata=meta))
                            
                    except Exception as e:
                        print(f"Error on Page {real_page_num}: {e}")

            doc.close()
            print(f"Finished {file_name}. Extracted {len(documents)} valid pages.")
            return documents

        except Exception as e:
            print(f"[Typhoon OCR] Critical Failure on {file_name}: {e}")
            return []