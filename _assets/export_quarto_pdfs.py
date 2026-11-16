import os
import re
import glob
import fitz  # PyMuPDF
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Map Quarto subject folders -> Master PDF names expected by deploys6m5
SUBJECTS = {
    "1_Algebra": "S6M5_Algebra.pdf",
    "2_Geometry": "S6M5_Geometry.pdf",
    "3_Stochastics": "S6M5_Stochastics.pdf",
}

ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]

def build_subject_pdfs(book_dir="_book", target_base=None):
    if target_base is None:
        target_base = os.path.expanduser("~/Documents/Math Notes/Curriculum/S6M5_Quarto")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        for folder, master_pdf_name in SUBJECTS.items():
            html_files = sorted(glob.glob(os.path.join(book_dir, folder, "*", "*.html")))
            if not html_files:
                continue

            out_folder = os.path.join(target_base, folder)
            os.makedirs(out_folder, exist_ok=True)
            master_pdf_path = os.path.join(out_folder, master_pdf_name)

            merged_doc = fitz.open()
            toc_entries = []

            for idx, html_path in enumerate(html_files):
                abs_url = "file://" + os.path.abspath(html_path)
                page.goto(abs_url, wait_until="networkidle")
                # Give MathJax a brief moment to finish typesetting all equations
                page.wait_for_timeout(800)

                temp_pdf = html_path + ".tmp.pdf"
                page.pdf(
                    path=temp_pdf,
                    format="A4",
                    print_background=True,
                    margin={"top": "15mm", "bottom": "15mm", "left": "14mm", "right": "14mm"},
                )

                # Extract Chapter Title & ## Section Titles to build a clean PDF TOC
                with open(html_path, "r", encoding="utf-8") as f:
                    soup = BeautifulSoup(f.read(), "html.parser")

                h1 = soup.find("h1")
                chapter_title = h1.get_text(" ", strip=True) if h1 else f"Chapter {idx + 1}"
                h2_titles = [
                    h2.get_text(" ", strip=True)
                    for h2 in soup.select("main.content h2")
                    if not h2.find_parent(id="TOC")
                ]

                chap_doc = fitz.open(temp_pdf)
                start_page = len(merged_doc) + 1  # 1-based page number for PyMuPDF TOC

                # Level 1 bookmark matches split_sections.py's Part regex!
                roman_num = ROMAN[idx] if idx < len(ROMAN) else str(idx + 1)
                toc_entries.append([1, f"Part {roman_num}", start_page])

                # Find exact starting page of each numbered ## section inside this chapter
                # Find exact starting page of each numbered ## section inside this chapter
                for sec_title in h2_titles:
                    m = re.match(r"^(\d+)\.?\s+(.*)$", sec_title)
                    if not m:
                        continue
                    sec_num = int(m.group(1))
                    clean_name = f"{sec_num:02d} {m.group(2)}"
                    sec_page = start_page
                    for pno in range(len(chap_doc)):
                        if m.group(2)[:25] in chap_doc[pno].get_text():
                            sec_page = start_page + pno
                            break
                    toc_entries.append([2, clean_name, sec_page])


                merged_doc.insert_pdf(chap_doc)
                chap_doc.close()
                os.remove(temp_pdf)

            if len(merged_doc) > 0:
                merged_doc.set_toc(toc_entries)
                merged_doc.save(master_pdf_path)
                print(f"✅ Built {master_pdf_name} ({len(merged_doc)} pages) -> {out_folder}")
            merged_doc.close()

        browser.close()

if __name__ == "__main__":
    build_subject_pdfs()
