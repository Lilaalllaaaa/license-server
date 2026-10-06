from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Bật CORS cho phép truy cập siêu tốc
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Danh sách Key lưu trên RAM (Siêu nhanh, không bị nghẽn DB Vercel)
VALID_KEYS = {
    "VL-ONLINE-8888": {"status": "active", "expires_at": "2030-12-31"}
}

@app.get("/")
def home():
    return {"status": "online", "message": "Server Van Long Media dang hoat dong!"}

@app.get("/verify-key")
def verify_key(key: str = "", hwid: str = ""):
    clean_key = key.strip()
    
    if not clean_key:
        return {"status": "error", "message": "Vui lòng nhập Key!"}

    if clean_key in VALID_KEYS:
        key_info = VALID_KEYS[clean_key]
        if key_info["status"] == "active":
            return {
                "status": "success", 
                "message": f"Kích hoạt thành công! Hạn dùng: {key_info['expires_at']}"
            }
        else:
            return {"status": "error", "message": "Key đã bị khóa!"}

    return {"status": "error", "message": "Key không tồn tại!"}
