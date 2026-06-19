#!/bin/bash
# wait for postgres to be ready
echo "Waiting for PostgreSQL..."

# This loop ensures the DB is ready before proceeding
while ! pg_isready -h user-db -U user -d user_db; do
  sleep 1
done

echo "PostgreSQL is ready. Creating tables..."

# Run a Python script to execute the table creation function
python -c "
from app.usermain import create_db_and_tables
create_db_and_tables()
"

echo "Tables created. Starting Uvicorn server."

# Finally, start the FastAPI application
exec uvicorn app.usermain:app --host 0.0.0.0 --port 8000