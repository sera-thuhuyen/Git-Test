"""
upload_data.py — Upload CSV/Excel files from data/ folder to MySQL.

Usage:
    python upload_data.py --option 1                                      # All CSV → separate tables
    python upload_data.py --option 1 --subfolder sales                    # CSV in data/sales/
    python upload_data.py --option 1 --files a.csv b.csv                  # Only selected files
    python upload_data.py --option 2 --subfolder reports                  # All Excel → sheets as tables
    python upload_data.py --option 2 --files report1.xlsx                 # Only selected Excel files
    python upload_data.py --option 3 --subfolder logs                     # All CSV merged → 1 table
    python upload_data.py --option 3                                       # All CSV merged → table "data"

Options:
    1 = Each CSV file → 1 table  (table name = filename without .csv)
    2 = Each Excel sheet → 1 table  (table name = sheet name)
    3 = All CSV files merged → 1 table  (table name = subfolder name, or "data" if no subfolder)

File selection (option 1 & 2 only):
    --files file1.csv file2.csv   → upload only these files
    (omit --files)                → interactive prompt to choose all or pick specific files
"""

import os
import argparse
import pandas as pd
from mysql_config import get_engine


BASE_DIR = "data"


def get_data_path(subfolder: str = "") -> str:
    path = os.path.join(BASE_DIR, subfolder) if subfolder else BASE_DIR
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ Path not found: {path}")
    return path


def sanitize_table_name(name: str) -> str:
    return name.strip().replace(" ", "_").replace("-", "_").lower()


def upload_dataframe(df: pd.DataFrame, table_name: str, engine, if_exists: str = "replace"):
    table_name = sanitize_table_name(table_name)
    df.to_sql(table_name, con=engine, if_exists=if_exists, index=False)
    print(f"  ✅ Table '{table_name}' — {len(df)} rows uploaded.")


# ──────────────────────────────────────────────
# Interactive file selector
# ──────────────────────────────────────────────
def prompt_file_selection(available_files: list, file_type: str = "file") -> list:
    """
    Show available files and let user pick all or a specific subset.
    Returns a list of selected filenames.
    """
    print(f"\n📋 Available {file_type}s ({len(available_files)} found):")
    for i, f in enumerate(available_files, start=1):
        print(f"   [{i}] {f}")

    print("\n  Enter  'all'               → upload all files")
    print("  Enter  numbers e.g. 1 3 4  → upload selected files only")
    print("  Enter  filenames e.g. a.csv b.csv → upload by name\n")

    while True:
        raw = input("Your choice: ").strip()

        if not raw:
            print("⚠️  No input. Please try again.")
            continue

        if raw.lower() == "all":
            print(f"  → Selected all {len(available_files)} file(s).")
            return available_files

        # Try parsing as index numbers
        parts = raw.split()
        try:
            indices = [int(p) for p in parts]
            selected = []
            valid = True
            for idx in indices:
                if 1 <= idx <= len(available_files):
                    selected.append(available_files[idx - 1])
                else:
                    print(f"⚠️  Index {idx} is out of range (1–{len(available_files)}).")
                    valid = False
                    break
            if valid and selected:
                print(f"  → Selected: {', '.join(selected)}")
                return selected
        except ValueError:
            # Try parsing as filenames
            selected = []
            valid = True
            for name in parts:
                if name in available_files:
                    selected.append(name)
                else:
                    print(f"⚠️  File '{name}' not found in folder.")
                    valid = False
                    break
            if valid and selected:
                print(f"  → Selected: {', '.join(selected)}")
                return selected

        print("⚠️  Invalid input. Enter 'all', index numbers, or filenames.\n")

# List all files in a folder with a specific extension (e.g. .csv, .xlsx) and let user select which ones to upload.
def show_all_files(subfolder: str = ""):
    """
    Lists all files in the specified subfolder relative to
    BASE_DIR.
    If subfolder is empty, it lists files in BASE_DIR.
    """
    try:
        path = get_data_path(subfolder)
        
        files = sorted([
            f for f in os.listdir(path) 
            if os.path.isfile(os.path.join(path, f))
        ])

        if not files:
            print(f"No files found in: {path}")
            return []

        print(f"Files in {path}:")
        for filename in files:
            print(filename)
            
        return files

    except FileNotFoundError:
        print(f"Error: Subfolder '{subfolder}' not found.")
        return []
    except Exception as e:
        print(f"Error: {e}") # Added return to ensure consistency on all exception paths
