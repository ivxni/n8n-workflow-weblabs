"""
Weblabs Lead Generator - Datenmodelle
SQLAlchemy Models & Pydantic Schemas
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, DECIMAL, ARRAY, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel, EmailStr, Field

Base = declarative_base()


# ============================================
# Enums
# ============================================

class LeadStatus(str, Enum):
    NEW = "new"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    SENT = "sent"
    RESPONDED = "responded"
    REJECTED = "rejected"
    CONVERTED = "converted"


# ============================================
# SQLAlchemy Models (Database)
# ============================================

class Lead(Base):
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Unternehmensdaten
    company_name = Column(String(255), nullable=False)
    industry = Column(String(100))
    address = Column(Text)
    city = Column(String(100))
    postal_code = Column(String(20))
    phone = Column(String(50))
    email = Column(String(255))
    
    # Website-Analyse
    current_website = Column(String(500))
    has_website = Column(Boolean, default=False)
    website_quality_score = Column(Integer, default=0)
    website_issues = Column(ARRAY(Text))
    
    # Google/Maps Daten
    google_rating = Column(DECIMAL(2, 1))
    google_reviews_count = Column(Integer)
    google_place_id = Column(String(255))
    
    # AI-generierte Inhalte
    generated_email_subject = Column(Text)
    generated_email_body = Column(Text)
    generated_website_concept = Column(Text)
    
    # Status
    status = Column(String(50), default=LeadStatus.NEW)
    priority = Column(Integer, default=0)
    
    # Tracking
    email_sent_at = Column(DateTime)
    email_opened_at = Column(DateTime)
    response_received_at = Column(DateTime)
    
    # Metadaten
    source = Column(String(100))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Setting(Base):
    __tablename__ = "settings"
    
    key = Column(String(100), primary_key=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EmailTemplate(Base):
    __tablename__ = "email_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    subject_template = Column(Text, nullable=False)
    body_template = Column(Text, nullable=False)
    industry = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================
# Pydantic Schemas (API)
# ============================================

class LeadBase(BaseModel):
    company_name: str
    industry: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    current_website: Optional[str] = None
    has_website: bool = False
    google_rating: Optional[float] = None
    google_reviews_count: Optional[int] = None


class LeadCreate(LeadBase):
    source: Optional[str] = "manual"


class LeadUpdate(BaseModel):
    company_name: Optional[str] = None
    industry: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[LeadStatus] = None
    priority: Optional[int] = None
    generated_email_subject: Optional[str] = None
    generated_email_body: Optional[str] = None
    notes: Optional[str] = None


class LeadResponse(LeadBase):
    id: int
    website_quality_score: int = 0
    website_issues: Optional[List[str]] = None
    generated_email_subject: Optional[str] = None
    generated_email_body: Optional[str] = None
    generated_website_concept: Optional[str] = None
    status: LeadStatus = LeadStatus.NEW
    priority: int = 0
    source: Optional[str] = None
    notes: Optional[str] = None
    email_sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class LeadListResponse(BaseModel):
    leads: List[LeadResponse]
    total: int
    page: int
    per_page: int


# Email Generation
class EmailGenerationRequest(BaseModel):
    lead_id: int
    regenerate: bool = False


class EmailGenerationResponse(BaseModel):
    subject: str
    body: str
    lead_id: int


# Email Sending
class SendEmailRequest(BaseModel):
    lead_id: int
    subject: Optional[str] = None  # Override generated
    body: Optional[str] = None  # Override generated


class SendEmailResponse(BaseModel):
    success: bool
    message: str
    lead_id: int


class ApproveRequest(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None



# Search/Scrape Request
class SearchRequest(BaseModel):
    city: str = "Stuttgart"
    radius_km: int = 60
    industries: List[str] = Field(default_factory=lambda: [
        "Restaurant",
        "Friseur", 
        "Handwerker",
        "Autowerkstatt",
        "Zahnarzt",
        "Rechtsanwalt",
        "Steuerberater",
        "Immobilienmakler"
    ])
    max_results: int = 50


class SearchResponse(BaseModel):
    found: int
    new_leads: int
    message: str


# Stats
class DashboardStats(BaseModel):
    total_leads: int
    new_leads: int
    pending_review: int
    emails_sent: int
    responses: int
    conversion_rate: float
