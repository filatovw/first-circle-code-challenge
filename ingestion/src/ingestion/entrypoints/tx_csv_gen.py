import os
import argparse
import random
from datetime import datetime, UTC
from uuid import uuid4
from ingestion import dto
import faker
import time
import polars as pl
from dataclasses import dataclass
import dotenv

random.seed(time.time())

APP_NAME = "tx_csv_gen"


@dataclass
class Config:
    output_path: str
    pg_user: str
    pg_password: str
    pg_port: int
    pg_db: str
    pg_host: str
    date_start: datetime
    date_end: datetime

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
    parser.add_argument("--pg-user", "-u", type=str, help="database user")
    parser.add_argument("--pg-port", type=str, help="database port")
    parser.add_argument("--pg-host", type=str, help="database host")
    parser.add_argument("--pg-db", type=str, help="database name")
    parser.add_argument(
        "--date-start",
        "-s",
        type=str,
        required=True,
        help="start date of a transaction stream",
    )
    parser.add_argument(
        "--date-end",
        "-e",
        type=str,
        required=True,
        help="end date of a transaction stream",
    )
    parsed = parser.parse_args()

    pg_password = os.environ["PG_PASSWORD"]
    if not parsed.pg_user:
        parsed.pg_user = os.environ["PG_USER"]
    if not parsed.pg_port:
        parsed.pg_port = os.environ["PG_PORT"]
    if not parsed.pg_host:
        parsed.pg_host = os.environ["PG_HOST"]
    if not parsed.pg_db:
        parsed.pg_db = os.environ["PG_DATABASE"]

    date_format = "%Y-%m-%d"
    date_start = datetime.strptime(parsed.date_start, date_format)
    date_end = datetime.strptime(parsed.date_end, date_format)
    if date_start > date_end:
        raise ValueError("Start date cannot go after the end date")

    return Config(
        output_path=parsed.output_path,
        pg_user=parsed.pg_user,
        pg_port=parsed.pg_port,
        pg_host=parsed.pg_host,
        pg_db=parsed.pg_db,
        pg_password=pg_password,
        date_start=date_start,
        date_end=date_end,
    )


def main():
    dotenv.load_dotenv(verbose=True)
    config = get_config()

    factory = faker.Faker()
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
    batch_size = 1000
    for i in range(batch_size):
        tx = dto.Transaction.model_construct(
            transaction_id=str(uuid4()),
            sender_id=users_df["user_id"][random.randint(0, users_count - 1)],
            receiver_id=users_df["user_id"][
                random.randint(0, users_count - 1)
            ],  # can be a duplicate for sender_id
            currency=currency,
            amount=factory.random_int(10000, 9999999) / 100,  # can be a large number
            timestamp=factory.date_time_between_dates(
                config.date_start, config.date_end
            ).astimezone(UTC),
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
        timestamp=pl.col("timestamp").dt.offset_by("20s")
    )
    failed_df = failed_df.with_columns(status=pl.lit("failed"))
    df = df.vstack(failed_df)

    df = df.with_columns(pl.col("timestamp").dt.strftime("%Y-%m-%dT%H:%M:%SZ"))

    df.write_csv(
        config.output_path, include_header=True, separator=",", float_precision=2
    )


if __name__ == "__main__":
    main()
