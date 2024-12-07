from fastapi import UploadFile, HTTPException
from typing import List
import os
import shutil
from datetime import datetime
from app.models.schemas import Document
from app.config import settings
import uuid

async def process_uploaded_file(file: UploadFile) -> Document:
    """
    Process and save uploaded file
    """
    # Validate file size
    file.file.seek(0, 2)
    size = file.file.tell()
    if size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE/(1024*1024)}MB"
        )
    file.file.seek(0)

    # Validate file type
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ['.pdf', '.txt', '.pptx', '.ipynb']:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type"
        )

    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")

    return Document(
        id=str(uuid.uuid4()),
        filename=file.filename,
        file_type=file_ext[1:],
        file_size=size,
        upload_date=datetime.now(),
        processed=False
    )