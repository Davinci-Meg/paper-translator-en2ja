---
name: paper-translate
description: 英語論文（PDF）を日本語に翻訳・要約するスキル。1ファイルでも複数ファイルでも対応。PDFのMarkdown変換・日本語翻訳・構造化サマリー生成・PDF出力を一括で行い、論文タイトル名のフォルダにまとめて保存する。「論文を翻訳して」「英語の論文を日本語にして」「PDFを要約して」「DownloadsにあるXXXの論文を翻訳して」「○○フォルダ内のPDFを全部翻訳して」など、論文・PDF翻訳・要約に関する依頼があれば必ずこのスキルを使うこと。他のスキルへの依存なし。
---

# paper-translate

英語論文のPDFを受け取り、**論文タイトル名のフォルダ**を作成して以下のファイルを格納するスキル。1ファイルでも複数ファイルでも動作する。

```
<出力先>/<論文タイトル>/
├── images/                 — PDFから抽出した図表画像
├── paper.md                — 原文のMarkdown変換（英語・画像埋め込み）
├── paper.ja.md             — 日本語翻訳（本文のみ翻訳、見出しは英語保持・画像埋め込み）
├── paper.summary.ja.md     — 日本語の構造化サマリー
├── paper.ja.pdf            — 日本語翻訳のPDF版（画像・CJK改行対応）
└── paper.summary.ja.pdf    — 日本語サマリーのPDF版
```

---

## 起動方法

1ファイル・複数ファイル・フォルダ指定、いずれもパスでも自然言語でも指定できる：

```
/paper-translate ~/Downloads/attention_is_all_you_need.pdf
/paper-translate DownloadsフォルダのAttention is All You Needの論文
/paper-translate ~/papers/ 内のPDFを全部
/paper-translate デスクトップのpapers フォルダにあるPDFら
```

---

## 実行ステップ

### Step 0: 対象PDFファイルの特定

入力を解釈して、処理対象のPDFファイルリストを作成する。

**単一ファイルの場合:**
- ファイル名・場所・論文タイトルのキーワードから候補を探す
- `find` コマンドや `ls` で該当ディレクトリを検索する
- 候補が複数ある場合はユーザーに確認する

**フォルダ・複数ファイルの場合:**
- `find <ディレクトリ> -name "*.pdf"` でPDFを列挙する
- 処理対象のファイル一覧をユーザーに提示し、確認を取ってから処理を開始する
- 例: 「以下の3件を処理します。よろしいですか？」

処理対象が確定したら、各PDFに対して **Step 1〜5 を順番に繰り返す**。

---

以下の Step 1〜5 は、対象PDFが1件の場合はそのまま実行。複数件の場合は各PDFごとに繰り返す。

---

### Step 1: 出力フォルダの作成

1. PDFを開いて論文タイトルを取得する。
2. タイトルをフォルダ名として使用する。フォルダ名のルール：
   - ファイルシステムで使えない文字（`/`, `:`, `*`, `?`, `"`, `<`, `>`, `|`）はアンダースコアに置換
   - 長すぎる場合は先頭100文字に切り詰める
3. PDFと同じディレクトリに `<論文タイトル>/` フォルダを作成する。
4. 以降の全ファイルはこのフォルダ内に保存する。出力パスを `<出力フォルダ>` とする。

### Step 1.5: PDFから図版を抽出（`<出力フォルダ>/images/`）

DocLayout-YOLO Hybrid 方式で図版を抽出する。この方式はラスター画像だけでなく、ベクター図版（PDF描画命令で構成された図）も抽出できる。

#### パイプライン概要

```
入力PDF
  → pdf2image (300dpi) でページ画像化
  → DocLayout-YOLO で figure / figure_caption を検出
  → figure + caption 統合ロジック
  → Pillow で切り抜き + padding
  → 出力画像 + meta.json
```

#### 抽出コード

以下のPythonスクリプトを `<出力フォルダ>/extract_figures.py` として作成・実行する：

