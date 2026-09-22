from pathlib import Path
from disti.repository import Repository

repo = Repository.from_environment()
for migration in sorted((Path(__file__).parents[1] / "migrations").glob("*.sql")):
    conn = repo.connection_factory()
    try:
        with conn.cursor() as cursor: cursor.execute(migration.read_text())
        conn.commit()
    finally: conn.close()
