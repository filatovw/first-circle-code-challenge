# Developer guide

## Required tools:

- docker (with compose)
- make
- python3.12 (if you're developer)
- uv package manager

## Dockerized environment

Spin up a cluster of pg, kafka, kafka consumer and a couple of one-shot jobs:

    make up

Stop everything:

    make down

Delete containers and volumes:

    make clean
