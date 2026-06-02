import os
from datetime import datetime
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from typing import List, Optional, Set, Dict, Any
from enum import Enum
from pydantic import BaseModel, EmailStr

#pydantic def ..

class Location(BaseModel):
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None

class Contact(BaseModel):
    phone: Optional[str] = None
    email: Optional[EmailStr] = None

class Overview(BaseModel):
    university_name: Optional[str] = None
    location: Optional[Location] = None
    contact: Optional[Contact] = None

class TuitionItem(BaseModel):
    fee_type: Optional[str] = None
    cost: Optional[int] = None
    currency: Optional[str] = None

class DeadlineType(str, Enum):
    EARLY_DECISION = "Early Decision"
    REGULAR_DECISION = "Regular Decision"
    TRANSFER_ADMISSION = "Transfer Admission"

class AdmissionDeadline(BaseModel):
    deadline_type: Optional[DeadlineType] = None
    deadline_date: Optional[str] = None
    notes: Optional[str] = None

class PageMetadata(BaseModel):
    url: Optional[str] = None
    page_title: Optional[str] = None
    scraped_at: Optional[str] = None
    status_code: Optional[str] = None

class UniversityData(BaseModel):
    overview: Optional[Overview] = None
    tuition_breakdown: List[TuitionItem] = []
    admission_deadlines: List[AdmissionDeadline] = []
    page_metadata: List[PageMetadata] = []


#crawler dynamic
class UniversityCrawler:
    def __init__(self, start_url: str):
        # Ensure the URL is properly formatted
        if not start_url.startswith(('http://', 'https://')):
            start_url = 'https://' + start_url
        self.start_url = start_url
        self.base_domain = urlparse(start_url).netloc

    def fetch_and_clean(self, url: str) -> str:
        """Fetches a single page and cleans the HTML of scripts/styles."""
        try:
            # We use a custom User-Agent so we don't get blocked by basic bot-protection
            response = requests.get(url, timeout=10, headers={'User-Agent': 'Data-ETL-Bot'})
            
            if response.status_code != 200:
                return f"Error: Status code {response.status_code}"
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # CRITICAL: Strip out scripts, styles, and navigation to save LLM tokens later
            for script in soup(["script", "style", "nav", "footer"]):
                script.extract()
            
            # Get clean text
            clean_text = soup.get_text(separator=' ', strip=True)
            return clean_text
            
        except requests.RequestException as e:
            return f"Request failed: {e}"

if __name__ == "__main__":
    print("[*] Phase 3: Testing Base Crawler Initialization...")
    
    # test of base crwaler on bucknell page
    crawler = UniversityCrawler("bucknell.edu")
    print(f"[*] Base Domain identified as: {crawler.base_domain}")
    print(f"[*] Fetching content from: {crawler.start_url} ...")
    
    text_content = crawler.fetch_and_clean(crawler.start_url)
    
    print("\n[*] Success! Here is a snippet of the cleaned text (First 300 chars):")
    print("-" * 50)
    print(text_content[:300] + "...\n")