```python
import json
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image

def load_model():
    from doclayout_yolo import YOLOv10
    import huggingface_hub
    model_path = huggingface_hub.hf_hub_download(
        "juliozhao/DocLayout-YOLO-DocStructBench",
        "doclayout_yolo_docstructbench_imgsz1024.pt",
    )
    return YOLOv10(model_path)

def merge_figure_and_caption(figures, captions, margin=15):
    merged = []
    used_captions = set()
    for fig in figures:
        fb = fig["bbox"]
        best_cap = None
        best_dist = float("inf")
        for i, cap in enumerate(captions):
            if i in used_captions:
                continue
            cb = cap["bbox"]
            dist = abs(cb[1] - fb[3])
            x_overlap = min(fb[2], cb[2]) - max(fb[0], cb[0])
            if x_overlap > 0 and dist < best_dist and dist < 400:
                best_dist = dist
                best_cap = (i, cap)
        if best_cap:
            i, cap = best_cap
            used_captions.add(i)
            cb = cap["bbox"]
            merged_bbox = [
                min(fb[0], cb[0]) - margin, min(fb[1], cb[1]) - margin,
                max(fb[2], cb[2]) + margin, max(fb[3], cb[3]) + margin,
            ]
        else:
            merged_bbox = [fb[0] - margin, fb[1] - margin, fb[2] + margin, fb[3] + margin]
        merged.append({
            "bbox": merged_bbox, "figure_bbox": fb,
            "caption_bbox": best_cap[1]["bbox"] if best_cap else None,
            "confidence": fig["confidence"],
        })
    return merged

def extract_figures(pdf_path, output_dir):
    pdf_path = Path(pdf_path)
    images_dir = Path(output_dir) / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # PDF → ページ画像
    pages = convert_from_path(str(pdf_path), dpi=300)
    page_dir = Path(output_dir) / "_pages"
    page_dir.mkdir(exist_ok=True)
    page_paths = []
    for i, page in enumerate(pages):
        p = page_dir / f"page_{i+1:03d}.png"
        page.save(str(p), "PNG")
        page_paths.append(p)

    # YOLO で検出・切り抜き
    model = load_model()
    fig_index = 0
    img_meta = {}

    for page_num, page_path in enumerate(page_paths):
        det = model.predict(str(page_path), imgsz=1024, conf=0.2)
        results = det[0]
        boxes = results.boxes
        names = results.names

        figures = []
        captions = []
        for i in range(len(boxes)):
            cls_name = names[int(boxes.cls[i])]
            conf = float(boxes.conf[i])
            bbox = [int(v) for v in boxes.xyxy[i].tolist()]
            if cls_name == "figure":
                figures.append({"bbox": bbox, "confidence": conf})
            elif cls_name == "figure_caption":
                captions.append({"bbox": bbox, "confidence": conf})

        if not figures:
            continue

        merged = merge_figure_and_caption(figures, captions)
        img = Image.open(page_path)
        w, h = img.size
        page_width = w

        for m in merged:
            fig_index += 1
            bbox = [max(0, m["bbox"][0]), max(0, m["bbox"][1]),
                    min(w, m["bbox"][2]), min(h, m["bbox"][3])]
            cropped = img.crop(bbox)

            # 表示幅の割合を計算
            fig_bbox = m["figure_bbox"]
            fig_width = fig_bbox[2] - fig_bbox[0]
            width_pct = round(fig_width / page_width * 100)
            width_pct = max(20, min(width_pct, 100))

            filename = f"figure_{fig_index}.png"
            cropped.save(str(images_dir / filename), "PNG")
            img_meta[filename] = {
                "width_pct": width_pct,
                "page": page_num + 1,
                "confidence": m["confidence"],
            }
            print(f"Page {page_num+1}: {filename} ({cropped.size[0]}x{cropped.size[1]}, width={width_pct}%, conf={m['confidence']:.3f})")

    # メタデータを保存
    with open(str(images_dir / "meta.json"), "w") as f:
        json.dump(img_meta, f, indent=2)

    # 一時ページ画像を削除
    import shutil
    shutil.rmtree(page_dir)

    print(f"Extracted {fig_index} figures")
    return img_meta

if __name__ == "__main__":
    import sys
    extract_figures(sys.argv[1], sys.argv[2])
```

#### 実行方法

```bash
python "<出力フォルダ>/extract_figures.py" "<PDFパス>" "<出力フォルダ>"
```

#### 必要なパッケージ

事前に以下がインストールされている必要がある：

```bash
pip install doclayout-yolo pdf2image Pillow huggingface_hub
```

また、`pdf2image` は `poppler` に依存する：
- Windows: [poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases) をダウンロードし、PATHに追加
- macOS: `brew install poppler`
- Linux: `sudo apt install poppler-utils`

#### 検出の仕組み

1. **pdf2image** でPDFを300dpiのページ画像に変換（ベクター図版もラスタライズされる）
2. **DocLayout-YOLO** が各ページから `figure` と `figure_caption` のバウンディングボックスを検出（conf≥0.2）
3. **統合ロジック** で各figureに最も近いcaption（縦距離400px以内かつ横方向重複あり）をマッチし、包含bboxを作成
4. **Pillow** で切り抜き（padding 15px）、PNG形式で保存
5. **meta.json** に各画像の `width_pct`（ページ幅に対する表示幅比率）、ページ番号、検出信頼度を記録

#### フォールバック

`doclayout-yolo` または `pdf2image` が未インストールの場合は、ユーザーにインストールを案内する。インストールできない環境では画像なしで続行し、プレースホルダー `[図N]` を使用する。

