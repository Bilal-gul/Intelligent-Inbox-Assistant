from pydantic import BaseModel
from typing import List, Optional

class Classification(BaseModel):
    primary_category: str
    tags: List[str]
    email_type: str

class TaskItem(BaseModel):
    title: str
    description: str
    deadline: Optional[str] = None
    priority: str = "medium"
    status: str = "pending"

class EventItem(BaseModel):
    title: str
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    location: Optional[str] = None

class EvidenceItem(BaseModel):
    field_path: str
    quote: str

class EmailRequest(BaseModel):
    source_email_id: str
    thread_id: str
    sender: str
    recipients: List[str]
    subject: str
    received_at: str
    body_html: Optional[str] = None

class EmailResponse(BaseModel):
    schema_version: str = "v1.0"
    source_email_id: str
    thread_id: Optional[str] = None
    sender: Optional[str] = None
    subject: Optional[str] = None
    received_at: Optional[str] = None
    classification: Classification
    summary: str
    tasks: List[TaskItem]
    events: List[EventItem]
    evidence: List[EvidenceItem]
    processing_status: str = "success"
