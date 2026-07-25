import re
import uuid

from app.settings import get_settings

_MEDIA_URL_RE = re.compile(
    r"/media/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
    r"/([^\s\"'<>()/]+)"
)


def extract_media_filenames(content: str, user_id: uuid.UUID) -> set[str]:
    """Return filenames referenced in `content` that belong to `user_id`."""
    owner = str(user_id)
    return {filename for owner_id, filename in _MEDIA_URL_RE.findall(content) if owner_id == owner}


def delete_media_files(filenames: set[str], user_id: uuid.UUID) -> None:
    """Delete the given uploaded files for `user_id`, ignoring missing ones."""
    user_dir = (get_settings().uploads_dir / str(user_id)).resolve()
    for filename in filenames:
        path = (user_dir / filename).resolve()
        if path.parent != user_dir:
            continue
        path.unlink(missing_ok=True)
