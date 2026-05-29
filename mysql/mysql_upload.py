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
    (omit --files)                → automatically process all files in the directory
"""

import os
import argparse
import pandas as pd
from mysql_config import get_engine


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))


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


def show_all_files(subfolder: str = ""):
    """
    Lists all files in the specified subfolder relative to BASE_DIR.
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
        print(f"Error: {e}")
        return []


# ──────────────────────────────────────────────
# Option 1: Each CSV → separate table
# ──────────────────────────────────────────────
def upload_csv(subfolder: str = "", files: list = None, db_name: str = "testing_auto", mode: str = "local"):
    path = get_data_path(subfolder)
    engine = get_engine(db_name, mode)  # Truyền db_name và mode vào hàm config nhận tham số
    all_csv = sorted([f for f in os.listdir(path) if f.lower().endswith(".csv")])

    if not all_csv:
        print(f"⚠️  No CSV files found in: {path}")
        return

    print(f"\n📂 Path: {path}")

    # Nếu có chỉ định list files, lọc đúng các file đó. Nếu không, chọn tất cả file CSV.
    if files:
        selected = []
        for f in files:
            if f in all_csv:
                selected.append(f)
            else:
                print(f"  ⚠️  '{f}' not found in {path}, skipping.")
    else:
        print("  → No explicit files requested. Selecting ALL CSV files in folder.")
        selected = all_csv

    if not selected:
        print("⚠️  No valid files to process.")
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
def upload_excel(subfolder: str = "", files: list = None, db_name: str = "testing_auto", mode: str = "local"):
    path = get_data_path(subfolder)
    engine = get_engine(db_name, mode)
    all_excel = sorted([f for f in os.listdir(path) if f.lower().endswith((".xlsx", ".xls"))])

    if not all_excel:
        print(f"⚠️  No Excel files found in: {path}")
        return

    print(f"\n📂 Path: {path}")

    # Nếu có chỉ định list files, lọc đúng các file đó. Nếu không, chọn tất cả file Excel.
    if files:
        selected = []
        for f in files:
            if f in all_excel:
                selected.append(f)
            else:
                print(f"  ⚠️  '{f}' not found in {path}, skipping.")
    else:
        print("  → No explicit files requested. Selecting ALL Excel files in folder.")
        selected = all_excel

    if not selected:
        print("⚠️  No valid files to process.")
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
def upload_csv_folder(subfolder: str = "", db_name: str = "testing_auto", mode: str = "local"):
    path = get_data_path(subfolder)
    engine = get_engine(db_name, mode)  # Truyền db_name và mode vào hàm config nhận tham số

    # Lấy danh sách tất cả các file CSV và Excel
    valid_extensions = (".csv", ".xlsx", ".xls")
    all_files = sorted([
        f for f in os.listdir(path) 
        if os.path.isfile(os.path.join(path, f)) and f.lower().endswith(valid_extensions)
    ])

    if not all_files:
        print(f"⚠️  No CSV or Excel files found in: {path}")
        return

    # Tên table mặc định là tên subfolder, nếu ở root thì đặt là "merged_data"
    table_name = subfolder if subfolder else "merged_data"

    print(f"\n📂 Path: {path}")
    print(f"🗄️  Target DB: {db_name}")
    print(f"📄 Merging {len(all_files)} file(s) → table '{sanitize_table_name(table_name)}'...\n")

    dfs = []
    for filename in all_files:
        filepath = os.path.join(path, filename)
        ext = os.path.splitext(filename)[1].lower()
        
        try:
            # Trường hợp 1: Xử lý file CSV
            if ext == ".csv":
                df = pd.read_csv(filepath)
                if not df.empty:
                    dfs.append(df)
                    print(f"  📎 Loaded CSV   '{filename}' — {len(df)} rows")
                
            # Trường hợp 2: Xử lý file Excel (Duyệt qua tất cả các sheets)
            elif ext in (".xlsx", ".xls"):
                xl = pd.ExcelFile(filepath)
                for sheet_name in xl.sheet_names:
                    df = xl.parse(sheet_name)
                    if not df.empty:
                        dfs.append(df)
                        print(f"  📘 Loaded Excel '{filename}' (Sheet: {sheet_name}) — {len(df)} rows")
                        
        except Exception as e:
            print(f"  ❌ Failed to process '{filename}': {e}")

    # Tiến hành gộp dữ liệu thuần và upload lên MySQL
    if dfs:
        merged_df = pd.concat(dfs, ignore_index=True)
        print(f"\n  🔗 Total merged: {len(merged_df)} rows từ tất cả các file/sheets (chỉ chứa nội dung gốc).")
        upload_dataframe(merged_df, table_name, engine)
    else:
        print("⚠️  No valid data to upload.")

