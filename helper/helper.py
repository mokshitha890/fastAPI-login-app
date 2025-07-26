# helper/helper.py
from fastapi import HTTPException
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

load_dotenv()

# Get MongoDB URL from environment
MONGODB_URL = os.getenv("MONGODB_URL")

# Raise an error if the environment variable is missing
if not MONGODB_URL:
    raise RuntimeError("MONGODB_URL is not set in the environment variables")

# Initialize MongoDB client
client = AsyncIOMotorClient(MONGODB_URL)
db = client["login_db"]
users_collection = db["users"]
# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Pydantic model
class User(BaseModel):
    username: str
    password: str

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
        raise HTTPException(status_code=400, detail={"message": "Username already exists"})

    hashed_password = pwd_context.hash(user.password)
    await users_collection.insert_one({"username": user.username.strip(), "password": hashed_password})
    return {"message": "User registered successfully"}

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
