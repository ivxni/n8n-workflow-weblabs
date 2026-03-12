"""
Weblabs Lead Generator - Scraper Service
Findet lokale Unternehmen über Google Maps / Places API
"""

import os
import re
import httpx
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

# API Keys
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

# Koordinaten für Stuttgart
STUTTGART_LAT = 48.7758
STUTTGART_LNG = 9.1829


async def search_businesses(
    city: str = "Stuttgart",
    radius_km: int = 60,
    industries: List[str] = None,
    max_results: int = 50
) -> List[Dict[str, Any]]:
    """
    Sucht nach lokalen Unternehmen.
    Versucht verschiedene Methoden in folgender Reihenfolge:
    1. Google Places API (wenn Key vorhanden)
    2. SerpAPI (Google Maps Scraping, wenn Key vorhanden)
    3. Demo-Daten (für Entwicklung)
    """
    
    if industries is None:
        industries = [
            "Restaurant",
            "Friseur",
            "Handwerker",
            "Autowerkstatt",
            "Bäckerei",
            "Metzgerei",
            "Blumenladen"
        ]
    
    results = []
    
    # Methode 1: Google Places API
    if GOOGLE_PLACES_API_KEY:
        print("🔍 Suche mit Google Places API...")
        for industry in industries[:5]:  # Limitiert um API Kosten zu sparen
            try:
                found = await _search_google_places(
                    query=f"{industry} in {city}",
                    radius_m=radius_km * 1000
                )
                results.extend(found)
                if len(results) >= max_results:
                    break
            except Exception as e:
                print(f"Google Places Fehler für {industry}: {e}")
    
    # Methode 2: SerpAPI
    elif SERPAPI_KEY:
        print("🔍 Suche mit SerpAPI...")
        for industry in industries[:5]:
            try:
                found = await _search_serpapi(
                    query=f"{industry} {city}",
                )
                results.extend(found)
                if len(results) >= max_results:
                    break
            except Exception as e:
                print(f"SerpAPI Fehler für {industry}: {e}")
    
    # Methode 3: Demo-Daten für Entwicklung
    else:
        print("⚠️ Keine API Keys konfiguriert - verwende Demo-Daten")
        results = _get_demo_data(city, industries)
    
    # Deduplizieren nach Name
    seen = set()
    unique_results = []
    for r in results:
        name = r.get("name", "").lower()
        if name and name not in seen:
            seen.add(name)
            unique_results.append(r)
    
    return unique_results[:max_results]


async def _search_google_places(
    query: str,
    radius_m: int = 25000
) -> List[Dict[str, Any]]:
    """Google Places API Text Search"""
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://maps.googleapis.com/maps/api/place/textsearch/json",
            params={
                "query": query,
                "location": f"{STUTTGART_LAT},{STUTTGART_LNG}",
                "radius": radius_m,
                "language": "de",
                "key": GOOGLE_PLACES_API_KEY
            }
        )
        response.raise_for_status()
        data = response.json()
    
    results = []
    for place in data.get("results", []):
        # Details abrufen für Kontaktdaten
        details = await _get_place_details(place["place_id"])
        
        results.append({
            "name": place.get("name"),
            "address": place.get("formatted_address"),
            "city": _extract_city(place.get("formatted_address", "")),
            "postal_code": _extract_postal_code(place.get("formatted_address", "")),
            "rating": place.get("rating"),
            "reviews_count": place.get("user_ratings_total"),
            "place_id": place.get("place_id"),
            "industry": _categorize_industry(place.get("types", [])),
            "phone": details.get("phone"),
            "website": details.get("website"),
            "email": details.get("email")
        })
    
    return results


async def _get_place_details(place_id: str) -> Dict[str, Any]:
    """Holt Details wie Telefon, Website von Google Places"""
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://maps.googleapis.com/maps/api/place/details/json",
            params={
                "place_id": place_id,
                "fields": "formatted_phone_number,website",
                "language": "de",
                "key": GOOGLE_PLACES_API_KEY
            }
        )
        response.raise_for_status()
        data = response.json()
    
    result = data.get("result", {})
    
    # E-Mail von Website extrahieren (wenn vorhanden)
    email = None
    website = result.get("website")
    if website:
        email = await _extract_email_from_website(website)
    
    return {
        "phone": result.get("formatted_phone_number"),
        "website": website,
        "email": email
    }


async def _search_serpapi(query: str) -> List[Dict[str, Any]]:
    """SerpAPI Google Maps Suche"""
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://serpapi.com/search",
            params={
                "engine": "google_maps",
                "q": query,
                "ll": f"@{STUTTGART_LAT},{STUTTGART_LNG},14z",
                "type": "search",
                "api_key": SERPAPI_KEY
            }
        )
        response.raise_for_status()
        data = response.json()
    
    results = []
    for place in data.get("local_results", []):
        results.append({
            "name": place.get("title"),
            "address": place.get("address"),
            "city": _extract_city(place.get("address", "")),
            "rating": place.get("rating"),
            "reviews_count": place.get("reviews"),
            "phone": place.get("phone"),
            "website": place.get("website"),
            "industry": place.get("type"),
            "place_id": place.get("place_id")
        })
    
    return results