def detect_format_and_read(filepath: str) -> pd.DataFrame:
    """
    Detects if the file is a standard delimited file or a Python dictionary log,
    then reads it into a DataFrame.
    """
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        first_line = f.readline().strip()
    
    if not first_line:
        return pd.DataFrame()

    # 1. Check if it's a Python dictionary format (starts with { and contains u')
    if first_line.startswith('{') and ("u'" in first_line or 'u"' in first_line):
        print(f"     (Format detected: Python Dictionary Log)")
        data = []
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                if line.strip():
                    try:
                        data.append(ast.literal_eval(line.strip()))
                    except Exception:
                        continue
        return pd.DataFrame(data)

    # 2. Otherwise, treat as a standard delimited file
    # Check for common delimiters
    delimiter = "\t" # Default
    for d in ["|", ";", ","]:
        if d in first_line:
            delimiter = d
            break
    
    print(f"     (Format detected: Delimited Text, sep={repr(delimiter)})")
    # FIX: pd.read_csv does not have an 'errors' parameter.
    return pd.read_csv(filepath, sep=delimiter, encoding="utf-8", engine='python')

# ──────────────────────────────────────────────
# Option 4 (Flexible): Each TXT file → separate table
# ──────────────────────────────────────────────
def upload_txt(subfolder: str = "", files: list = None, db_name: str = "testing_auto", mode: str = "local"):
    try:
        path = get_data_path(subfolder)
    except FileNotFoundError as e:
        print(e)
        return

    engine = get_engine(db_name, mode)
    all_txt = sorted([f for f in os.listdir(path) if f.lower().endswith(".txt")])

    if not all_txt:
        print(f"⚠️  No TXT files found in: {path}")
        return

    print(f"\n📂 Path: {path}")

    if files:
        selected = [f for f in files if f in all_txt]
        missing = set(files) - set(selected)
        for m in missing:
            print(f"  ⚠️  '{m}' not found in {path}, skipping.")
    else:
        print("  → No explicit files requested. Selecting ALL TXT files in folder.")
        selected = all_txt

    if not selected:
        print("⚠️  No valid files to process.")
        return

    print(f"\n🚀 Uploading {len(selected)} file(s) to DB '{db_name}' ({mode} mode)...\n")
    for filename in selected:
        table_name = os.path.splitext(filename)[0]
        filepath = os.path.join(path, filename)
        try:
            print(f"  📖 Processing '{filename}'...")
            df = detect_format_and_read(filepath)
            if not df.empty:
                upload_dataframe(df, table_name, engine)
            else:
                print(f"  ⚠️  '{filename}' is empty or has invalid format.")
        except Exception as e:
            print(f"  ❌ Failed '{filename}': {e}")

# ──────────────────────────────────────────────
# Option 5 (Flexible): All TXT files merged → 1 table
# ──────────────────────────────────────────────
def upload_txt_folder(subfolder: str = "", db_name: str = "testing_auto", mode: str = "local"):
    try:
        path = get_data_path(subfolder)
    except FileNotFoundError as e:
        print(e)
        return

    engine = get_engine(db_name, mode)
    all_txt = sorted([f for f in os.listdir(path) if f.lower().endswith(".txt")])

    if not all_txt:
        print(f"⚠️  No TXT files found in: {path}")
        return

    table_name = subfolder if subfolder else "merged_txt"
    print(f"\n📂 Path: {path}")
    print(f"🗄️  Target DB: {db_name} (Mode: {mode})")
    print(f"📄 Merging {len(all_txt)} file(s) → table '{sanitize_table_name(table_name)}'...\n")

    first_file = True
    total_rows = 0
    
    for filename in all_txt:
        filepath = os.path.join(path, filename)
        try:
            print(f"  📎 Processing '{filename}'...")
            df = detect_format_and_read(filepath)
            if not df.empty:
                if_exists = "replace" if first_file else "append"
                upload_dataframe(df, table_name, engine, if_exists=if_exists)
                total_rows += len(df)
                first_file = False
        except Exception as e:
            print(f"  ❌ Failed to process '{filename}': {e}")

    if not first_file:
        print(f"\n✅ Total merged and uploaded: {total_rows} rows.")
    else:
        print("⚠️  No valid data was uploaded.")


if __name__ == "__main__":
    # Test tự động chạy toàn bộ file Excel trong thư mục data/fin_data/ mà không cần hỏi
    files_list = ['log21.txt']
    upload_txt("fpt_test", db_name="testing_auto", mode="remote")