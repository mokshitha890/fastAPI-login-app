# helper/helper.py
from fastapi import HTTPException
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from uuid import uuid4
from datetime import datetime, timedelta, timezone
import os
import re
from dotenv import load_dotenv
load_dotenv()
# import openai
# openai.api_key = os.getenv("OPENAI_API_KEY")

# import google.generativeai as genai
from google import genai
from google.genai import types
from datetime import datetime, timedelta, timezone

# Set API key
# genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
# client = genai.Client(
#         api_key=os.environ.get("GOOGLE_API_KEY"),
#     )

# Get MongoDB URL from environment
MONGODB_URL = os.getenv("MONGODB_URL")

# Raise an error if the environment variable is missing
if not MONGODB_URL:
    raise RuntimeError("MONGODB_URL is not set in the environment variables")

# Initialize MongoDB client
client = AsyncIOMotorClient(MONGODB_URL)
db = client["login_db"]
users_collection = db["users"]
sessions_collection = db["sessions"]
user_bio_collection = db["user_bio"]
# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Pydantic model
class User(BaseModel):
    username: str
    password: str

class UserBio(BaseModel):
    username : str
    firstname: str
    lastname: str
    age: int
    bio: str

# Initialize DB
async def init_db():
    try:
        await db.command("ping")
        print("Connected to MongoDB")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

def close_db():
    client.close()
    print("MongoDB connection closed")

# Register logic
async def register_user(user: User):
    if not user.username.strip() or not user.password:
        raise HTTPException(status_code=400, detail={"message": "Username and password cannot be empty"})

    existing_user = await users_collection.find_one({"username": user.username.strip()})
    if existing_user:
        print("Duplicate username found. Calling OpenAI for suggestions...")
        suggestions = await suggest_usernames(user.username)
        raise HTTPException(status_code=400, detail={
            "message": "Username already exists",
            "suggestions": suggestions
        })

    hashed_password = pwd_context.hash(user.password)
    await users_collection.insert_one({"username": user.username.strip(), "password": hashed_password})
    return {"message": "User registered successfully"}


async def suggest_usernames(username: str):  
    print("v5.0 - Suggesting usernames for:", username)
    prompt = (
        f"Suggest 3 creative and likely unused usernames based on the name '{username}' "
        f"in CSV comma seprated format. Do not include any explanation or additional text—only the usernames."
    )

    print("Calling Gemini with prompt:", prompt)

    try:
        print("GEMINI ---->"+os.getenv("GOOGLE_API_KEY"))
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

        model = "gemini-2.0-flash"
        contents = [
            types.Content(
                role="user",
                parts=[types.Part(text=prompt)],
            ),
        ]
        generate_content_config = types.GenerateContentConfig()

        # Remove await since generate_content is not async
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )

        response_text = response.text
        if not response_text or not response_text.strip():
            return ["TryGemini001", "UserXGen", "AltHandleGem"]

        print("Gemini raw response:", response_text)

        # convert comma to array of strings
        suggestions = [s.strip() for s in response_text.split(",") if s.strip()]    
        if suggestions:
            print("Gemini suggestions:", suggestions)
            return suggestions[:3]

    except Exception as e:
        print("Gemini error:", e)
        return ["BackupUser01", "FallbackName02", "SafeHandle03"]

async def register_and_create_session(user: User, sessions_collection, expires_in_sec: int = 3600):
    # Step 1: Register user
    result = await register_user(user)

    # Step 2: Create session
    session_id = f"{user.username}_{str(uuid4())}"
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_sec)

    session_data = {
        "session_id": session_id,
        "username": user.username,
        "expires_at": expires_at
    }

    await sessions_collection.insert_one(session_data)

    return session_id

# Login logic
async def login_user(user: User):
    if not user.username.strip() or not user.password:
        raise HTTPException(status_code=400, detail={"message": "Username and password cannot be empty"})

    db_user = await users_collection.find_one({"username": user.username.strip()})
    if not db_user:
        raise HTTPException(status_code=400, detail={"message": "Invalid username"})

    if "password" not in db_user or not db_user["password"]:
        raise HTTPException(status_code=400, detail={"message": "Invalid user data"})

    if not pwd_context.verify(user.password, db_user["password"]):
        raise HTTPException(status_code=400, detail={"message": "Invalid password"})

    return {"message": "Login successful"}

## await sessions_collection.insert_one({"session_id": session_id, "username": user.username})
async def store_session(session_id: str, username: str,expires_in_sec: int = 3600):
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_sec)
    session_data = {
        "session_id": session_id,
        "username": username,
        "expires_at": expires_at
    }
    await sessions_collection.insert_one(session_data)
    print(f"Session stored: {session_data}")

async def add_user_bio(userBio: UserBio):
    bio_dict = userBio.model_dump()
    user_record = await user_bio_collection.find_one({"username": userBio.username})
    if user_record:
        await user_bio_collection.update_one({"username": userBio.username}, {"$set": bio_dict})
    else:
        await user_bio_collection.insert_one(bio_dict)
    return {"message": "User bio added successfully"}

async def checkUserSession(session_id: str):
    session_data = await sessions_collection.find_one({"session_id": session_id})
    return session_data

async def get_user_bio(username: str):
    user_record = await user_bio_collection.find_one({"username": username})
    if not user_record:
        raise HTTPException(status_code=404, detail="User bio not found")
    return user_record

async def remove_session(session_id: str):
    result = await sessions_collection.delete_one({"session_id": session_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session removed successfully"}

async def check_session(session_id: str):
    session_data = await sessions_collection.find_one({"session_id": session_id})
    if not session_data:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid session")
    return session_data
    
    