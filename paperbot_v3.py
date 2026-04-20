import os
import re
import time
import argparse
import markdown
import subprocess
from datetime import datetime
from playwright.sync_api import sync_playwright

# --- 配置區 ---
BASE_PATH = r"C:\Users\folow\.openclaw\workspace\downloads"
HISTORY_FILE = os.path.join(BASE_PATH, "paper_history.md")
TEMP_TASK = os.path.join(BASE_PATH, "temp_task.md")
TEMP_RESULT = os.path.join(BASE_PATH, "temp_result.md")
SUMMARY_FILE = os.path.join(BASE_PATH, "paper_summary.md")
OUTPUT_HTML = "index.html" 
REPO_PATH = os.getcwd()

JOURNAL_URL = "https://www.mdpi.com/journal/remotesensing"

def ensure_directory_exists():
    if not os.path.exists(BASE_PATH):
        os.makedirs(BASE_PATH)

# ==========================================
# 核心功能：格式校驗與自動修復
# ==========================================
def validate_and_fix_md(content):
    """檢查內容格式，並針對硬性標籤進行強制補齊或修正"""
    standard_headers = {
        "eng": "## 文獻名稱",
        "chi": "## 文獻中文名稱",
        "core": "### 一句話核心",
        "motive": "### 為什麼要研究這個？（研究動機）",
        "method": "### 他們做了什麼？（研究方法）",
        "result": "### 驚人發現與具體數據（關鍵結果）",
        "usage": "### 這對我有什麼意義？（實際應用）"
    }

    # 1. 物理修正常見變體
    content = content.replace("### 驚人發現", standard_headers["result"])
    content = content.replace("### 研究動機", standard_headers["motive"])
    content = content.replace("### 研究方法", standard_headers["method"])
    content = content.replace("### 實際應用", standard_headers["usage"])

    # 2. 硬性校驗關鍵標籤
    critical_tags = [standard_headers["eng"], standard_headers["core"]]
    for tag in critical_tags:
        if tag not in content:
            print(f"[Check Failed] Missing critical tag: {tag}")
            return None, False

    # 3. 自動補齊歸檔時間
    if "# 歸檔時間:" not in content:
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        content = f"# 歸檔時間: {now_str}\n" + content

    return content, True

# ==========================================
# 自動化發布：Git Push
# ==========================================
def git_push_auto():
    """自動執行 Git 同步流程，移除所有 Unicode 符號以避免 CP950 錯誤"""
    try:
        # 切換到倉庫根目錄
        os.chdir(REPO_PATH)
        
        # 1. Add
        subprocess.run(["git", "add", "."], check=True)
        
        # 2. Commit
        commit_msg = f"Auto-Update: {datetime.now().strftime('%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True)
        
        # 3. Push
        print("[Git] Attempting to push to origin main...")
        result = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True)
        
        if result.returncode != 0:
            # 備援機制：如果 main 失敗，嘗試 master
            subprocess.run(["git", "push", "origin", "master"], check=True)
            
        print("[Git] Push Success!")
    except Exception as e:
        print(f"[Git Error] Sync failed: {str(e)}")

