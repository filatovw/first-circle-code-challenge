from __future__ import annotations

import datetime
from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator, Mount
from airflow.sdk import Param
from airflow.hooks.base import BaseHook


def get_pg_env(conn_id: str) -> dict:
    conn = BaseHook.get_connection(conn_id)
    return {
        "PG_USER": conn.login,
        "PG_PASSWORD": conn.password,
        "PG_HOST": conn.host,
        "PG_PORT": str(conn.port),
        "PG_DATABASE": conn.schema,
        "KAFKA_BOOTSTRAP_SERVERS": "kafka:9092",
        "KAFKA_TRANSACTIONS_TOPIC": "transactions",
        "KAFKA_FAILED_TRANSACTIONS_TOPIC": "failedTransactions",
        "KAFKA_REPORTS_TOPIC": "reports",
    }


with DAG(
    dag_id="csv_transactions_to_db_ingest",
    start_date=datetime.datetime(2021, 6, 10),
    schedule=None,
    catchup=False,
    params={
        "path_to_file": Param(
            type="string",
            minLength=5,
            description="Path to the CSV file on FS mounted to workers under the /data folder",
        ),
    },
) as dag:
    pg_env = get_pg_env("db")
    importer = DockerOperator(
        task_id="csv2db_ingestor",
        image="first_circle-tx_csv2db_ingestor:latest",
        command="uv run tx_csv2db_ingestor --source-path /data/{{ params.path_to_file }}",
        auto_remove="success",
        environment=pg_env,
        network_mode="first_circle_default",
        mount_tmp_dir=False,
        mounts=[
            Mount(
                source="/Users/filatovw/projects/filatovw/jobs/first_circle/data",
                target="/data",
                type="bind",
            ),
        ],
    )
    importer
