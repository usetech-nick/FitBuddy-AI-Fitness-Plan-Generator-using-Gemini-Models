"""
FitBuddy — AI Fitness Plan Generator
======================================
Backend: FastAPI + SQLAlchemy (SQLite) + Google Gemini API
Author : (your name here)

Run with:
    uvicorn main:app --reload
"""

import os
import json
import textwrap
from datetime import datetime
from typing import Optional

import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, create_engine
)
from sqlalchemy.orm import DeclarativeBase, Session

# ─────────────────────────────────────────────
# 0.  Environment & Gemini setup
# ─────────────────────────────────────────────
import os
from dotenv import load_dotenv

# 0. Environment & Gemini setup
# -----------------------------------------------------

load_dotenv()  # reads .env file if present

# Fetch the key from your environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    # Safely pass the variable here, NOT the hardcoded string
    genai.configure(api_key=GEMINI_API_KEY)
    # Use the latest Gemini Flash model for fast, cost-effective responses
    gemini_model = genai.GenerativeModel("gemini-2.5-flash")
else:
    gemini_model = None
    print("WARNING: GEMINI_API_KEY not found in environment. Running in demo mode.")

# ─────────────────────────────────────────────
# 1.  Database  (SQLAlchemy + SQLite)
# ─────────────────────────────────────────────
DATABASE_URL = "sqlite:///./fitbuddy.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},    # required for SQLite + FastAPI
)


class Base(DeclarativeBase):
    pass


class FitnessPlan(Base):
    """Stores every generated (or updated) plan for a user session."""
    __tablename__ = "fitness_plans"

    id          = Column(Integer, primary_key=True, index=True)
    user_name   = Column(String(120), nullable=False)
    age         = Column(Integer, nullable=False)
    weight      = Column(String(20), nullable=False)   # stored as string e.g. "75 kg"
    goal        = Column(String(60), nullable=False)
    intensity   = Column(String(30), nullable=False)
    plan_json   = Column(Text, nullable=False)          # raw JSON string from Gemini
    nutrition_tip = Column(Text, nullable=True)
    feedback    = Column(Text, nullable=True)           # last feedback that changed plan
    version     = Column(Integer, default=1)
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Create tables on startup
Base.metadata.create_all(bind=engine)


# ─────────────────────────────────────────────
# 2.  FastAPI app + Jinja2 templates
# ─────────────────────────────────────────────
app = FastAPI(title="FitBuddy", version="1.0.0")
templates = Jinja2Templates(directory="templates")


# ─────────────────────────────────────────────
# 3.  Gemini prompt templates
# ─────────────────────────────────────────────

def build_plan_prompt(name: str, age: int, weight: str, goal: str, intensity: str) -> str:
    """
    SYSTEM PROMPT — 7-Day Workout Plan Generator
    -----------------------------------------------
    We instruct Gemini to return a strict JSON object so the frontend
    can render it programmatically without fragile markdown parsing.
    """
    return textwrap.dedent(f"""
    You are FitBuddy, an elite, certified personal trainer and sports scientist.
    Your task is to create a highly personalized 7-day workout plan.

    USER PROFILE:
    - Name       : {name}
    - Age        : {age} years old
    - Weight     : {weight}
    - Fitness Goal : {goal}
    - Intensity Level : {intensity}

    OUTPUT RULES (CRITICAL — follow exactly):
    1. Respond ONLY with a valid JSON object. No markdown fences, no prose outside JSON.
    2. The JSON must conform to this exact schema:
    {{
      "plan_title": "string — catchy personalised plan name",
      "summary": "string — 2-sentence motivational overview for {name}",
      "days": [
        {{
          "day": "Day 1 — Monday",
          "focus": "string — e.g. Upper Body Strength",
          "warm_up": "string — 3-5 minute warm-up description",
          "exercises": [
            {{
              "name": "Exercise name",
              "sets": "e.g. 3",
              "reps_or_duration": "e.g. 12 reps or 30 seconds",
              "rest": "e.g. 60 sec",
              "tip": "one-line form cue or modification"
            }}
          ],
          "cool_down": "string — cool-down/stretch description",
          "estimated_duration": "string — e.g. 45 minutes"
        }}
      ],
      "weekly_note": "string — end-of-week motivation and what to watch for"
    }}
    3. Include exactly 7 day objects in the "days" array.
    4. Scale exercise difficulty, volume, and rest periods to the {intensity} intensity level.
    5. Tailor exercises directly to the goal: {goal}.
    6. Be specific — use real exercise names (e.g. "Dumbbell Romanian Deadlift"), not generic terms.
    """).strip()


def build_feedback_prompt(existing_plan_json: str, feedback: str, user_profile: dict) -> str:
    """
    SYSTEM PROMPT — Feedback-Based Plan Regeneration
    --------------------------------------------------
    Sends the old plan + user's feedback to Gemini for a surgical update.
    """
    return textwrap.dedent(f"""
    You are FitBuddy, an adaptive personal trainer.
    The user has reviewed their existing workout plan and provided feedback.
    Your job is to regenerate an improved plan that incorporates the feedback.

    USER PROFILE:
    - Name: {user_profile['name']}, Age: {user_profile['age']}, Weight: {user_profile['weight']}
    - Goal: {user_profile['goal']}, Intensity: {user_profile['intensity']}

    EXISTING PLAN (JSON):
    {existing_plan_json}

    USER FEEDBACK:
    "{feedback}"

    OUTPUT RULES (CRITICAL — follow exactly):
    1. Respond ONLY with a valid JSON object using the EXACT same schema as the existing plan.
    2. Intelligently incorporate the feedback — if the user mentions an injury, replace those
       exercises with safe alternatives and note the modification in the "tip" field.
    3. Add a "feedback_applied" key at the top level with a short string explaining what changed.
    4. No markdown, no prose — pure JSON only.
    """).strip()


