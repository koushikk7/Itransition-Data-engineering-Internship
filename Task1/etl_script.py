import re
import json
import sqlite3


def parse_custom_format(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        raw_data = f.read()

    json_friendly_data = re.sub(r':(\w+)=>', r'"\1":', raw_data)

    return json.loads(json_friendly_data)


def load_to_db(data, db_name="books.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT,
            author TEXT,
            genre TEXT,
            publisher TEXT,
            year INTEGER,
            price TEXT
        )
    ''')

    for book in data:
        cursor.execute('''
            INSERT OR IGNORE INTO books (id, title, author, genre, publisher, year, price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(book['id']),
            book['title'],
            book['author'],
            book['genre'],
            book['publisher'],
            book['year'],
            book['price']
        ))

    conn.commit()
    return conn


def create_summary_table(conn):
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS summary")

    cursor.execute('''
        CREATE TABLE summary AS
        SELECT 
            year as publication_year,
            COUNT(*) as book_count,
            ROUND(
                AVG(
                    CASE 
                        WHEN price LIKE '€%' THEN CAST(SUBSTR(price, 2) AS REAL) * 1.2
                        WHEN price LIKE '$%' THEN CAST(SUBSTR(price, 2) AS REAL)
                        ELSE 0 
                    END
                ), 2
            ) as average_price
        FROM books
        GROUP BY year
        ORDER BY year
    ''')

    conn.commit()
    print("Summary table created successfully.")


if __name__ == "__main__":
    data = parse_custom_format("task1_d.json")
    print(f"Parsed {len(data)} records.")

    connection = load_to_db(data)
    print("Data loaded into 'books' table.")

    create_summary_table(connection)

    cursor = connection.cursor()

    print("\n--- Row Counts ---")
    print(f"Books Table: {cursor.execute('SELECT COUNT(*) FROM books').fetchone()[0]}")
    print(f"Summary Table: {cursor.execute('SELECT COUNT(*) FROM summary').fetchone()[0]}")

    print("\n--- Summary Table ---")
    rows = cursor.execute("SELECT * FROM summary").fetchall()
    print("Year | Count | Avg Price ($)")
    for row in rows:
        print(row)

    connection.close()