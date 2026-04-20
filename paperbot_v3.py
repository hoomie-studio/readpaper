import os
import re
import time
import argparse
import markdown
import subprocess
from datetime import datetime
from playwright.sync_api import sync_playwright

# --- 基礎路徑設定 (請確保路徑正確) ---
BASE_PATH = r"C:\Users\folow\.openclaw\workspace\downloads"
HISTORY_FILE = os.path.join(BASE_PATH, "paper_history.md")
TEMP_TASK = os.path.join(BASE_PATH, "temp_task.md")
TEMP_RESULT = os.path.join(BASE_PATH, "temp_result.md")
SUMMARY_FILE = os.path.join(BASE_PATH, "paper_summary.md")
OUTPUT_HTML = os.path.join(os.getcwd(), "index.html")
REPO_PATH = os.getcwd() 

JOURNAL_URL = "https://www.mdpi.com/journal/remotesensing"

def ensure_directory_exists():
    if not os.path.exists(BASE_PATH):
        os.makedirs(BASE_PATH)

# ==========================================
# 核心功能：格式校驗與物理修復
# ==========================================
def validate_and_fix_content(content):
    """檢查內容格式，並針對硬性標籤進行強制補齊或修正"""
    # 定義必須存在的標籤
    required_structure = {
        "eng_title": r"## 文獻名稱",
        "chi_title": r"## 文獻中文名稱",
        "core_statement": r"### 一句話核心"
    }

    # 1. 自動修正常見的 AI 標題格式錯誤 (物理修復)
    content = content.replace("### 驚人發現", "### 驚人發現與具體數據")
    content = content.replace("### 研究動機", "### 為什麼要研究這個？")
    content = content.replace("### 研究方法", "### 他們做了什麼？")
    content = content.replace("### 實際應用", "### 這對我有什麼意義？")

    # 2. 硬性檢查：如果缺少最核心的標題，回傳 False 強制 AI 重寫
    for label, pattern in required_structure.items():
        if not re.search(pattern, content):
            print(f"[Check Failed] 缺少關鍵區塊: {label}")
            return content, False

    # 3. 確保開頭有歸檔時間 (如果沒有就自動補上目前的)
    if "# 歸檔時間:" not in content:
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        content = f"# 歸檔時間: {now_str}\n" + content

    return content, True

# ==========================================
# 模式 1：採集 (Collect)
# ==========================================
def mode_collect():
    ensure_directory_exists()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_window()
        print(f"🌐 正在掃描: {JOURNAL_URL}")
        page.goto(JOURNAL_URL, wait_until="networkidle")
        articles = page.query_selector_all(".article-content")
        
        # 讀取歷史避免重複
        history_content = ""
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f: history_content = f.read()

        new_tasks = []
        for art in articles:
            link_el = art.query_selector(".title-link")
            if not link_el: continue
            url = "https://www.mdpi.com" + link_el.get_attribute("href")
            if url in history_content: continue
            
            title = link_el.inner_text().strip()
            new_tasks.append(f"## {title}\n- URL: {url}\n- [PENDING]")
            break # 每次僅處理最新的一篇

        if new_tasks:
            with open(TEMP_TASK, "w", encoding="utf-8") as f: f.write("\n\n".join(new_tasks))
            with open(HISTORY_FILE, "a", encoding="utf-8") as f: f.write("\n" + "\n".join(new_tasks))
            print(f"✅ 任務已建立: {TEMP_TASK}")
        else:
            print("📅 沒有發現新論文。")
        browser.close()

# ==========================================
# 模式 2：合併、校驗、渲染、發布 (Merge)
# ==========================================
def git_push_auto():
    """自動化 Git 同步 - 修正 Windows 編碼問題"""
    try:
        os.chdir(REPO_PATH)
        subprocess.run(["git", "add", "."], check=True)
        commit_msg = f"Auto-Update: {datetime.now().strftime('%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True)
        
        # 嘗試推送至 main 或 master
        result = subprocess.run(["git", "push", "origin", "main"], capture_output=True)
        if result.returncode != 0:
            subprocess.run(["git", "push", "origin", "master"], check=True)
        print("[Git] Push Success!")
    except Exception as e:
        print(f"[Git Error] {str(e)}")

