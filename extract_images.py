#!/usr/bin/env python3
"""
extract_images.py  —  PDF から画像を抽出し、Markdown の Figure 参照に挿入する

使い方:
  python extract_images.py <pdf_path> <output_dir>

出力:
  <output_dir>/images/   に画像ファイルを保存
  stdout に JSON で { "figures": [ { "label": "Figure 1", "file": "images/fig1.png", "page": 1, "caption": "..." }, ... ] }
"""

import sys
import os
import json
import re
import fitz  # PyMuPDF


MIN_WIDTH  = 80   # px: これより小さい画像は装飾とみなしてスキップ
MIN_HEIGHT = 80


def estimate_width_pct(display_rect: fitz.Rect, page_rect: fitz.Rect) -> int:
    """
    PDF上での画像の表示幅をページ幅に対する % で返す。
    5% 単位に丸める（例: 43% → 45%）。
    最小 20%、最大 95% にクランプ。
    """
    if page_rect.width == 0:
        return 80
    ratio = display_rect.width / page_rect.width
    pct = round(ratio * 100 / 5) * 5   # 5% 単位に丸め
    return max(20, min(95, pct))


def extract_images(pdf_path: str, output_dir: str) -> list[dict]:
    """
    PDF から画像を抽出し images/ に保存。
    各画像の表示サイズ（ページ幅比 %）も記録する。
    """
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    doc = fitz.open(pdf_path)
    extracted = []
    seen_xrefs = set()

    for page_num, page in enumerate(doc, start=1):
        img_list = page.get_images(full=True)
        page_rect = page.rect
        page_counter = 0

        for img_info in img_list:
            xref = img_info[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)

            try:
                pix = fitz.Pixmap(doc, xref)

                # CMYK → RGB 変換
                if pix.n > 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)

                # サイズフィルタ
                if pix.width < MIN_WIDTH or pix.height < MIN_HEIGHT:
                    continue

                # PDF 上での表示領域を取得
                rects = page.get_image_rects(xref)
                if rects:
                    display_rect = rects[0]  # 最初の配置箇所
                    width_pct = estimate_width_pct(display_rect, page_rect)
                else:
                    width_pct = 80  # 取得できない場合のデフォルト

                page_counter += 1
                filename = f"page{page_num:02d}_{page_counter:02d}.png"
                filepath = os.path.join(images_dir, filename)
                pix.save(filepath)

                extracted.append({
                    "file": os.path.join("images", filename).replace("\\", "/"),
                    "page": page_num,
                    "width": pix.width,
                    "height": pix.height,
                    "width_pct": width_pct,
                    "xref": xref,
                })
            except Exception as e:
                sys.stderr.write(f"[WARN] xref={xref} page={page_num}: {e}\n")

    doc.close()
    return extracted


def extract_text_by_page(pdf_path: str) -> dict[int, str]:
    """ページごとのテキストを返す。"""
    doc = fitz.open(pdf_path)
    result = {}
    for page_num, page in enumerate(doc, start=1):
        result[page_num] = page.get_text()
    doc.close()
    return result


def find_captions(page_texts: dict[int, str]) -> list[dict]:
    """
    行頭の "Figure N:" / "Fig. N." パターンのみをキャプションとして検索。
    本文中のインライン参照（"...see Figure 3."）は除外する。
    """
    # 行頭または改行直後に現れる Figure N: / Figure N. のみを対象
    pattern = re.compile(
        r'(?:^|\n)(Figure\s+(\d+)|Fig\.\s*(\d+))[:\.\s]+([^\n]{5,160})',
        re.IGNORECASE
    )
    results = []
    seen = set()
    for page_num, text in page_texts.items():
        for m in pattern.finditer(text):
            num = m.group(2) or m.group(3)
            caption_text = m.group(4).strip()
            key = f"Figure {num}"
            # 本文中の参照っぽいものを除外:
            # キャプションは通常10文字以上・動詞や名詞で始まる
            # セクション番号で始まる場合はスキップ（例: "3.3 System Design"）
            if re.match(r'^\d+\.\d+', caption_text):
                continue
            # 短すぎる or "Figure" で再び始まる場合はスキップ
            if len(caption_text) < 8 or caption_text.lower().startswith("figure"):
                continue
            if key not in seen:
                seen.add(key)
                results.append({
                    "label": key,
                    "caption": caption_text,
                    "page": page_num,
                })
    results.sort(key=lambda x: int(re.search(r'\d+', x['label']).group()))
    return results


