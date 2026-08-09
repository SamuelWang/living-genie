import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.image_processing import InvalidImageError, compress_image
from app.models import User
from app.schemas import UploadResponse
from app.security import get_current_user
from app.settings import get_settings

router = APIRouter(prefix="/uploads", tags=["uploads"])
media_router = APIRouter(tags=["media"])


@router.post("/images", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def upload_image(
    file: UploadFile = File(...), current_user: User = Depends(get_current_user)
) -> UploadResponse:
    try:
        processed, extension = compress_image(file.file.read())
    except InvalidImageError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is not a valid image"
        )

    uploads_dir = get_settings().uploads_dir / str(current_user.id)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4()}{extension}"
    destination = uploads_dir / filename
    destination.write_bytes(processed)

    return UploadResponse(url=f"/media/{current_user.id}/{filename}")


@media_router.get("/media/{owner_id}/{filename}")
def get_media(
    owner_id: uuid.UUID, filename: str, current_user: User = Depends(get_current_user)
) -> FileResponse:
    if current_user.id != owner_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    path = get_settings().uploads_dir / str(owner_id) / filename
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return FileResponse(path)
