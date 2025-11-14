import os
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import db, create_document, get_documents

app = FastAPI(title="PGRKAM Analytics & Recommendations API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TrackEventRequest(BaseModel):
    user_id: Optional[str] = None
    event_type: str
    page: Optional[str] = None
    service: Optional[str] = None
    properties: Dict[str, Any] = {}
    device: Optional[str] = None

class UpsertUserProfileRequest(BaseModel):
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    education: Optional[str] = None
    experience_years: Optional[float] = None
    skills: Optional[List[str]] = None
    channel: Optional[str] = None

@app.get("/")
def read_root():
    return {"message": "PGRKAM Analytics Backend Running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:100]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:100]}"
    return response

# -------- Analytics Endpoints --------

@app.post("/analytics/track")
def track_event(payload: TrackEventRequest):
    try:
        event_doc = payload.model_dump()
        event_doc["type"] = event_doc.pop("event_type")
        create_document("event", event_doc)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analytics/user")
def upsert_user_profile(payload: UpsertUserProfileRequest):
    try:
        # upsert by user_id
        data = {k: v for k, v in payload.model_dump().items() if v is not None}
        existing = db["userprofile"].find_one({"user_id": payload.user_id})
        if existing:
            db["userprofile"].update_one({"_id": existing["_id"]}, {"$set": data})
        else:
            create_document("userprofile", data)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/overview")
def analytics_overview(limit: int = 50):
    try:
        events = get_documents("event", limit=limit)
        users = get_documents("userprofile", limit=limit)
        # Simple aggregates
        channel_counts: Dict[str, int] = {}
        page_counts: Dict[str, int] = {}
        for e in events:
            ch = (e.get("properties", {}) or {}).get("channel") or e.get("channel")
            if ch:
                channel_counts[ch] = channel_counts.get(ch, 0) + 1
            pg = e.get("page")
            if pg:
                page_counts[pg] = page_counts.get(pg, 0) + 1
        demographics = {
            "gender": {},
            "education": {},
            "location": {},
            "age_buckets": {"<18":0, "18-24":0, "25-34":0, "35-44":0, "45+":0}
        }
        for u in users:
            g = u.get("gender")
            if g:
                demographics["gender"][g] = demographics["gender"].get(g, 0) + 1
            ed = u.get("education")
            if ed:
                demographics["education"][ed] = demographics["education"].get(ed, 0) + 1
            loc = u.get("location")
            if loc:
                demographics["location"][loc] = demographics["location"].get(loc, 0) + 1
            age = u.get("age")
            if isinstance(age, int):
                if age < 18:
                    demographics["age_buckets"]["<18"] += 1
                elif age < 25:
                    demographics["age_buckets"]["18-24"] += 1
                elif age < 35:
                    demographics["age_buckets"]["25-34"] += 1
                elif age < 45:
                    demographics["age_buckets"]["35-44"] += 1
                else:
                    demographics["age_buckets"]["45+"] += 1
        return {
            "channels": channel_counts,
            "pages": page_counts,
            "demographics": demographics,
            "samples": {"events": len(events), "users": len(users)}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------- Simple Recommendation Engine --------

def jaccard(a: List[str], b: List[str]) -> float:
    sa, sb = set(a or []), set(b or [])
    if not sa and not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0

@app.get("/recommendations/{user_id}")
def recommend_jobs(user_id: str, top_k: int = 5):
    try:
        user = db["userprofile"].find_one({"user_id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user_skills = user.get("skills", [])
        jobs = get_documents("job", limit=1000)
        scored = []
        for job in jobs:
            score = jaccard(user_skills, job.get("requirements", []))
            # Simple experience penalty if under-experienced
            min_exp = job.get("min_experience")
            if isinstance(min_exp, (int, float)) and isinstance(user.get("experience_years"), (int, float)):
                if user["experience_years"] < min_exp:
                    score *= 0.8
            scored.append({"job_id": job.get("job_id"), "title": job.get("title"), "score": round(score, 3)})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return {"user_id": user_id, "recommendations": scored[:top_k]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/success-rate/{user_id}")
def success_rate(user_id: str):
    try:
        outcomes = list(db["applicationoutcome"].find({"user_id": user_id}))
        total = len(outcomes)
        success = sum(1 for o in outcomes if str(o.get("outcome")).lower() == "success")
        rate = (success / total) if total else 0.0
        return {"user_id": user_id, "total": total, "success": success, "rate": round(rate, 3)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
