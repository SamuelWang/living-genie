from tests.conftest import AuthedUser


def test_user_a_cannot_get_user_b_entry_404(authed_user: AuthedUser, other_user: AuthedUser):
    create_resp = other_user.client.post("/diaries", json={"title": "B's private entry"})
    entry_id = create_resp.json()["id"]

    resp = authed_user.client.get(f"/diaries/{entry_id}")
    assert resp.status_code == 404


def test_user_a_cannot_update_user_b_entry_404(authed_user: AuthedUser, other_user: AuthedUser):
    create_resp = other_user.client.post("/diaries", json={"title": "B's private entry"})
    entry_id = create_resp.json()["id"]

    resp = authed_user.client.put(f"/diaries/{entry_id}", json={"title": "hijacked"})
    assert resp.status_code == 404


def test_user_a_cannot_delete_user_b_entry_404(authed_user: AuthedUser, other_user: AuthedUser):
    create_resp = other_user.client.post("/diaries", json={"title": "B's private entry"})
    entry_id = create_resp.json()["id"]

    resp = authed_user.client.delete(f"/diaries/{entry_id}")
    assert resp.status_code == 404

    # entry is untouched from B's perspective
    assert other_user.client.get(f"/diaries/{entry_id}").status_code == 200


def test_user_a_list_excludes_user_b_entries(authed_user: AuthedUser, other_user: AuthedUser):
    other_user.client.post("/diaries", json={"title": "B's private entry"})
    authed_user.client.post("/diaries", json={"title": "A's own entry"})

    resp = authed_user.client.get("/diaries")
    titles = [e["title"] for e in resp.json()]
    assert "A's own entry" in titles
    assert "B's private entry" not in titles


def test_user_a_cannot_fetch_user_b_media_404(authed_user: AuthedUser, other_user: AuthedUser):
    upload_resp = other_user.client.post(
        "/uploads/images",
        files={"file": ("photo.png", b"b-owns-this", "image/png")},
    )
    url = upload_resp.json()["url"]

    resp = authed_user.client.get(url)
    assert resp.status_code == 404


def test_user_a_cannot_get_user_b_todo_404(authed_user: AuthedUser, other_user: AuthedUser):
    create_resp = other_user.client.post("/todos", json={"title": "B's private todo"})
    todo_id = create_resp.json()["id"]

    resp = authed_user.client.get(f"/todos/{todo_id}")
    assert resp.status_code == 404


def test_user_a_cannot_update_user_b_todo_404(authed_user: AuthedUser, other_user: AuthedUser):
    create_resp = other_user.client.post("/todos", json={"title": "B's private todo"})
    todo_id = create_resp.json()["id"]

    resp = authed_user.client.put(f"/todos/{todo_id}", json={"title": "hijacked"})
    assert resp.status_code == 404


def test_user_a_cannot_delete_user_b_todo_404(authed_user: AuthedUser, other_user: AuthedUser):
    create_resp = other_user.client.post("/todos", json={"title": "B's private todo"})
    todo_id = create_resp.json()["id"]

    resp = authed_user.client.delete(f"/todos/{todo_id}")
    assert resp.status_code == 404

    # todo is untouched from B's perspective
    assert other_user.client.get(f"/todos/{todo_id}").status_code == 200


def test_user_a_list_excludes_user_b_todos(authed_user: AuthedUser, other_user: AuthedUser):
    other_user.client.post("/todos", json={"title": "B's private todo"})
    authed_user.client.post("/todos", json={"title": "A's own todo"})

    resp = authed_user.client.get("/todos")
    titles = [t["title"] for t in resp.json()]
    assert "A's own todo" in titles
    assert "B's private todo" not in titles
