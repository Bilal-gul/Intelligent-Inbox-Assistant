import os

import pyodbc

SERVER = os.getenv("DB_SERVER", ".\\SQLEXPRESS")
DATABASE = os.getenv("DB_NAME", "Intelligent_Inbox_Assistant")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_TRUSTED_CONNECTION = os.getenv(
    "DB_TRUSTED_CONNECTION", "yes" if not DB_USER else "no"
).lower() in {"yes", "true", "1"}

def get_connection():
    connection_string = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )

    if DB_USER and DB_PASSWORD:
        connection_string += f"UID={DB_USER};PWD={DB_PASSWORD};"
    elif DB_TRUSTED_CONNECTION:
        connection_string += "Trusted_Connection=yes;"
    else:
        raise RuntimeError(
            "Set DB_USER and DB_PASSWORD, or enable DB_TRUSTED_CONNECTION."
        )

    return pyodbc.connect(connection_string)


if __name__ == "__main__":
    try:
        conn = get_connection()
        print("SQL Server bağlantısı başarılı!")
        conn.close()
    except pyodbc.Error as error:
        print("SQL Server bağlantı hatası:", error)
