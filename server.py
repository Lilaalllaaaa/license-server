from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
from datetime import datetime, timedelta
import uvicorn

app = FastAPI(title="Văn Long License Management Server")
DB_NAME = "licenses.db"

# Khởi tạo Database SQLite lưu danh sách Key
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keys (
            key TEXT PRIMARY KEY,
            registered_hwid TEXT,
            registered_ip TEXT,
            expires_at TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Cấu trúc dữ liệu gửi lên từ Client
class VerifyRequest(BaseModel):
    key: str
    hwid: str
    ip: str

# API Tạo Key mới (Dành cho bạn tạo/bán Key)
@app.get("/create-key")
def create_key(key: str, days: int = 30):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tính ngày hết hạn
    expire_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        cursor.execute("INSERT INTO keys (key, expires_at) VALUES (?, ?)", (key, expire_date))
        conn.commit()
        conn.close()
        return {"status": "success", "message": f"Đã tạo Key: {key}", "expires_at": expire_date}
    except Exception:
        conn.close()
        return {"status": "error", "message": "Key này đã tồn tại trên hệ thống!"}

# API Xác thực Key (Gọi từ App của khách)
@app.post("/verify-key")
def verify_key(data: VerifyRequest):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT registered_hwid, registered_ip, expires_at, status FROM keys WHERE key = ?", (data.key,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return {"status": "error", "message": "Key không tồn tại trên hệ thống!"}
        
    registered_hwid, registered_ip, expires_at, status = row
    
    # 1. Kiểm tra trạng thái Key
    if status != 'active':
        conn.close()
        return {"status": "error", "message": "Key đã bị khóa hoặc vô hiệu hóa!"}
        
    # 2. Kiểm tra ngày hết hạn
    expire_dt = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
    if datetime.now() > expire_dt:
        conn.close()
        return {"status": "error", "message": f"Key đã hết hạn sử dụng vào {expires_at}!"}
        
    # 3. Kiểm tra HWID & IP (Kích hoạt lần đầu hoặc So sánh)
    if not registered_hwid and not registered_ip:
        # Lần đầu kích hoạt -> Khóa cứng HWID và IP này lại
        cursor.execute("UPDATE keys SET registered_hwid = ?, registered_ip = ? WHERE key = ?", (data.hwid, data.ip, data.key))
        conn.commit()
        conn.close()
        return {"status": "success", "message": f"Kích hoạt thành công thiết bị mới! Hạn dùng: {expires_at}"}
    
    # Kiểm tra xem có đúng máy và đúng IP không
    if registered_hwid != data.hwid:
        conn.close()
        return {"status": "error", "message": "Key này đang được sử dụng trên máy tính (HWID) khác!"}
        
    if registered_ip != data.ip:
        conn.close()
        return {"status": "error", "message": f"Địa chỉ IP không khớp! (Đã đăng ký với IP: {registered_ip})"}

    conn.close()
    return {"status": "success", "message": f"Xác thực thành công! Hạn dùng đến {expires_at}"}

# Đoạn khởi chạy Server tự động
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)