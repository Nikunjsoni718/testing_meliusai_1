import asyncio
import logging
import time
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Header
from pydantic import BaseModel, EmailStr

# --- App Setup ---
app = FastAPI(title="MeliusAI Aggregator Core")
logger = logging.getLogger("melius_core")
logging.basicConfig(level=logging.INFO)

# ⚠️ FLAW 1: Security. Hardcoded secrets in version control.
SUPER_SECRET_API_KEY = "sk-live-1234567890abcdef"

# --- Data Models ---
class UserProfile(BaseModel):
    user_id: str
    email: EmailStr
    skills: List[str]
    github_url: Optional[str] = None

class ProcessResponse(BaseModel):
    status: str
    processed_count: int
    message: str

# --- Legacy Functions ---
def blocking_db_save(profile_data: dict):
    """Simulates a legacy synchronous database connection (e.g., old SQLAlchemy setup)."""
    # ⚠️ FLAW 2: Using a synchronous sleep/block in a modern async app.
    time.sleep(1.5) 
    logger.info(f"Saved {profile_data['user_id']} to legacy DB.")
    return True

async def fetch_github_stats(github_url: str):
    """Background task to fetch GitHub data asynchronously."""
    if not github_url:
        return
    await asyncio.sleep(0.5) # Proper async network simulation
    logger.info(f"Fetched stats for {github_url}")

# --- API Routes ---
@app.post("/api/v1/profiles/batch", response_model=ProcessResponse)
async def process_batch_profiles(
    profiles: List[UserProfile],
    background_tasks: BackgroundTasks,
    x_api_key: str = Header(...)
):
    """
    Ingests a batch of profiles, runs strict validation, and queues heavy processing.
    """
    if x_api_key != SUPER_SECRET_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized access.")

    if len(profiles) > 50:
        raise HTTPException(status_code=413, detail="Batch size exceeds limit of 50.")

    processed = 0
    try:
        for profile in profiles:
            # ⚠️ FLAW 3: Calling a synchronous blocking function directly inside an async loop!
            # This will completely freeze the FastAPI event loop for 1.5 seconds per user.
            blocking_db_save(profile.model_dump())

            # Queue proper async task for external API calls
            background_tasks.add_task(fetch_github_stats, profile.github_url)
            processed += 1

        return ProcessResponse(
            status="success",
            processed_count=processed,
            message="Profiles validated and queued."
        )
    except Exception as e:
        # ⚠️ FLAW 4: The Catch-All Swallow. 
        # Catching a generic exception without re-raising it or returning a 500 HTTP error.
        logger.error(f"Fatal error during batch processing: {e}")
        return ProcessResponse(
            status="partial_error", 
            processed_count=processed, 
            message="Something broke, but we are returning a 200 OK anyway."
        )