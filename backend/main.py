"""
Weblabs AI Lead Generator - Backend API

FastAPI server handling lead management, AI-powered email generation,
and automated SMTP delivery for local business outreach.
"""

import os
import json
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from database import get_db, init_db, engine
from models import (
    Base, Lead, Setting, EmailTemplate, LeadStatus,
    LeadCreate, LeadUpdate, LeadResponse, LeadListResponse,
    EmailGenerationRequest, EmailGenerationResponse,
    SendEmailRequest, SendEmailResponse, ApproveRequest,
    SearchRequest, SearchResponse, DashboardStats
)
from ai_service import generate_personalized_email, analyze_website
from email_service import send_email
from scraper_service import search_businesses

# ============================================
# App Initialisierung
# ============================================

app = FastAPI(
    title="Weblabs Lead Generator API",
    description="Automatisierte Lead-Generierung für Webentwicklung",
    version="1.0.0"
)

# CORS für Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """Datenbank beim Start initialisieren"""
    # Tabellen erstellen falls nicht vorhanden
    Base.metadata.create_all(bind=engine)
    print("Weblabs Lead Generator API started")


# ============================================
# Dashboard & Stats
# ============================================

@app.get("/")
async def root():
    return {"message": "Weblabs Lead Generator API", "status": "running"}


@app.get("/api/stats", response_model=DashboardStats)
async def get_stats(db: Session = Depends(get_db)):
    """Dashboard Statistiken abrufen"""
    total = db.query(func.count(Lead.id)).scalar() or 0
    new = db.query(func.count(Lead.id)).filter(Lead.status == LeadStatus.NEW).scalar() or 0
    reviewed = db.query(func.count(Lead.id)).filter(Lead.status == LeadStatus.REVIEWED).scalar() or 0
    sent = db.query(func.count(Lead.id)).filter(Lead.status.in_([LeadStatus.SENT, LeadStatus.RESPONDED, LeadStatus.CONVERTED])).scalar() or 0
    responses = db.query(func.count(Lead.id)).filter(Lead.status.in_([LeadStatus.RESPONDED, LeadStatus.CONVERTED])).scalar() or 0
    converted = db.query(func.count(Lead.id)).filter(Lead.status == LeadStatus.CONVERTED).scalar() or 0
    
    conversion_rate = (converted / sent * 100) if sent > 0 else 0.0
    
    return DashboardStats(
        total_leads=total,
        new_leads=new,
        pending_review=reviewed,
        emails_sent=sent,
        responses=responses,
        conversion_rate=round(conversion_rate, 1)
    )


# ============================================
# Lead Management
# ============================================

@app.get("/api/leads", response_model=LeadListResponse)
async def get_leads(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[LeadStatus] = None,
    city: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Alle Leads mit Pagination und Filtern abrufen"""
    query = db.query(Lead)
    
    # Filter anwenden
    if status:
        query = query.filter(Lead.status == status)
    if city:
        query = query.filter(Lead.city.ilike(f"%{city}%"))
    if search:
        query = query.filter(
            (Lead.company_name.ilike(f"%{search}%")) |
            (Lead.industry.ilike(f"%{search}%"))
        )
    
    # Total Count
    total = query.count()
    
    # Pagination
    leads = query.order_by(desc(Lead.priority), desc(Lead.created_at)) \
                 .offset((page - 1) * per_page) \
                 .limit(per_page) \
                 .all()
    
    return LeadListResponse(
        leads=[LeadResponse.model_validate(lead) for lead in leads],
        total=total,
        page=page,
        per_page=per_page
    )


@app.get("/api/leads/{lead_id}", response_model=LeadResponse)
async def get_lead(lead_id: int, db: Session = Depends(get_db)):
    """Einzelnen Lead abrufen"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nicht gefunden")
    return LeadResponse.model_validate(lead)


