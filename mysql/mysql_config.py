from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pymysql

DB_USER = "test"
DB_PASSWORD = "test1"
DB_HOST = "localhost"

# Sử dụng một dictionary để lưu trữ các engine tương ứng với từng database (Tránh tạo lại engine nhiều lần)
_engines = {}


def ensure_database_exists(db_name: str):
    """
    Kết nối tới MySQL Server và tự động tạo Database nếu chưa tồn tại.
    """
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=3306
        )
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
        connection.commit()
        connection.close()
        print(f" 🗄️  Database '{db_name}' đã sẵn sàng (Đã kiểm tra/Tạo mới).")
    except Exception as e:
        print(f"⚠️  Không thể tự động tạo Database '{db_name}': {e}")
        print("    (Sẽ thử kết nối trực tiếp, hãy đảm bảo tài khoản có quyền hoặc DB đã tồn tại)")


def get_engine(db_name: str):
    """
    Trả về SQLAlchemy Engine cho database được chỉ định.
    Nếu chưa có engine cho database này, hàm sẽ tự động kiểm tra/tạo DB và khởi tạo engine mới.
    """
    global _engines
    
    if not db_name:
        raise ValueError("❌ Tên Database không được để trống!")
        
    # Nếu database này đã được tạo engine trước đó rồi thì trả về luôn, không làm lại
    if db_name in _engines:
        return _engines[db_name]
    
    # 1. Tự động kiểm tra / tạo DB
    ensure_database_exists(db_name)
    
    # 2. Khởi tạo Engine mới cho DB này
    database_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{db_name}"
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False
    )
    
    # Lưu lại vào dictionary để tái sử dụng
    _engines[db_name] = engine
    return engine


def test_connection(db_name: str = "testing"):
    try:
        engine = get_engine(db_name)
        with engine.connect() as conn:
            print(f"✅ Kết nối thành công đến MySQL DB: {db_name}")
    except Exception as e:
        print(f"❌ Kết nối thất bại: {e}")


if __name__ == "__main__":
    # Chạy thử nghiệm trực tiếp tạo/kết nối tới db tên là 'testing_auto'
    test_connection("testing_auto")