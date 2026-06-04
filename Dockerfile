FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV HOST=0.0.0.0
ENV PORT=8765

WORKDIR /app

COPY pyproject.toml requirements.txt ./
COPY src ./src
COPY web ./web
COPY data ./data
COPY docs ./docs
COPY README.md ./

EXPOSE 8765

CMD ["python", "-m", "feedback_agent", "serve"]
