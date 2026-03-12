"""
Weblabs Lead Generator - AI Service

Handles AI-powered email generation with smart industry detection.
Uses a two-stage approach: first checks company name keywords for industry,
then falls back to Google Places category mapping.
"""

import os
import httpx
import random
import json
import re
from typing import Dict, Any, Optional

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")

SENDER_NAME = os.getenv("SENDER_NAME", "Max Mustermann")
WEBSITE_URL = os.getenv("WEBSITE_URL", "https://example.com")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "contact@example.com")

PROFILE = {
    "name": os.getenv("SENDER_NAME", "Max Mustermann"),
    "company": os.getenv("SENDER_COMPANY", "WebLabs"),
    "phone": os.getenv("SENDER_PHONE", "+49 123 456789"),
    "website": os.getenv("SENDER_WEBSITE", "example.com"),
}

def get_email_signature() -> str:
    """Builds a clean professional email signature from env config."""
    return f"""
Freundliche Grüße

{PROFILE['name']}
{PROFILE['company']} · {PROFILE['website']} · {PROFILE['phone']}"""

def get_smart_review_text(rating: float, count: int) -> str:
    """Returns a contextual review mention based on Google rating thresholds."""
    if not rating or not count:
        return ""
    
    if count >= 20 and rating >= 4.6:
        return "Ich habe gesehen, dass Sie bei Google sehr gut bewertet sind."
    
    elif count >= 5 and rating >= 4.0:
        return "Ich habe gesehen, dass Sie bei Google gut bewertet sind."
        
    return ""

def get_safe_industry_term(industry: str, company_name: str = "") -> str:
    """
    Resolves the industry term using a two-stage lookup:
    name keywords first, then Google Places categories, with a safe fallback.
    """
    # Name-based keyword matching takes priority
    name_lower = company_name.lower() if company_name else ""
    
    keyword_map = {
        "hausmeister": "Hausmeisterservices",
        "reinigung": "Reinigungsdiensten",
        "garten": "Gartenbau-Betrieben",
        "landschaft": "Landschaftsgärtnern",
        "maler": "Malerbetrieben",
        "lackierer": "Lackierern",
        "stuckateur": "Stuckateuren",
        "elektro": "Elektrikern",
        "sanitär": "Sanitär-Betrieben",
        "fliesen": "Fliesenlegern",
        "dach": "Dachdeckern",
        "gerüst": "Gerüstbauern",
        "umzug": "Umzugsunternehmen",
        "transport": "Transportunternehmen",
        "auto": "Kfz-Betrieben",
        "kfz": "Kfz-Betrieben",
        "werkstatt": "Werkstätten",
        "physio": "Physiotherapeuten",
        "praxis": "Praxen",
        "zahn": "Zahnärzten",
        "anwalt": "Anwälten",
        "steuer": "Steuerberatern",
        "friseur": "Friseuren",
        "hair": "Friseuren",
        "kosmetik": "Kosmetikstudios",
        "restaurant": "Restaurants",
        "hotel": "Hotels",
        "gaststätte": "Gaststätten"
    }
    
    for key, term in keyword_map.items():
        if key in name_lower:
            return term

    # Google Places category mapping as fallback
    if not industry:
        return "Betrieben"

    mappings = {
        "general_contractor": "Handwerksbetrieben",
        "plumber": "Installateuren",
        "electrician": "Elektrikern",
        "dentist": "Zahnärzten",
        "lawyer": "Anwälten",
        "real_estate_agency": "Immobilienmaklern",
        "restaurant": "Restaurants",
        "car_repair": "Werkstätten",
        "roofing_contractor": "Dachdeckern",
        "painter": "Malern",
        "store": "Geschäften",
        "health": "Gesundheitsdienstleistern",
        "finance": "Finanzdienstleistern",
        "insurance_agency": "Versicherungen",
        "consultant": "Beratern"
    }
    
    industry_lower = industry.lower()
    
    if industry_lower in mappings:
        return mappings[industry_lower]
        
    # Technical terms with underscores that aren't mapped get a safe fallback
    if "_" in industry_lower:
        return "Betrieben"

    # Filter out generic/unhelpful terms
    bad_terms = ["Einzelhandel", "Store", "Point Of Interest", "Establishment", "Ladengeschäft"]
    if any(term.lower() in industry_lower for term in bad_terms):
        return "Betrieben"
        
    return industry

def clean_company_name(name: str) -> str:
    """Strips legal suffixes and truncates overly long company names."""
    if not name:
        return ""

    legal_forms = ["gmbh", "ug", "kg", "ag", "e.k.", "& co.", "co.", "ltd", "limited"]
    clean_name = name
    
    for form in legal_forms:
        clean_name = re.sub(f",? {form}\.?", "", clean_name, flags=re.IGNORECASE)
    
    clean_name = clean_name.split(" - ")[0].split(" | ")[0]
    
    # Strip trailing punctuation
    while True:
        clean_name = clean_name.strip()
        original_len = len(clean_name)
        if clean_name.endswith("..."):
            clean_name = clean_name[:-3]
        elif clean_name.endswith(("&", ",", "-", "+", ".", ":")):
            clean_name = clean_name[:-1]
        if len(clean_name) == original_len:
            break

    if len(clean_name) > 35 and " " in clean_name:
        words = clean_name.split()
        if len(words) > 3:
            clean_name = " ".join(words[:3])
            
    return clean_name.strip()

