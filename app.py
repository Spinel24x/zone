from fastapi import FastAPI, Request, HTTPException, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import secrets
import subprocess
import json
import uuid
import os
import time
import asyncio
from datetime import datetime
from typing import Optional
import hashlib

app = FastAPI(title="Xray Tunnel Manager Pro", version="3.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBasic()

# تنظیمات
class Settings:
    UUID = os.getenv("UUID", str(uuid.uuid4()))
    CF_DOMAIN = os.getenv("CF_DOMAIN", "worker-name.workers.dev")
    RW_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN", "app-name.railway.app")
    WS_PATH = os.getenv("WS_PATH", "/ws")
    XRAY_PORT = int(os.getenv("XRAY_PORT", 8080))
    PANEL_PORT = int(os.getenv("PORT", 8000))
    ADMIN_USER = os.getenv("ADMIN_USER", "admin")
    ADMIN_PASS = os.getenv("ADMIN_PASS", "admin123")
    SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
    
settings = Settings()

# سشن‌های ساده
sessions = {}

# احراز هویت
def verify_credentials(username: str, password: str):
    return username == settings.ADMIN_USER and password == settings.ADMIN_PASS

def get_current_user(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return sessions[session_id]

# نصب و راه‌اندازی Xray
def setup_xray():
    try:
        with open("config.json", "r") as f:
            xray_config = json.load(f)
        
        xray_config["inbounds"][0]["settings"]["clients"][0]["id"] = settings.UUID
        xray_config["inbounds"][0]["streamSettings"]["wsSettings"]["path"] = settings.WS_PATH
        
        os.makedirs("/etc/xray", exist_ok=True)
        with open("/etc/xray/config.json", "w") as f:
            json.dump(xray_config, f, indent=2)
        
        subprocess.Popen(["/usr/local/bin/xray", "run", "-config", "/etc/xray/config.json"])
        print("✅ Xray started successfully")
        return True
    except Exception as e:
        print(f"❌ Xray setup failed: {e}")
        return False

@app.on_event("startup")
async def startup():
    setup_xray()

@app.get("/")
async def root(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id in sessions:
        return RedirectResponse(url="/dashboard")
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    with open("login.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    if verify_credentials(username, password):
        session_id = secrets.token_urlsafe(32)
        sessions[session_id] = {
            "username": username,
            "login_time": datetime.now().isoformat(),
            "ip": "local"
        }
        
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            max_age=86400,
            samesite="lax"
        )
        return response
    
    return JSONResponse(
        status_code=401,
        content={"error": "نام کاربری یا رمز عبور اشتباه است"}
    )

@app.get("/logout")
async def logout(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id in sessions:
        del sessions[session_id]
    
    response = RedirectResponse(url="/login")
    response.delete_cookie("session_id")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id not in sessions:
        return RedirectResponse(url="/login")
    
    with open("dashboard.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/style.css")
async def get_css():
    with open("style.css", "r") as f:
        return HTMLResponse(content=f.read(), media_type="text/css")

@app.get("/zone.js")
async def get_zone_js():
    with open("zone.js", "r") as f:
        return HTMLResponse(content=f.read(), media_type="application/javascript")

@app.get("/api/status")
async def api_status(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id not in sessions:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        xray_check = subprocess.run(
            ["pgrep", "xray"],
            capture_output=True,
            text=True
        )
        xray_status = "running" if xray_check.returncode == 0 else "stopped"
    except:
        xray_status = "unknown"
    
    return {
        "status": "active",
        "uptime": "24/7",
        "connections": 0,
        "xray_status": xray_status,
        "cf_domain": settings.CF_DOMAIN,
        "rw_domain": settings.RW_DOMAIN,
        "ws_path": settings.WS_PATH,
        "uuid": settings.UUID[:8] + "...",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/configs")
async def api_configs(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id not in sessions:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    vless_base = f"vless://{settings.UUID}@{settings.CF_DOMAIN}:443"
    vless_params = f"?encryption=none&security=tls&sni={settings.CF_DOMAIN}&type=ws&host={settings.CF_DOMAIN}&path={settings.WS_PATH}&fp=random"
    vless_full = vless_base + vless_params + "#Premium-Proxy"
    
    worker_env = f"""TARGET_WS_URL=wss://{settings.RW_DOMAIN}{settings.WS_PATH}
UUID={settings.UUID}
WS_PATH={settings.WS_PATH}
CF_DOMAIN={settings.CF_DOMAIN}
RW_DOMAIN={settings.RW_DOMAIN}
ENABLE_AUTH=true
AUTH_TOKEN={secrets.token_hex(16)}"""
    
    return {
        "vless_config": vless_full,
        "worker_env": worker_env,
        "uuid": settings.UUID,
        "details": {
            "domain": settings.CF_DOMAIN,
            "port": 443,
            "network": "ws",
            "path": settings.WS_PATH,
            "security": "tls"
        }
    }

@app.get("/api/update-config")
async def update_config(
    request: Request,
    new_uuid: Optional[str] = None,
    new_cf_domain: Optional[str] = None,
    new_rw_domain: Optional[str] = None,
    new_ws_path: Optional[str] = None
):
    session_id = request.cookies.get("session_id")
    if session_id not in sessions:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if new_uuid:
        settings.UUID = new_uuid
    if new_cf_domain:
        settings.CF_DOMAIN = new_cf_domain
    if new_rw_domain:
        settings.RW_DOMAIN = new_rw_domain
    if new_ws_path:
        settings.WS_PATH = new_ws_path
    
    setup_xray()
    
    return {"success": True, "message": "تنظیمات بروزرسانی شد"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

app.mount("/public", StaticFiles(directory="public"), name="public")