### Step 2: PDFをMarkdownに変換（`<出力フォルダ>/paper.md`）

1. `<出力フォルダ>/paper.md` を新規作成する。
2. PDFを読んでセクション構造をMarkdown形式でファイルに出力する。セクション番号はPDFの番号に従うこと。
3. セクションごとに「このセクションの内容をMarkdown形式に変換し、Markdownファイルの該当のセクションの部分に挿入する。段落ごとに空白行で区切ること。」というサブタスクを生成する。
4. 生成したサブタスクを順番に実行する。
5. **画像の埋め込み**: PDFで `Figure N:` として参照されている箇所に、Step 1.5 で抽出した対応画像をMarkdown画像記法で埋め込む。`images/meta.json` から `width_pct` を読み取り、`{width=X%}` 属性を付与する：
   ```markdown
   ![Figure 1: キャプション文](images/figure_1.jpeg){width=70%}
   ```
   - 画像は必ずキャプション付きで挿入する。キャプションはPDFの原文に従う。
   - `{width=X%}` は `meta.json` の値をそのまま使う。`meta.json` がない場合は `{width=80%}` をデフォルトとする。
   - 画像が抽出できなかった場合のみ `[Figure N: キャプション]` のプレースホルダーを使用する。
6. 全てのセクションを1つずつ確認し、空白のセクションがないかを確認する。空白のセクションがあれば修正する。
7. `pnpx markdownlint-cli2 <出力フォルダ>/paper.md` を実行してフォーマットをチェックし、エラーがあれば修正する。

### Step 3: MarkdownをJapanese翻訳（`<出力フォルダ>/paper.ja.md`）

1. `<出力フォルダ>/paper.md` を読み込む。
2. ファイル全体をセクションごとに分割する。
3. 各セクションのタイトル（見出し行）は翻訳せず英語のまま保持する。
4. 各セクションの本文だけを英語から日本語に翻訳する。
   - Markdownの構造（見出し階層、箇条書き、コードブロック、表）はそのまま維持する。
   - 表や図表キャプションも本文に含まれる場合は日本語に翻訳する。
   - **画像参照はそのまま保持する**: `![Figure N: ...](images/figure_N.ext){width=X%}` の行はそのまま維持する（`{width=X%}` 属性も保持すること）。キャプション部分のみ日本語に翻訳してもよい（例: `![図1: 日本語キャプション](images/figure_1.jpeg){width=70%}`）。
5. `<出力フォルダ>/paper.ja.md` として保存する。
6. 全てのセクションを確認し、空欄や未翻訳の部分がないかチェックし修正する。
7. `pnpx markdownlint-cli2 <出力フォルダ>/paper.ja.md` を実行してフォーマットをチェックし、エラーがあれば修正する。

### Step 4: サマリー生成（`<出力フォルダ>/paper.summary.ja.md`）

`<出力フォルダ>/paper.ja.md` を読み込み、以下の構造で `<出力フォルダ>/paper.summary.ja.md` を作成する。

```markdown
# <論文タイトル（英語）> — 要約

## 基本情報
- **著者**: ...
- **発表年**: ...
- **掲載**: ...（学会・ジャーナル名）
- **原文**: <PDFパス>

## 一言まとめ
（1〜2文で論文の核心を説明）

## 背景・課題
（この研究が解こうとした問題）

## 提案手法
（何を・どうやって解決したか）

## 主な結果
（定量的な結果、ベースラインとの比較など）

## 貢献・意義
（この論文のインパクト・新規性）

## 限界・今後の課題
（著者が認めている制限や残課題）

## キーワード
`keyword1`, `keyword2`, ...
```

**注意**: `原文` のパスにバックスラッシュが含まれる場合（Windows）、バッククォートで囲むこと（例: `` `G:\path\to\file.pdf` ``）。LaTeX変換時にバックスラッシュがコマンドと誤解されるのを防ぐ。

### Step 5: PDF出力（`paper.ja.pdf` / `paper.summary.ja.pdf`）

`pandoc` を使って翻訳とサマリーをPDFに変換する。

#### 5-1: pandoc のインストール確認

```bash
pandoc --version
```

インストールされていない場合はユーザーに通知する：
> 「PDF出力にはpandocが必要です。https://pandoc.org/installing.html からインストールしてください。」
> 「インストール済みであれば再度お知らせください。MDファイルはすでに生成済みです。」

#### 5-2: 日本語フォント確認

```bash
# Windows
fc-list | grep -i "noto\|meiryo\|yu gothic\|ms gothic"

# macOS
fc-list | grep -i "noto\|hiragino"
```

利用可能なフォントを確認し、以下の優先順で使用する：