def mode_render():
    """生成高質感左右翻頁網頁"""
    if not os.path.exists(SUMMARY_FILE): return
    with open(SUMMARY_FILE, "r", encoding="utf-8") as f: full_content = f.read()

    entries = full_content.split("# 歸檔時間:")[1:]
    if not entries: return
    
    all_slides_html = ""
    for entry in reversed(entries):
        raw_text = entry.strip()
        eng_match = re.search(r"## (.*?)\n", raw_text)
        chi_match = re.search(r"## 文獻中文名稱\n(.*?)\n", raw_text)
        core_match = re.search(r"### 一句話核心\n(.*?)\n", raw_text)
        
        eng_title = eng_match.group(1) if eng_match else "Academic Paper"
        chi_title = chi_match.group(1) if chi_match else eng_title
        core_text = core_match.group(1) if core_match else ""

        # 內容轉換與標註紅粗體
        md_body = re.sub(r"## .*?\n", "", raw_text)
        html_body = markdown.markdown(md_body, extensions=['extra', 'nl2br'])
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
                    <footer><div>Slide to View More</div><div>© Hoomie Studio</div></footer>
                </div>
            </div>
        </div>"""

    # HTML 模板與樣式 (統一字體 1.3rem)
    style = """
    :root { --bg: #f0f2f5; --card: #ffffff; --accent: #e60012; --highlight: #fff176; }
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
    .scroll-content::-webkit-scrollbar { width: 4px; }
    .scroll-content::-webkit-scrollbar-thumb { background: #eee; }
    .eng-title { font-size: 0.9rem; color: #888; border-left: 4px solid var(--accent); padding-left: 10px; margin-bottom: 10px; }
    h1 { font-family: 'Noto Serif TC', serif; font-size: clamp(1.8rem, 4vw, 2.5rem); line-height: 1.2; font-weight: 900; margin-bottom: 30px; }
    .core-statement { font-size: 1.3rem; background: #fff9f9; padding: 25px; border-left: 8px solid #000; margin-bottom: 40px; line-height: 1.6; }
    .red { color: var(--accent) !important; font-weight: 900; }
    main h3 { background: var(--highlight); display: inline-block; padding: 0 8px; font-size: 1.6rem; margin: 35px 0 15px; font-family: 'Noto Serif TC', serif; }
    main p, main li { font-size: 1.3rem; margin-bottom: 20px; line-height: 1.8; text-align: justify; color: #333; }
    footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; display: flex; justify-content: space-between; font-size: 0.8rem; color: #ccc; }
    """
    
    full_html = f"""<!DOCTYPE html><html lang="zh-TW"><head><meta charset="UTF-8">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css" />
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@900&family=Inter:wght@400;700&family=Noto+Sans+TC:wght@300;400;700&display=swap" rel="stylesheet">
    <style>{style}</style></head><body><div class="swiper"><div class="swiper-wrapper">{all_slides_html}</div><div class="swiper-pagination"></div></div>
    <script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>
    <script>const swiper = new Swiper('.swiper', {{ direction: 'horizontal', pagination: {{ el: '.swiper-pagination', clickable: true }}, grabCursor: true, mousewheel: {{ forceToAxis: true }} }});</script>
    </body></html>"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f: f.write(full_html)
    print("[Render] index.html updated.")
    git_push_auto()

def mode_merge():
    target_file = TEMP_RESULT if os.path.exists(TEMP_RESULT) else TEMP_TASK
    if not os.path.exists(target_file): return

    with open(target_file, "r", encoding="utf-8") as f: raw_content = f.read()

    # --- 關鍵步驟：校驗與物理修正 ---
    fixed_content, success = validate_and_fix_content(raw_content)
    if not success:
        print("[Error] 內容缺失嚴重，終止流程並要求重寫。")
        exit(1) # 回傳錯誤代碼 1 讓 OpenClaw 偵測到並重試

    # 歸檔
    with open(SUMMARY_FILE, "a", encoding="utf-8") as sf:
        sf.write(f"\n\n{fixed_content}")

    # 更新 PENDING 狀態
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as hf: hist = hf.read()
        titles = re.findall(r'## (.*?)\n', fixed_content)
        for t in titles:
            hist = re.sub(rf"(## {re.escape(t)}.*?)\[PENDING\]", r"\1[已完成]", hist, flags=re.DOTALL)
        with open(HISTORY_FILE, "w", encoding="utf-8") as hf: hf.write(hist)

    # 清理
    for f in [TEMP_TASK, TEMP_RESULT]:
        if os.path.exists(f): os.remove(f)
    
    print("[Merge] Completed. Starting Render...")
    mode_render()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["collect", "merge", "render"], default="render")
    args = parser.parse_args()

    if args.mode == "collect": mode_collect()
    elif args.mode == "merge": mode_merge()
    elif args.mode == "render": mode_render()
       # python paperbot_v3.py --mode render