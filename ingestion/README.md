# Generate transactions and store in CSV format

    POSTGRES_PASSWORD=apppass uv run python src/ingestion/entrypoints/tx_csv_gen.py -o ../data/tx_stream.csv --pg-host 0.0.0.0 --pg-port 5432 --pg-user appuser --pg-db dwh

# Read generated transactions and push them to the Queue

