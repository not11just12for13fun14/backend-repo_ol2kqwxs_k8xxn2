"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

# Core entities for analytics and recommendations

class UserProfile(BaseModel):
    """
    Users collection schema (collection: "userprofile")
    Captures demographics and acquisition channel.
    """
    user_id: str = Field(..., description="Unique ID for the user (app auth ID or device ID)")
    name: Optional[str] = Field(None, description="Full name")
    email: Optional[str] = Field(None, description="Email address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    gender: Optional[str] = Field(None, description="Gender")
    location: Optional[str] = Field(None, description="City/District/State")
    education: Optional[str] = Field(None, description="Highest qualification")
    experience_years: Optional[float] = Field(None, ge=0, description="Years of experience")
    skills: Optional[List[str]] = Field(default_factory=list, description="List of skills")
    channel: Optional[str] = Field(None, description="Where user spotted the PGRKAM advertisement")

class Event(BaseModel):
    """
    Analytics events (collection: "event")
    """
    user_id: Optional[str] = Field(None, description="User ID if identified; otherwise anonymous")
    event_type: str = Field(..., description="Type of event: page_view, click, search, apply_job, etc.")
    page: Optional[str] = Field(None, description="Page or screen name")
    service: Optional[str] = Field(None, description="Service/component accessed")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Additional event properties")
    device: Optional[str] = Field(None, description="Device or platform info")

class Job(BaseModel):
    """
    Job postings (collection: "job")
    """
    job_id: str = Field(..., description="External or internal job identifier")
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    requirements: List[str] = Field(default_factory=list, description="Required skills/keywords")
    min_experience: Optional[float] = Field(None, ge=0)

class ApplicationOutcome(BaseModel):
    """
    Application outcomes for success/failure analytics (collection: "applicationoutcome")
    """
    user_id: str
    job_id: str
    outcome: str = Field(..., description="success or failure")
    notes: Optional[str] = None

# Backward compatible example schemas (kept for tooling expectations)
class User(BaseModel):
    name: str
    email: str
    address: str
    age: Optional[int] = None
    is_active: bool = True

class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True