@app.post("/api/leads", response_model=LeadResponse)
async def create_lead(lead_data: LeadCreate, db: Session = Depends(get_db)):
    """Neuen Lead manuell erstellen"""
    lead = Lead(**lead_data.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return LeadResponse.model_validate(lead)


@app.patch("/api/leads/{lead_id}", response_model=LeadResponse)
async def update_lead(lead_id: int, lead_data: LeadUpdate, db: Session = Depends(get_db)):
    """Lead aktualisieren"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nicht gefunden")
    
    update_data = lead_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead, field, value)
    
    lead.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(lead)
    return LeadResponse.model_validate(lead)


@app.delete("/api/leads/{lead_id}")
async def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    """Lead löschen"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nicht gefunden")
    
    db.delete(lead)
    db.commit()
    return {"message": "Lead gelöscht", "id": lead_id}


# ============================================
# Lead Navigation (für Kartenansicht)
# ============================================

@app.get("/api/leads/navigate/{current_id}")
async def navigate_leads(
    current_id: int,
    direction: str = Query(..., regex="^(next|prev)$"),
    status: Optional[LeadStatus] = None,
    db: Session = Depends(get_db)
):
    """Nächsten/Vorherigen Lead für Navigation"""
    current = db.query(Lead).filter(Lead.id == current_id).first()
    if not current:
        raise HTTPException(status_code=404, detail="Lead nicht gefunden")
    
    query = db.query(Lead)
    if status:
        query = query.filter(Lead.status == status)
    
    if direction == "next":
        # Nächster Lead (höhere ID oder niedrigere Priorität)
        next_lead = query.filter(Lead.id > current_id).order_by(Lead.id).first()
        if not next_lead:
            # Wrap around zum ersten
            next_lead = query.order_by(Lead.id).first()
        return {"lead_id": next_lead.id if next_lead else None}
    else:
        # Vorheriger Lead
        prev_lead = query.filter(Lead.id < current_id).order_by(desc(Lead.id)).first()
        if not prev_lead:
            # Wrap around zum letzten
            prev_lead = query.order_by(desc(Lead.id)).first()
        return {"lead_id": prev_lead.id if prev_lead else None}


# ============================================
# AI Email Generation
# ============================================

@app.post("/api/leads/{lead_id}/generate-email", response_model=EmailGenerationResponse)
async def generate_email(lead_id: int, db: Session = Depends(get_db)):
    """AI-generierte personalisierte E-Mail für Lead erstellen"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nicht gefunden")
    
    # E-Mail generieren
    result = await generate_personalized_email(lead)
    
    # In Datenbank speichern
    lead.generated_email_subject = result["subject"]
    lead.generated_email_body = result["body"]
    lead.status = LeadStatus.REVIEWED
    lead.updated_at = datetime.utcnow()
    db.commit()
    
    return EmailGenerationResponse(
        subject=result["subject"],
        body=result["body"],
        lead_id=lead_id
    )


@app.post("/api/leads/{lead_id}/analyze-website")
async def analyze_lead_website(lead_id: int, db: Session = Depends(get_db)):
    """Website des Leads analysieren"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nicht gefunden")
    
    if not lead.current_website:
        return {"message": "Keine Website vorhanden", "has_website": False}
    
    analysis = await analyze_website(lead.current_website)
    
    lead.website_quality_score = analysis.get("score", 0)
    lead.website_issues = analysis.get("issues", [])
    db.commit()
    
    return analysis


# ============================================
# Email Sending
# ============================================

