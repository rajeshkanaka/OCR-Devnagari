<div align="center">

<!-- Animated Header Banner -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=200&section=header&text=OCR-Devnagari&fontSize=50&fontColor=fff&animation=fadeIn&fontAlignY=28&desc=Sacred%20Manuscripts%20→%20Digital%20Wisdom%20⚡%20in%20Seconds&descAlignY=50&descSize=18" width="100%"/>

<!-- Divine Invocation -->
<h4>॥ श्री गणेशाय नमः ॥</h4>

<!-- Animated Typing Effect -->
<a href="https://github.com/rajeshkanaka/OCR-Devnagari">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=22&duration=3000&pause=1000&color=FF6B35&center=true&vCenter=true&multiline=true&repeat=false&width=620&height=80&lines=Gemini+2.0+Flash+%E2%80%A2+Streamlit+UI+%E2%80%A2+Batch+API;Hindi+%E2%80%A2+Sanskrit+%E2%80%A2+Devanagari+%E2%80%A2+FTS5+Search" alt="Typing SVG" />
</a>

<br>

<!-- Hero Badges -->
<p>
  <img src="https://img.shields.io/badge/5_pages-12_sec_•_$0.002-FF6B35?style=for-the-badge&labelColor=1a1a2e" alt="Performance"/>
  &nbsp;
  <img src="https://img.shields.io/badge/50K_pages-~$7_projected-00C853?style=for-the-badge&labelColor=1a1a2e" alt="Cost"/>
  &nbsp;
  <img src="https://img.shields.io/badge/0_failures-crash_safe-9C27B0?style=for-the-badge&labelColor=1a1a2e" alt="Reliability"/>
</p>

<!-- Action Buttons -->
<p>
  <a href="#-quick-start">
    <img src="https://img.shields.io/badge/⚡_GET_STARTED-2_Minutes-00C853?style=for-the-badge&logo=rocket&logoColor=white" alt="Quick Start"/>
  </a>
  &nbsp;&nbsp;
  <a href="#-streamlit-ui">
    <img src="https://img.shields.io/badge/🖥️_LAUNCH_UI-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Launch UI"/>
  </a>
  &nbsp;&nbsp;
  <a href="https://github.com/rajeshkanaka/OCR-Devnagari/stargazers">
    <img src="https://img.shields.io/badge/⭐_STAR_THIS-Repo-FFD700?style=for-the-badge&logo=github&logoColor=black" alt="Star"/>
  </a>
</p>

<br>

<!-- Tech Badge Row -->
<p>
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/Gemini_2.0-Flash-4285F4?style=flat-square&logo=google&logoColor=white"/>
  <img src="https://img.shields.io/badge/UV-Package_Manager-DE5FE9?style=flat-square&logo=astral&logoColor=white"/>
  <img src="https://img.shields.io/badge/Streamlit-UI-FF4B4B?style=flat-square&logo=streamlit&logoColor=white"/>
  <img src="https://img.shields.io/badge/SQLite-FTS5_Search-003B57?style=flat-square&logo=sqlite&logoColor=white"/>
  <img src="https://img.shields.io/badge/Batch-GCS_API-F9A825?style=flat-square&logo=googlecloud&logoColor=white"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square"/>
</p>

<!-- GitHub Stats -->
<p>
  <img src="https://img.shields.io/github/stars/rajeshkanaka/OCR-Devnagari?style=social"/>
  <img src="https://img.shields.io/github/forks/rajeshkanaka/OCR-Devnagari?style=social"/>
  <img src="https://img.shields.io/github/watchers/rajeshkanaka/OCR-Devnagari?style=social"/>
</p>

</div>

---

## 🔥 What's New

