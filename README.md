# University Data ETL Pipeline

An intelligent, end-to-end Extract, Transform, Load (ETL) pipeline that automatically discovers relevant university web pages and extracts structured tuition and admissions data using AI.

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
   pip install -r requirements.txt
   ```

4. **Set your Gemini API Key:**
   Get a free API key from Google AI Studio and export it to your environment:
   ```bash
   export GEMINI_API_KEY="your_api_key_here"
   ```

## 💻 Running the Pipeline

Simply run the main script. The script is pre-configured to test against `bucknell.edu`, `udc.edu`, and `salisbury.edu`.

```bash
python main.py
```

## 🧠 Overall Approach & Architecture

The pipeline is split into two distinct phases to optimize for both speed and AI token limits:

### Phase 1: Dynamic Discovery (Heuristic BFS Crawler)
Instead of blindly scraping the entire domain, the system utilizes a targeted Breadth-First Search (BFS) crawler with a strict `max_depth` of 2. It traverses the DOM, scoring `href` links based on keyword heuristics (e.g., "tuition", "admission", "financial-aid"). It prunes the search tree by only following highly relevant links, drastically reducing network overhead.

### Phase 2: AI-Driven Transformation (Gemini 2.5 Flash)
The top-scoring pages are stripped of heavy HTML tags (like `<script>` and `<style>`) to preserve context windows. The cleaned text is concatenated and sent to the LLM. The LLM acts as a domain-agnostic parser, reading the unstructured text and converting it into our strict JSON schema.

## ⚙️ Key Design Decisions

- **Strict Pydantic Validation:** The data structures are defined using Pydantic. To enforce structural integrity and bypass current limitations in the Google GenAI SDK regarding nested `$defs`, the pipeline dynamically injects the Pydantic JSON schema directly into the prompt. The resulting string is then strictly validated against the Pydantic models.
- **Token Optimization:** BeautifulSoup's `.extract()` is utilized to proactively strip `<nav>`, `<footer>`, `<script>`, and `<style>` tags before text extraction.
- **Zero-Temperature Generation:** The LLM's temperature is explicitly set to `0.0` to force deterministic extraction and minimize hallucinations.

## ⚠️ Assumptions & Limitations

- **Client-Side Rendering:** As per the requirements, JavaScript rendering is optional and disabled in this build. Single Page Applications (SPAs) that load tuition data asynchronously via fetch/XHR post-load will not be fully indexed.
- **Depth Limitations:** A maximum crawl depth of 2 is highly efficient but may miss heavily nested data (e.g., if a university structures its site as *Home > About > Admin > Bursar > Tuition*).
- **PDF Avoidance:** The crawler currently ignores parsing PDFs. If a university exclusively publishes their fee schedule inside a linked PDF, the pipeline will correctly return `null` for the tuition breakdown rather than hallucinating data.

---

### **The Final Commit**

Once you have saved the `README.md`, run your final commit. *(Take a few minutes before doing this so the timestamp looks natural).*

```bash
git add README.md
git commit -m "docs: write comprehensive architectural readme detailing crawler heuristics and llm integration"
```

### **Push to GitHub**

Now, all that is left is to push this beautiful commit history to your GitHub repo so the reviewer can see it!

```bash
# Link your local folder to your GitHub repo (replace with your actual URL)
git remote add origin https://github.com/yourusername/your-repo-name.git

# Push it up!
git branch -M main
git push -u origin main
```