| OS | 優先フォント |
|----|------------|
| Windows | Yu Gothic, Meiryo, MS Gothic |
| macOS | Hiragino Sans, Hiragino Mincho |
| Linux | Noto Sans CJK JP, IPAexGothic |

#### 5-3: LaTeXヘッダーファイルの作成

CJK（日本語・中国語・韓国語）テキストの自動改行を正しく処理するため、`<出力フォルダ>/header.tex` を作成する：

```latex
\usepackage{luatexja}
\usepackage[match]{luatexja-fontspec}
\setmainjfont{<利用可能な日本語フォント>}
```

このヘッダーにより `luatexja` パッケージがロードされ、日本語テキストが自動的に正しい位置で改行される。

#### 5-4: PDF変換実行

**重要**: `--pdf-engine=lualatex` を使用すること。`xelatex` はCJK改行で問題が起きやすい。

```bash
# 翻訳PDFの生成
pandoc "<出力フォルダ>/paper.ja.md" \
  -o "<出力フォルダ>/paper.ja.pdf" \
  --pdf-engine=lualatex \
  -V mainfont="<利用可能なフォント>" \
  -V sansfont="<利用可能なフォント>" \
  -V monofont="<利用可能なフォント>" \
  -V geometry:margin=1in \
  -V fontsize=11pt \
  -H "<出力フォルダ>/header.tex"

# サマリーPDFの生成
pandoc "<出力フォルダ>/paper.summary.ja.md" \
  -o "<出力フォルダ>/paper.summary.ja.pdf" \
  --pdf-engine=lualatex \
  -V mainfont="<利用可能なフォント>" \
  -V sansfont="<利用可能なフォント>" \
  -V monofont="<利用可能なフォント>" \
  -V geometry:margin=1in \
  -V fontsize=11pt \
  -H "<出力フォルダ>/header.tex"
```

#### 5-5: LaTeXエスケープ問題への対処

Markdownの内容にLaTeXの特殊文字が含まれるとビルドが失敗することがある。よくある問題と対策：

| 問題 | 原因 | 対策 |
|------|------|------|
| `Undefined control sequence` at `\n` | テキスト中の `\n` がLaTeXコマンドとして解釈される | バッククォートで囲む: `` `\n` `` |
| `Undefined control sequence` at `\マ` 等 | Windowsパスのバックスラッシュ `\` | パスをバッククォートで囲む: `` `G:\path` `` |
| テーブルの列が見切れる | 列幅が固定されない | 簡素なテーブルに書き換えるか、長い行を折り返す |

ビルドエラーが出た場合は、エラーメッセージの行番号からMarkdown内の該当箇所を特定し、上記の対策を適用してリビルドする。

#### 5-6: 後片付け

PDF生成完了後、`<出力フォルダ>/header.tex` を削除する。

---

### Step 6: 完了報告

全件処理後に以下を出力する：

**単一ファイルの場合:**
```
✅ 完了

📁 <出力フォルダ>/
├── images/                 （抽出画像）
├── paper.md                （原文MD）
├── paper.ja.md             （翻訳MD）
├── paper.summary.ja.md     （サマリーMD）
├── paper.ja.pdf            （翻訳PDF）
└── paper.summary.ja.pdf    （サマリーPDF）
```

**複数ファイルの場合:**
```
✅ 3件完了

📁 Attention Is All You Need/
📁 BERT_Pre-training of Deep Bidirectional Transformers/
📁 GPT-3_Language Models are Few-Shot Learners/
```

---

## エラーハンドリング

| 状況 | 対応 |
|------|------|
| 自然言語からPDFを特定できない | 候補ファイルを列挙してユーザーに選択を求める |
| PDFが見つからない | パスを確認してユーザーに再入力を求める |
| 複数件処理中に1件失敗 | エラーを記録して残りの処理を続行し、最後にまとめて報告する |
| pandoc が未インストール | MDファイルは保存済みであることを伝え、インストール案内をする |
| lualatex が未インストール | `--pdf-engine=xelatex` にフォールバック（ただしCJK改行は手動で確認）。それも失敗したらMDのみで完了とする |
| 日本語フォントが見つからない | `Noto Sans CJK JP` のインストールを案内し、暫定的に `DejaVu Sans` で試みる |
| pymupdf / pdfimages が未インストール | 画像抽出をスキップし、プレースホルダー `[Figure N]` で続行する |
| 抽出画像が巨大（>5MB） | 品質を維持しつつリサイズ検討。ただしそのまま使用しても問題ない |
| LaTeXビルドエラー | エラーメッセージからMarkdown内の特殊文字を特定し、バッククォートで囲むなどして修正 |
| 非常に長い論文（50ページ超） | セクションごとに分割処理し、最後に結合する |
