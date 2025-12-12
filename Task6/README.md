# Task 6 — Documentation

## Overview
This project is a fast, deterministic fake data generator written entirely as PostgreSQL stored procedures. It creates realistic user profiles (names, addresses, contact info, biometrics, and random geolocations) without any external code. Given the same inputs it always returns the same results.

---

## Main Stored Procedure

generate_fake_people
- Purpose: Generate a batch of fake user records.
- Signature:
```sql
FUNCTION generate_fake_people(
  input_seed INT,      -- base seed for deterministic output
  batch_size INT,      -- number of rows to return
  input_locale TEXT,   -- locale code like 'en_US' or 'de_DE'
  page_offset INT      -- skip (page_offset * batch_size) rows
)
RETURNS TABLE (
  user_num INT,
  id UUID,
  full_name TEXT,
  address TEXT,
  phone TEXT,
  email TEXT,
  height_cm INT,
  weight_kg INT,
  eye_color TEXT,
  lat FLOAT,
  lon FLOAT
)
```

---

## How it works

### 1. Deterministic randomness
- We do not use PostgreSQL's RANDOM() because we need repeatable results.
- Instead, we derive pseudo random numbers from MD5 hashes:
  - Hash = MD5(seed || '-' || step_index)
  - Take the first bits of that hash, convert to an integer, then scale to a float between 0 and 1.
- Small changes in the seed or step index produce very different, but reproducible, values.

### 2. Realistic biometrics (normal distribution)
- Height and weight should look natural (cluster around an average).
- We use the Box–Muller transform to turn two uniform random numbers into a normally distributed value:
  - Generate two uniform numbers u1 and u2 (from the MD5 based random generator).
  - Compute z = sqrt(-2 * ln(u1)) * cos(2 * pi * u2).
  - Use z to get:
    - height_cm = round(175 + z * 10)
    - weight_kg = round(80 + z2 * 15)  (z2 from another pair)
- This produces values that follow a bell curve instead of a flat spread.

### 3. Evenly distributed random locations on the globe
- Picking latitude uniformly causes clustering near the poles. To avoid that we:
  - Choose longitude uniformly between -180 and 180.
  - For latitude, use inverse transform sampling of the sphere:
    - Let u be uniform in [0,1].
    - latitude = acos(2 * u - 1) - (pi / 2)
  - This gives a constant probability per area on the sphere.

### 4. Performance and extensibility
- All names/cities for a locale are loaded into PostgreSQL arrays at the start of the procedure.
- Inside the generation loop we pick elements by array index (no SELECTs per row).
- This reduces database I/O and allows very fast generation (target > 5,000 users/sec).
- Schema is unified: a single names table includes a `locale` column so adding locales is easy.

---

## Implementation notes
- The generator is designed to be deterministic: same seed + same parameters → identical output.
- To extend locales or data lists, add rows to the central lookup table (locale column kept).
- Avoid running SELECTs in the inner loop — use arrays and indexing for performance.

---

## Example call
```sql
SELECT * FROM generate_fake_people(12345, 1000, 'en_US', 0);
```
This returns 1,000 deterministic fake users for the `en_US` locale using seed 12345.

---