<table>
<tr>
<td>🚀 <b>Gemini 2.0 Flash</b></td>
<td>Lightning-fast AI OCR with <code>thinking_level: low</code> — 5 pages in 12 seconds</td>
</tr>
<tr>
<td>🖥️ <b>Streamlit UI</b></td>
<td>Beautiful 4-page web app: Process → Library → Search → Settings</td>
</tr>
<tr>
<td>📦 <b>Batch API</b></td>
<td>Upload to GCS, process thousands of pages with <code>--batch --gcs-bucket</code></td>
</tr>
<tr>
<td>🔍 <b>FTS5 Search</b></td>
<td>Full-text search across all your processed manuscripts with SQLite FTS5</td>
</tr>
<tr>
<td>📐 <b>UV First</b></td>
<td>Zero-config install — <code>uv sync</code> and you're running</td>
</tr>
</table>

---

## 📊 Real Test Results

> **Book:** *Phalit Jyotish Vigyan* &nbsp;|&nbsp; **Engine:** `gemini-2.0-flash` &nbsp;|&nbsp; **Pages:** 5

| Metric | Result |
|:-------|-------:|
| ⏱️ Time | **12 seconds** |
| 💰 Cost | **$0.0022** |
| ❌ Failures | **0** |
| 📄 Output | Clean Unicode Markdown |

> **Projected at scale:** 50,000 pages ≈ **~$7** total cost

---

## ⚡ Quick Start

### 📦 Install

```bash
git clone https://github.com/rajeshkanaka/OCR-Devnagari.git
cd OCR-Devnagari

# Install with UV (recommended)
uv sync
uv pip install easyocr    # optional: for hybrid/easyocr engine
```

### 🔑 Configure API

```bash
# Option A: API Key (quickest)
export GEMINI_API_KEY="your-key"

# Option B: Vertex AI (production)
export GOOGLE_CLOUD_PROJECT="your-project"
export GOOGLE_CLOUD_LOCATION="global"
export GOOGLE_GENAI_USE_VERTEXAI=1
gcloud auth application-default login
```

### 🚀 Run — CLI

```bash
# Gemini OCR — fast, accurate, cheap
uv run python -m ocr_hindi ocr book.pdf -e gemini --pages all

# Hybrid mode — EasyOCR local + Gemini for hard pages
uv run python -m ocr_hindi ocr book.pdf -e hybrid --pages '1-50'

# 100% FREE local OCR
uv run python -m ocr_hindi ocr book.pdf -e easyocr --pages all
```

### 🖥️ Run — Streamlit UI

```bash
uv run streamlit run src/ocr_hindi/app.py
```

Opens at `http://localhost:8501` with 4 pages: **Process** · **Library** · **Search** · **Settings**

---

## 📖 All CLI Commands

<details open>
<summary><b>🔀 OCR Processing</b></summary>

```bash
# Full book — all pages with Gemini
uv run python -m ocr_hindi ocr manuscript.pdf -e gemini --pages all

# Hybrid — smart routing, 90% cost savings
uv run python -m ocr_hindi ocr manuscript.pdf -e hybrid --pages '1-50'

# Page ranges
uv run python -m ocr_hindi ocr manuscript.pdf -e gemini --pages '1-100,200-250'

# More workers for speed
uv run python -m ocr_hindi ocr manuscript.pdf -e gemini --pages all --workers 10

# Resume interrupted processing
uv run python -m ocr_hindi ocr manuscript.pdf --resume

# Dry run — preview what will be processed
uv run python -m ocr_hindi ocr manuscript.pdf --dry-run
```

</details>

<details>
<summary><b>🔍 Search & Index</b></summary>

```bash
# Search across all processed manuscripts
uv run python -m ocr_hindi search 'गणेश' --folder ./output

# Reindex a folder for search
uv run python -m ocr_hindi reindex ./output
```

</details>

<details>
<summary><b>📦 Batch Processing (GCS)</b></summary>

```bash
# Batch process via Google Cloud Storage
uv run python -m ocr_hindi ocr book.pdf -e gemini --batch --gcs-bucket my-bucket
```

