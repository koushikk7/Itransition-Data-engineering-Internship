# Bookstore Analytics Dashboard (Task 4)

This solution processes raw bookstore data—**YAML**, **Parquet**, and **CSV**—resolves user identities using graph logic, and visualizes sales trends via an interactive dashboard.

---

## How to Run

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Launch the dashboard**
   ```bash
   streamlit run dashboard.py
   ```

---

## Verification Scripts

To ensure accuracy, three standalone scripts are provided. These cross-check dashboard logic using the original raw data.

---

## Dashboard Screenshots

If the live server is unavailable, view the full-page results in the `dashboard_images/` folder:

- `DATA1_dashboard.png`
- `DATA2_dashboard.png`
- `DATA3_dashboard.png`

---

### Folder Structure

```
dashboard.py
requirements.txt
dashboard_images/
    ├── DATA1_dashboard.png
    ├── DATA2_dashboard.png
    └── DATA3_dashboard.png
verification_scripts/
    ├── verify_yaml.py
    ├── verify_parquet.py
    └── verify_csv.py
```

---

### Key Features

- **Multi-format data support** (YAML, Parquet, CSV)
- **Identity resolution via graph logic**
- **Sales analytics & visualization**
