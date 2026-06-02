import os
from datetime import datetime
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from typing import List, Optional, Set, Dict, Any
from enum import Enum
from pydantic import BaseModel, EmailStr

# ==========================================
# 1. PYDANTIC SCHEMA DEFINITION
# ==========================================

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

# ... (Keep your Pydantic schemas and imports exactly the same at the top) ...

# ==========================================
# 2. DYNAMIC CRAWLER (Max Depth 2 BFS)
# ==========================================

class UniversityCrawler:
    def __init__(self, start_url: str):
        if not start_url.startswith(('http://', 'https://')):
            start_url = 'https://' + start_url
        self.start_url = start_url
        self.base_domain = urlparse(start_url).netloc
        self.visited: Set[str] = set()
        
        # Heuristics designed to hit the target URLs
        self.target_keywords = ['admission', 'apply', 'tuition', 'cost', 'fee', 'financial-aid', 'attendance']
        
    def _is_internal(self, url: str) -> bool:
        netloc = urlparse(url).netloc
        return netloc == '' or self.base_domain in netloc

    def _score_relevance(self, url: str, text: str) -> int:
        """Scores a URL based on the presence of keywords in the URL or anchor text."""
        url_lower, text_lower = url.lower(), text.lower()
        score = 0
        for kw in self.target_keywords:
            if kw in url_lower:
                score += 3  # High weight for keywords in URL path
            if kw in text_lower:
                score += 1  # Lower weight for text-based matches
        return score

    def discover_pages(self, max_depth: int = 2) -> List[Dict[str, Any]]:
        queue = [(self.start_url, 0)]
        self.visited.add(self.start_url)
        relevant_pages = []
        scrape_time = datetime.now().isoformat()

        print(f"[*] Commencing Breadth-First Search (Max Depth: {max_depth}) from {self.start_url}...")

        while queue:
            current_url, depth = queue.pop(0)
            
            try:
                response = requests.get(current_url, timeout=10, headers={'User-Agent': 'Data-ETL-Bot'})
                status_code = str(response.status_code)
                
                if response.status_code != 200:
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                title = soup.title.string.strip() if soup.title else ""
                
                relevance_score = self._score_relevance(current_url, title)
                
                # If it's a relevant page, extract and clean the text
                if depth > 0 and relevance_score > 0:
                    for script in soup(["script", "style", "nav", "footer"]):
                        script.extract()
                    clean_text = soup.get_text(separator=' ', strip=True)
                    
                    relevant_pages.append({
                        'url': current_url,
                        'title': title,
                        'content': clean_text[:12000], # Chunking to save LLM context
                        'score': relevance_score,
                        'status_code': status_code,
                        'scraped_at': scrape_time
                    })

                # Extract links for the next depth
                if depth < max_depth:
                    for a_tag in soup.find_all('a', href=True):
                        href = a_tag['href']
                        next_url = urljoin(current_url, href).split('#')[0] # Remove fragment identifiers
                        
                        if self._is_internal(next_url) and next_url not in self.visited:
                            link_text = a_tag.get_text(strip=True)
                            link_score = self._score_relevance(next_url, link_text)
                            
                            # Prune tree: only explore relevant links to save time and memory
                            if depth == 0 or link_score > 0:
                                self.visited.add(next_url)
                                queue.append((next_url, depth + 1))
                                
            except requests.RequestException:
                continue

        # Sort by relevance and return the top 5
        relevant_pages.sort(key=lambda x: x['score'], reverse=True)
        return relevant_pages[:5]

if __name__ == "__main__":
    print("[*] Phase 4: Testing Dynamic Discovery Algorithm...\n")
    crawler = UniversityCrawler("bucknell.edu")
    
    # Run the discovery
    top_pages = crawler.discover_pages(max_depth=2)
    
    print("\n[*] Discovery Complete. Top Pages Found:")
    print("-" * 50)
    for idx, page in enumerate(top_pages):
        print(f"{idx + 1}. Score: {page['score']} | URL: {page['url']}")
        print(f"   Title: {page['title']}\n")