# ──────────────────────────────────────────────
# Option 1: Each CSV → separate table
# ──────────────────────────────────────────────
def upload_csv_separate(subfolder: str = "", files: list = None):
    path = get_data_path(subfolder)
    engine = get_engine()
    all_csv = sorted([f for f in os.listdir(path) if f.lower().endswith(".csv")])

    if not all_csv:
        print(f"⚠️  No CSV files found in: {path}")
        return

    print(f"\n📂 Path: {path}")

    # Resolve which files to process
    if files:
        # Validate --files input against actual files in folder
        selected = []
        for f in files:
            if f in all_csv:
                selected.append(f)
            else:
                print(f"  ⚠️  '{f}' not found in {path}, skipping.")
    else:
        selected = prompt_file_selection(all_csv, file_type="CSV")

    if not selected:
        print("⚠️  No valid files selected.")
        return

    print(f"\n🚀 Uploading {len(selected)} file(s) → {len(selected)} table(s)...\n")
    for filename in selected:
        table_name = os.path.splitext(filename)[0]
        filepath = os.path.join(path, filename)
        try:
            df = pd.read_csv(filepath)
            upload_dataframe(df, table_name, engine)
        except Exception as e:
            print(f"  ❌ Failed '{filename}': {e}")


# ──────────────────────────────────────────────
# Option 2: Each Excel sheet → separate table
# ──────────────────────────────────────────────
def upload_excel_sheets(subfolder: str = "", files: list = None):
    path = get_data_path(subfolder)
    engine = get_engine()
    all_excel = sorted([f for f in os.listdir(path) if f.lower().endswith((".xlsx", ".xls"))])

    if not all_excel:
        print(f"⚠️  No Excel files found in: {path}")
        return

    print(f"\n📂 Path: {path}")

    # Resolve which files to process
    if files:
        selected = []
        for f in files:
            if f in all_excel:
                selected.append(f)
            else:
                print(f"  ⚠️  '{f}' not found in {path}, skipping.")
    else:
        selected = prompt_file_selection(all_excel, file_type="Excel")

    if not selected:
        print("⚠️  No valid files selected.")
        return

    total_sheets = 0
    print(f"\n🚀 Uploading {len(selected)} Excel file(s)...\n")

    for filename in selected:
        filepath = os.path.join(path, filename)
        print(f"  📘 File: {filename}")
        try:
            xl = pd.ExcelFile(filepath)
            print(f"     Sheets found: {xl.sheet_names}")
            for sheet_name in xl.sheet_names:
                df = xl.parse(sheet_name)
                upload_dataframe(df, sheet_name, engine)
                total_sheets += 1
        except Exception as e:
            print(f"  ❌ Failed '{filename}': {e}")

    print(f"\n✅ Total tables created: {total_sheets}")


# ──────────────────────────────────────────────
# Option 3: All CSV merged → 1 table
# ──────────────────────────────────────────────
def upload_csv_merged(subfolder: str = ""):
    path = get_data_path(subfolder)
    engine = get_engine()
    csv_files = sorted([f for f in os.listdir(path) if f.lower().endswith(".csv")])

    if not csv_files:
        print(f"⚠️  No CSV files found in: {path}")
        return

    table_name = subfolder if subfolder else "data"

    print(f"\n📂 Path: {path}")
    print(f"📄 Merging {len(csv_files)} CSV file(s) → table '{sanitize_table_name(table_name)}'...\n")

    dfs = []
    for filename in csv_files:
        filepath = os.path.join(path, filename)
        try:
            df = pd.read_csv(filepath)
            df["_source_file"] = filename
            dfs.append(df)
            print(f"  📎 Loaded '{filename}' — {len(df)} rows")
        except Exception as e:
            print(f"  ❌ Failed '{filename}': {e}")

    if dfs:
        merged_df = pd.concat(dfs, ignore_index=True)
        print(f"\n  🔗 Total merged: {len(merged_df)} rows")
        upload_dataframe(merged_df, table_name, engine)


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Upload data files to MySQL")
    parser.add_argument(
        "--option", type=int, required=True, choices=[1, 2, 3],
        help="1=CSV→separate tables | 2=Excel sheets→separate tables | 3=CSV→merged table"
    )
    parser.add_argument(
        "--subfolder", type=str, default="",
        help="Subfolder inside data/ (default: empty = use data/ directly)"
    )
    parser.add_argument(
        "--files", type=str, nargs="+", default=None,
        help="(Option 1 & 2) Specific filenames to upload. Omit to get interactive prompt."
    )
    args = parser.parse_args()

    print(f"\n🚀 Upload Option {args.option} | Subfolder: '{args.subfolder or '(none)'}'\n")

    if args.option == 1:
        upload_csv_separate(args.subfolder, args.files)
    elif args.option == 2:
        upload_excel_sheets(args.subfolder, args.files)
    elif args.option == 3:
        upload_csv_merged(args.subfolder)

    print("\n✅ Done!\n")


if __name__ == "__main__":
    main()