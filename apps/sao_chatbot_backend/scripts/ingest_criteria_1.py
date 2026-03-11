import os
import csv
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def row_exists(cur, row):
    cur.execute(
        """
        SELECT 1
        FROM initial_review_agencies
        WHERE
            agency_code IS NOT DISTINCT FROM %s AND
            agency_name IS NOT DISTINCT FROM %s AND
            department_code IS NOT DISTINCT FROM %s AND
            department_name IS NOT DISTINCT FROM %s AND
            ministry_code IS NOT DISTINCT FROM %s AND
            ministry_name IS NOT DISTINCT FROM %s AND
            search_key IS NOT DISTINCT FROM %s
        LIMIT 1
        """,
        (
            row.get("agency_code"),
            row.get("agency_name"),
            row.get("department_code"),
            row.get("department_name"),
            row.get("ministry_code"),
            row.get("ministry_name"),
            row.get("agency_name_search_key")
        )
    )

    return cur.fetchone() is not None


def import_agencies():

    db_url = os.getenv("SQL_DATABASE_URL")

    if not db_url:
        print("Error: SQL_DATABASE_URL missing from .env")
        return

    CSV_PATH = "storage/agency.csv"

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        inserted = 0
        skipped = 0

        with open(CSV_PATH, newline="", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)

            print("Headers:", reader.fieldnames)

            for row in reader:

                # skip exact duplicates
                if row_exists(cur, row):
                    skipped += 1
                    continue

                cur.execute(
                    """
                    INSERT INTO initial_review_agencies (
                        agency_code,
                        agency_name,
                        department_code,
                        department_name,
                        ministry_code,
                        ministry_name,
                        search_key
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        row.get("agency_code"),
                        row.get("agency_name"),
                        row.get("department_code"),
                        row.get("department_name"),
                        row.get("ministry_code"),
                        row.get("ministry_name"),
                        row.get("agency_name_search_key")
                    )
                )

                inserted += 1

                if inserted % 1000 == 0:
                    conn.commit()
                    print(f"Inserted {inserted} rows...")

        conn.commit()

        print("\n🎉 Import completed!")
        print(f"Inserted: {inserted}")
        print(f"Skipped (exact duplicates): {skipped}")

    except Exception as e:
        print(f"Database Error: {e}")

    finally:
        if "conn" in locals() and conn:
            cur.close()
            conn.close()


if __name__ == "__main__":
    import_agencies()