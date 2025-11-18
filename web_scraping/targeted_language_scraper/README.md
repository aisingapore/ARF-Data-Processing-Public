# Targeted Language Scraping Framework

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Scrapy](https://img.shields.io/badge/scrapy-2.11%2B-60a839?style=flat-square&logo=scrapy&logoColor=white)](https://scrapy.org/)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square)](https://github.com/psf/black)

_A production-ready, multilingual web scraping framework with AI-powered language validation_

[Features](#-features) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Contributing](#-contributing)

</div>

---

## 🎯 Overview

The Targeted Language Scraping Framework is a holistic, production-ready solution for discovering, configuring, and scraping web and PDF content in specific target languages. Built on Scrapy and powered by GlotLID for language validation, it provides a complete 3-stage pipeline orchestrated from a single command.

### Why This Framework?

- **Language-First Design**: Ensures scraped content matches your target language using state-of-the-art NLP
- **Zero-Config Language Addition**: Add new languages via JSON without writing code
- **Production-Ready**: Built-in resume capability, comprehensive logging, and error handling
- **Dual Content Support**: Handles both web articles and PDF documents seamlessly

## ✨ Features

### Core Capabilities

- 🎯 **Single-Command Orchestration** - Execute entire pipelines with one command
- 🌍 **Generalized Language Support** - Add languages via JSON configuration
- 🤖 **AI-Powered Validation** - GlotLID-based language detection and filtering
- 📄 **Dual Content Pipelines** - Web (HTML) and PDF scraping workflows
- 💾 **Graceful Resume** - Stop and resume long-running jobs without data loss
- ⚙️ **Centralized Configuration** - All settings in `config.ini`

### Technical Highlights

- Automatic CMS detection (WordPress, Drupal, etc.)
- Dynamic CSS selector generation
- Playwright integration for JavaScript-heavy sites
- Concurrent PDF processing
- Comprehensive error handling and logging

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        run.py (Orchestrator)                 │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │     Stage 1       │
                    │  Discover Spider  │
                    │ (Shared Component)│
                    └─────────┬─────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
         [Web Pipeline]                  [PDF Pipeline]
              │                               │
    ┌─────────┴─────────┐                    │
    │                   │                    │
┌───▼────────┐   ┌──────▼──────┐      ┌─────▼──────┐
│  Stage 2   │   │   Stage 3   │      │  Stage 2   │
│ Configure  │──▶│   Execute   │      │  Execute   │
│(auto-gen)  │   │(master.py)  │      │(language   │
│            │   │             │      │ _pdf.py)   │
└────────────┘   └──────┬──────┘      └─────┬──────┘
                        │                    │
                        └────────┬───────────┘
                                 ▼
                  [LanguageService Validation]
```

### Project Structure

```
targeted_language_scraper/
├── 📄 run.py                      # Main entry point
├── ⚙️ config.ini                  # Central configuration
├── 🌍 languages.json              # Language definitions
├── 📦 requirements.txt            # Python dependencies
├── 📝 scrapy.cfg                  # Scrapy configuration
│
├── 📁 jobs/                       # Resume state storage
├── 📁 language_models/            # GlotLID model cache
├── 📁 output/                     # Scraped data output
│
└── 📁 unified_scraper/            # Main package
    ├── items.py                   # Data schemas
    ├── pipelines.py               # Data processing
    ├── settings.py                # Scrapy settings
    │
    ├── 📁 core/
    │   ├── config_generator.py    # Selector auto-generation
    │   └── language_service.py    # Language validation engine
    │
    └── 📁 spiders/
        ├── discover.py            # URL discovery
        ├── master.py              # Web scraping
        ├── language_pdf.py        # PDF scraping
        └── base_pdf_spider.py     # PDF base class
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Git
- ~1.6 GB free disk space (for GlotLID model)
- Stable internet connection

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/aisingapore/ARF-Data-Processing-Public.git
cd targeted_language_scraper

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers (one-time setup)
playwright install
```

### First Run

On your first execution, the framework will automatically download the GlotLID model (~300MB). This is a one-time operation.

```bash
# Example: Scrape Filipino news articles
python run.py web -l filipino -t "Filipino news,Tagalog articles" -n 20
```

**Expected output:**

```
[INFO] Initializing LanguageService...
[INFO] Downloading GlotLID model from Hugging Face...
[INFO] Model downloaded successfully to language_models/
[INFO] Starting Web Pipeline for language: Filipino
...
```

## 📖 Usage

### Command Structure

```bash
python run.py {web|pdf} -l LANGUAGE -t "TERMS" -n NUM_URLS
```

### Web Scraping Pipeline

Discovers URLs, auto-configures selectors, and scrapes HTML articles.

```bash
# Filipino news from top 20 sites
python run.py web -l filipino -t "Filipino news,Tagalog articles" -n 20

# Filipino news from top 20 sites (resume scrapping job)
python run.py web -l filipino -t "Filipino news,Tagalog articles" -n 20 --job-id 20251117_155030

# Malay government websites
python run.py web -l malay -t "berita Malaysia,kerajaan" -n 15
```

**Pipeline stages:**

1. **Discover** - Finds seed URLs via search
2. **Configure** - Analyzes sites and generates `site_configs.json`
3. **Execute** - Scrapes articles with language validation

### PDF Scraping Pipeline

Discovers URLs and extracts text from PDF documents.

```bash
# Malay government PDFs
python run.py pdf -l malay -t "dokumen kerajaan malaysia pdf" -n 50

# Filipino academic papers
python run.py pdf -l filipino -t "Filipino research papers pdf" -n 30
```

**Pipeline stages:**

1. **Discover** - Finds seed URLs via search
2. **Execute** - Crawls sites, downloads PDFs, validates language

### Command Options

| Option        | Description                          | Required | Default |
| ------------- | ------------------------------------ | -------- | ------- |
| `web\|pdf`    | Pipeline type                        | Yes      | -       |
| `-l, --lang`  | Language key (from `languages.json`) | Yes      | -       |
| `-t, --terms` | Comma-separated search terms         | Yes      | -       |
| `-n, --num`   | Maximum seed URLs to discover        | No       | 10      |

### Resume Capability

All jobs automatically save state. To resume an interrupted job:

```bash
# Stop a job with Ctrl+C
^C
[INFO] Gracefully shutting down...
[INFO] Job state saved to jobs/

# Resume by running the exact same command
python run.py web -l filipino -t "Filipino news" -n 20
[INFO] Resuming previous job...
```

## ⚙️ Configuration

### 1. Main Configuration (`config.ini`)

Controls all file paths and directories.

```ini
[Paths]
# Output directories
output_dir = output
job_dir = jobs

# Configuration files
language_file = languages.json
site_config_file = site_configs.json

# Model cache
model_cache_dir = language_models
```

### 2. Language Configuration (`languages.json`)

Define target languages and their properties.

```json
{
  "filipino": {
    "name": "Filipino",
    "glotlid_codes": ["tgl_Latn", "fil_Latn"],
    "download_dir": "filipino_pdfs"
  },
  "malay": {
    "name": "Malay",
    "glotlid_codes": ["zsm_Latn", "zlm_Latn"],
    "download_dir": "malay_pdfs"
  }
```

**Adding a new language:**

1. Find GlotLID language codes at [GlotLID documentation](https://github.com/cisnlp/GlotLID)
2. Add entry to `languages.json`
3. Run pipeline with new language key

### 3. Site Configuration (`site_configs.json`)

Auto-generated by the Configure stage. Contains CSS selectors for each site.

```json
{
  "example.com": {
    "title_selector": "h1.article-title",
    "content_selector": "div.article-body",
    "cms": "wordpress"
  }
}
```

### Key Modules

#### `LanguageService` (Core Engine)

The central brain for language operations.

```python
from unified_scraper.core.language_service import LanguageService

# Initialize once per spider
service = LanguageService(config_path="config.ini")

# Load language configuration
config = service.get_language_config("filipino")

# Validate text
is_valid = service.validate_language(text, "filipino")
```

#### Custom Spider Development

Extend the base spiders for custom functionality:

```python
from unified_scraper.spiders.base_pdf_spider import BasePdfLanguageSpider

class CustomPdfSpider(BasePdfLanguageSpider):
    name = "custom_pdf"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Custom initialization
```

## 🔧 Troubleshooting

### Common Issues

#### GlotLID Model Download Fails

**Symptom:** Model download times out or fails

**Solution:**

```bash
# Manual download
mkdir -p language_models
cd language_models
wget https://huggingface.co/cis-lmu/glotlid/resolve/main/model.bin

# Verify file size (should be ~300MB)
ls -lh model.bin
```

#### Playwright Browser Not Found

**Symptom:** `Error: Browser executable not found`

**Solution:**

```bash
# Reinstall Playwright browsers
playwright install chromium

# Or install all browsers
playwright install
```

#### Memory Issues on Large Crawls

**Symptom:** Spider crashes with `MemoryError`

**Solution:**

```python
# In settings.py, adjust concurrent requests
CONCURRENT_REQUESTS = 8  # Reduce from default 16
CONCURRENT_REQUESTS_PER_DOMAIN = 4
```

#### No Results from Discovery Stage

**Symptom:** `discover.py` returns 0 URLs

**Solution:**

- Try more specific search terms
- Increase `-n` parameter
- Check internet connection
- Verify search terms match target language

### Code Standards

- Follow PEP 8 style guide
- Use Black for formatting
- Add docstrings to public methods
- Include unit tests for new features
- Update documentation as needed

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Scrapy](https://scrapy.org/) - Web scraping framework
- [GlotLID](https://github.com/cisnlp/GlotLID) - Language identification model
- [Playwright](https://playwright.dev/) - Browser automation
- [fastText](https://fasttext.cc/) - Text processing library

---

<div align="center">
**[⬆ back to top](#-table-of-contents)**
</div>
