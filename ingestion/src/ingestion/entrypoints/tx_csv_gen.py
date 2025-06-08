import os
import argparse
import random
from datetime import datetime, UTC
from uuid import uuid4
from ingestion import models
import faker
import time
import polars as pl
from dataclasses import dataclass

random.seed(time.time())


@dataclass
class Config:
    output_path: str
    pg_user: str
    pg_password: str
    pg_port: int
    pg_db: str
    pg_host: str

    def to_uri(self) -> str:
        return f"postgresql://{self.pg_user}:{self.pg_password}@{self.pg_host}:{self.pg_port}/{self.pg_db}"


def get_config() -> Config:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-path",
        "-o",
        type=str,
        required=True,
        help="place where the generated file should be saved",
    )
    parser.add_argument(
        "--pg-user", "-u", type=str, required=True, help="database user"
    )
    parser.add_argument("--pg-port", type=str, required=True, help="database port")
    parser.add_argument("--pg-host", type=str, required=True, help="database host")
    parser.add_argument("--pg-db", type=str, required=True, help="database name")
    parsed = parser.parse_args()

    pg_password = os.environ.get("POSTGRES_PASSWORD")
    if not pg_password:
        raise ValueError("POSTGRES_PASSWORD Env Var is not set")

    return Config(
        output_path=parsed.output_path,
        pg_user=parsed.pg_user,
        pg_port=parsed.pg_port,
        pg_host=parsed.pg_host,
        pg_db=parsed.pg_db,
        pg_password=pg_password,
    )


def main():
    config = get_config()

    factory = faker.Faker()
    date_start = datetime(2023, 1, 1, 1, 1, 1, 1, tzinfo=UTC)
    date_end = datetime(2025, 6, 1, 1, 1, 1, 1, tzinfo=UTC)

    uri = config.to_uri()

    query = """SELECT user_id FROM users LIMIT 5"""
    users_df = pl.read_database_uri(query, uri)
    users_count = users_df.count()["user_id"][0]
    if users_count == 0:
        raise ValueError("No users registered")

    query = """SELECT symbol FROM currencies LIMIT 5"""
    currencies_df = pl.read_database_uri(query, uri)
    currency = currencies_df["symbol"][0]

    df = pl.DataFrame()
    # create pending transactions
    batch_size = 10
    for i in range(batch_size):
        tx = models.Transaction(
            transaction_id=str(uuid4()),
            sender_id=users_df["user_id"][random.randint(0, users_count - 1)],
            receiver_id=users_df["user_id"][
                random.randint(0, users_count - 1)
            ],  # can be a duplicate for sender_id
            currency=currency,
            amount=factory.random_int(10000, 9999999) / 100,  # can be a large number
            timestamp=factory.date_time_between_dates(date_start, date_end).astimezone(
                UTC
            ),
            status="pending",
        )
        tx_dict = tx.model_dump()
        tx_dict["transaction_id"] = str(tx_dict["transaction_id"])
        tx_dict["sender_id"] = str(tx_dict["sender_id"])
        tx_dict["receiver_id"] = str(tx_dict["receiver_id"])
        new_df = pl.DataFrame(tx_dict)
        df = df.vstack(new_df)

    # create duplicates
    df = df.vstack(df[0 : random.randint(5, batch_size - 1)])

    # some transactions will have comleted state
    success_df = df[0 : batch_size // 3]
    success_df = success_df.with_columns(
        timestamp=pl.col("timestamp").dt.offset_by("30s")
    )
    success_df = success_df.with_columns(status=pl.lit("completed"))
    df = df.vstack(success_df)
    # some transactions will have failed state
    failed_df = df[batch_size // 3 : batch_size - 1]
    failed_df = failed_df.with_columns(
        timestamp=pl.col("timestamp").dt.offset_by("30s")
    )
    failed_df = failed_df.with_columns(status=pl.lit("failed"))
    df = df.vstack(failed_df)

    df = df.with_columns(pl.col("timestamp").dt.strftime("%Y-%m-%dT%H:%M:%SZ"))

    df.write_csv(
        config.output_path, include_header=True, separator=",", float_precision=2
    )


if __name__ == "__main__":
    main()