async def generate_personalized_email(lead) -> Dict[str, str]:
    """Generates a personalized outreach email for the given lead using AI."""
    
    # Build context from lead data
    city = lead.city or "Ihrer Region"
    company = lead.company_name
    short_company = clean_company_name(company)
    
    industry_raw = lead.industry or ""
    industry_safe = get_safe_industry_term(industry_raw, company)
    
    if industry_safe == "Ihrem Betrieb" or industry_safe == "Betrieben":
        context_start = f"ich bin bei der Suche nach Betrieben in {city} auf Ihr Google-Profil gestoßen."
    else:
        context_start = f"ich habe in {city} nach Anbietern für {industry_safe} gesucht und bin auf Ihr Profil gestoßen."

    review_text = get_smart_review_text(lead.google_rating, lead.google_reviews_count)
    if review_text:
        context_start += f" {review_text}"

    # Randomly select one of three email variants for natural diversity
    variant = random.choice(["A", "B", "C"])
    system_prompt = """
Du bist Can Cadirci (WebLabs). Schreibe eine kurze Erstkontakt-Mail auf Deutsch.
REGELN:
1. Vermeide, Sätze ständig mit "Ich" zu beginnen.
2. Lege den Fokus auf den Empfänger ("Sie", "Ihr Betrieb").
3. Erwähne DEZENT: "Als Webentwickler aus der Region..." (oder ähnlich).
4. VERBOTEN: Werbewörter wie "stark", "wirklich", "pragmatisch", "potenzielle Kunden".
5. Betreff: NUTZE GENAU DAS VORGEGEBENE FORMAT.
"""

    if variant == "A":
        user_prompt = f"""
Variante A (Beobachtung):
1. Betreff: "Kurze Frage zu {short_company} ({city})"
2. Anrede
3. Kontext: "{context_start} Dabei ist mir aufgefallen, dass Sie bereits viele positive Rückmeldungen haben."
4. Identity & Value: "Als Webentwickler aus der Region helfe ich lokalen Betrieben dabei, diese Qualität auch auf der eigenen Webseite widerzuspiegeln, damit Interessenten schneller anfragen."
5. CTA: "Wenn Sie möchten, erstelle ich Ihnen drei kurze, konkrete Verbesserungsvorschläge. Das ist für Sie kostenfrei. Geben Sie mir einfach kurz Bescheid, ob das für Sie interessant ist."

Antworte als JSON: {{ "subject": "...", "body": "..." }}
"""
    elif variant == "B":
        user_prompt = f"""
Variante B (Strukturiert):
1. Betreff: "{short_company} in {city} – kurze Rückfrage"
2. Anrede
3. Kontext: "{context_start}"
4. Identity & Value: "Mir ist wichtig, dass lokale Betriebe online genau so professionell wirken wie vor Ort. Als Entwickler aus Stuttgart unterstütze ich dabei, den Web-Auftritt gezielt zu verbessern."
5. CTA: "Darf ich Ihnen unverbindlich eine kurze Übersicht senden, was man bei {short_company} konkret optimieren könnte? Ein kurzes 'Ja' reicht."

Antworte als JSON: {{ "subject": "...", "body": "..." }}
"""
    else:
        user_prompt = f"""
Variante C (Potenzial):
1. Betreff: "Kurze Frage an {short_company} ({city})"
2. Anrede
3. Kontext: "{context_start}"
4. Identity & Value: "Oft sehe ich, dass man schon mit kleinen Anpassungen deutlich besser gefunden wird. Als Webentwickler aus der Nachbarschaft würde ich Sie dabei gerne unterstützen."
5. CTA: "Haben Sie grundsätzlich Interesse an drei konkreten Ideen für Ihre Webseite? Dann schicke ich Ihnen diese gerne unverbindlich zu."

Antworte als JSON: {{ "subject": "...", "body": "..." }}
"""

    # Send to AI provider (OpenAI preferred, Ollama as local fallback)
    try:
        if OPENAI_API_KEY and OPENAI_API_KEY.startswith("sk-"):
            result = await _call_openai(system_prompt, user_prompt)
        else:
            result = await _call_ollama(system_prompt, user_prompt)
            
        if not result.get("body") or len(result["body"]) < 20:
            raise ValueError("AI Text zu kurz")
            
    except Exception as e:
        print(f"❌ AI Fallback: {e}")
        result = _fallback_template(short_company, city, context_start)

    # Post-process: strip duplicate greetings and append signature
    body_clean = result["body"].strip()
    for greeting in ["Mit freundlichen Grüßen", "Beste Grüße", "Freundliche Grüße", "Viele Grüße"]:
        body_clean = body_clean.replace(greeting, "")
        
    result["body"] = f"{body_clean.strip()}\n\n{get_email_signature()}"
    
    # Fallback subject if AI returned empty
    if not result.get("subject"):
        result["subject"] = f"Kurze Frage zu {short_company} ({city})"
        
    return result

async def _call_openai(system: str, user: str) -> Dict[str, str]:
    import openai
    client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.6,
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

async def _call_ollama(system: str, user: str) -> Dict[str, str]:
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": "llama3.1:8b",
                "prompt": f"{system}\n\nAUFGABE:\n{user}\n\nANTWORTE ALS JSON:",
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.6}
            }
        )
        return json.loads(response.json().get("response", "{}"))

def _fallback_template(short_company, city, context) -> Dict[str, str]:
    """Static template used when AI generation fails."""
    return {
        "subject": f"Kurze Frage zu {short_company} ({city})",
        "body": f"""Sehr geehrte Damen und Herren,

{context}

Als Webentwickler aus der Region unterstütze ich lokale Betriebe dabei, ihre Online-Präsenz so zu optimieren, dass Interessenten schneller das finden, was sie suchen.

Darf ich Ihnen dazu unverbindlich drei konkrete Verbesserungsvorschläge für Ihre Seite zusenden?

Geben Sie mir einfach kurz Bescheid, ob das für Sie interessant ist."""
    }

async def analyze_website(url: str) -> Dict[str, Any]:
    return {"url": url, "score": 50, "issues": [], "recommendation": "Check"}
