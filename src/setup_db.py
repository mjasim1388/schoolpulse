from pathlib import Path
from db import test_connection, run_sql_file

if __name__ == "__main__":
    print("Testing connection...")
    test_connection()

    schema_path = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"
    print(f"\nCreating tables from {schema_path}...")
    run_sql_file(str(schema_path))

    print("\nDone. Tables created.")