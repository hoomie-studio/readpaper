import os
import re
import sys
import argparse
import markdown
import subprocess
from datetime import datetime
from playwright.sync_api import sync_playwright

# 強制控制台輸出為 UTF-8，解決 Windows 環境下可能的編碼報錯
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

def get_read_history():
    if not os.path.exists(HISTORY_FILE): return set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        return set(re.findall(r'https://www.mdpi.com/\d+-\d+/\d+/\d+/\d+', content))

# ==========================================
# 自動化發布：Git Push (解決 master/main 分支衝突)
# ==========================================
def git_push_auto():
    try:
        os.chdir(REPO_PATH)
        if not os.path.exists(".git"):
            subprocess.run(["git", "init"], check=True)

        # 檢查遠端倉庫設定
        remote_check = subprocess.run(["git", "remote"], capture_output=True, text=True)
        if "origin" not in remote_check.stdout:
            subprocess.run(["git", "remote", "add", "origin", GITHUB_REMOTE_URL], check=True)
        
        # 強制將分支重新命名為 main 以符合現代 GitHub 規範
        subprocess.run(["git", "branch", "-M", "main"], check=True)
        
        # 檢查檔案變動狀態
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if not status.stdout.strip():
            print("[Git] No changes to commit.")
            return

        subprocess.run(["git", "add", "."], check=True)
        commit_msg = f"Auto-Update: {datetime.now().strftime('%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        
        print("[Git] Pushing to origin main...")
        result = subprocess.run(["git", "push", "-u", "origin", "main"], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("[Git] Push Success!")
        else:
            print(f"[Git Error] Push failed: {result.stderr}")
            
    except Exception as e:
        print(f"[Git Error] Sync failed: {str(e)}")

# ==========================================
# 模式 1：採集 (Collect)
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
                print(f"[OK] Task created: {TEMP_TASK}")
            else:
                print("[!] No new papers.")
        except Exception as e:
            print(f"[Error] Collect: {e}")
        finally:
            browser.close()

# ==========================================
# 模式 2：渲染 (Render) - Humankind 藝術風格
# ==========================================
def mode_render():
    if not os.path.exists(SUMMARY_FILE):
        print("[!] Summary file not found.")
        return
    
    with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
        full_content = f.read()

    # 依歸檔時間分割內容
    entries = re.split(r"# 歸檔時間[:：]?\s*\d{4}-\d{2}-\d{2}.*?\n", full_content)
    entries = [e.strip() for e in entries if e.strip()]
    if not entries: return
    entries.reverse() # 最新的排前面
    
    all_slides_html = ""
    for entry in entries:
        # 提取標題與核心內容
        eng_match = re.search(r"(?:#+)\s*文獻名稱\s*\n(.*?)\n", entry)
        chi_match = re.search(r"(?:#+)\s*文獻中文名稱\s*\n(.*?)\n", entry)
        core_match = re.search(r"(?:#+)\s*一句話核心\s*\n(.*?)\n", entry)
        
        eng_title = eng_match.group(1).strip() if eng_match else "RESEARCH PAPER"
        chi_title = chi_match.group(1).strip() if chi_match else "未命名研究"
        core_statement = core_match.group(1).strip() if core_match else ""

        # 清除已提取的標題，轉換剩餘內容為 HTML
        md_body = re.sub(r"(?:#+)\s*文獻(中文)?名稱.*?\n(.*?)\n", "", entry)
        md_body = re.sub(r"(?:#+)\s*一句話核心.*?\n(.*?)\n", "", md_body)
        content_html = markdown.markdown(md_body, extensions=['extra', 'nl2br', 'sane_lists'])

        all_slides_html += f"""
        <div class="swiper-slide">
            <div class="hk-container">
                <div class="hk-background-text">RESEARCH</div>
                <div class="hk-grid">
                    <div class="hk-left-col">
                        <div class="hk-tag">[ {datetime.now().strftime('%m/%d')} ]</div>
                        <h1 class="hk-main-title">{chi_title}</h1>
                        <p class="hk-eng-subtitle">{eng_title}</p>
                        <div class="hk-core-statement">
                            <span class="hk-label">CORE</span>
                            <p>{core_statement}</p>
                        </div>
                    </div>
                    <div class="hk-right-col">
                        <div class="hk-content-scroll">
                            {content_html}
                        </div>
                    </div>
                </div>
                <div class="hk-footer">
                    <div class="hk-logo">HUMANKIND <span>×</span> GEOMATICS</div>
                    <div class="hk-scroll-hint">SCROLL TO DISCOVER —</div>
                </div>
            </div>
        </div>"""

    style = """
    :root {
        --hk-bg: #f8f8f8; --hk-black: #0a0a0a; --hk-red: #ff3b30; --hk-gray: #e0e0e0;
        --serif: 'Noto Serif TC', serif; --sans: 'Noto Sans TC', sans-serif;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body, html { height: 100%; overflow: hidden; background: var(--hk-bg); color: var(--hk-black); font-family: var(--sans); }
    
    .swiper { width: 100%; height: 100vh; }
    .swiper-slide { background: var(--hk-bg); }

    .hk-container {
        width: 100%; height: 100%; padding: 60px;
        display: flex; flex-direction: column; justify-content: space-between;
        position: relative; overflow: hidden;
    }

    .hk-background-text {
        position: absolute; top: -10%; right: -5%;
        font-size: 25vw; font-weight: 900; color: rgba(0,0,0,0.03);
        z-index: 0; pointer-events: none;
    }

    .hk-grid {
        display: grid; grid-template-columns: 1.2fr 1fr;
        gap: 80px; z-index: 1; height: 75vh;
    }

    .hk-tag { font-weight: 700; letter-spacing: 5px; margin-bottom: 40px; font-size: 0.9rem; }

    .hk-main-title {
        font-family: var(--serif); font-size: clamp(2.5rem, 5vw, 5rem);
        line-height: 1.1; font-weight: 900; letter-spacing: -2px;
        margin-bottom: 20px;
    }

    .hk-eng-subtitle {
        font-size: 1rem; color: #888; text-transform: uppercase;
        letter-spacing: 2px; margin-bottom: 60px; max-width: 80%;
    }

    .hk-core-statement { display: flex; gap: 20px; align-items: flex-start; }
    .hk-label { 
        background: var(--hk-black); color: #fff; padding: 4px 10px;
        font-size: 0.7rem; font-weight: 900; transform: rotate(-90deg) translateX(-10px);
    }
    .hk-core-statement p { font-size: 1.5rem; font-family: var(--serif); line-height: 1.4; font-weight: 700; }

    .hk-content-scroll { 
        height: 100%; overflow-y: auto; padding-right: 20px; 
    }
    h3 { 
        font-family: var(--serif); font-size: 1.6rem; margin: 40px 0 15px;
        border-bottom: 2px solid var(--hk-black); display: inline-block;
    }
    p { font-size: 1.1rem; line-height: 1.7; margin-bottom: 20px; text-align: justify; }
    
    strong, b { color: var(--hk-red); font-weight: 700; }
    
    ul, ol { list-style: none; margin-bottom: 40px; }
    li { 
        font-size: 1.1rem; padding: 10px 0; border-bottom: 1px solid var(--hk-gray);
        display: flex; gap: 10px;
    }
    li::before { content: "→"; font-weight: 900; color: var(--hk-red); }

    .hk-footer {
        display: flex; justify-content: space-between; align-items: flex-end;
        border-top: 1px solid #000; padding-top: 20px;
    }
    .hk-logo { font-weight: 900; letter-spacing: 2px; font-size: 1.2rem; }
    .hk-logo span { color: var(--hk-red); }
    .hk-scroll-hint { font-size: 0.8rem; letter-spacing: 3px; font-weight: 700; }

    @media (max-width: 1024px) {
        .hk-grid { grid-template-columns: 1fr; gap: 40px; height: auto; }
        .hk-container { padding: 30px; overflow-y: auto; }
    }
    """

    full_html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Humankind Research Archive</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css" />
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@700;900&family=Noto+Sans+TC:wght@300;400;700&display=swap" rel="stylesheet">
    <style>{style}</style>
</head>
<body>
    <div class="swiper">
        <div class="swiper-wrapper">{all_slides_html}</div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>
    <script>
        const swiper = new Swiper('.swiper', {{
            mousewheel: true,
            keyboard: true,
            grabCursor: true,
            speed: 800
        }});
    </script>
</body>
</html>"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"[Render] {OUTPUT_HTML} updated with Humankind Art style.")
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