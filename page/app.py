"""Tiny task browser: a JSON API over the task folders plus one static page.

The API reads tasks/<id>/ directly on every request, so the page can never
drift from the tasks that Harbor actually runs.

    GET /api/tasks          list of tasks (id, title, kind, difficulty)
    GET /api/tasks/{id}     one task: statement, difficulty note, environment,
                            and verified results from results/summary.json
"""
import json
import os
import re
import tomllib
from pathlib import Path

import markdown
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
TASKS_DIR = Path(os.environ.get("TASKS_DIR", REPO / "tasks"))
RESULTS_FILE = Path(os.environ.get("RESULTS_FILE",
                                   REPO / "results" / "summary.json"))
TASK_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")

app = FastAPI(title="Adzzat take-home tasks")


def _task_dirs():
    if not TASKS_DIR.is_dir():
        return []
    return sorted(p for p in TASKS_DIR.iterdir()
                  if (p / "task.toml").is_file() and TASK_ID.match(p.name))


def _load(task_dir: Path, full: bool):
    meta = tomllib.loads((task_dir / "task.toml").read_text("utf-8"))
    md = meta.get("metadata", {})
    statement = (task_dir / "instruction.md").read_text("utf-8")
    title_match = re.search(r"^#\s+(.+)$", statement, re.M)
    task = {
        "id": task_dir.name,
        "title": title_match.group(1).strip() if title_match else task_dir.name,
        "kind": md.get("kind", ""),
        "difficulty": md.get("difficulty", ""),
        "tags": md.get("tags", []),
    }
    if full:
        dockerfile = (task_dir / "environment" / "Dockerfile").read_text("utf-8")
        base = re.search(r"^FROM\s+(\S+)", dockerfile, re.M)
        task.update({
            "difficulty_note": md.get("difficulty_note", ""),
            "statement_markdown": statement,
            "statement_html": markdown.markdown(
                statement, extensions=["fenced_code"]),
            "environment": {
                "base_image": base.group(1) if base else None,
                "dockerfile": dockerfile,
                "graded_artifacts": meta.get("artifacts", []),
                "verifier_mode": meta.get("verifier", {}).get(
                    "environment_mode"),
            },
            "results": _results().get(task_dir.name, {}),
        })
    return task


def _results():
    try:
        return json.loads(RESULTS_FILE.read_text("utf-8"))
    except (OSError, ValueError):
        return {}


@app.get("/api/tasks")
def list_tasks():
    return [_load(d, full=False) for d in _task_dirs()]


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):
    for d in _task_dirs():
        if d.name == task_id:
            return _load(d, full=True)
    raise HTTPException(status_code=404, detail="task not found")


@app.get("/")
def index():
    return FileResponse(HERE / "static" / "index.html")


app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
