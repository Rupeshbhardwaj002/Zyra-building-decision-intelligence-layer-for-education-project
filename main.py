import os
import logging
from datetime import datetime
from urllib.parse import urljoin, urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from bs4 import BeautifulSoup
from typing import List, Optional, Set, Dict, Any
from enum import Enum
from pydantic import BaseModel, EmailStr, ValidationError
from google import genai
from google.genai import types

#structured logging config..
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger("UniversityETLPipeline")

API_KEY = os.environ.get("GEMINI_API_KEY")

#pydantic schema configuration

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

#dynamic crawler logic

class UniversityCrawler:
    def __init__(self, start_url: str):
        if not start_url.startswith(('http://', 'https://')):
            start_url = 'https://' + start_url
        self.start_url = start_url
        self.base_domain = urlparse(start_url).netloc
        self.visited: Set[str] = set()
        self.target_keywords = ['admission', 'apply', 'tuition', 'cost', 'fee', 'financial-aid', 'attendance']
        
        # Robust Session Setup with Auto-Retry & Backoff Strategy
        self.session = requests.Session()
        retries = Retry(
            total=3,                # Total number of retries
            backoff_factor=1,       # Wait 1s, 2s, 4s between retries
            status_forcelist=[500, 502, 503, 504], # Status codes to retry
            raise_on_status=False
        )
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    def _is_internal(self, url: str) -> bool:
        netloc = urlparse(url).netloc
        return netloc == '' or self.base_domain in netloc

    def _score_relevance(self, url: str, text: str) -> int:
        url_lower, text_lower = url.lower(), text.lower()
        score = 0
        for kw in self.target_keywords:
            if kw in url_lower:
                score += 3 
            if kw in text_lower:
                score += 1 
        return score

    def discover_pages(self, max_depth: int = 2) -> List[Dict[str, Any]]:
        queue = [(self.start_url, 0)]
        self.visited.add(self.start_url)
        relevant_pages = []
        scrape_time = datetime.now().isoformat()

        logger.info(f"Starting BFS crawl for domain: {self.base_domain} (Max Depth: {max_depth})")

        while queue:
            current_url, depth = queue.pop(0)
            
            try:
                response = self.session.get(
                    current_url, 
                    timeout=10, 
                    headers={'User-Agent': 'Data-ETL-Bot/2.0'}
                )
                status_code = str(response.status_code)
                
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch {current_url} - Status Code: {status_code}")
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                title = soup.title.string.strip() if soup.title else ""
                
                relevance_score = self._score_relevance(current_url, title)
                
                if depth > 0 and relevance_score > 0:
                    for script in soup(["script", "style", "nav", "footer"]):
                        script.extract()
                    clean_text = soup.get_text(separator=' ', strip=True)
                    
                    relevant_pages.append({
                        'url': current_url,
                        'title': title,
                        'content': clean_text[:12000],
                        'score': relevance_score,
                        'status_code': status_code,
                        'scraped_at': scrape_time
                    })

                if depth < max_depth:
                    for a_tag in soup.find_all('a', href=True):
                        href = a_tag['href']
                        next_url = urljoin(current_url, href).split('#')[0] 
                        
                        if self._is_internal(next_url) and next_url not in self.visited:
                            link_text = a_tag.get_text(strip=True)
                            link_score = self._score_relevance(next_url, link_text)
                            
                            if depth == 0 or link_score > 0:
                                self.visited.add(next_url)
                                queue.append((next_url, depth + 1))
                                
            except requests.RequestException as e:
                logger.error(f"Network error crawling {current_url}: {e}")
                continue

        relevant_pages.sort(key=lambda x: x['score'], reverse=True)
        return relevant_pages[:5]


#llm extraction pipeline

def extract_structured_data(domain: str, pages_data: List[Dict[str, Any]]) -> UniversityData:
    if not API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")
        
    client = genai.Client(api_key=API_KEY)
    
    context = f"Domain: {domain}\n\n"
    for page in pages_data:
        context += f"--- URL: {page['url']} ---\n"
        context += f"Title: {page['title']}\n"
        context += f"Scraped At: {page['scraped_at']} | Status: {page['status_code']}\n"
        context += f"Content: {page['content']}\n\n"
        
    schema_definition = UniversityData.model_json_schema()
        
    prompt = f"""
    You are an AI data extraction system. Analyze the following website contents scraped from {domain}.
    Extract the required information and strictly output a JSON object matching this exact JSON schema:
    
    {schema_definition}
    
    Rules:
    1. For the `tuition_breakdown`, create individual items for each fee (e.g., In-State Tuition, Room & Board) and convert costs to integers.
    2. For `admission_deadlines`, map the deadline type strictly to the Enums ("Early Decision", "Regular Decision", "Transfer Admission"). Use `notes` for any context.
    3. Populate `page_metadata` using the URL, Title, Scraped At, and Status Code provided in the context headers above.
    4. Return null for fields you cannot confidently populate. Do not hallucinate data.
    
    Web Data Context:
    {context}
    """
    
    logger.info(f"Dispatching payload to Gemini 2.5 Flash for domain: {domain}")
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.0 
        ),
    )
    
    return UniversityData.model_validate_json(response.text)


#Data quality auditor and runner

def run_pipeline_for_domains(domains: List[str]):
    summary_report = {}

    for domain in domains:
        logger.info(f"=== Starting Execution for {domain} ===")
        start_time = datetime.now()
        
        try:
            crawler = UniversityCrawler(domain)
            top_pages = crawler.discover_pages(max_depth=2)
            
            if not top_pages:
                logger.warning(f"No relevant landing pages discovered for {domain}. Skipping extraction.")
                summary_report[domain] = {"status": "FAILED", "reason": "No pages discovered"}
                continue
                
            structured_data = extract_structured_data(domain, top_pages)
            
            # --- Data Quality Checks ---
            missing_fields = []
            if not structured_data.overview or not structured_data.overview.university_name:
                missing_fields.append("overview.university_name")
            if not structured_data.tuition_breakdown:
                missing_fields.append("tuition_breakdown")
                
            execution_time = (datetime.now() - start_time).total_seconds()
            
            summary_report[domain] = {
                "status": "SUCCESS",
                "execution_time_seconds": execution_time,
                "pages_scraped_count": len(top_pages),
                "records_extracted_tuition": len(structured_data.tuition_breakdown),
                "records_extracted_deadlines": len(structured_data.admission_deadlines),
                "data_quality_warnings": missing_fields if missing_fields else "None"
            }
            
            logger.info(f"Successfully processed {domain} in {execution_time:.2s}s")
            print(structured_data.model_dump_json(indent=2))
            
        except ValidationError as ve:
            logger.error(f"Pydantic Validation failed for {domain}: {ve}")
            summary_report[domain] = {"status": "FAILED", "reason": f"Pydantic Schema Failure: {ve}"}
        except Exception as e:
            logger.error(f"Unexpected operational pipeline failure for {domain}: {e}")
            summary_report[domain] = {"status": "FAILED", "reason": str(e)}

    # Print Global Execution Summary Table
    print("\n" + "="*60)
    print("GLOBAL BATCH EXECUTION SUMMARY")
    print("="*60)
    for dom, details in summary_report.items():
        print(f"Domain: {dom}")
        for k, v in details.items():
            print(f"  - {k}: {v}")
        print("-" * 40)

if __name__ == "__main__":
    # Task Bonus Support for processing multiple university domains in a single run
    target_universities = ["udc.edu", "bucknell.edu"]
    run_pipeline_for_domains(target_universities)