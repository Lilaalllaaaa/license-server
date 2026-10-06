from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from datetime import datetime, timedelta
import uvicorn

app = FastAPI(title="Văn Long License Management Server")

# Cấu hình CORS để cho phép mọi Client kết nối không bị chặn
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "licenses.db"

# Khởi tạo Database SQLite
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keys (
            key TEXT PRIMARY KEY,
            registered_hwid TEXT,
            expires_at TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.get("/")
def home():
    return {"status": "online", "message": "Văn Long License Server is running!"}

# 1. API Tạo Key mới
@app.get("/create-key")
def create_key(key: str, days: int = 30):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    expire_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        cursor.execute("INSERT INTO keys (key, expires_at) VALUES (?, ?)", (key, expire_date))
        conn.commit()
        conn.close()
        return {"status": "success", "message": f"Đã tạo Key: {key}", "expires_at": expire_date}
    except Exception:
        conn.close()
        return {"status": "error", "message": "Key này đã tồn tại trên hệ thống!"}

# 2. API Xác thực Key (Dùng GET Query Parameters: /verify-key?key=...&hwid=...)
@app.get("/verify-key")
def verify_key(key: str, hwid: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT registered_hwid, expires_at, status FROM keys WHERE key = ?", (key,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return {"status": "error", "message": "Key không tồn tại trên hệ thống!"}
        
    registered_hwid, expires_at, status = row
    
    # Kiểm tra trạng thái
    if status != 'active':
        conn.close()
        return {"status": "error", "message": "Key đã bị khóa hoặc vô hiệu hóa!"}
        
    # Kiểm tra ngày hết hạn
    expire_dt = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
    if datetime.now() > expire_dt:
        conn.close()
        return {"status": "error", "message": f"Key đã hết hạn sử dụng vào {expires_at}!"}
        
    # Kích hoạt lần đầu -> Đăng ký HWID máy tính
    if not registered_hwid:
        cursor.execute("UPDATE keys SET registered_hwid = ? WHERE key = ?", (hwid, key))
        conn.commit()
        conn.close()
        return {"status": "success", "message": f"Kích hoạt thành công thiết bị mới! Hạn dùng: {expires_at}"}
    
    # Kiểm tra xem có đúng HWID máy tính cũ không
    if registered_hwid != hwid:
        conn.close()
        return {"status": "error", "message": "Key này đang được sử dụng trên máy tính khác!"}

    conn.close()
    return {"status": "success", "message": f"Xác thực thành công! Hạn dùng đến {expires_at}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
