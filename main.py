# main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Query
from fastapi.responses import Response
from uuid import uuid4

from helper.helper import User,UserBio,checkUserSession,add_user_bio,remove_session,get_user_bio,check_session, init_db, close_db, login_user, register_user,suggest_usernames,store_session

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
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def get_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/signin", response_class=HTMLResponse)
async def get_register(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(user: User,response: Response):
    await login_user(user)
    session_id = f"{user.username}_{str(uuid4())}"  # Unique session value
    response.set_cookie(
        key="session_id",
        value=session_id,
        max_age=3600,  # 1 hour
        httponly=True
    )
    # Store session in the database
    await store_session(session_id=session_id,username= user.username, expires_in_sec=3600)
    
    return {"message": "Login successful"}

@app.post("/register")
async def register(user: User):
    return await register_user(user)

@app.get("/suggest_usernames")
async def get_username_suggestions(name: str = Query(..., min_length=3)):
    try:
        suggestions = await suggest_usernames(name)
        return suggestions
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error fetching suggestions")
    
@app.post("/user_bio")
async def add_user_bio_api(userBio: UserBio,request: Request):
    session_id = request.cookies.get("session_id")

    # get username from session
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized: No session found")
    # get username from session
    session_data = await checkUserSession(session_id)

    if not session_data:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid session")
    session_username = session_data["username"]

    if session_username != userBio.username:
        raise HTTPException(status_code=403, detail="Forbidden: You can only add bio for your own account")

    await add_user_bio(userBio)
    return {"message": "User bio added successfully"}

@app.get("/user_bio/{username}")
async def get_user_bio_api(username: str):
    user_bio = await get_user_bio(username)
    new_user_bio = { 
        "firstname": user_bio["firstname"],
        "lastname": user_bio["lastname"],
        "age": user_bio["age"],
        "bio": user_bio["bio"]
    } 
    print("User bio fetched:", new_user_bio)
    return new_user_bio
    # return user_bio

@app.get("/remove_session")
async def remove_session_api(request: Request,responce: Response):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized: No session found")
    await remove_session(session_id)
    responce.delete_cookie("session_id")
    return {"message": "Session removed successfully"}

@app.get("/check_session")
async def check_session_api(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthorized: No session found")
    session_data = await check_session(session_id)
    return {"message": "Session is valid"}

# @app.get("/test-gemini")
# async def test_gemini():
#     return await suggest_usernames("moksh")
