from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_list_returns_both_tasks():
    res = client.get("/api/tasks")
    assert res.status_code == 200
    tasks = {t["id"]: t for t in res.json()}
    assert {"fix-calday-dates", "count-workdays"} <= set(tasks)
    assert tasks["fix-calday-dates"]["kind"] == "language-driven"
    assert tasks["count-workdays"]["kind"] == "outcome-driven"
    for t in tasks.values():
        assert t["title"] and t["difficulty"] in {"easy", "medium", "hard"}


def test_detail_has_statement_difficulty_and_environment():
    res = client.get("/api/tasks/fix-calday-dates")
    assert res.status_code == 200
    t = res.json()
    assert t["title"].startswith("Fix CALDAY")
    assert "<h1>" in t["statement_html"]
    assert t["difficulty"] == "medium" and t["difficulty_note"]
    assert t["environment"]["base_image"] == "debian:bookworm-slim"
    assert t["environment"]["graded_artifacts"] == ["/app/calday.f"]
    assert t["environment"]["verifier_mode"] == "separate"


def test_unknown_and_malicious_ids_are_404():
    for bad in ["nope", "..", "%2e%2e%2fREADME.md", "Fix-Calday-Dates"]:
        assert client.get("/api/tasks/" + bad).status_code == 404


def test_index_page_is_served():
    res = client.get("/")
    assert res.status_code == 200
    assert 'id="task-list"' in res.text
