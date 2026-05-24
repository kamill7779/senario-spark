from app.database import connect_mysql
from app.repositories import MySQLRepository


def main() -> None:
    connection = connect_mysql()
    try:
        MySQLRepository(connection).init_schema()
    finally:
        connection.close()
    print("MySQL schema initialized.")


if __name__ == "__main__":
    main()
