import os
import re
import sys
import argparse
import markdown
import subprocess
import webbrowser
from datetime import datetime
from playwright.sync_api import sync_playwright

# 強制控制台輸出為 UTF-8，解決 Windows 編碼報錯問題
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
# 自動化發布：Git Push
# ==========================================
def git_push_auto():
    try:
        os.chdir(REPO_PATH)
        if not os.path.exists(".git"):
            subprocess.run(["git", "init"], check=True)

        remote_check = subprocess.run(["git", "remote"], capture_output=True, text=True)
        if "origin" not in remote_check.stdout:
            subprocess.run(["git", "remote", "add", "origin", GITHUB_REMOTE_URL], check=True)
        
        subprocess.run(["git", "branch", "-M", "main"], check=True)
        subprocess.run(["git", "add", "."], check=True)
        
        commit_msg = f"Auto-Update: {datetime.now().strftime('%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True)
        
        result = subprocess.run(["git", "push", "-u", "origin", "main"], capture_output=True, text=True)
        if result.returncode != 0:
            subprocess.run(["git", "push", "origin", "master"], check=True)
            
        print("[Git] Push Success!")
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
# 模式 2：渲染 (Render) - 整合 Yale 橫向滑動風格
# ==========================================
def mode_render():
    if not os.path.exists(SUMMARY_FILE):
        print("[!] Summary file not found.")
        return
    
    with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
        full_content = f.read()

    # 以歸檔時間分割內容
    entries = re.split(r"# 歸檔時間[:：]?\s*\d{4}-\d{2}-\d{2}.*?\n", full_content)
    entries = [e.strip() for e in entries if e.strip()]
    
    if not entries: return

    # 第一篇從最新的文章開始 (反轉列表)
    entries.reverse()
    
    all_slides_html = ""
    for entry in entries:
        # 解析標題
        eng_match = re.search(r"(?:#+)\s*文獻名稱\s*\n(.*?)\n", entry)
        chi_match = re.search(r"(?:#+)\s*文獻中文名稱\s*\n(.*?)\n", entry)
        core_match = re.search(r"(?:#+)\s*一句話核心\s*\n(.*?)\n", entry)
        
        eng_title = eng_match.group(1).strip() if eng_match else "Yale Research Archive"
        chi_title = chi_match.group(1).strip() if chi_match else "未命名研究"
        core_statement = core_match.group(1).strip() if core_match else ""

        # 清理正文 Markdown
        md_body = re.sub(r"(?:#+)\s*文獻(中文)?名稱.*?\n(.*?)\n", "", entry)
        md_body = re.sub(r"(?:#+)\s*一句話核心.*?\n(.*?)\n", "", md_body)
        
        # 轉換內容並修正序號清單問題
        content_html = markdown.markdown(md_body, extensions=['extra', 'nl2br', 'sane_lists'])

        all_slides_html += f"""
        <div class="swiper-slide">
            <div class="poster-inner">
                <div class="yale-top-bar">
                    <span class="yale-brand">Yale University</span>
                    <span class="archive-tag">Academic Publication</span>
                </div>
                
                <header>
                    <div class="eng-meta">{eng_title}</div>
                    <h1>{chi_title.replace('：', ':<br>')}</h1>
                </header>
                
                <div class="core-box">
                    <strong>核心摘要：</strong>{core_statement}
                </div>

                <div class="article-columns">
                    {content_html}
                </div>

                <footer>
                    <span>Yale University Urban Planning & Geomatics</span>
                    <span>Slide Right for Next Paper →</span>
                </footer>
            </div>
        </div>"""

    # 耶魯風格與 Swiper 整合之 CSS
    style = """
    :root {
        --yale-blue: #00356b;
        --accent-red: #e60012;
        --highlight: #fff176;
        --text-main: #222222;
        --bg-shade: #f4f4f4;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body, html { height: 100%; overflow: hidden; background: #1a1a1a; font-family: 'Noto Sans TC', sans-serif; }
    
    .swiper { width: 100%; height: 100vh; }
    .swiper-slide { display: flex; justify-content: center; align-items: center; padding: 20px; }

    .poster-inner {
        background: #fff;
        width: 100%;
        max-width: 1300px;
        height: 92vh;
        padding: 50px 60px;
        border-top: 12px solid var(--yale-blue);
        box-shadow: 0 30px 60px rgba(0,0,0,0.5);
        position: relative;
        overflow-y: auto; /* 內部內容過長可滾動 */
    }
    .yale-top-bar {
        display: flex; justify-content: space-between; border-bottom: 1px solid #eee;
        padding-bottom: 15px; margin-bottom: 40px; font-weight: 700; text-transform: uppercase; font-size: 0.9rem; letter-spacing: 1px;
    }
    .yale-brand { color: var(--yale-blue); }
    header h1 { font-family: 'Noto Serif TC', serif; font-size: clamp(1.8rem, 4vw, 3rem); line-height: 1.2; color: var(--yale-blue); margin-bottom: 30px; letter-spacing: -1px; }
    .eng-meta { font-size: 1rem; color: #888; margin-bottom: 10px; font-weight: 300; }
    .core-box { font-size: 1.3rem; background: var(--bg-shade); padding: 30px; border-left: 8px solid var(--yale-blue); margin-bottom: 50px; line-height: 1.6; }
    
    .article-columns { column-count: 2; column-gap: 60px; column-rule: 1px solid #f0f0f0; }
    h3 { break-inside: avoid; background: var(--highlight); display: inline-block; padding: 0 8px; font-size: 1.6rem; margin: 30px 0 15px 0; font-family: 'Noto Serif TC', serif; }
    p { font-size: 1.25rem; margin-bottom: 20px; text-align: justify; color: var(--text-main); }
    
    /* 修正序號顯示問題 */
    ul, ol { margin-bottom: 30px; padding-left: 25px; break-inside: avoid; }
    li { font-size: 1.2rem; margin-bottom: 12px; color: #444; border-bottom: 1px dotted #eee; padding-bottom: 8px; }
    
    strong, b { color: var(--accent-red); font-weight: 700; }
    
    footer { margin-top: 60px; padding-top: 20px; border-top: 1px solid #eee; display: flex; justify-content: space-between; font-size: 0.85rem; color: #bbb; }
    
    @media (max-width: 900px) {
        .poster-inner { padding: 30px; }
        .article-columns { column-count: 1; }
        header h1 { font-size: 2.2rem; }
    }
    """

    full_html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Yale Research Collection</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css" />
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@700;900&family=Noto+Sans+TC:wght@300;400;700&display=swap" rel="stylesheet">
    <style>{style}</style>
</head>
<body>
    <div class="swiper">
        <div class="swiper-wrapper">
            {all_slides_html}
        </div>
        <div class="swiper-pagination"></div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>
    <script>
        new Swiper('.swiper', {{
            pagination: {{ el: '.swiper-pagination', clickable: true }},
            mousewheel: true,
            keyboard: true,
            grabCursor: true,
            spaceBetween: 30
        }});
    </script>
</body>
</html>
    """

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f: f.write(full_html)
    print(f"[Render] {OUTPUT_HTML} updated with Yale Horizontal Swiper style.")
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