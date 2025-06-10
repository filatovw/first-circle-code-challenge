# Generate transactions and store in CSV format

Using `CLI`:

    PG_PASSWORD=apppass uv run python src/ingestion/entrypoints/tx_csv_gen.py -o ../data/tx_stream_20200101_20240601.csv --pg-host 0.0.0.0 --pg-port 5432 --pg-user appuser --pg-db dwh --date-start 2020-01-01 --date-end 2024-06-01


Using `.env` file:

    uv run python src/ingestion/entrypoints/tx_csv_gen.py -o ../data/tx_stream_20200101_20240601.csv -date-start 2020-01-01 --date-end 2024-06-01

# Read generated transactions and push them to the Queue

Using `CLI`:

    uv run python src/ingestion/entrypoints/tx_csv2stream_ingestor.py --bootstrap-servers localhost:9094 --transactions-topic transactions --source-path ../data/tx_stream_20200101_20240601.csv

Using `.env` file:

    uv run python src/ingestion/entrypoints/tx_csv2stream_ingestor.py --bootstrap-servers localhost:9094 --transactions-topic transactions --source-path ../data/tx_stream_20200101_20240601.csv

# Ingest transactions stream to DB

Using `CLI`:

    PG_PASSWORD=apppass uv run python src/ingestion/entrypoints/tx_stream_ingestor.py --bootstrap-servers localhost:9094 --topic-failed-transactions failedTransactions --topic-transactions transactions --pg-user appuser --pg-host 0.0.0.0 --pg-port 5432 --pg-db dwh

Using `.env` file:

    uv run python src/ingestion/entrypoints/tx_stream_ingestor.py --bootstrap-servers localhost:9094 --topic-failed-transactions failedTransactions --topic-transactions transactions

# Ingest transactions from CSV to DB

Using `CLI`:

    PG_PASSWORD=apppass uv run python src/ingestion/entrypoints/tx_csv2db_ingestor.py --bootstrap-servers localhost:9094 --topic-failed-transactions failedTransactions --source-path ../data/tx_stream_20200101_20240601.csv --pg-user appuser --pg-host 0.0.0.0 --pg-port 5432 --pg-db dwh

Using `.env` file:

    uv run python src/ingestion/entrypoints/tx_csv2db_ingestor.py --bootstrap-servers localhost:9094 --topic-failed-transactions failedTransactions --source-path ../data/tx_stream_20200101_20240601.csv