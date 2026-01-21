<div align="center">

<!-- Divine Invocation -->
<sub>॥ श्री गणेशाय नमः ॥</sub>

<br>

<!-- Logo -->
<img src="https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Scroll/3D/scroll_3d.png" width="140" alt="Sacred Scroll"/>

<br>

<!-- Title with Devanagari flair -->
# OCR-Devnagari (Sanskrit, Marathi and Hindi)

### *Digitizing Sacred Wisdom, One Page at a Time*

<br>

**Production-grade OCR for Hindi, Sanskrit & Devanagari manuscripts**<br>
*Intelligent hybrid processing • Crash-safe architecture • 90% cost savings*

<br>

<!-- Primary Action Badges -->
[<img src="https://img.shields.io/badge/⚡_Quick_Start-2_Minutes-00C853?style=for-the-badge" alt="Quick Start"/>](#-quick-start)
&nbsp;
[<img src="https://img.shields.io/badge/💰_Save-Up_to_90%25-FF6B35?style=for-the-badge" alt="Cost Savings"/>](#-cost-comparison)
&nbsp;
[<img src="https://img.shields.io/badge/📖_Documentation-View_Docs-0288D1?style=for-the-badge" alt="Documentation"/>](#-architecture)

<br>

<!-- Tech Stack Badges -->
<img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"/>
&nbsp;
<img src="https://img.shields.io/badge/Gemini_3-Flash_Preview-4285F4?style=flat-square&logo=google&logoColor=white" alt="Gemini"/>
&nbsp;
<img src="https://img.shields.io/badge/EasyOCR-Built_In-00C853?style=flat-square&logo=opencv&logoColor=white" alt="EasyOCR"/>
&nbsp;
<img src="https://img.shields.io/badge/Architecture-Crash_Safe-9C27B0?style=flat-square&logo=shield&logoColor=white" alt="Crash Safe"/>
&nbsp;
<img src="https://img.shields.io/badge/License-MIT-F9A825?style=flat-square" alt="License"/>

<br>
<br>

<!-- Animated Demo Placeholder -->
<img src="https://user-images.githubusercontent.com/placeholder/ocr-hindi-demo.gif" width="750" alt="OCR Hindi in Action"/>

<sub>*Processing a 1000-page tantric manuscript with crash-safe resume capability*</sub>

</div>

<br>

---

<br>

## 🪔 Why OCR Hindi?

<table>
<tr>
<td width="60%">

### The Problem

Ancient Sanskrit and Hindi manuscripts—tantras, stotras, and sacred texts—are being lost to time. Existing OCR tools either:

- ❌ **Can't handle Devanagari** complex conjuncts (संयुक्ताक्षर)
- ❌ **Destroy mantras** like ॐ ह्रीं श्रीं क्लीं
- ❌ **Cost a fortune** for large manuscripts
- ❌ **Crash and lose work** on long documents

### The Solution

OCR Hindi combines the **speed of local OCR** with the **accuracy of Gemini AI**, using intelligent routing to achieve **90% cost savings** while preserving every sacred syllable.

</td>
<td width="40%" align="center">

```
┌─────────────────────────┐
│                         │
│   📜 1000-page Tantra   │
│                         │
│   Before: $10+ cost     │
│   After:  $1 cost       │
│                         │
│   ✨ 90% Savings ✨     │
│                         │
│   Zero data loss on     │
│   crash or interrupt    │
│                         │
└─────────────────────────┘
```

</td>
</tr>
</table>

<br>

---

<br>

## ⚡ Quick Start

<table>
<tr>
<td>

### 1️⃣ &nbsp; Clone & Install

```bash
git clone https://github.com/rajeshkanaka/OCR-Devnagari.git
cd OCR-Devnagari
uv sync && uv pip install easyocr
```

</td>
</tr>
<tr>
<td>

### 2️⃣ &nbsp; Configure API *(for Gemini features)*

```bash
# Option A: Vertex AI (Recommended)
export GOOGLE_CLOUD_PROJECT="your-project"
export GOOGLE_CLOUD_LOCATION="global"
export GOOGLE_GENAI_USE_VERTEXAI=1

# Option B: API Key
export GEMINI_API_KEY="your-key"
```

</td>
</tr>
<tr>
<td>

### 3️⃣ &nbsp; Run!

```bash
# 🔥 Hybrid mode — 90% savings, maximum accuracy
python -m ocr_hindi ocr manuscript.pdf --pages "all"

# 🆓 100% FREE local processing
python -m ocr_hindi ocr manuscript.pdf -e easyocr
```

</td>
</tr>
</table>

<br>

---

<br>

## 💎 Features at a Glance

<div align="center">

|  |  |  |
|:---:|:---:|:---:|
| **🔀 Multi-Engine** | **🧠 Smart Hybrid** | **🕉️ Mantra Detection** |
| 5 OCR backends to choose from | EasyOCR + Gemini when needed | Auto-detect sacred text |
| **⚡ High Performance** | **💾 Crash-Safe** | **📊 Live Progress** |
| Async concurrent workers | Resume from any interruption | Real-time with ETA |
| **🛡️ Graceful Shutdown** | **🧹 Memory Efficient** | **✅ Response Validation** |
| Ctrl+C saves all work | Handles 1000+ page PDFs | Rejects invalid results |

</div>

<br>

---

<br>

## 💰 Cost Comparison

<div align="center">

### *How much can you save?*

</div>

<br>

<table>
<tr>
<th width="50%" align="center">

### ❌ &nbsp; Traditional Approach

</th>
<th width="50%" align="center">

### ✅ &nbsp; With OCR Hindi

</th>
</tr>
<tr>
<td align="center">

```
📄 1000-page Manuscript

💸 Cost:     ~$10-15
🔄 API Calls: 1000
⏱️ Time:     ~45 min
🛡️ Crash:    LOSE EVERYTHING
```

</td>
<td align="center">

```
📄 1000-page Manuscript

💸 Cost:     ~$1-2 (90% less!)
🔄 API Calls: ~100-150 (mantras only)
⏱️ Time:     ~90 min
🛡️ Crash:    Resume instantly ✓
```

</td>
</tr>
</table>

<br>

<div align="center">

### Engine Comparison

| Engine | Cost | Accuracy | Speed | Best For |
|:------:|:----:|:--------:|:-----:|:---------|
| 🔀 **hybrid** | ~$0.30/1K | ⭐⭐⭐⭐⭐ | ⚡⚡⚡ | **Recommended** — Optimal balance |
| 🆓 **easyocr** | FREE | ⭐⭐⭐⭐ | ⚡⚡ | Budget-conscious, good Hindi |
| 🆓 **marker** | FREE | ⭐⭐⭐⭐⭐ | ⚡⚡⚡ | Structured PDFs, books |
| 🆓 **tesseract** | FREE | ⭐⭐⭐ | ⚡⚡⚡⚡ | Simple documents |
| 💎 **gemini** | ~$2/1K | ⭐⭐⭐⭐⭐ | ⚡⚡⚡⚡ | Critical accuracy needed |

<br>

<sub>

**Gemini 3 Flash Pricing:** Input $0.50/1M tokens • Output $3.00/1M tokens

</sub>

</div>

<br>

---

<br>

## 🏗️ Architecture

<div align="center">

> *"Write once, crash anywhere, resume everywhere"*

</div>

<br>

```
                              ┌─────────────────────────────────────────┐
                              │           📄 PDF Input                  │
                              └───────────────────┬─────────────────────┘
                                                  │
                                                  ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              🔀 INTELLIGENT ROUTING                                  │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│    │  hybrid  │    │ easyocr  │    │  marker  │    │tesseract │    │  gemini  │   │
│    │ DEFAULT  │    │   FREE   │    │   FREE   │    │   FREE   │    │ PREMIUM  │   │
│    └────┬─────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘   │
│         │                                                                          │
│         ▼                                                                          │
│    ┌─────────────────────────────────────────────────────────────────────────┐    │
│    │                     🧠 HYBRID DECISION ENGINE                            │    │
│    │                                                                          │    │
│    │   ┌─────────────┐         ┌─────────────────┐         ┌─────────────┐   │    │
│    │   │  EasyOCR    │ ──────▶ │ Confidence Check │ ──────▶ │   Mantra    │   │    │
│    │   │    FREE     │         │     < 85% ?      │         │  Detected?  │   │    │
│    │   └─────────────┘         └─────────────────┘         └──────┬──────┘   │    │
│    │                                    │                          │          │    │
│    │                                    ▼                          ▼          │    │
│    │                           ┌───────────────────────────────────────┐      │    │
│    │                           │        💎 Gemini 3 Flash             │      │    │
│    │                           │   • thinking_level: "low"            │      │    │
│    │                           │   • media_resolution: "high"         │      │    │
│    │                           │   • Token tracking for cost          │      │    │
│    │                           └───────────────────────────────────────┘      │    │
│    └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                                  │
                                                  ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              🛡️ CRASH-SAFE PIPELINE                                 │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│    For each page:                                                                   │
│                                                                                     │
│    ┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│    │   OCR    │────▶│    Cache     │────▶│   Progress   │────▶│   Release    │    │
│    │ Process  │     │ Atomic Write │     │   Update     │     │   Memory     │    │
│    └──────────┘     │ page_NNN.txt │     └──────────────┘     │ gc.collect() │    │
│                     └──────────────┘                          └──────────────┘    │
│                            │                                                        │
│                            ▼                                                        │
│                   .ocr_cache_{pdf}/                                                 │
│                   ├── page_0001.txt  ◀── Survives crash!                           │
│                   ├── page_0002.txt                                                 │
│                   └── ...                                                           │
│                                                                                     │
│    On interrupt (Ctrl+C) or crash:                                                 │
│    ┌─────────────────────────────────────────────────────────────────────────┐    │
│    │  ✓ All cached pages preserved    ✓ Resume skips completed pages        │    │
│    │  ✓ No duplicate API charges      ✓ Output merged from cache            │    │
│    └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                                  │
                                                  ▼
                              ┌─────────────────────────────────────────┐
                              │   📝 Markdown Output + 💰 Cost Report   │
                              └─────────────────────────────────────────┘
```

<br>

<div align="center">

📚 **[Read the Full Architecture Documentation →](docs/HYBRID_ARCHITECTURE.md)**

</div>

<br>

---

<br>

## 🕉️ Mantra Detection

<div align="center">

*Intelligent detection of sacred text patterns ensures mantras are always verified with maximum accuracy*

</div>

<br>

<table>
<tr>
<td width="25%" align="center">

**बीज मन्त्र**<br>
*Seed Syllables*

```
ॐ    ह्रीं   श्रीं
क्लीं   ऐं    हुं
```

</td>
<td width="25%" align="center">

**मन्त्र समाप्ति**<br>
*Sacred Endings*

```
स्वाहा   नमः   फट्
वौषट्   हुं   ठः
```

</td>
<td width="25%" align="center">

**श्लोक चिह्न**<br>
*Verse Markers*

```
॥१॥  ॥२॥  ॥३॥
॥ इति ॥
```

</td>
<td width="25%" align="center">

**विभाग सूचक**<br>
*Section Indicators*

```
विनियोग  न्यास
ध्यान   कवच
```

</td>
</tr>
</table>

<br>

---

<br>

## 📖 Usage Examples

<details open>
<summary><h3>🔀 Hybrid Mode <sub>(Recommended)</sub></h3></summary>

```bash
# Process entire manuscript with intelligent routing
python -m ocr_hindi ocr sacred_text.pdf --pages "all"

# Adjust confidence threshold (higher = more Gemini verification)
python -m ocr_hindi ocr sacred_text.pdf --confidence 0.90

# Disable mantra verification for faster processing
python -m ocr_hindi ocr sacred_text.pdf --no-verify-mantras

# Process specific page ranges
python -m ocr_hindi ocr sacred_text.pdf --pages "1-100,200-250"

# Use more workers for faster processing
python -m ocr_hindi ocr sacred_text.pdf --workers 10
```

</details>

<details>
<summary><h3>🆓 Free Local Processing</h3></summary>

```bash
# EasyOCR — Good Hindi/Devanagari support, no API needed
python -m ocr_hindi ocr book.pdf -e easyocr

# Marker — Best for structured books and PDFs
python -m ocr_hindi ocr book.pdf -e marker

# Tesseract — Fast, requires system installation
python -m ocr_hindi ocr book.pdf -e tesseract
```

</details>

<details>
<summary><h3>💎 Premium Gemini Mode</h3></summary>

```bash
# Maximum accuracy for critical manuscripts
python -m ocr_hindi ocr rare_manuscript.pdf -e gemini

# With high concurrency
python -m ocr_hindi ocr rare_manuscript.pdf -e gemini --workers 15
```

</details>

<details>
<summary><h3>🛠️ Utility Commands</h3></summary>

```bash
# List all available engines with details
python -m ocr_hindi engines

# Validate your setup (dependencies + authentication)
python -m ocr_hindi validate

# View PDF information
python -m ocr_hindi info manuscript.pdf

# Dry run — see what would be processed
python -m ocr_hindi ocr manuscript.pdf --dry-run

# Resume interrupted processing
python -m ocr_hindi ocr manuscript.pdf --resume
```

</details>

<br>

---

<br>

## ⚙️ Configuration

<div align="center">

| Option | Description | Default |
|:------:|:------------|:-------:|
| `-e, --engine` | OCR engine (`hybrid`, `easyocr`, `marker`, `tesseract`, `gemini`) | `hybrid` |
| `-p, --pages` | Page range (`all`, `1-50`, `1,5,10-20`) | *interactive* |
| `-w, --workers` | Concurrent workers (1-20) | `5` |
| `-c, --confidence` | Hybrid threshold (0.0-1.0) | `0.85` |
| `--verify-mantras` | Verify mantra pages with Gemini | `true` |
| `-r, --resume` | Resume from previous progress | `false` |
| `-n, --dry-run` | Preview without processing | `false` |
| `--dpi` | PDF rendering quality | `200` |

</div>

<br>

---

<br>

## 📁 Output Files

```
your_manuscript/
├── manuscript.pdf                        # Original file
├── manuscript_unicode.md                 # ✨ Final output (Devanagari text)
├── ocr_manuscript_20240120_143022.log    # Processing log
├── .ocr_progress_manuscript.json         # Resume state
└── .ocr_cache_manuscript/                # 🛡️ Crash-safe cache
    ├── page_0001.txt                     #    Individual page cache
    ├── page_0001.meta.json               #    Page metadata
    ├── page_0002.txt
    └── ...
```

<br>

---

<br>

## 📊 Performance

<div align="center">

| Mode | 1000 Pages | Throughput | Cost | Notes |
|:----:|:----------:|:----------:|:----:|:------|
| 🔀 Hybrid | ~90 min | ~11 ppm | **~$1** | Best value |
| 🆓 EasyOCR | ~120 min | ~8 ppm | **$0** | 100% free |
| 🆓 Marker | ~60 min | ~16 ppm | **$0** | Structured PDFs |
| 💎 Gemini | ~45 min | ~22 ppm | ~$10 | Max accuracy |

<sub>*ppm = pages per minute • Tested on M1 MacBook Pro with 10 workers*</sub>

</div>

<br>

---

<br>

## 🔧 Troubleshooting

<details>
<summary><b>❌ &nbsp; "poppler not found"</b></summary>

```bash
# macOS
brew install poppler

# Ubuntu/Debian
sudo apt-get install poppler-utils

# Windows
# Download from: https://github.com/oschwartz10612/poppler-windows/releases
```

</details>

<details>
<summary><b>❌ &nbsp; "EasyOCR not installed"</b></summary>

```bash
uv pip install easyocr
# or
pip install easyocr
```

</details>

<details>
<summary><b>❌ &nbsp; "Tesseract not installed"</b></summary>

```bash
# macOS
brew install tesseract tesseract-lang

# Ubuntu/Debian
sudo apt install tesseract-ocr tesseract-ocr-hin tesseract-ocr-san

# Windows
# Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
```

</details>

<details>
<summary><b>❌ &nbsp; Authentication errors</b></summary>

```bash
# Verify Vertex AI setup
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID

# Or use API key instead
export GEMINI_API_KEY="your-api-key-here"

# Test authentication
python -m ocr_hindi validate
```

</details>

<details>
<summary><b>❌ &nbsp; Rate limiting (429 errors)</b></summary>

```bash
# Reduce concurrent workers
python -m ocr_hindi ocr book.pdf --workers 3

# The system will automatically retry with exponential backoff
# If persistent, wait a few minutes before retrying
```

</details>

<details>
<summary><b>❌ &nbsp; High memory usage</b></summary>

```bash
# Reduce workers (each worker holds images in memory)
python -m ocr_hindi ocr book.pdf --workers 2

# Or process in smaller batches
python -m ocr_hindi ocr book.pdf --pages "1-100"
python -m ocr_hindi ocr book.pdf --pages "101-200" --resume
```

</details>

<br>

---

<br>

## 🤝 Contributing

<div align="center">

*Contributions are what make the open source community amazing!*

</div>

<br>

We welcome contributions of all kinds:

- 🐛 **Bug Reports** — Found a bug? [Open an issue](https://github.com/rajeshkanaka/OCR-Devnagari/issues)
- 💡 **Feature Requests** — Have an idea? [Start a discussion](https://github.com/rajeshkanaka/OCR-Devnagari/discussions)
- 🔧 **Pull Requests** — Ready to code? Fork and submit a PR
- 📖 **Documentation** — Help improve our docs
- 🌍 **Translations** — Help us reach more users

<br>

```bash
# Fork, clone, and create a branch
git clone https://github.com/YOUR_USERNAME/OCR-Devnagari.git
cd OCR-Devnagari
git checkout -b feature/amazing-feature

# Make your changes, then
git commit -m "Add amazing feature"
git push origin feature/amazing-feature

# Open a Pull Request 🎉
```

<br>

---

<br>

## 📜 License

<div align="center">

**MIT License** — Free for personal and commercial use

See [LICENSE](LICENSE) for details

</div>

<br>

---

<br>

<div align="center">

## 🙏 Acknowledgments

*This project stands on the shoulders of giants*

<br>

[Google Gemini](https://deepmind.google/technologies/gemini/) •
[EasyOCR](https://github.com/JaidedAI/EasyOCR) •
[Tesseract](https://github.com/tesseract-ocr/tesseract) •
[Marker](https://github.com/VikParuchuri/marker) •
[pdf2image](https://github.com/Belval/pdf2image)

<br>

---

<br>

<sub>

*Dedicated to the preservation of sacred wisdom*

*May this tool help digitize and preserve ancient manuscripts for generations to come*

</sub>

<br>

### ॥ सर्वे भवन्तु सुखिनः ॥

*May all beings be happy*

<br>

<img src="https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Om/3D/om_3d.png" width="60" alt="Om"/>

<br>

<sub>

**Built with ❤️ for the Sanskrit & Hindu community**

[⭐ Star this repo](https://github.com/rajeshkanaka/OCR-Devnagari) if you find it useful!

</sub>

</div>
