import os
import re
import sys
import argparse
import markdown
import subprocess
from datetime import datetime
from playwright.sync_api import sync_playwright

# 強制控制台輸出為 UTF-8
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# --- 配置區 ---
BASE_PATH = r"C:\Users\folow\.openclaw\workspace\downloads"
HISTORY_FILE = os.path.join(BASE_PATH, "paper_history.md")
TEMP_TASK = os.path.join(BASE_PATH, "temp_task.md")
TEMP_RESULT = os.path.join(BASE_PATH, "temp_result.md")
SUMMARY_FILE = os.path.join(BASE_PATH, "paper_summary.md")
OUTPUT_HTML = "index.html" 
REPO_PATH = os.getcwd()

GITHUB_REMOTE_URL = "https://github.com/hoomie-studio/readpaper.git"
JOURNAL_URL = "https://www.mdpi.com/journal/remotesensing"
MAX_ARTICLES = 1

def ensure_directory_exists():
    if not os.path.exists(BASE_PATH):
        os.makedirs(BASE_PATH)

def reformat_markdown_by_keywords(raw_text):
    """
    使用正則表達式抓取關鍵字並強制重構格式
    """
    # 定義抓取模式
    patterns = {
        "title_en": r"(?:文獻名稱|##)\s*(.*?)\n",
        "title_cn": r"文獻中文名稱\s*[:：]\s*(.*?)\n",
        "url": r"論文來源URL\s*[:：]\s*(.*?)\n",
        "core": r"一句話核心\s*[:：]?\s*(.*?)(?=\n(?:##|###|為什麼要研究這個|他們做了什麼|驚人發現|這對我有什麼意義)|$)",
        "why": r"為什麼要研究這個？\s*（研究動機）\s*[:：]?\s*(.*?)(?=\n(?:##|###|他們做了什麼|驚人發現|這對我有什麼意義)|$)",
        "how": r"他們做了什麼？\s*（研究方法）\s*[:：]?\s*(.*?)(?=\n(?:##|###|驚人發現|這對我有什麼意義)|$)",
        "discovery": r"驚人發現與具體數據\s*[:：]?\s*(.*?)(?=\n(?:##|###|這對我有什麼意義)|$)",
        "value": r"這對我有什麼意義？\s*（應用價值）\s*[:：]?\s*(.*?)(?=\n(?:##|###)|$)"
    }

    data = {}
    for key, p in patterns.items():
        match = re.search(p, raw_text, re.S | re.I)
        data[key] = match.group(1).strip() if match else "資訊未擷取"

    # 強制重構為標準 Markdown 格式，確保存入檔案時擁有正確的 MD 符號
    new_md = f"## {data['title_en']}\n\n"
    new_md += f"## 文獻中文名稱：{data['title_cn']}\n\n"
    new_md += f"- 論文來源URL: {data['url']}\n"
    new_md += f"- 抓取時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    new_md += f"### 一句話核心\n{data['core']}\n\n"
    new_md += f"### 為什麼要研究這個？（研究動機）\n{data['why']}\n\n"
    new_md += f"### 他們做了什麼？（研究方法）\n{data['how']}\n\n"
    new_md += f"### 驚人發現與具體數據\n{data['discovery']}\n\n"
    new_md += f"### 這對我有什麼意義？（應用價值）\n{data['value']}\n"
    
    return new_md

def git_push_auto():
    try:
        os.chdir(REPO_PATH)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"Auto-Update: {datetime.now().strftime('%m-%d %H:%M')}"], check=True)
        # 先拉取遠端變更，解決 push rejected 問題
        subprocess.run(["git", "pull", "origin", "main", "--rebase"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("[Git] Push success.")
    except Exception as e:
        print(f"[Git Error] Push failed: {e}")

def mode_render():
    if not os.path.exists(SUMMARY_FILE):
        print("[!] Summary file not found.")
        return

    with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # 以分隔線或歸檔標記切分
    articles = re.split(r'\n---\n|# 歸檔時間:', content)
    slides_html = ""

    for art in articles:
        if len(art.strip()) < 50: continue
        
        # 轉換為 HTML
        art_html = markdown.markdown(art, extensions=['tables', 'fenced_code'])
        slides_html += f'<div class="swiper-slide"><div class="card">{art_html}</div></div>'

    full_html = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Humankind Paper Gallery</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css" />
        <style>
            :root {{ --bg: #050505; --text: #ffffff; --accent: #00d4ff; }}
            body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; margin: 0; overflow: hidden; }}
            .swiper {{ width: 100vw; height: 100vh; }}
            .swiper-slide {{ display: flex; align-items: center; justify-content: center; padding: 5vw; box-sizing: border-box; }}
            .card {{ max-width: 900px; width: 100%; max-height: 85vh; overflow-y: auto; background: rgba(255,255,255,0.05); padding: 40px; border-radius: 20px; backdrop-filter: blur(15px); border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 20px 50px rgba(0,0,0,0.5); }}
            h2 {{ color: var(--accent); font-size: 2rem; margin-bottom: 0.5em; }}
            h3 {{ color: #ff9f43; margin-top: 1.5em; border-left: 4px solid #ff9f43; padding-left: 15px; background: rgba(255,159,67,0.05); padding-top: 5px; padding-bottom: 5px; }}
            p, li {{ line-height: 1.7; opacity: 0.85; font-size: 1.05rem; }}
            table {{ width: 100%; border-collapse: collapse; margin: 1.5em 0; background: rgba(0,0,0,0.2); }}
            th, td {{ border: 1px solid rgba(255,255,255,0.1); padding: 12px; text-align: left; }}
            th {{ background: rgba(0,212,255,0.1); color: var(--accent); }}
            .card::-webkit-scrollbar {{ width: 6px; }}
            .card::-webkit-scrollbar-thumb {{ background: var(--accent); border-radius: 10px; }}
        </style>
    </head>
    <body>
        <div class="swiper"><div class="swiper-wrapper">{slides_html}</div></div>
        <script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>
        <script>
            const swiper = new Swiper('.swiper', {{
                mousewheel: true, keyboard: true, grabCursor: true, speed: 800,
                freeMode: false, centeredSlides: true
            }});
        </script>
    </body>
    </html>"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"[Render] {OUTPUT_HTML} updated with Humankind style.")
    git_push_auto()

def mode_merge():
    target_file = TEMP_RESULT if os.path.exists(TEMP_RESULT) else TEMP_TASK
    if not os.path.exists(target_file):
        print("[!] No files to merge.")
        return

    with open(target_file, "r", encoding="utf-8") as f:
        raw_content = f.read()

    # 核心修改：先解析並強制重構格式
    formatted_content = reformat_markdown_by_keywords(raw_content)

    with open(SUMMARY_FILE, "a", encoding="utf-8") as sf:
        sf.write(f"\n\n---\n# 歸檔時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        sf.write(formatted_content)

    for f in [TEMP_TASK, TEMP_RESULT]:
        if os.path.exists(f): os.remove(f)
            
    print("[Merge] Success. Auto-rendering...")
    mode_render()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["merge", "render"], default="merge")
    args = parser.parse_args()

    ensure_directory_exists()
    if args.mode == "merge":
        mode_merge()
    elif args.mode == "render":
        mode_render()
       # python paperbot_v3.py --mode render