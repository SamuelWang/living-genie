from tests.conftest import AuthedUser


def test_full_crud_lifecycle(authed_user: AuthedUser):
    client = authed_user.client

    create_resp = client.post(
        "/todos",
        json={"title": "Buy milk", "description": "2%", "due_date": "2026-08-05"},
    )
    assert create_resp.status_code == 201, create_resp.text
    todo = create_resp.json()
    todo_id = todo["id"]
    assert todo["title"] == "Buy milk"
    assert todo["description"] == "2%"
    assert todo["due_date"] == "2026-08-05"
    assert todo["completed"] is False

    list_resp = client.get("/todos")
    assert list_resp.status_code == 200
    assert any(t["id"] == todo_id for t in list_resp.json())

    get_resp = client.get(f"/todos/{todo_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Buy milk"

    update_resp = client.put(f"/todos/{todo_id}", json={"title": "Buy oat milk", "completed": True})
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["title"] == "Buy oat milk"
    assert updated["completed"] is True

    get_after_update = client.get(f"/todos/{todo_id}")
    assert get_after_update.json()["title"] == "Buy oat milk"

    delete_resp = client.delete(f"/todos/{todo_id}")
    assert delete_resp.status_code == 204

    get_after_delete = client.get(f"/todos/{todo_id}")
    assert get_after_delete.status_code == 404

    list_after_delete = client.get("/todos")
    assert all(t["id"] != todo_id for t in list_after_delete.json())


def test_create_missing_title_returns_422(authed_user: AuthedUser):
    resp = authed_user.client.post("/todos", json={"description": "no title"})
    assert resp.status_code == 422


def test_get_nonexistent_todo_404(authed_user: AuthedUser):
    resp = authed_user.client.get("/todos/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_update_nonexistent_todo_404(authed_user: AuthedUser):
    resp = authed_user.client.put(
        "/todos/00000000-0000-0000-0000-000000000000", json={"title": "x"}
    )
    assert resp.status_code == 404


def test_delete_nonexistent_todo_404(authed_user: AuthedUser):
    resp = authed_user.client.delete("/todos/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_list_ordered_by_completed_then_due_date_then_created_at_desc(authed_user: AuthedUser):
    client = authed_user.client
    no_due = client.post("/todos", json={"title": "No due date"}).json()
    later = client.post("/todos", json={"title": "Later", "due_date": "2026-09-01"}).json()
    sooner = client.post("/todos", json={"title": "Sooner", "due_date": "2026-08-10"}).json()
    completed = client.post("/todos", json={"title": "Already done"}).json()
    client.put(f"/todos/{completed['id']}", json={"completed": True})

    resp = client.get("/todos")
    assert resp.status_code == 200
    ids = [t["id"] for t in resp.json()]

    # incomplete todos (due-date asc, nulls last) come before the completed one
    assert ids.index(sooner["id"]) < ids.index(later["id"]) < ids.index(no_due["id"]) < ids.index(
        completed["id"]
    )


def test_list_filters_by_completed_query_param(authed_user: AuthedUser):
    client = authed_user.client
    pending = client.post("/todos", json={"title": "Pending"}).json()
    done = client.post("/todos", json={"title": "Done"}).json()
    client.put(f"/todos/{done['id']}", json={"completed": True})

    pending_resp = client.get("/todos", params={"completed": "false"})
    pending_ids = [t["id"] for t in pending_resp.json()]
    assert pending["id"] in pending_ids
    assert done["id"] not in pending_ids

    done_resp = client.get("/todos", params={"completed": "true"})
    done_ids = [t["id"] for t in done_resp.json()]
    assert done["id"] in done_ids
    assert pending["id"] not in done_ids


def test_create_allows_omitted_optional_fields(authed_user: AuthedUser):
    resp = authed_user.client.post("/todos", json={"title": "Just a title"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["description"] is None
    assert body["due_date"] is None
