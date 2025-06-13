from __future__ import annotations

import datetime
from airflow import DAG
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator


with DAG(
    dag_id="report_daily_user_stats",
    start_date=datetime.datetime(2021, 6, 10),
    schedule="*/5 * * * *",
    catchup=False,
) as dag:
    create_pet_table = SQLExecuteQueryOperator(
        task_id="create_report",
        conn_id="db",
        sql="""
        BEGIN;

        DELETE FROM report_daily_user_stats;

        INSERT INTO report_daily_user_stats
        SELECT
            u.user_id AS user_id,
            DATE_TRUNC('month', t.created_at)::DATE AS month,
            COUNT(CASE WHEN t.sender_id = u.user_id THEN 1 END) AS sent_count,
            COUNT(CASE WHEN t.receiver_id = u.user_id THEN 1 END) AS received_count,
            SUM(CASE WHEN t.sender_id = u.user_id THEN t.amount::float ELSE 0 END) AS total_sent,
            SUM(CASE WHEN t.receiver_id = u.user_id THEN t.amount::float ELSE 0 END) AS total_received
        FROM users u
        JOIN transactions t
            ON t.status = 'completed' AND (t.sender_id = u.user_id OR t.receiver_id = u.user_id)
        GROUP BY u.user_id, DATE_TRUNC('month', t.created_at);

        COMMIT;
        """,
    )
    create_pet_table