</details>

<details>
<summary><b>🛠️ Utility Commands</b></summary>

```bash
# List available engines
uv run python -m ocr_hindi engines

# Validate setup (dependencies + auth)
uv run python -m ocr_hindi validate

# View PDF info
uv run python -m ocr_hindi info manuscript.pdf
```

</details>

---

## 🖥️ Streamlit UI

Launch with `uv run streamlit run src/ocr_hindi/app.py` — a beautiful 4-page web interface:

| Page | What It Does |
|:-----|:-------------|
| 📄 **Process** | Upload PDF, pick engine, set pages, watch live progress |
| 📚 **Library** | Browse all processed manuscripts with metadata |
| 🔍 **Search** | Full-text search across your entire library (FTS5) |
| ⚙️ **Settings** | Configure API keys, default engine, workers, DPI |

---

## 💰 Cost Comparison

<div align="center">

<table>
<tr>
<th width="45%">❌ Traditional OCR</th>
<th width="10%"></th>
<th width="45%">✅ OCR-Devnagari</th>
</tr>
<tr>
<td align="center">

| Metric | Value |
|:------:|:-----:|
| 📄 Pages | 1,000 |
| 💸 Cost | ~$10–15 |
| 🔄 API Calls | 1,000 |
| ⏱️ Time | ~45 min |
| 🛡️ On Crash | **LOSE ALL** |

</td>
<td align="center"><h3>→</h3></td>
<td align="center">

| Metric | Value |
|:------:|:-----:|
| 📄 Pages | 1,000 |
| 💸 Cost | **~$0.44** |
| 🔄 API Calls | ~100–150 |
| ⏱️ Time | ~40 min |
| 🛡️ On Crash | **Resume ✓** |

</td>
</tr>
</table>

</div>

### 🏆 Engine Comparison

| Engine | Cost/1K Pages | Accuracy | Speed | Best For |
|:------:|:------------:|:--------:|:-----:|:---------|
| 💎 **gemini** | ~$0.44 | ⭐⭐⭐⭐⭐ | ⚡⚡⚡⚡ | **Best value** — Gemini 2.0 Flash |
| 🔀 **hybrid** | ~$0.30 | ⭐⭐⭐⭐⭐ | ⚡⚡⚡ | Sacred texts with mantras |
| 🆓 **easyocr** | FREE | ⭐⭐⭐⭐ | ⚡⚡ | Budget / offline |
| 🆓 **marker** | FREE | ⭐⭐⭐⭐⭐ | ⚡⚡⚡ | Structured PDFs |
| 🆓 **tesseract** | FREE | ⭐⭐⭐ | ⚡⚡⚡⚡ | Simple documents |

---

## 🏗️ Architecture

```
                              ┌─────────────────────────────────────────┐
                              │              📄 PDF Input               │
                              └───────────────────┬─────────────────────┘
                                                  │
                                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          🔀 INTELLIGENT ROUTING                             │
│                                                                             │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│   │  hybrid  │  │  gemini  │  │ easyocr  │  │  marker  │  │tesseract │   │
│   │ DEFAULT  │  │ PREMIUM  │  │   FREE   │  │   FREE   │  │   FREE   │   │
│   └────┬─────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│        │                                                                    │
│        ▼                                                                    │
│   ┌─────────────────────────────────────────────────────────────────┐      │
│   │                   🧠 HYBRID DECISION ENGINE                     │      │
│   │                                                                 │      │
│   │   EasyOCR ──▶ Confidence < 85%? ──▶ Mantra Detected?           │      │
│   │    (FREE)           │                      │                    │      │
│   │                     ▼                      ▼                    │      │
│   │            ┌──────────────────────────────────────┐             │      │
│   │            │      💎 Gemini 2.0 Flash              │             │      │
│   │            │   • thinking_level: "low"             │             │      │
│   │            │   • media_resolution: "high"          │             │      │
│   │            │   • Token tracking for cost            │             │      │
│   │            └──────────────────────────────────────┘             │      │
│   └─────────────────────────────────────────────────────────────────┘      │
│                                                                             │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        🛡️ CRASH-SAFE PIPELINE                               │
│                                                                             │
│   OCR ──▶ Cache (atomic write) ──▶ Progress Update ──▶ Release Memory      │
│            page_NNN.txt                                                     │
│                                                                             │
│   On interrupt: ✓ Pages preserved  ✓ Resume skips done  ✓ No duplicate $   │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
                  ┌─────────────────────────────────────────┐
                  │  📝 Markdown Output + 💰 Cost Report     │
                  │  🔍 FTS5 Indexed  + 📚 Library Entry     │
                  └─────────────────────────────────────────┘
```

