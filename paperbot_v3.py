import os
import re
import time
import argparse
import markdown
import subprocess
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright

# 強制控制台輸出為 UTF-8，解決 Windows 亂碼與編碼報錯問題
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

# 如果 Agent 找不到遠端倉庫連結，會自動修復為此網址 (請確認網址正確)
GITHUB_REMOTE_URL = "https://github.com/hoomie-studio/readpaper.git"
JOURNAL_URL = "https://www.mdpi.com/journal/remotesensing"
MAX_ARTICLES = 1

def ensure_directory_exists():
    if not os.path.exists(BASE_PATH):
        os.makedirs(BASE_PATH)

def get_read_history():
    if not os.path.exists(HISTORY_FILE): return set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        return set(re.findall(r'https://www.mdpi.com/\d+-\d+/\d+/\d+/\d+', content))

# ==========================================
# 自動化發布：Git Push (具備自我修復功能)
# ==========================================
def git_push_auto():
    try:
        os.chdir(REPO_PATH)
        
        # 1. 檢查 Git 初始化
        if not os.path.exists(".git"):
            print("[Git] Initializing repository...")
            subprocess.run(["git", "init"], check=True)

        # 2. 檢查並修復 Origin 連結
        remote_check = subprocess.run(["git", "remote"], capture_output=True, text=True)
        if "origin" not in remote_check.stdout:
            print(f"[Git] Adding missing remote: {GITHUB_REMOTE_URL}")
            subprocess.run(["git", "remote", "add", "origin", GITHUB_REMOTE_URL], check=True)
        
        # 3. 執行同步流程
        subprocess.run(["git", "branch", "-M", "main"], check=True)
        subprocess.run(["git", "add", "."], check=True)
        
        commit_msg = f"Auto-Update: {datetime.now().strftime('%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True)
        
        print("[Git] Attempting push to GitHub...")
        # 使用 -u 建立追蹤，若失敗則嘗試 master
        result = subprocess.run(["git", "push", "-u", "origin", "main"], capture_output=True, text=True)
        if result.returncode != 0:
            print("[Git] Main push failed, trying master...")
            subprocess.run(["git", "push", "origin", "master"], check=True)
            
        print("[Git] Push Success!")
    except Exception as e:
        print(f"[Git Error] Sync failed: {str(e)}")

