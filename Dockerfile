# Runner image: the benchmark driver. Pure standard library, no pip install.
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY blastbench ./blastbench
COPY scenarios ./scenarios
COPY tasks ./tasks
ENTRYPOINT ["python", "-m", "blastbench"]