<div align="center">

📚 **[Full Architecture Documentation →](docs/HYBRID_ARCHITECTURE.md)**

</div>

---

## 🕉️ Mantra Detection

<div align="center">

*Intelligent detection ensures sacred text is always verified with maximum accuracy*

</div>

<table align="center">
<tr>
<td align="center" width="25%">

**बीज मन्त्र**<br>
<sub>Seed Syllables</sub>

```
ॐ    ह्रीं   श्रीं
क्लीं   ऐं    हुं
```

</td>
<td align="center" width="25%">

**मन्त्र समाप्ति**<br>
<sub>Sacred Endings</sub>

```
स्वाहा   नमः   फट्
वौषट्   हुं   ठः
```

</td>
<td align="center" width="25%">

**श्लोक चिह्न**<br>
<sub>Verse Markers</sub>

```
॥१॥  ॥२॥  ॥३॥
॥ इति ॥
```

</td>
<td align="center" width="25%">

**विभाग सूचक**<br>
<sub>Section Indicators</sub>

```
विनियोग  न्यास
ध्यान   कवच
```

</td>
</tr>
</table>

---

## ⚙️ Configuration

| Option | Description | Default |
|:------:|:-----------|:-------:|
| `-e, --engine` | `hybrid`, `gemini`, `easyocr`, `marker`, `tesseract` | `hybrid` |
| `-p, --pages` | `all`, `1-50`, `1,5,10-20` | *interactive* |
| `-w, --workers` | Concurrent workers (1–20) | `5` |
| `-c, --confidence` | Hybrid threshold (0.0–1.0) | `0.85` |
| `--verify-mantras` | Verify mantra pages with Gemini | `true` |
| `-r, --resume` | Resume from previous progress | `false` |
| `-n, --dry-run` | Preview without processing | `false` |
| `--dpi` | PDF rendering quality | `200` |
| `--batch` | Enable batch processing via GCS | `false` |
| `--gcs-bucket` | GCS bucket for batch mode | — |

---

## 📁 Output Structure

```
your_manuscript/
├── 📄 manuscript.pdf                        # Original
├── 📝 manuscript_unicode.md                 # ✨ Final output (Devanagari)
├── 📋 ocr_manuscript_20240120_143022.log    # Processing log
├── 📊 .ocr_progress_manuscript.json         # Resume state
├── 🗄️ .ocr_search.db                        # FTS5 search index
└── 📂 .ocr_cache_manuscript/                # 🛡️ Crash-safe cache
    ├── page_0001.txt
    ├── page_0001.meta.json
    └── ...
```

---

## 🔧 Troubleshooting

<details>
<summary><b>❌ "poppler not found"</b></summary>

```bash
brew install poppler          # macOS
sudo apt install poppler-utils  # Ubuntu/Debian
```

</details>

<details>
<summary><b>❌ "EasyOCR not installed"</b></summary>

```bash
uv pip install easyocr
```

</details>

<details>
<summary><b>❌ "Tesseract not installed"</b></summary>

