import time
from datetime import date

from tests.conftest import AuthedUser


def test_full_crud_lifecycle(authed_user: AuthedUser):
    client = authed_user.client

    create_resp = client.post(
        "/diaries",
        json={"title": "First entry", "content": "hello world", "entry_date": "2026-01-01"},
    )
    assert create_resp.status_code == 201, create_resp.text
    entry = create_resp.json()
    entry_id = entry["id"]
    assert entry["title"] == "First entry"
    assert entry["content"] == "hello world"
    assert entry["entry_date"] == "2026-01-01"

    list_resp = client.get("/diaries")
    assert list_resp.status_code == 200
    assert any(e["id"] == entry_id for e in list_resp.json())

    get_resp = client.get(f"/diaries/{entry_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "First entry"

    update_resp = client.put(f"/diaries/{entry_id}", json={"title": "Updated entry"})
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "Updated entry"

    get_after_update = client.get(f"/diaries/{entry_id}")
    assert get_after_update.json()["title"] == "Updated entry"

    delete_resp = client.delete(f"/diaries/{entry_id}")
    assert delete_resp.status_code == 204

    get_after_delete = client.get(f"/diaries/{entry_id}")
    assert get_after_delete.status_code == 404

    list_after_delete = client.get("/diaries")
    assert all(e["id"] != entry_id for e in list_after_delete.json())


def test_create_defaults_entry_date_to_today_when_omitted(authed_user: AuthedUser):
    resp = authed_user.client.post("/diaries", json={"title": "No date given"})
    assert resp.status_code == 201, resp.text
    assert resp.json()["entry_date"] == date.today().isoformat()


def test_create_missing_title_returns_422(authed_user: AuthedUser):
    resp = authed_user.client.post("/diaries", json={"content": "no title"})
    assert resp.status_code == 422


def test_get_nonexistent_entry_404(authed_user: AuthedUser):
    resp = authed_user.client.get("/diaries/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_update_nonexistent_entry_404(authed_user: AuthedUser):
    resp = authed_user.client.put(
        "/diaries/00000000-0000-0000-0000-000000000000", json={"title": "x"}
    )
    assert resp.status_code == 404


def test_delete_nonexistent_entry_404(authed_user: AuthedUser):
    resp = authed_user.client.delete("/diaries/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_list_ordered_by_entry_date_desc(authed_user: AuthedUser):
    client = authed_user.client
    client.post("/diaries", json={"title": "Oldest", "entry_date": "2026-01-01"})
    client.post("/diaries", json={"title": "Newest", "entry_date": "2026-03-01"})
    client.post("/diaries", json={"title": "Middle", "entry_date": "2026-02-01"})

    resp = client.get("/diaries")
    assert resp.status_code == 200
    dates = [e["entry_date"] for e in resp.json()]
    assert dates == sorted(dates, reverse=True)


def test_update_refreshes_updated_at(authed_user_real_commits: AuthedUser):
    # updated_at is refreshed by Postgres's onupdate=func.now() (a server-side trigger
    # evaluated on UPDATE) — there's no pure-Python path to exercise this, so it's
    # covered here as an integration test rather than in tests/unit/.
    #
    # This needs `authed_user_real_commits` (real, separate transactions per request)
    # rather than the usual SAVEPOINT-wrapped `authed_user`: Postgres's now() is fixed
    # for the lifetime of a transaction, so under the shared-transaction test fixture
    # the create and update would see the same now() no matter how long we sleep.
    client = authed_user_real_commits.client
    create_resp = client.post("/diaries", json={"title": "Before edit"})
    entry_id = create_resp.json()["id"]
    created_at = create_resp.json()["created_at"]
    original_updated_at = create_resp.json()["updated_at"]

    time.sleep(0.01)

    update_resp = client.put(f"/diaries/{entry_id}", json={"title": "After edit"})
    assert update_resp.status_code == 200
    updated = update_resp.json()

    assert updated["created_at"] == created_at
    assert updated["updated_at"] != original_updated_at
    assert updated["updated_at"] > original_updated_at
