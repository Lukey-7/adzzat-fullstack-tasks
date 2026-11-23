# Build from the repository root:  docker build -f page/Dockerfile -t adzzat-page .
FROM python:3.12-slim
RUN pip install --no-cache-dir uv==0.8.*
WORKDIR /srv/page
COPY page/pyproject.toml page/uv.lock ./
RUN uv sync --frozen --no-dev
COPY page/ ./
# The API reads the task folders directly, so the page cannot drift from them.
COPY tasks/ /srv/tasks/
COPY results/ /srv/results/
ENV TASKS_DIR=/srv/tasks RESULTS_FILE=/srv/results/summary.json
EXPOSE 8000
CMD ["uv", "run", "--no-dev", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
