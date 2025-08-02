# main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Query

from helper.helper import User, init_db, close_db, login_user, register_user,suggest_usernames

app = FastAPI()

# Static and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Startup and shutdown
@app.on_event("startup")
async def startup_db():
    await init_db()

@app.on_event("shutdown")
async def shutdown_db():
    close_db()


# @app.get("/test-openai")
# async def test_openai():
#     return await suggest_usernames("moksh")
# Routes
@app.get("/", response_class=HTMLResponse)
async def get_login(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def get_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/login")
async def login(user: User):
    return await login_user(user)

@app.post("/register")
async def register(user: User):
    return await register_user(user)

@app.get("/test-openai")
async def get_username_suggestions(name: str = Query(..., min_length=3)):
    try:
        suggestions = await suggest_usernames(name)
        return suggestions
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error fetching suggestions")

# @app.get("/test-gemini")
# async def test_gemini():
#     return await suggest_usernames("moksh")
