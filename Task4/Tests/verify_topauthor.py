import pandas as pd
import yaml
import re

print("Loading Books...")
with open("../DATA3/books.yaml", 'r', encoding='utf-8') as f:
    content = re.sub(r':(\w+)', r'\1', f.read())
books = pd.DataFrame(yaml.safe_load(content))

print("Loading Orders...")
orders = pd.read_parquet("../DATA3/orders.parquet")
merged = orders.merge(books, left_on='book_id', right_on='id', how='left')

def normalize_authors(auth_str):
    if not isinstance(auth_str, str): return "Unknown"
    parts = sorted([a.strip() for a in auth_str.split(',')])
    return ", ".join(parts)

print("Normalizing Author sets...")
merged['author_set'] = merged['author'].apply(normalize_authors)

top_authors = merged.groupby('author_set')['quantity'].sum().sort_values(ascending=False).head(10)

print("\n" + "="*40)
print("TOP 10 MOST POPULAR AUTHORS (DATA1)")
print("="*40)
print(f"{'Rank':<5} | {'Quantity Sold':<15} | {'Author(s)'}")
print("-" * 40)

rank = 1
for author, quantity in top_authors.items():
    print(f"{rank:<5} | {quantity:<15} | {author}")
    rank += 1
print("="*40)