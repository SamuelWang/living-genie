import io

from PIL import Image

from app.settings import get_settings
from tests.conftest import AuthedUser


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (10, 8), (200, 50, 100)).save(buf, format="PNG")
    return buf.getvalue()


def _jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (10, 8), (10, 220, 30)).save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def test_upload_png_saves_file_and_returns_lossless_webp_url(authed_user: AuthedUser):
    resp = authed_user.client.post(
        "/uploads/images",
        files={"file": ("photo.png", _png_bytes(), "image/png")},
    )
    assert resp.status_code == 201, resp.text
    url = resp.json()["url"]
    assert url.startswith(f"/media/{authed_user.user_id}/")
    assert url.endswith(".webp")


def test_upload_jpeg_stays_jpeg(authed_user: AuthedUser):
    resp = authed_user.client.post(
        "/uploads/images",
        files={"file": ("photo.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert resp.status_code == 201, resp.text
    url = resp.json()["url"]
    assert url.endswith(".jpg")


def test_upload_non_image_rejected_with_400(authed_user: AuthedUser):
    resp = authed_user.client.post(
        "/uploads/images",
        files={"file": ("notes.txt", b"this is definitely not an image", "text/plain")},
    )
    assert resp.status_code == 400

    user_dir = get_settings().uploads_dir / str(authed_user.user_id)
    assert not user_dir.exists() or not any(user_dir.iterdir())


def test_owner_can_fetch_uploaded_media_with_session_cookie(authed_user: AuthedUser):
    source = _png_bytes()
    upload_resp = authed_user.client.post(
        "/uploads/images",
        files={"file": ("photo.png", source, "image/png")},
    )
    assert upload_resp.status_code == 201
    url = upload_resp.json()["url"]

    media_resp = authed_user.client.get(url)
    assert media_resp.status_code == 200

    fetched = Image.open(io.BytesIO(media_resp.content))
    original = Image.open(io.BytesIO(source))
    assert list(fetched.convert("RGB").getdata()) == list(original.convert("RGB").getdata())


def test_fetch_nonexistent_media_404(authed_user: AuthedUser):
    resp = authed_user.client.get(f"/media/{authed_user.user_id}/does-not-exist.png")
    assert resp.status_code == 404
