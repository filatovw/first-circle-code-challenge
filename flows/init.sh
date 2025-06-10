airflow connections add 'db' \
    --conn-json '{
        "conn_type": "postgres", 
        "description": null, 
        "login": "appuser", 
        "password": "apppass", 
        "host": "db", 
        "port": 5432, 
        "schema": "dwh", 
        "extra": null
    }'