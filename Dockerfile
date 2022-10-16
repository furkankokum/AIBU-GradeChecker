FROM python:3.10.4-slim as builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc

COPY . .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheel -r requirements.txt

CMD ["python", "gradeChecker.py"]
