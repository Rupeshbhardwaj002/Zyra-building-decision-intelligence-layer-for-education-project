# Production-Grade University Data ETL Pipeline

An intelligent, end-to-end Extract, Transform, Load (ETL) pipeline that automatically discovers relevant university web pages and extracts structured tuition and admissions data using AI. This implementation goes beyond basic scraping by incorporating fault-tolerant networking, automated testing, batch processing, and data quality auditing.

## 🚀 Installation & Setup

1. **Clone the repository and navigate to the directory:**
   ```bash
   git clone <your-repo-url>
   cd university-etl-pipeline
   ```

2. **Set up a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   python -m pip install -r requirements.txt
   ```

4. **Set your Gemini API Key:**
   Get an API key from Google AI Studio and export it to your environment:
   ```bash
   # On Mac/Linux
   export GEMINI_API_KEY="your_api_key_here"

   # On Windows (PowerShell)
   $env:GEMINI_API_KEY="your_api_key_here"
   ```

## 💻 Running the Pipeline & Automated Tests

To execute the ETL batch pipeline:
The pipeline is pre-configured to process multiple domains (`udc.edu` and `bucknell.edu`) sequentially in a single run.
```bash
python main.py
```

To run the automated unit test suite:
```bash
python -m pytest test_pipeline.py
```

## 🧠 Overall Approach & Architecture

The pipeline uses a decoupled, two-phase architecture to optimize for network speed, cost efficiency, and strict type safety:

### Phase 1: Dynamic Discovery (Heuristic BFS Crawler)
Instead of relying on brittle, hardcoded URLs, the system utilizes a targeted Breadth-First Search (BFS) crawler capped at a strict `max_depth` of 2. It traverses the internal DOM tree, scoring links using a custom keyword heuristic array (e.g., tuition, admission, financial-aid, attendance). The search tree aggressively prunes irrelevant paths to minimize network overhead.

### Phase 2: AI-Driven Transformation (Gemini 2.5 Flash)
Discovered pages are stripped of heavy non-informational elements (`<script>`, `<style>`, `<nav>`, `<footer>`) before being passed to the LLM context. The LLM processes the unstructured HTML string and maps it directly onto our strict data types.

## 🛠️ Advanced Features Implemented (Bonus Tasks)

- **Automated Unit Testing Suite (`test_pipeline.py`):** Includes independent pytest coverage verifying domain resolution integrity, structural schema initialization defaults, and the mathematical accuracy of the heuristic link-scoring algorithm.
- **Fault-Tolerant Network Retries:** Replaced basic HTTP requests with a configured `requests.Session()` mount backed by an exponential backoff strategy (retrying up to 3 times on transient 5xx server errors).
- **Structured Execution Logging:** Replaced standard print streams with Python’s native logging module to track system health timestamps, tracking warnings for non-200 responses and errors for schema validation anomalies.
- **Data Quality Auditor:** Features a post-extraction validation layer that scans incoming validated JSON payloads for logical completeness, flagging missing high-value fields (e.g., empty overview maps or empty tuition arrays) inside a final execution report.
- **Multi-Domain Batch Processing:** Supports automated sequence running over an array of university inputs, compiling performance and data metrics into a unified terminal dashboard.

## ⚙️ Key Architectural Decisions

- **Prompt Schema Injection:** To bypass the current `google-genai` SDK bug handling complex nested Pydantic schemas using `$defs`, the pipeline dynamically serializes the Pydantic model into a raw JSON schema string and injects it directly into the structural system prompt. Validation is then enforced client-side via `model_validate_json()`.
- **Zero-Temperature Generation:** The LLM temperature is pinned strictly at `0.0` to force deterministic parsing behavior and prevent information hallucination.

## ⚠️ Assumptions & Limitations

- **Client-Side Rendering:** JavaScript execution is omitted in this build. Single Page Applications (SPAs) loading fee matriculations asynchronously post-onload through hydration fetch events are outside the indexing scope.
- **Strict PDF Avoidance:** PDF document streams are intentionally ignored. If a university hosts pricing matrix data exclusively inside a linked PDF file, the pipeline returns a clean `null` value rather than synthesizing metrics.
`;in main
```
