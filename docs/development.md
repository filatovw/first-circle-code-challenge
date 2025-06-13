# Developer guide

## Required tools:

- docker (with compose)
- make
- python3.12 (if you're developer)
- uv package manager

## Dockerized environment

### Spin up core services

persistance layer:
    - db - postgres instance
    - db-init - apply migrations and fill with seed data

streaming:
    - queue - single node kafka
    - queue-init - create topics

orchestration:
    - airflow - single node Airflow instance in dev mode

    docker compose up -d db db-init queue queue-init airflow tx_stream2db_ingestor

### Generate transaction CSV files

Create 2 CSV files with transactions.

Why not to use committed files? Because DB instances have auto-generated UUID identifiers.
Why is it so? Thus I can test on a randomly generated data and find potential bugs with DB/Data schema quickly.

    docker compose up tx_csv_gen_1 tx_csv_gen_2

### Ingest generated data to the queue

    docker compose up tx_csv2stream_ingestor

### Ingest generated data from CSV to the DB directly

    docker compose up tx_csv2db_ingestor

### Airflow jobs

Airflow UI: http://0.0.0.0:8080/

Login/pass:

    cat ./flows/auth/simple_auth_manager_passwords.json.generated

Go to DAGs page: http://0.0.0.0:8080/dags

- Enable dags
- Trigger them manually to generate reports in DB. Reports are available as aggregated data in tables
  - report_monthly_user_stats
  - report_daily_user_stats
  - csv_transactions_to_db_ingest - run `tx_csv2db_ingestor` job from the Airflow


### Stop everything:

    make down

### Delete containers and volumes:

    make clean