def build_nutrition_prompt(goal: str, name: str) -> str:
    """
    SYSTEM PROMPT — Daily Nutrition / Recovery Tip
    ------------------------------------------------
    Returns a short, goal-specific JSON object with actionable advice.
    """
    return textwrap.dedent(f"""
    You are FitBuddy's nutrition and recovery specialist.
    Generate ONE daily tip for {name} whose fitness goal is: {goal}.

    OUTPUT RULES:
    1. Respond ONLY with a valid JSON object — no markdown, no extra text.
    2. Use this exact schema:
    {{
      "tip_type": "Nutrition" or "Recovery" (choose the most relevant for the goal),
      "headline": "short punchy headline (max 10 words)",
      "advice": "2-3 sentence actionable advice tailored to {goal}",
      "macro_snapshot": {{
        "protein": "e.g. 1.8g per kg bodyweight",
        "carbs": "e.g. 45% of daily calories",
        "fats": "e.g. 25% of daily calories"
      }},
      "bonus_tip": "one sentence recovery or sleep tip"
    }}
    """).strip()


# ─────────────────────────────────────────────
# 4.  Helper: call Gemini safely
# ─────────────────────────────────────────────

def call_gemini(prompt: str) -> dict:
    """
    Calls the Gemini API and parses the JSON response.
    Returns a dict on success, or raises HTTPException on failure.
    """
    if not gemini_model:
        raise HTTPException(
            status_code=503,
            detail="Gemini API key not configured. Set GEMINI_API_KEY in your .env file."
        )

    try:
        response = gemini_model.generate_content(prompt)
        raw_text = response.text.strip()

        # Strip accidental markdown code fences if Gemini adds them anyway
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        return json.loads(raw_text)

    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini returned non-JSON output: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini API error: {str(e)}"
        )


# ─────────────────────────────────────────────
# 5.  Routes
# ─────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main Glassmorphism UI."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/generate-plan")
async def generate_plan(
    name      : str = Form(...),
    age       : int = Form(...),
    weight    : str = Form(...),
    goal      : str = Form(...),
    intensity : str = Form(...),
):
    """
    Scenario 1 — Generate a fresh 7-day plan.
    1. Build prompt → call Gemini → parse JSON
    2. Also fetch a nutrition/recovery tip in one extra call
    3. Save both to SQLite
    4. Return combined JSON to the frontend
    """
    # --- Generate workout plan ---
    plan_prompt = build_plan_prompt(name, age, weight, goal, intensity)
    plan_data   = call_gemini(plan_prompt)

    # --- Generate nutrition/recovery tip ---
    nutrition_prompt = build_nutrition_prompt(goal, name)
    nutrition_data   = call_gemini(nutrition_prompt)

    # --- Persist to database ---
    with Session(engine) as session:
        record = FitnessPlan(
            user_name     = name,
            age           = age,
            weight        = weight,
            goal          = goal,
            intensity     = intensity,
            plan_json     = json.dumps(plan_data),
            nutrition_tip = json.dumps(nutrition_data),
            version       = 1,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        plan_id = record.id

    return JSONResponse({
        "plan_id"       : plan_id,
        "plan"          : plan_data,
        "nutrition_tip" : nutrition_data,
    })


@app.post("/update-plan/{plan_id}")
async def update_plan(plan_id: int, feedback: str = Form(...)):
    """
    Scenario 2 — Feedback loop.
    1. Load existing plan from SQLite
    2. Send old plan + feedback to Gemini
    3. Save updated plan (incremented version) to SQLite
    4. Return updated plan JSON
    """
    with Session(engine) as session:
        record = session.get(FitnessPlan, plan_id)
        if not record:
            raise HTTPException(status_code=404, detail="Plan not found")

        user_profile = {
            "name"      : record.user_name,
            "age"       : record.age,
            "weight"    : record.weight,
            "goal"      : record.goal,
            "intensity" : record.intensity,
        }
        existing_plan = record.plan_json

    # --- Call Gemini with feedback ---
    feedback_prompt  = build_feedback_prompt(existing_plan, feedback, user_profile)
    updated_plan     = call_gemini(feedback_prompt)

    # --- Save new version ---
    with Session(engine) as session:
        record = session.get(FitnessPlan, plan_id)
        record.plan_json  = json.dumps(updated_plan)
        record.feedback   = feedback
        record.version    += 1
        record.updated_at = datetime.utcnow()
        session.commit()

    return JSONResponse({
        "plan_id" : plan_id,
        "plan"    : updated_plan,
        "version" : record.version,
    })


@app.get("/plan/{plan_id}")
async def get_plan(plan_id: int):
    """Retrieve a stored plan by ID."""
    with Session(engine) as session:
        record = session.get(FitnessPlan, plan_id)
        if not record:
            raise HTTPException(status_code=404, detail="Plan not found")

        return JSONResponse({
            "plan_id"       : record.id,
            "user_name"     : record.user_name,
            "plan"          : json.loads(record.plan_json),
            "nutrition_tip" : json.loads(record.nutrition_tip) if record.nutrition_tip else None,
            "version"       : record.version,
            "created_at"    : record.created_at.isoformat(),
        })
