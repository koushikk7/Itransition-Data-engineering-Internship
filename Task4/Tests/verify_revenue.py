import pandas as pd
import re

def clean_price(price_str):
    if pd.isna(price_str) or price_str == '': return 0.0
    price_str = str(price_str).strip()
    is_euro = '€' in price_str
    nums = re.findall(r'\d+', price_str)
    if not nums: return 0.0
    if len(nums) == 1: val = float(nums[0])
    else: val = float(f"{nums[0]}.{nums[1]}")
    if is_euro: val = val * 1.2
    return val

df = pd.read_parquet("../DATA1/orders.parquet")

df['timestamp'] = df['timestamp'].astype(str).str.replace(';', ' ').str.replace(',', ' ')

df['date_obj'] = pd.to_datetime(df['timestamp'], format='mixed', dayfirst=False, errors='coerce')
df['date_str'] = df['date_obj'].dt.strftime('%Y-%m-%d')

df['clean_price'] = df['unit_price'].apply(clean_price)
df['total_val'] = df['quantity'] * df['clean_price']

daily_stats = df.groupby('date_str')['total_val'].sum().sort_values(ascending=False)

print("--- TOP 5 REVENUE DAYS (VERIFICATION) ---")
print(daily_stats.head(5))