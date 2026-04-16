import os
import re
import time
import markdown
import argparse
import subprocess
from datetime import datetime
from playwright.sync_api import sync_playwright

# --- 統一配置區 ---
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

def get_read_history():
    if not os.path.exists(HISTORY_FILE): return set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return set(re.findall(r'https://www.mdpi.com/\d+-\d+/\d+/\d+/\d+', f.read()))

# --- 模式 1：採集與建立任務 ---
def mode_collect():
    ensure_directory_exists()
    read_history = get_read_history()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print(f"🌐 正在存取: {JOURNAL_URL}")
        page.goto(JOURNAL_URL, wait_until="networkidle")
        articles = page.query_selector_all(".article-content")
        new_tasks = []
        for art in articles:
            link_el = art.query_selector(".title-link")
            if not link_el: continue
            url = "https://www.mdpi.com" + link_el.get_attribute("href")
            if url in read_history: continue
            title = link_el.inner_text().strip()
            new_tasks.append(f"## {title}\n- URL: {url}\n- [PENDING]")
            if len(new_tasks) >= 1: break # 每次抓 1 篇

        if new_tasks:
            with open(TEMP_TASK, "w", encoding="utf-8") as f:
                f.write("\n\n".join(new_tasks))
            with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                f.write("\n" + "\n".join(new_tasks))
            print(f"✅ 已發現新論文並寫入 {TEMP_TASK}")
        else:
            print("📅 目前沒有新論文。")
        browser.close()

# --- 模式 2：合併歸檔 (現在包含自動渲染與推送) ---
def mode_merge():
    """將 AI 轉譯好的結果歸檔，並自動連動執行渲染與 Git 推送"""
    if os.path.exists(TEMP_RESULT):
        target_file = TEMP_RESULT
    elif os.path.exists(TEMP_TASK):
        target_file = TEMP_TASK
    else:
        print("[!] 暫存檔 (temp_result.md) 不存在，無法合併。")
        return

    with open(target_file, "r", encoding="utf-8") as f:
        content_to_merge = f.read()

    # 1. 寫入長期摘要檔
    with open(SUMMARY_FILE, "a", encoding="utf-8") as sf:
        sf.write(f"\n\n# 歸檔時間: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        sf.write(content_to_merge)

    # 2. 更新歷史狀態
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as hf:
            history = hf.read()
        titles = re.findall(r'## (.*?)\n', content_to_merge)
        for title in titles:
            pattern = rf"(## {re.escape(title)}.*?)\[PENDING\]"
            history = re.sub(pattern, r"\1[已完成摘要]", history, flags=re.DOTALL)
        with open(HISTORY_FILE, "w", encoding="utf-8") as hf:
            hf.write(history)

    print("✅ [Merge] 檔案歸檔成功。")
    
    # --- 自動連動執行渲染 ---
    print("🚀 [Auto] 正在啟動自動網頁渲染與 GitHub 推送...")
    mode_render()

# --- 模式 3：渲染與 Git 推送 ---
def git_push_auto():
    try:
        os.chdir(REPO_PATH)
        subprocess.run(["git", "add", "."], check=True)
        msg = f"🤖 Auto-Update: {datetime.now().strftime('%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", msg], capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("🌍 [GitHub] 網頁已即時更新至 GitHub Pages！")
    except Exception as e:
        print(f"❌ [Git] 同步失敗: {e}")

def mode_render():
    if not os.path.exists(SUMMARY_FILE):
        print("[!] 找不到歸檔檔案，無法渲染。")
        return
    with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
        full_content = f.read()

    entries = full_content.split("# 歸檔時間:")[1:]
    if not entries: return
    
    all_slides_html = ""
    for entry in reversed(entries):
        raw_text = entry.strip()
        # 提取資訊
        eng_match = re.search(r"## (.*?)\n", raw_text)
        chi_match = re.search(r"## 文獻中文名稱\n(.*?)\n", raw_text)
        core_match = re.search(r"一句話核心[:：]\s*(.*?)\n", raw_text)
        
        eng_title = eng_match.group(1) if eng_match else "Academic Paper"
        chi_title = chi_match.group(1) if chi_match else eng_title
        core_text = core_match.group(1) if core_match else ""

        # 清理並轉為 HTML (粗體轉紅粗體)
        md_body = re.sub(r"## .*?\n", "", raw_text)
        html_body = markdown.markdown(md_body, extensions=['extra', 'nl2br'])
        html_body = html_body.replace('<strong>', '<strong class="red">').replace('<b>', '<strong class="red">')

        all_slides_html += f"""
        <div class="swiper-slide">
            <div class="poster-card">
                <div class="meta-header"><div>POSTER ARCHIVE</div><div>{datetime.now().strftime('%Y/%m%d')}</div></div>
                <div class="scroll-content">
                    <header>
                        <div class="eng-title">{eng_title}</div>
                        <h1>{chi_title.split('—')[0]}</h1>
                        <div class="core-statement">{core_text}</div>
                    </header>
                    <main>{html_body}</main>
                    <footer><div>Slide to view more</div><div>© Hoomie Studio</div></footer>
                </div>
            </div>
        </div>"""

    # CSS 統一字體大小 1.3rem
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
    h1 { font-family: 'Noto Serif TC', serif; font-size: clamp(1.8rem, 6vw, 3rem); line-height: 1.2; font-weight: 900; margin-bottom: 30px; }
    .core-statement { font-size: 1.3rem; background: #fff9f9; padding: 25px; border-left: 8px solid #000; margin-bottom: 40px; line-height: 1.6; }
    .red { color: var(--accent) !important; font-weight: 900; }
    main h3 { background: var(--highlight); display: inline-block; padding: 0 8px; font-size: 1.6rem; margin: 35px 0 15px; font-family: 'Noto Serif TC', serif; }
    main p, main li { font-size: 1.3rem; margin-bottom: 20px; line-height: 1.8; text-align: justify; color: #333; }
    footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; display: flex; justify-content: space-between; font-size: 0.8rem; color: #ccc; }
    """

    full_html = f"""<!DOCTYPE html>
<html lang="zh-TW"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css" />
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@900&family=Inter:wght@400;700&family=Noto+Sans+TC:wght@300;400;700&display=swap" rel="stylesheet">
<style>{style}</style></head>
<body><div class="swiper"><div class="swiper-wrapper">{all_slides_html}</div><div class="swiper-pagination"></div></div>
<script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>
<script>const swiper = new Swiper('.swiper', {{ direction: 'horizontal', pagination: {{ el: '.swiper-pagination', clickable: true }}, grabCursor: true, mousewheel: {{ forceToAxis: true }} }});</script>
</body></html>"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f: f.write(full_html)
    git_push_auto()

# --- 主程式 ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["collect", "merge", "render"], default="render")
    args = parser.parse_args()

    if args.mode == "collect":
        mode_collect()
    elif args.mode == "merge":
        mode_merge() # 這裡現在會自動跑 render + git push
    elif args.mode == "render":
        mode_render()

       # python paperbot_v3.py --mode collect