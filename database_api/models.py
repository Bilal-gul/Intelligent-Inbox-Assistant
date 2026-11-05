from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Classification(BaseModel):
    primary_category: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    email_type: Optional[str] = None


class Task(BaseModel):
    title: str
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    priority: str = "medium"
    status: str = "pending"


class Event(BaseModel):
    title: str
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    location: Optional[str] = None


class Evidence(BaseModel):
    field_path: Optional[str] = None
    quote: Optional[str] = None


class EmailAnalysis(BaseModel):
    schema_version: str = "v1.0"
    source_email_id: str
    thread_id: Optional[str] = None
    sender: Optional[str] = None
    subject: Optional[str] = None
    received_at: Optional[datetime] = None
    classification: Classification
    summary: Optional[str] = None
    tasks: list[Task] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    processing_status: str = "success"