# ==========================================
# 模式 1：採集 (Collect) - 修正 API 報錯
# ==========================================
def mode_collect():
    ensure_directory_exists()
    read_history = get_read_history()
    new_papers = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) 
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        print(f"[*] Scanning: {JOURNAL_URL}")
        
        try:
            page.goto(JOURNAL_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector("a.title-link", timeout=30000)
            elements = page.query_selector_all("a.title-link")
            
            for el in elements:
                if len(new_papers) >= MAX_ARTICLES: break
                title = el.inner_text().strip()
                href = el.get_attribute("href")
                full_url = "https://www.mdpi.com" + href

                if full_url in read_history: continue

                new_papers.append({
                    "title": title, "url": full_url, 
                    "fetch_time": datetime.now().strftime('%Y-%m-%d %H:%M')
                })

            if new_papers:
                with open(TEMP_TASK, "w", encoding="utf-8") as tf:
                    for p_item in new_papers:
                        tf.write(f"## {p_item['title']}\n- URL: {p_item['url']}\n- [PENDING]\n")
                with open(HISTORY_FILE, "a", encoding="utf-8") as hf:
                    for p_item in new_papers:
                        hf.write(f"\n## {p_item['title']}\n- URL: {p_item['url']}\n- [PENDING]\n")
                print(f"[OK] Task created: {TEMP_TASK}")
            else:
                print("[!] No new papers.")
        except Exception as e:
            print(f"[Error] Collect: {e}")
        finally:
            browser.close()

# ==========================================
# 模式 2：渲染 (Render) - 強化標題解析彈性
# ==========================================
def mode_render():
    if not os.path.exists(SUMMARY_FILE):
        print("[!] Summary file not found.")
        return
    
    with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
        full_content = f.read()

    # 使用正則分割歸檔區塊
    entries = re.split(r"# 歸檔時間[:：]?\s*\d{4}-\d{2}-\d{2}.*?\n", full_content)
    entries = [e.strip() for e in entries if e.strip()]
    
    if not entries: return
    
    all_slides_html = ""
    for entry in reversed(entries):
        # 強化匹配：支援 # 數量變動與空格變動
        eng_match = re.search(r"(?:#+)\s*文獻名稱\s*\n(.*?)\n", entry)
        chi_match = re.search(r"(?:#+)\s*文獻中文名稱\s*\n(.*?)\n", entry)
        core_match = re.search(r"(?:#+)\s*一句話核心\s*\n(.*?)\n", entry)
        
        # 容錯處理：如果 LLM 合併了標題
        if not eng_match and not chi_match:
            first_line = entry.split('\n')[0]
            chi_title = first_line.replace('#', '').strip()
            eng_title = "Research Paper"
        else:
            eng_title = eng_match.group(1).strip() if eng_match else "RESEARCH"
            chi_title = chi_match.group(1).strip() if chi_match else "未命名研究"

        core_statement = core_match.group(1).strip() if core_match else ""

        # 移除已提取的標題資訊，避免重複出現在正文中
        md_body = re.sub(r"(?:#+)\s*文獻(中文)?名稱.*?\n(.*?)\n", "", entry)
        md_body = re.sub(r"(?:#+)\s*一句話核心.*?\n(.*?)\n", "", md_body)
        
        content_html = markdown.markdown(md_body, extensions=['extra', 'nl2br'])
        content_html = content_html.replace('<strong>', '<strong class="red">').replace('<b>', '<strong class="red">')

        all_slides_html += f"""
        <div class="swiper-slide">
            <div class="poster-card">
                <div class="meta-header"><div>POSTER // {datetime.now().strftime('%m%d')}</div></div>
                <div class="scroll-content">
                    <header>
                        <div class="eng-title">{eng_title}</div>
                        <h1>{chi_title.replace('：', ':<br>')}</h1>
                        <div class="core-statement">{core_statement}</div>
                    </header>
                    <main>{content_html}</main>
                    <footer><div>(c) Hoomie Studio</div></footer>
                </div>
            </div>
        </div>"""

    # 此處保留你原本強大的 CSS Style
    style = ":root { --bg: #f0f0f0; --card: #ffffff; --accent: #e60012; --highlight: #fff176; } * { box-sizing: border-box; margin: 0; padding: 0; } body, html { height: 100%; overflow: hidden; background: var(--bg); font-family: 'Inter', 'Noto Sans TC', sans-serif; } .swiper { width: 100%; height: 100%; } .swiper-slide { display: flex; justify-content: center; align-items: center; padding: 20px; } .poster-card { background: var(--card); width: 100%; max-width: 800px; height: 90vh; display: flex; flex-direction: column; padding: 40px; box-shadow: 0 30px 60px rgba(0,0,0,0.2); border-radius: 4px; border-top: 6px solid var(--accent); } .meta-header { display: flex; justify-content: space-between; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 20px; font-size: 0.8rem; font-weight: 800; } .scroll-content { flex: 1; overflow-y: auto; padding-right: 15px; } .eng-title { font-size: 0.9rem; color: #888; border-left: 5px solid var(--accent); padding-left: 12px; margin-bottom: 15px; } h1 { font-family: 'Noto Serif TC', serif; font-size: 2.2rem; line-height: 1.2; font-weight: 900; margin-bottom: 30px; } .core-statement { font-size: 1.3rem; background: #f8f8f8; padding: 25px; border-left: 8px solid #000; margin-bottom: 40px; line-height: 1.6; } .red { color: var(--accent) !important; font-weight: 900; } main h3 { background: var(--highlight); display: inline-block; padding: 0 8px; font-size: 1.6rem; margin: 30px 0 15px; } main p, main li { font-size: 1.3rem; margin-bottom: 20px; line-height: 1.8; } footer { margin-top: 50px; padding-top: 20px; border-top: 1px solid #eee; display: flex; justify-content: space-between; font-size: 0.8rem; color: #bbb; }"
    
    full_html = f"<!DOCTYPE html><html><head><meta charset='UTF-8'><link rel='stylesheet' href='https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css' /><style>{style}</style></head><body><div class='swiper'><div class='swiper-wrapper'>{all_slides_html}</div><div class='swiper-pagination'></div></div><script src='https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js'></script><script>new Swiper('.swiper', {{ pagination: {{ el: '.swiper-pagination' }}, mousewheel: true, grabCursor: true }});</script></body></html>"

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f: f.write(full_html)
    print("[Render] index.html updated.")
    git_push_auto()

# ==========================================
# 模式 3：合併 (Merge)
# ==========================================
def mode_merge():
    target_file = TEMP_RESULT if os.path.exists(TEMP_RESULT) else TEMP_TASK
    if not os.path.exists(target_file):
        print("[!] No files to merge.")
        return

    with open(target_file, "r", encoding="utf-8") as f:
        content = f.read()

    with open(SUMMARY_FILE, "a", encoding="utf-8") as sf:
        sf.write(f"\n\n# 歸檔時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        sf.write(content)

    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as hf: history = hf.read()
        titles = re.findall(r'## (.*?)\n', content)
        for title in titles:
            history = history.replace(f"## {title}\n- URL:", f"## {title} [已完成]\n- URL:")
        with open(HISTORY_FILE, "w", encoding="utf-8") as hf: hf.write(history)

    for f in [TEMP_TASK, TEMP_RESULT]:
        if os.path.exists(f): os.remove(f)
            
    print("[Merge] Success. Auto-rendering...")
    mode_render()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["collect", "merge", "render"], required=True)
    args = parser.parse_args()
    if args.mode == "collect": mode_collect()
    elif args.mode == "merge": mode_merge()
    elif args.mode == "render": mode_render()

       # python paperbot_v3.py --mode render