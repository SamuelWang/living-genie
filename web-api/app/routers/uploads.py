import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, status

from app.schemas import UploadResponse
from app.settings import get_settings

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/images", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def upload_image(file: UploadFile = File(...)) -> UploadResponse:
    uploads_dir = get_settings().uploads_dir
    suffix = Path(file.filename or "").suffix
    filename = f"{uuid.uuid4()}{suffix}"
    destination = uploads_dir / filename

    with destination.open("wb") as out_file:
        shutil.copyfileobj(file.file, out_file)

    return UploadResponse(url=f"/media/{filename}")
