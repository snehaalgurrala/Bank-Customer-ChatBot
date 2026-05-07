import argparse

from database.seed import seed_demo_data
from database.session import SessionLocal, init_db, reset_db


def initialize_database(seed: bool = True, reset: bool = False) -> None:
    if reset:
        reset_db()
    else:
        init_db()
    if seed:
        with SessionLocal() as db:
            seed_demo_data(db)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize the loan chatbot SQLite database.")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all local database tables first.")
    parser.add_argument("--no-seed", action="store_true", help="Create tables without inserting demo seed data.")
    args = parser.parse_args()

    initialize_database(seed=not args.no_seed, reset=args.reset)
    print("SQLite database initialized and demo seed data inserted.")
