# :page_facing_up: paper-translator-en2ja

A Claude Code skill that translates English academic papers (PDF) into Japanese — with figures, structured summaries, and PDF output.

![Claude Code](https://img.shields.io/badge/Claude_Code-Skill-blueviolet?logo=anthropic)
![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![License](https://img.shields.io/badge/License-AGPL--v3-green)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy_Me_a_Coffee-FFDD00?logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/megumu)

> :jp: [日本語](README.md)

## :sparkles: Features

- **PDF to Markdown** — Converts paper PDFs to Markdown while preserving section structure
- **Japanese translation** — Translates body text to Japanese (section headings remain in English)
- **Figure extraction** — Auto-detects raster and vector figures using DocLayout-YOLO, merges with captions, and embeds in Markdown
- **Structured summary** — Generates a structured summary with one-line overview, section summaries, and keywords
- **PDF export** — Outputs both translation and summary as PDF (CJK line-break aware)
- **Batch processing** — Supports processing multiple PDFs at once
- **Flexible input** — Accepts file paths or natural language descriptions

## :package: Output

```
<same directory as PDF>/<paper title>/
├── images/                 — Figures extracted from the PDF
├── paper.md                — Original Markdown conversion (English, with figures)
├── paper.ja.md             — Japanese translation (headings in English, with figures)
├── paper.summary.ja.md     — Structured summary in Japanese
├── paper.ja.pdf            — Japanese translation as PDF
└── paper.summary.ja.pdf    — Japanese summary as PDF
```

## :wrench: Installation

### 1. Clone this repository

```bash
git clone https://github.com/Davinci-Meg/paper-translator-en2ja.git
```

### 2. Register as a Claude Code skill

Copy `SKILL.md` to the Claude Code custom skill directory:

```bash
# macOS / Linux
mkdir -p ~/.claude/commands/paper-translate
cp SKILL.md ~/.claude/commands/paper-translate/SKILL.md

# Windows (PowerShell)
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\commands\paper-translate"
Copy-Item SKILL.md "$env:USERPROFILE\.claude\commands\paper-translate\SKILL.md"
```

### 3. Install dependencies

**Python libraries (for figure extraction)**

```bash
pip install doclayout-yolo pdf2image Pillow huggingface_hub
```

**poppler (required by pdf2image)**

| OS | Command |
|---|---|
| Windows | Download [poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases) and add to PATH |
| macOS | `brew install poppler` |
| Linux | `sudo apt install poppler-utils` |

**PDF conversion engine (for PDF output)**

- Install [pandoc](https://pandoc.org/installing.html)
- Install a TeX distribution with lualatex:

| OS | Command |
|---|---|
| Windows | Install [MiKTeX](https://miktex.org/) |
| macOS | `brew install --cask mactex` |
| Linux | `sudo apt install texlive-luatex texlive-lang-japanese` |

## :rocket: Usage

Launch Claude Code and run `/paper-translate`:

```
/paper-translate ~/Downloads/attention_is_all_you_need.pdf
/paper-translate path/to/papers/
```

## :gear: Requirements

| Item | Requirement |
|---|---|
| Claude Code | Latest version |
| Python | 3.10+ |
| doclayout-yolo | Latest |
| pdf2image | Latest |
| poppler | Latest |
| pandoc | 2.x+ |
| TeX engine | lualatex (recommended) or xelatex |
| Japanese font | Yu Gothic (Win) / Hiragino (Mac) / Noto CJK (Linux) |

## :building_construction: How It Works

1. **Step 0** — Identify PDF files and create output folder
2. **Step 1** — Extract figures from PDF (`DocLayout-YOLO Hybrid`)
3. **Step 2** — Convert PDF to Markdown with section structure
4. **Step 3** — Translate to Japanese (keep headings in English)
5. **Step 4** — Generate structured summary
6. **Step 5** — Generate PDFs via pandoc + lualatex
7. **Step 6** — Final verification and completion report

## :file_folder: File Structure

```
paper-translator-en2ja/
├── SKILL.md    — Claude Code skill definition (main logic)
├── LICENSE     — AGPL-v3
└── README.md   — This file
```

## :scroll: License

[GNU Affero General Public License v3.0](LICENSE)
