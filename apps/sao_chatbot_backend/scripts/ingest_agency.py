import os
import csv
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv

load_dotenv()


BATCH_SIZE = 1000
CSV_PATH = "storage/agency.csv"


def import_agencies():

    db_url = os.getenv("SQL_DATABASE_URL")

    if not db_url:
        print("❌ SQL_DATABASE_URL missing from .env")
        return

    inserted = 0
    skipped = 0
    buffer = []

    try:
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:

                with open(CSV_PATH, newline="", encoding="utf-8-sig") as csvfile:
                    reader = csv.DictReader(csvfile)
                    print("Headers:", reader.fieldnames)

                    for row in reader:

                        buffer.append((
                            row.get("agency_name"),
                            row.get("department_name"),
                            row.get("ministry_name"),
                            row.get("agency_name_search_key"),
                        ))

                        if len(buffer) >= BATCH_SIZE:
                            inserted += _flush_batch(cur, buffer)
                            buffer.clear()

                # final flush
                if buffer:
                    inserted += _flush_batch(cur, buffer)

            conn.commit()

        print("\n🎉 Import completed!")
        print(f"Inserted (new rows): {inserted}")

    except Exception as e:
        print(f"❌ Database Error: {e}")


def _flush_batch(cur, batch):

    execute_batch(
        cur,
        """
        INSERT INTO initial_review_agencies (
            agency_name,
            department_name,
            ministry_name,
            search_key
        )
        VALUES (%s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        """,
        batch,
    )

    return len(batch)


if __name__ == "__main__":
    import_agencies()