async def _extract_email_from_website(url: str) -> Optional[str]:
    """Versucht E-Mail von Website zu extrahieren"""
    
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(url)
            html = response.text
        
        # E-Mail Regex
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, html)
        
        # Filter ungültige
        valid_emails = [
            e for e in emails 
            if not any(x in e.lower() for x in ['example', 'test', 'your', '.png', '.jpg', 'wixpress'])
        ]
        
        # Präferiere info@, kontakt@, contact@
        preferred = ['info@', 'kontakt@', 'contact@', 'mail@', 'office@']
        for prefix in preferred:
            for email in valid_emails:
                if email.lower().startswith(prefix):
                    return email
        
        return valid_emails[0] if valid_emails else None
        
    except Exception as e:
        print(f"Email Extraktion fehlgeschlagen für {url}: {e}")
        return None


def _extract_city(address: str) -> str:
    """Extrahiert Stadt aus Adresse"""
    # Deutsches Format: Straße Nr, PLZ Stadt
    match = re.search(r'\d{5}\s+([^,]+)', address)
    if match:
        return match.group(1).strip()
    return "Stuttgart"


def _extract_postal_code(address: str) -> str:
    """Extrahiert PLZ aus Adresse"""
    match = re.search(r'(\d{5})', address)
    return match.group(1) if match else ""


def _categorize_industry(types: List[str]) -> str:
    """Kategorisiert Google Places Types zu deutschen Branchen"""
    mapping = {
        "restaurant": "Restaurant",
        "food": "Gastronomie",
        "cafe": "Café",
        "bakery": "Bäckerei",
        "hair_care": "Friseur",
        "beauty_salon": "Kosmetik",
        "car_repair": "Autowerkstatt",
        "car_dealer": "Autohaus",
        "dentist": "Zahnarzt",
        "doctor": "Arztpraxis",
        "lawyer": "Rechtsanwalt",
        "accounting": "Steuerberater",
        "real_estate_agency": "Immobilienmakler",
        "store": "Einzelhandel",
        "florist": "Blumenladen",
        "gym": "Fitnessstudio",
        "electrician": "Elektriker",
        "plumber": "Installateur",
        "painter": "Maler",
        "roofing_contractor": "Dachdecker"
    }
    
    for t in types:
        if t in mapping:
            return mapping[t]
    
    return types[0] if types else "Sonstiges"


def _get_demo_data(city: str, industries: List[str]) -> List[Dict[str, Any]]:
    """Demo-Daten für Entwicklung ohne API Keys"""
    
    return [
        {
            "name": "Pizzeria Da Luigi",
            "industry": "Restaurant",
            "address": "Königstraße 45",
            "city": city,
            "postal_code": "70173",
            "phone": "0711 123456",
            "email": "info@pizzeria-luigi.de",
            "website": None,
            "rating": 4.3,
            "reviews_count": 127
        },
        {
            "name": "Friseursalon Haargenau",
            "industry": "Friseur",
            "address": "Marienstraße 12",
            "city": city,
            "postal_code": "70178",
            "phone": "0711 234567",
            "email": None,
            "website": "http://haargenau-stuttgart.de",
            "rating": 4.7,
            "reviews_count": 89
        },
        {
            "name": "KFZ Meister Müller",
            "industry": "Autowerkstatt",
            "address": "Industriestraße 78",
            "city": city,
            "postal_code": "70565",
            "phone": "0711 345678",
            "email": "werkstatt@mueller-kfz.de",
            "website": None,
            "rating": 4.5,
            "reviews_count": 203
        },
        {
            "name": "Bäckerei Sonnenschein",
            "industry": "Bäckerei",
            "address": "Rotebühlplatz 3",
            "city": city,
            "postal_code": "70178",
            "phone": "0711 456789",
            "email": "kontakt@baeckerei-sonnenschein.de",
            "website": "https://baeckerei-sonnenschein.de",
            "rating": 4.8,
            "reviews_count": 312
        },
        {
            "name": "Blumen Paradies",
            "industry": "Blumenladen",
            "address": "Charlottenplatz 17",
            "city": city,
            "postal_code": "70173",
            "phone": "0711 567890",
            "email": None,
            "website": None,
            "rating": 4.6,
            "reviews_count": 56
        },
        {
            "name": "Dr. Schmidt Zahnarztpraxis",
            "industry": "Zahnarzt",
            "address": "Theodor-Heuss-Straße 14",
            "city": city,
            "postal_code": "70174",
            "phone": "0711 678901",
            "email": "praxis@dr-schmidt-zahnarzt.de",
            "website": "http://www.dr-schmidt-zahnarzt.de",
            "rating": 4.4,
            "reviews_count": 178
        },
        {
            "name": "Elektro Blitz GmbH",
            "industry": "Elektriker",
            "address": "Wagenburgstraße 89",
            "city": city,
            "postal_code": "70184",
            "phone": "0711 789012",
            "email": "info@elektro-blitz.de",
            "website": None,
            "rating": 4.2,
            "reviews_count": 45
        },
        {
            "name": "Trattoria Bella Italia",
            "industry": "Restaurant",
            "address": "Eberhardstraße 33",
            "city": city,
            "postal_code": "70173",
            "phone": "0711 890123",
            "email": None,
            "website": "http://bella-italia-stuttgart.de",
            "rating": 4.5,
            "reviews_count": 234
        }
    ]