def assign_images_to_figures(
    images: list[dict],
    captions: list[dict],
) -> list[dict]:
    """
    各 Figure キャプションに最も近いページの画像を割り当てる。
    同じ画像が複数の Figure に使われないよう管理する。
    """
    used = set()
    figures = []

    for cap in captions:
        cap_page = cap["page"]
        # キャプションと同じページ、または前後1ページ以内の画像を候補に
        candidates = [
            img for img in images
            if abs(img["page"] - cap_page) <= 1 and img["xref"] not in used
        ]
        if not candidates:
            # 範囲を広げる
            candidates = [img for img in images if img["xref"] not in used]

        if candidates:
            # キャプションページとの距離が最小のものを選択（同距離ならサイズ優先）
            best = min(
                candidates,
                key=lambda img: (abs(img["page"] - cap_page), -img["width"] * img["height"])
            )
            used.add(best["xref"])
            figures.append({
                "label": cap["label"],
                "caption": cap["caption"],
                "page": cap["page"],
                "file": best["file"],
                "width": best["width"],
                "height": best["height"],
                "width_pct": best.get("width_pct", 80),
            })
        else:
            figures.append({
                "label": cap["label"],
                "caption": cap["caption"],
                "page": cap["page"],
                "file": None,
            })

    return figures


def insert_figures_into_markdown(md_path: str, figures: list[dict]) -> None:
    """
    paper.md / paper.ja.md の Figure 参照箇所の後ろに
    ![Figure N: caption](images/...) を挿入する。

    - 英語 Markdown: "Figure N" を検索
    - 日本語 Markdown: "図N"（全角・半角数字両対応）を検索
    - キャプション行（行末が図のタイトルで終わる行）も検索対象
    - すでに挿入済みの場合はスキップ
    """
    with open(md_path, encoding="utf-8") as f:
        content = f.read()

    for fig in figures:
        if fig["file"] is None:
            continue

        label = fig["label"]       # e.g. "Figure 1"
        img_path = fig["file"]     # e.g. "images/page01_01.png"
        width_pct = fig.get("width_pct", 80)
        alt = f'{label}: {fig["caption"]}'
        # pandoc の画像サイズ指定: ![alt](path){ width=X% }
        img_md = f'\n\n![{alt}]({img_path}){{width={width_pct}%}}\n'

        # すでに挿入済みならスキップ
        if img_path in content:
            continue

        num = re.search(r'\d+', label).group()  # "1"

        # 検索パターン: 英語 "Figure N" または 日本語 "図N"（段落末尾の行）
        patterns = [
            # 英語: "Figure N" を含む段落（行）の終端
            re.compile(rf'([^\n]*\bFigure\s*{num}\b[^\n]*\n)', re.IGNORECASE),
            # 日本語: 「図N」を含む段落の終端
            re.compile(rf'([^\n]*図\s*{num}[^\n]*\n)'),
        ]

        best_pos = None
        for pat in patterns:
            match = pat.search(content)
            if match:
                # 最初のヒット位置の段落末尾に挿入
                # ただし直後が空行・見出し・箇条書きでない場所を優先
                pos = match.end()
                # 連続する空行をスキップして段落区切りの後ろに挿入
                while pos < len(content) and content[pos] == '\n':
                    pos += 1
                best_pos = match.end()
                break

        if best_pos is not None:
            content = content[:best_pos] + img_md + content[best_pos:]
        else:
            sys.stderr.write(f"[WARN] {label} の挿入位置が見つかりませんでした: {md_path}\n")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <pdf_path> <output_dir>", file=sys.stderr)
        sys.exit(1)

    pdf_path   = sys.argv[1]
    output_dir = sys.argv[2]

    print(f"[1/3] 画像を抽出中: {pdf_path}", file=sys.stderr)
    images = extract_images(pdf_path, output_dir)
    print(f"      {len(images)} 枚の画像を抽出しました", file=sys.stderr)

    print("[2/3] Figure キャプションを検索中...", file=sys.stderr)
    page_texts = extract_text_by_page(pdf_path)
    captions   = find_captions(page_texts)
    print(f"      {len(captions)} 個のキャプションを検出しました", file=sys.stderr)

    figures = assign_images_to_figures(images, captions)

    print("[3/3] Markdown に画像参照を挿入中...", file=sys.stderr)
    for md_file in ["paper.md", "paper.ja.md"]:
        md_path = os.path.join(output_dir, md_file)
        if os.path.exists(md_path):
            insert_figures_into_markdown(md_path, figures)
            print(f"      {md_file} を更新しました", file=sys.stderr)

    # 結果を JSON で出力
    print(json.dumps({"figures": figures}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
