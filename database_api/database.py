import pyodbc

SERVER = "Melih"
DATABASE = "Intelligent_Inbox_Assistant"

def get_connection():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        "Trusted_Connection=yes;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )


if __name__ == "__main__":
    try:
        conn = get_connection()
        print("SQL Server bağlantısı başarılı!")
        conn.close()
    except pyodbc.Error as error:
        print("SQL Server bağlantı hatası:", error)