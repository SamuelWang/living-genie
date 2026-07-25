from app.settings import get_settings
from tests.conftest import AuthedUser


def _upload_image(authed_user: AuthedUser) -> str:
    resp = authed_user.client.post(
        "/uploads/images",
        files={"file": ("photo.png", b"\x89PNG-fake-bytes", "image/png")},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["url"]


def _media_path(authed_user: AuthedUser, url: str):
    filename = url.rsplit("/", 1)[-1]
    return get_settings().uploads_dir / str(authed_user.user_id) / filename


def test_delete_diary_entry_deletes_referenced_images(authed_user: AuthedUser):
    url = _upload_image(authed_user)
    path = _media_path(authed_user, url)
    assert path.is_file()

    create_resp = authed_user.client.post(
        "/diaries",
        json={"title": "Has image", "content": f'<img src="{url}">'},
    )
    entry_id = create_resp.json()["id"]

    delete_resp = authed_user.client.delete(f"/diaries/{entry_id}")
    assert delete_resp.status_code == 204
    assert not path.is_file()


def test_update_removing_image_deletes_it(authed_user: AuthedUser):
    url = _upload_image(authed_user)
    path = _media_path(authed_user, url)

    create_resp = authed_user.client.post(
        "/diaries",
        json={"title": "Has image", "content": f'<img src="{url}">'},
    )
    entry_id = create_resp.json()["id"]

    update_resp = authed_user.client.put(
        f"/diaries/{entry_id}", json={"content": "no image anymore"}
    )
    assert update_resp.status_code == 200
    assert not path.is_file()

    get_resp = authed_user.client.get(f"/diaries/{entry_id}")
    assert get_resp.status_code == 200


def test_update_keeping_same_image_does_not_delete_it(authed_user: AuthedUser):
    url = _upload_image(authed_user)
    path = _media_path(authed_user, url)

    create_resp = authed_user.client.post(
        "/diaries",
        json={"title": "Has image", "content": f'<img src="{url}">'},
    )
    entry_id = create_resp.json()["id"]

    update_resp = authed_user.client.put(
        f"/diaries/{entry_id}", json={"content": f'<img src="{url}"> plus more text'}
    )
    assert update_resp.status_code == 200
    assert path.is_file()


def test_update_without_touching_content_does_not_delete_image(authed_user: AuthedUser):
    url = _upload_image(authed_user)
    path = _media_path(authed_user, url)

    create_resp = authed_user.client.post(
        "/diaries",
        json={"title": "Has image", "content": f'<img src="{url}">'},
    )
    entry_id = create_resp.json()["id"]

    update_resp = authed_user.client.put(f"/diaries/{entry_id}", json={"title": "Renamed"})
    assert update_resp.status_code == 200
    assert path.is_file()
