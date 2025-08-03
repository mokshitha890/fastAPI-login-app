# helper/helper.py
from fastapi import HTTPException
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
import os
import re
from dotenv import load_dotenv
load_dotenv()
# import openai
# openai.api_key = os.getenv("OPENAI_API_KEY")

# import google.generativeai as genai
from google import genai
from google.genai import types

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

        # Try to parse usernames from JSON-like response
        # try:
        #     import json
        #     parsed = json.loads(response_text)
        #     if isinstance(parsed, list):
        #         return parsed[:3]
        # except Exception as json_err:
        #     print("JSON parsing fallback:", json_err)

        # # Fallback: regex or line split
        # matches = re.findall(r"\b[\w\d_.-]{3,}\b", response_text)
        # return matches[:3] if matches else ["BackupUser01", "FallbackName02", "SafeHandle03"]

    except Exception as e:
        print("Gemini error:", e)
        return ["BackupUser01", "FallbackName02", "SafeHandle03"]




# async def suggest_usernames_old(username: str):
#     prompt = (
#         f"Suggest 3 creative and likely unused usernames based on the name '{username}' in json formate dont give any other text give only usernames . "
#         f"Return them as a plain list separated by newlines."
#     )

#     print("Calling Gemini with prompt:", prompt)

#     try:
#         model = genai.GenerativeModel("gemini-pro")
#         response = await model.generate_content(prompt)

#         if not response or not response.text.strip():
#             return ["TryGemini001", "UserXGen", "AltHandleGem"]

#         print("Gemini raw response:", response.text)

#         # Try regex to extract usernames from the text
#         matches = re.findall(r"\*\*?([\w\d_.-]+)\*\*?", response.text)
#         if matches:
#             return matches

#         # Fallback: extract first 3 non-empty lines
#         suggestions = response.text.strip().split("\n")
#         print(suggestions)
#         return [s.strip("-•. ").split()[0] for s in suggestions if s.strip()][:3]

#     except Exception as e:
#         print("Gemini error:", e)
#         return ["BackupUser01", "FallbackName02", "SafeHandle03"]



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