@app.post("/api/leads/{lead_id}/send-email", response_model=SendEmailResponse)
async def send_lead_email(
    lead_id: int, 
    request: SendEmailRequest = None,
    db: Session = Depends(get_db)
):
    """E-Mail an Lead senden"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nicht gefunden")
    
    if not lead.email:
        raise HTTPException(status_code=400, detail="Lead hat keine E-Mail-Adresse")
    
    # Subject und Body (override oder generated)
    subject = request.subject if request and request.subject else lead.generated_email_subject
    body = request.body if request and request.body else lead.generated_email_body
    
    if not subject or not body:
        raise HTTPException(status_code=400, detail="E-Mail muss erst generiert werden")
    
    # E-Mail senden
    success = await send_email(
        to_email=lead.email,
        subject=subject,
        body=body,
        company_name=lead.company_name
    )
    
    if success:
        lead.status = LeadStatus.SENT
        lead.email_sent_at = datetime.utcnow()
        db.commit()
        return SendEmailResponse(success=True, message="E-Mail erfolgreich gesendet", lead_id=lead_id)
    else:
        raise HTTPException(status_code=500, detail="E-Mail konnte nicht gesendet werden")


@app.post("/api/leads/{lead_id}/approve")
async def approve_lead(lead_id: int, request: ApproveRequest = None, db: Session = Depends(get_db)):
    """Lead genehmigen (bereit zum Senden)"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nicht gefunden")
    
    if request:
        if request.subject:
            lead.generated_email_subject = request.subject
        if request.body:
            lead.generated_email_body = request.body

    lead.status = LeadStatus.APPROVED
    lead.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(lead)
    
    return {"message": "Lead genehmigt", "status": LeadStatus.APPROVED}


@app.post("/api/leads/{lead_id}/reject")
async def reject_lead(lead_id: int, db: Session = Depends(get_db)):
    """Lead ablehnen"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nicht gefunden")
    
    lead.status = LeadStatus.REJECTED
    lead.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Lead abgelehnt", "status": LeadStatus.REJECTED}


# ============================================
# Business Search / Scraping
# ============================================

@app.post("/api/search", response_model=SearchResponse)
async def search_new_leads(request: SearchRequest, db: Session = Depends(get_db)):
    """Neue Unternehmen suchen und als Leads hinzufügen"""
    results = await search_businesses(
        city=request.city,
        radius_km=request.radius_km,
        industries=request.industries,
        max_results=request.max_results
    )
    
    new_count = 0
    for business in results:
        # Prüfen ob bereits vorhanden (nach Name und Stadt)
        existing = db.query(Lead).filter(
            Lead.company_name == business["name"],
            Lead.city == business.get("city", request.city)
        ).first()
        
        if not existing:
            lead = Lead(
                company_name=business["name"],
                industry=business.get("industry"),
                address=business.get("address"),
                city=business.get("city", request.city),
                postal_code=business.get("postal_code"),
                phone=business.get("phone"),
                email=business.get("email"),
                current_website=business.get("website"),
                has_website=bool(business.get("website")),
                google_rating=business.get("rating"),
                google_reviews_count=business.get("reviews_count"),
                google_place_id=business.get("place_id"),
                source="google_maps",
                status=LeadStatus.NEW
            )
            db.add(lead)
            new_count += 1
    
    db.commit()
    
    return SearchResponse(
        found=len(results),
        new_leads=new_count,
        message=f"{new_count} neue Leads von {len(results)} gefundenen Unternehmen hinzugefügt"
    )


# ============================================
# Settings
# ============================================

@app.get("/api/settings")
async def get_settings(db: Session = Depends(get_db)):
    """Alle Einstellungen abrufen"""
    settings = db.query(Setting).all()
    return {s.key: s.value for s in settings}


@app.put("/api/settings/{key}")
async def update_setting(key: str, value: str, db: Session = Depends(get_db)):
    """Einstellung aktualisieren"""
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        setting.value = value
        setting.updated_at = datetime.utcnow()
    else:
        setting = Setting(key=key, value=value)
        db.add(setting)
    
    db.commit()
    return {"key": key, "value": value}


# ============================================
# Bulk Operations
# ============================================

@app.post("/api/leads/bulk/generate-emails")
async def bulk_generate_emails(
    status: LeadStatus = LeadStatus.NEW,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """E-Mails für mehrere Leads generieren"""
    leads = db.query(Lead).filter(
        Lead.status == status,
        Lead.generated_email_body.is_(None)
    ).limit(limit).all()
    
    generated = 0
    for lead in leads:
        try:
            result = await generate_personalized_email(lead)
            lead.generated_email_subject = result["subject"]
            lead.generated_email_body = result["body"]
            lead.status = LeadStatus.REVIEWED
            generated += 1
        except Exception as e:
            print(f"Fehler bei Lead {lead.id}: {e}")
    
    db.commit()
    return {"generated": generated, "total": len(leads)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