```bash
brew install tesseract tesseract-lang          # macOS
sudo apt install tesseract-ocr tesseract-ocr-hin tesseract-ocr-san  # Ubuntu
```

</details>

<details>
<summary><b>❌ Authentication errors</b></summary>

```bash
# Verify Vertex AI
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID

# Or use API key
export GEMINI_API_KEY="your-key"

# Test
uv run python -m ocr_hindi validate
```

</details>

<details>
<summary><b>❌ Rate limiting (429 errors)</b></summary>

```bash
# Reduce workers — auto-retry with exponential backoff is built in
uv run python -m ocr_hindi ocr book.pdf --workers 3
```

</details>

<details>
<summary><b>❌ High memory usage</b></summary>

```bash
# Reduce workers or process in chunks
uv run python -m ocr_hindi ocr book.pdf --workers 2
uv run python -m ocr_hindi ocr book.pdf --pages '1-100' && \
uv run python -m ocr_hindi ocr book.pdf --pages '101-200' --resume
```

</details>

---

## 🤝 Contributing

<div align="center">

**Contributions make open source amazing!**

</div>

<table align="center">
<tr>
<td align="center">🐛 <b>Bugs</b><br><a href="https://github.com/rajeshkanaka/OCR-Devnagari/issues">Open Issue</a></td>
<td align="center">💡 <b>Ideas</b><br><a href="https://github.com/rajeshkanaka/OCR-Devnagari/discussions">Discuss</a></td>
<td align="center">🔧 <b>PRs</b><br>Fork & Submit</td>
<td align="center">📖 <b>Docs</b><br>Help improve</td>
</tr>
</table>

```bash
git clone https://github.com/YOUR_USERNAME/OCR-Devnagari.git
cd OCR-Devnagari && git checkout -b feature/amazing-feature
# Make changes, then:
git commit -m "Add amazing feature"
git push origin feature/amazing-feature
# Open a Pull Request 🎉
```

---

## 📜 License

<div align="center">

**MIT License** — Free for personal and commercial use. See [LICENSE](LICENSE).

</div>

---

## 🙏 Acknowledgments

<div align="center">

<a href="https://deepmind.google/technologies/gemini/">
  <img src="https://img.shields.io/badge/Google-Gemini_2.0-4285F4?style=for-the-badge&logo=google&logoColor=white"/>
</a>
&nbsp;
<a href="https://github.com/JaidedAI/EasyOCR">
  <img src="https://img.shields.io/badge/JaidedAI-EasyOCR-00C853?style=for-the-badge&logo=opencv&logoColor=white"/>
</a>
&nbsp;
<a href="https://github.com/tesseract-ocr/tesseract">
  <img src="https://img.shields.io/badge/Tesseract-OCR-FF6B35?style=for-the-badge&logo=google&logoColor=white"/>
</a>
&nbsp;
<a href="https://github.com/VikParuchuri/marker">
  <img src="https://img.shields.io/badge/VikParuchuri-Marker-9C27B0?style=for-the-badge&logo=markdown&logoColor=white"/>
</a>
&nbsp;
<a href="https://github.com/astral-sh/uv">
  <img src="https://img.shields.io/badge/Astral-UV-DE5FE9?style=for-the-badge&logo=astral&logoColor=white"/>
</a>

</div>

---

<div align="center">

### ॥ सर्वे भवन्तु सुखिनः ॥

*May all beings be happy*

<br>

<img src="https://img.shields.io/badge/🕉️-OM-FF6B35?style=for-the-badge&labelColor=1a1a2e"/>

<br>

**Built with ❤️ for the Sanskrit & Hindu community**

<br>

<a href="https://github.com/rajeshkanaka/OCR-Devnagari">
  <img src="https://img.shields.io/badge/⭐_Star_if_helpful!-FFD700?style=for-the-badge&logo=github&logoColor=black"/>
</a>

<br><br>

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=100&section=footer" width="100%"/>

</div>