# ==========================================
# 網頁渲染：Render HTML
# ==========================================
def mode_render():
    if not os.path.exists(SUMMARY_FILE): return
    with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
        full_content = f.read()

    entries = full_content.split("# 歸檔時間:")[1:]
    if not entries: return
    
    all_slides_html = ""
    for entry in reversed(entries):
        raw_text = entry.strip()
        # 提取標題邏輯
        eng_match = re.search(r"## 文獻名稱\n(.*?)\n", raw_text)
        chi_match = re.search(r"## 文獻中文名稱\n(.*?)\n", raw_text)
        core_match = re.search(r"### 一句話核心\n(.*?)\n", raw_text)
        
        eng_title = eng_match.group(1) if eng_match else "Academic Paper"
        chi_title = chi_match.group(1) if chi_match else eng_title
        core_text = core_match.group(1) if core_match else ""

        md_body = re.sub(r"## 文獻名稱\n.*?\n", "", raw_text)
        html_body = markdown.markdown(md_body, extensions=['extra', 'nl2br'])
        # 粗體轉紅色
        html_body = html_body.replace('<strong>', '<strong class="red">').replace('<b>', '<strong class="red">')

        all_slides_html += f"""
        <div class="swiper-slide">
            <div class="poster-card">
                <div class="meta-header"><div>ACADEMIC POSTER</div><div>{datetime.now().strftime('%Y/%m%d')}</div></div>
                <div class="scroll-content">
                    <header>
                        <div class="eng-title">{eng_title}</div>
                        <h1>{chi_title.split('—')[0]}</h1>
                        <div class="core-statement">{core_text}</div>
                    </header>
                    <main>{html_body}</main>
                    <footer><div>Slide to View More</div><div>(c) Hoomie Studio</div></footer>
                </div>
            </div>
        </div>"""

    # CSS 樣式
    style = """
    :root { --bg: #f0f2f5; --card: #ffffff; --accent: #e60012; --hl: #fff176; }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body, html { height: 100%; overflow: hidden; background: var(--bg); font-family: 'Inter', 'Noto Sans TC', sans-serif; }
    .swiper { width: 100%; height: 100%; }
    .swiper-slide { display: flex; justify-content: center; align-items: center; padding: 20px; }
    .poster-card {
        background: var(--card); width: 100%; max-width: 800px; height: 90vh;
        display: flex; flex-direction: column; padding: 40px;
        box-shadow: 0 30px 60px rgba(0,0,0,0.15); border-radius: 8px; border-top: 6px solid var(--accent);
    }
    .meta-header { display: flex; justify-content: space-between; border-bottom: 1px solid #ddd; padding-bottom: 10px; margin-bottom: 25px; font-size: 0.8rem; font-weight: 800; color: #999; }
    .scroll-content { flex: 1; overflow-y: auto; padding-right: 10px; }
    .eng-title { font-size: 0.9rem; color: #888; border-left: 4px solid var(--accent); padding-left: 10px; margin-bottom: 10px; }
    h1 { font-family: 'Noto Serif TC', serif; font-size: 2.2rem; line-height: 1.2; font-weight: 900; margin-bottom: 30px; }
    .core-statement { font-size: 1.3rem; background: #fff9f9; padding: 25px; border-left: 8px solid #000; margin-bottom: 40px; line-height: 1.6; }
    .red { color: var(--accent) !important; font-weight: 900; }
    main h3 { background: var(--hl); display: inline-block; padding: 0 8px; font-size: 1.5rem; margin: 35px 0 15px; }
    main p, main li { font-size: 1.3rem; margin-bottom: 20px; line-height: 1.8; color: #333; }
    footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; display: flex; justify-content: space-between; font-size: 0.8rem; color: #ccc; }
    """
    
    full_html = f"""<!DOCTYPE html><html lang="zh-TW"><head><meta charset="UTF-8">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css" />
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@900&family=Inter:wght@400;700&family=Noto+Sans+TC:wght@300;400;700&display=swap" rel="stylesheet">
    <style>{style}</style></head><body><div class="swiper"><div class="swiper-wrapper">{all_slides_html}</div><div class="swiper-pagination"></div></div>
    <script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>
    <script>const swiper = new Swiper('.swiper', {{ direction: 'horizontal', pagination: {{ el: '.swiper-pagination', clickable: true }}, grabCursor: true, mousewheel: {{ forceToAxis: true }} }});</script>
    </body></html>"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(full_html)
    print("[Render] index.html updated.")
    git_push_auto()

# ==========================================
# 模式切換與執行
# ==========================================
def mode_merge():
    target_file = TEMP_RESULT if os.path.exists(TEMP_RESULT) else TEMP_TASK
    if not os.path.exists(target_file):
        print("[!] No files to merge.")
        return

    with open(target_file, "r", encoding="utf-8") as f:
        raw_content = f.read()

    # 校驗與修補
    fixed_content, is_ok = validate_and_fix_md(raw_content)
    if not is_ok:
        print("[Error] MD format critical failure. Stopping.")
        exit(1)

    # 寫入 SUMMARY
    with open(SUMMARY_FILE, "a", encoding="utf-8") as sf:
        sf.write(f"\n\n{fixed_content}")

    # 清理暫存
    for f_path in [TEMP_TASK, TEMP_RESULT]:
        if os.path.exists(f_path): os.remove(f_path)
    
    print("[Merge] Success. Starting Render...")
    mode_render()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["collect", "merge", "render"], default="merge")
    args = parser.parse_args()

    if args.mode == "merge":
        mode_merge()
    elif args.mode == "render":
        mode_render()

       # python paperbot_v3.py --mode render