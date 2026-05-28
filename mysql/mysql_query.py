import pandas as pd
from sqlalchemy import text
# Import hàm get_engine từ file cấu hình của bạn
from mysql_config import get_engine


def clear_or_drop_table(table_name: str, db_name: str = "testing_auto", action: str = "drop"):
    """
    Xóa hoàn toàn bảng (drop) hoặc chỉ xóa sạch dữ liệu giữ lại cấu trúc bảng (truncate).
    action: 'drop' hoặc 'truncate'
    """
    engine = get_engine(db_name)
    action_upper = action.strip().upper()
    
    if action_upper not in ["DROP", "TRUNCATE"]:
        print("❌ Hành động không hợp lệ! Chỉ chọn 'drop' hoặc 'truncate'.")
        return

    # Sử dụng kết nối thuần từ SQLAlchemy để chạy lệnh SQL trực tiếp
    with engine.begin() as connection:
        try:
            if action_upper == "DROP":
                query = text(f"DROP TABLE IF EXISTS `{table_name}`;")
                connection.execute(query)
                print(f"🗑️  Đã xóa hoàn toàn bảng '{table_name}' khỏi DB '{db_name}'.")
            elif action_upper == "TRUNCATE":
                query = text(f"TRUNCATE TABLE `{table_name}`;")
                connection.execute(query)
                print(f"🧹 Đã xóa sạch dữ liệu trong bảng '{table_name}' (Giữ lại cấu trúc).")
        except Exception as e:
            print(f"❌ Thao tác {action_upper} thất bại cho bảng '{table_name}': {e}")


def insert_data_from_dataframe(df: pd.DataFrame, table_name: str, db_name: str = "testing_auto", if_exists: str = "append"):
    """
    Thêm dữ liệu (Insert) từ một DataFrame có sẵn vào bảng MySQL.
    if_exists: 
       - 'append': Thêm tiếp vào bảng đã có (Mặc định)
       - 'replace': Xóa bảng cũ tạo bảng mới nếu đã tồn tại
    """
    if df is None or df.empty:
        print("⚠️ DataFrame trống, không có dữ liệu để insert.")
        return

    engine = get_engine(db_name)
    try:
        # Tự động chuyển tên cột về dạng chuẩn viết thường, không khoảng cách
        df.columns = [str(col).strip().replace(" ", "_").replace("-", "_").lower() for col in df.columns]
        
        df.to_sql(name=table_name, con=engine, if_exists=if_exists, index=False)
        print(f"📥 Đã Insert thành công {len(df)} dòng dữ liệu vào bảng '{table_name}' (Chế độ: {if_exists}).")
    except Exception as e:
        print(f"❌ Insert dữ liệu vào bảng '{table_name}' thất bại: {e}")


def execute_custom_query(sql_script: str, params: dict = None, db_name: str = "testing_auto"):
    """
    Thực hiện các câu lệnh UPDATE, INSERT thủ công, hoặc DELETE bằng câu lệnh SQL thuần.
    """
    engine = get_engine(db_name)
    with engine.begin() as connection:
        try:
            # Chuyển chuỗi string thành đối tượng câu lệnh SQL an toàn của SQLAlchemy
            query = text(sql_script)
            result = connection.execute(query, params or {})
            print(f"⚡ Thực thi lệnh SQL thành công. Số dòng bị ảnh hưởng: {result.rowcount}")
            return result
        except Exception as e:
            print(f"❌ Không thể thực thi lệnh SQL: {e}")
            return None


def query_data_to_dataframe(sql_select_script: str, db_name: str = "testing_auto") -> pd.DataFrame:
    """
    Truy vấn (SELECT) dữ liệu từ MySQL và trả về định dạng Pandas DataFrame 
    để bạn dễ dàng xử lý hoặc xuất file excel/csv sau này.
    """
    engine = get_engine(db_name)
    try:
        # Sử dụng hàm read_sql của pandas để lấy trực tiếp dữ liệu ra DataFrame
        df = pd.read_sql(text(sql_select_script), con=engine)
        print(f"🔍 Truy vấn thành công! Lấy được {len(df)} dòng dữ liệu.")
        return df
    except Exception as e:
        print(f"❌ Truy vấn dữ liệu thất bại: {e}")
        return pd.DataFrame() # Trả về dataframe rỗng nếu lỗi


# ──────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    TARGET_DB = "finance_db"
    TABLE = "fin_data"

    print("--- BẮT ĐẦU CHẠY THỬ NGHIỆM ĐIỀU KHIỂN DATABASE ---")

    # 1. Thử nghiệm CHÈN (INSERT) một vài dòng dữ liệu thủ công bằng DataFrame trước
    data_test = {
        "Project Name": ["Dự án A", "Dự án B"],
        "Funding": [50000, 75000],
        "Status": ["Active", "Pending"]
    }
    df_new = pd.DataFrame(data_test)
    
    print("\n1. Thử nghiệm chèn dữ liệu:")
    insert_data_from_dataframe(df_new, table_name=TABLE, db_name=TARGET_DB, if_exists="append")

    # 2. Thử nghiệm TRUY VẤN (SELECT) dữ liệu vừa chèn
    print("\n2. Thử nghiệm truy vấn dữ liệu:")
    select_sql = f"SELECT * FROM `{TABLE}` WHERE funding > 60000;"
    df_result = query_data_to_dataframe(select_sql, db_name=TARGET_DB)
    print(df_result)

    # 3. Thử nghiệm CẬP NHẬT (UPDATE) trạng thái dự án bằng SQL thuần
    print("\n3. Thử nghiệm cập nhật dữ liệu (UPDATE):")
    update_sql = f"UPDATE `{TABLE}` SET status = :new_status WHERE project_name = :p_name;"
    # Sử dụng params (tham số hóa) để tránh lỗi SQL Injection và an toàn dữ liệu
    execute_custom_query(update_sql, params={"new_status": "Completed", "p_name": "Dự án B"}, db_name=TARGET_DB)

    # Xem lại kết quả sau khi Update
    print("\nKiểm tra lại dữ liệu sau khi UPDATE:")
    print(query_data_to_dataframe(f"SELECT * FROM `{TABLE}`;", db_name=TARGET_DB))

    # 4. Thử nghiệm XÓA BẢNG (DROP) - (Bỏ comment dòng dưới nếu bạn thực sự muốn xóa bảng test)
    print("\n4. Thử nghiệm xóa bảng:")
    clear_or_drop_table(table_name=TABLE, db_name=TARGET_DB, action="drop")