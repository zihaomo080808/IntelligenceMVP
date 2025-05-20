# api/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from api.twilio_routes import router as twilio_router
from api.onboarding_routes import router as onboarding_router
from profiles.profiles import router as profiles_router

app = FastAPI(title="AI Startup Recommender")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# async create tables on startup
@app.on_event("startup")
async def on_startup():
    await init_db()

app.include_router(user_router, prefix="/api")
app.include_router(twilio_router, prefix="/twilio")
