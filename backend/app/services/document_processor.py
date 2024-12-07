from typing import List, Dict, Optional
import PyPDF2
from pptx import Presentation
import nbformat
import os
import json
from datetime import datetime
from app.models.schemas import Document
import logging

logger = logging.getLogger(__name__)

class DocumentProcessor:
    supported_extensions = {'.pdf', '.txt', '.pptx', '.ipynb'}

    @staticmethod
    def process_pdf(file_path: str) -> List[str]:
        """Extract text from PDF file"""
        texts = []
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text.strip():
                        texts.append(text)
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {str(e)}")
            raise
        return texts

    @staticmethod
    def process_pptx(file_path: str) -> List[str]:
        """Extract text from PPTX file"""
        texts = []
        try:
            presentation = Presentation(file_path)
            for slide in presentation.slides:
                slide_text = []
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        slide_text.append(shape.text)
                if slide_text:
                    texts.append("\n".join(slide_text))
        except Exception as e:
            logger.error(f"Error processing PPTX {file_path}: {str(e)}")
            raise
        return texts

    @staticmethod
    def process_txt(file_path: str) -> List[str]:
        """Process text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
                # Split into manageable chunks (e.g., by paragraphs)
                return [chunk.strip() for chunk in text.split('\n\n') if chunk.strip()]
        except Exception as e:
            logger.error(f"Error processing TXT {file_path}: {str(e)}")
            raise

    @staticmethod
    def process_ipynb(file_path: str) -> List[str]:
        """Process Jupyter notebook"""
        texts = []
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                notebook = nbformat.read(file, as_version=4)
                for cell in notebook.cells:
                    if cell.cell_type == 'markdown':
                        texts.append(cell.source)
                    elif cell.cell_type == 'code':
                        # Include both code and outputs
                        code_text = f"```python\n{cell.source}\n```"
                        texts.append(code_text)
                        if 'outputs' in cell and cell.outputs:
                            output_texts = []
                            for output in cell.outputs:
                                if 'text' in output:
                                    output_texts.append(output.text)
                                elif 'data' in output and 'text/plain' in output.data:
                                    output_texts.append(output.data['text/plain'])
                            if output_texts:
                                texts.append("Output:\n" + "\n".join(output_texts))
        except Exception as e:
            logger.error(f"Error processing Jupyter notebook {file_path}: {str(e)}")
            raise
        return texts

    async def process_document(self, document: Document, file_path: str) -> List[Dict]:
        """Process document and prepare for vector store"""
        try:
            file_extension = os.path.splitext(file_path)[1].lower()
            
            if file_extension not in self.supported_extensions:
                raise ValueError(f"Unsupported file type: {file_extension}")

            # Process file based on type
            if file_extension == '.pdf':
                texts = self.process_pdf(file_path)
            elif file_extension == '.pptx':
                texts = self.process_pptx(file_path)
            elif file_extension == '.txt':
                texts = self.process_txt(file_path)
            elif file_extension == '.ipynb':
                texts = self.process_ipynb(file_path)
            
            # Prepare metadata for each chunk
            processed_chunks = []
            for idx, text in enumerate(texts):
                metadata = {
                    "document_id": document.id,
                    "filename": document.filename,
                    "chunk_index": idx,
                    "file_type": document.file_type,
                    "processed_date": datetime.now().isoformat()
                }
                processed_chunks.append({
                    "text": text,
                    "metadata": metadata
                })
            
            return processed_chunks

        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
            raise