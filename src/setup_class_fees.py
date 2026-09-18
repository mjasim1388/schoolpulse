from pathlib import Path
from db import run_sql_file

if __name__ == "__main__":
    path = Path(__file__).resolve().parent.parent / "sql" / "class_fees.sql"
    print(f"Running {path} ...")
    run_sql_file(str(path))
    print("Done.")