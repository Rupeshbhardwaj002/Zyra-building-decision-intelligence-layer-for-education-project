import pytest
from main import UniversityCrawler, UniversityData

def test_crawler_domain_resolution():
    """Test that the crawler properly handles and resolves short domains."""
    crawler = UniversityCrawler("bucknell.edu")
    assert crawler.base_domain == "bucknell.edu"
    assert crawler.start_url == "https://bucknell.edu"

def test_heuristic_scoring_logic():
    """Test that our page prioritization assigns higher scores to matching terms."""
    crawler = UniversityCrawler("udc.edu")
    
    high_score = crawler._score_relevance("https://www.udc.edu/admissions/tuition-fees", "Tuition Cost")
    low_score = crawler._score_relevance("https://www.udc.edu/about/history", "History and Mission")
    
    assert high_score > low_score
    assert high_score >= 4 # URL match (3) + title text match (1)

def test_pydantic_schema_empty_initialization():
    """Verify that our default schemas compile with appropriate fallbacks."""
    data = UniversityData()
    assert data.overview is None
    assert isinstance(data.tuition_breakdown, list)
    assert len(data.tuition_breakdown) == 0