FROM python:3.12-slim-bookworm

RUN apt-get update -y \
    && apt-get install -y curl make

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY . /ingestion
WORKDIR /ingestion
RUN make install