# :page_facing_up: paper-translator-en2ja

英語論文（PDF）を日本語に翻訳し、図版付きで出力する Claude Code スキル。

![Claude Code](https://img.shields.io/badge/Claude_Code-Skill-blueviolet?logo=anthropic)
![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![License](https://img.shields.io/badge/License-AGPL--v3-green)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy_Me_a_Coffee-FFDD00?logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/megumu)

> :us: [English](README.en.md)

## :sparkles: 特徴

- **PDF → Markdown 変換** — セクション構造を保ったまま論文PDFをMarkdownに変換
- **日本語翻訳** — 本文を日本語に翻訳（セクション見出しは英語のまま保持）
- **図表の自動抽出** — DocLayout-YOLO でラスター・ベクター図版を自動検出し、キャプションと統合して切り抜き
- **構造化サマリー** — 一言まとめ・セクション要約・キーワードを含むサマリーを生成
- **PDF出力** — 翻訳・サマリーをそれぞれPDFとして出力（CJK改行対応）
- **一括処理** — 複数PDFの一括処理に対応
- **柔軟な入力** — ファイルパス指定でも自然言語でも動作

## :package: 出力

```
<PDFと同じディレクトリ>/<論文タイトル>/
├── images/                 — PDFから抽出した図表画像
├── paper.md                — 原文の Markdown 変換（英語・画像埋め込み）
├── paper.ja.md             — 日本語翻訳（見出しは英語保持・画像埋め込み）
├── paper.summary.ja.md     — 日本語の構造化サマリー
├── paper.ja.pdf            — 日本語翻訳の PDF 版
└── paper.summary.ja.pdf    — 日本語サマリーの PDF 版
```

## :wrench: インストール

### 1. リポジトリをクローン

```bash
git clone https://github.com/Davinci-Meg/paper-translator-en2ja.git
```

### 2. Claude Code のスキルとして登録

`SKILL.md` をカスタムスキルディレクトリに配置する：

```bash
# macOS / Linux
mkdir -p ~/.claude/commands/paper-translate
cp SKILL.md ~/.claude/commands/paper-translate/SKILL.md

# Windows (PowerShell)
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\commands\paper-translate"
Copy-Item SKILL.md "$env:USERPROFILE\.claude\commands\paper-translate\SKILL.md"
```

### 3. 依存関係のインストール

**Python ライブラリ（図版抽出に必要）**

```bash
pip install doclayout-yolo pdf2image Pillow huggingface_hub
```

**poppler（pdf2image の依存）**

| OS | コマンド |
|---|---|
| Windows | [poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases) をダウンロードしPATHに追加 |
| macOS | `brew install poppler` |
| Linux | `sudo apt install poppler-utils` |

**PDF 変換エンジン（PDF 出力に必要）**

- [pandoc](https://pandoc.org/installing.html) をインストール
- lualatex を含む TeX ディストリビューションをインストール：

| OS | コマンド |
|---|---|
| Windows | [MiKTeX](https://miktex.org/) をインストール |
| macOS | `brew install --cask mactex` |
| Linux | `sudo apt install texlive-luatex texlive-lang-japanese` |

## :rocket: 使い方

Claude Code を起動して `/paper-translate` を実行：

```
/paper-translate ~/Downloads/attention_is_all_you_need.pdf
/paper-translate DownloadsフォルダのAttention is All You Needの論文
/paper-translate ~/papers/ 内のPDFを全部
```

## :gear: 動作環境

| 項目 | 要件 |
|---|---|
| Claude Code | 最新版 |
| Python | 3.10 以上 |
| doclayout-yolo | 最新版 |
| pdf2image | 最新版 |
| poppler | 最新版 |
| pandoc | 2.x 以上 |
| TeX エンジン | lualatex（推奨）または xelatex |
| 日本語フォント | Yu Gothic (Win) / Hiragino (Mac) / Noto CJK (Linux) |

## :building_construction: 処理フロー

1. **Step 0** — PDFファイルの特定と出力フォルダの作成
2. **Step 1** — PDFから図版を抽出 (`DocLayout-YOLO Hybrid`)
3. **Step 2** — PDFをセクション構造付きMarkdownに変換
4. **Step 3** — 日本語に翻訳（見出しは英語保持）
5. **Step 4** — 構造化サマリーを生成
6. **Step 5** — pandoc + lualatex で PDF を生成
7. **Step 6** — 最終確認と完了報告

## :file_folder: ファイル構成

```
paper-translator-en2ja/
├── SKILL.md       — Claude Code スキル定義（メインロジック）
├── LICENSE        — AGPL-v3
├── README.md      — このファイル（日本語）
└── README.en.md   — English README
```

## :scroll: ライセンス

[GNU Affero General Public License v3.0](LICENSE)
