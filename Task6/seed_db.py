import psycopg2
from faker import Faker

DB_URL = "postgresql://neondb_owner:npg_B3lEba1XmSJd@ep-misty-thunder-agf1by03-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

def init_db():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    print("Creating Schema...")
    cur.execute("""
                DROP TABLE IF EXISTS first_names;
                DROP TABLE IF EXISTS last_names;
                DROP TABLE IF EXISTS cities;
                DROP TABLE IF EXISTS streets;

                CREATE TABLE first_names
                (
                    id     SERIAL PRIMARY KEY,
                    name   TEXT,
                    locale TEXT
                );
                CREATE TABLE last_names
                (
                    id     SERIAL PRIMARY KEY,
                    name   TEXT,
                    locale TEXT
                );
                CREATE TABLE cities
                (
                    id     SERIAL PRIMARY KEY,
                    name   TEXT,
                    locale TEXT
                );
                CREATE TABLE streets
                (
                    id     SERIAL PRIMARY KEY,
                    name   TEXT,
                    locale TEXT
                );

                CREATE INDEX idx_fname_locale ON first_names (locale);
                CREATE INDEX idx_lname_locale ON last_names (locale);
                CREATE INDEX idx_city_locale ON cities (locale);
                CREATE INDEX idx_street_locale ON streets (locale);
                """)

    print("Generating Data...")
    fake_en = Faker('en_US')
    fake_de = Faker('de_DE')
    fake_fr = Faker('fr_FR')

    fnames, lnames, cities, streets = [], [], [], []

    for _ in range(2000):
        fnames.append((fake_en.first_name(), 'en_US'))
        lnames.append((fake_en.last_name(), 'en_US'))
        cities.append((fake_en.city(), 'en_US'))
        streets.append((fake_en.street_name(), 'en_US'))

        fnames.append((fake_de.first_name(), 'de_DE'))
        lnames.append((fake_de.last_name(), 'de_DE'))
        cities.append((fake_de.city(), 'de_DE'))
        streets.append((fake_de.street_name(), 'de_DE'))

        fnames.append((fake_fr.first_name(), 'fr_FR'))
        lnames.append((fake_fr.last_name(), 'fr_FR'))
        cities.append((fake_fr.city(), 'fr_FR'))
        streets.append((fake_fr.street_name(), 'fr_FR'))

    print("Uploading to Database...")

    def bulk_insert(table, data_list):
        args_str = ','.join(cur.mogrify("(%s,%s)", x).decode('utf-8') for x in data_list)
        cur.execute(f"INSERT INTO {table} (name, locale) VALUES " + args_str)

    bulk_insert("first_names", fnames)
    bulk_insert("last_names", lnames)
    bulk_insert("cities", cities)
    bulk_insert("streets", streets)

    conn.commit()
    cur.close()
    conn.close()
    print("Database Ready!")

if __name__ == "__main__":
    init_db()
s