from tests.conftest import AuthedUser


def test_upload_image_saves_file_and_returns_url(authed_user: AuthedUser):
    resp = authed_user.client.post(
        "/uploads/images",
        files={"file": ("photo.png", b"\x89PNG-fake-bytes", "image/png")},
    )
    assert resp.status_code == 201, resp.text
    url = resp.json()["url"]
    assert url.startswith(f"/media/{authed_user.user_id}/")
    assert url.endswith(".png")


def test_owner_can_fetch_uploaded_media_with_session_cookie(authed_user: AuthedUser):
    upload_resp = authed_user.client.post(
        "/uploads/images",
        files={"file": ("photo.png", b"\x89PNG-fake-bytes", "image/png")},
    )
    assert upload_resp.status_code == 201
    url = upload_resp.json()["url"]

    media_resp = authed_user.client.get(url)
    assert media_resp.status_code == 200
    assert media_resp.content == b"\x89PNG-fake-bytes"


def test_fetch_nonexistent_media_404(authed_user: AuthedUser):
    resp = authed_user.client.get(f"/media/{authed_user.user_id}/does-not-exist.png")
    assert resp.status_code == 404
