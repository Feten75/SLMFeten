from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.presentation import routes, auth_router

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# Routes API
app.include_router(auth_router.router, prefix="/api/user")
app.include_router(routes.router, prefix="/api/slm")

@app.get("/login")
async def login_page():
    return FileResponse("static/login.html")

@app.get("/admin")
async def admin_page():
    return FileResponse("static/admin.html")

@app.get("/")
async def root():
    return FileResponse("static/login.html")



