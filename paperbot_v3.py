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
OUTPUT_HTML = "index.html" # 網頁輸出的路徑
REPO_PATH = os.getcwd()

JOURNAL_URL = "https://www.mdpi.com/journal/remotesensing"
MAX_ARTICLES = 1

def ensure_directory_exists():
    if not os.path.exists(BASE_PATH):
        os.makedirs(BASE_PATH)

def get_read_history():
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        return set(re.findall(r'https://www.mdpi.com/\d+-\d+/\d+/\d+/\d+', content))

# --- 模式 1：採集與建立任務 (Collect) ---
def mode_collect():
    ensure_directory_exists()
    read_history = get_read_history()
    new_papers = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) 
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        print(f"[*] 正在檢查清單: {JOURNAL_URL}")
        
        try:
            page.goto(JOURNAL_URL, wait_until="domcontentloaded", timeout=60000)
            page.mouse.wheel(0, 1000)
            time.sleep(2) 
            page.wait_for_selector("a.title-link", timeout=30000)
            
            article_elements = page.query_selector_all("a.title-link")
            
            for el in article_elements:
                if len(new_papers) >= MAX_ARTICLES:
                    break
                
                title = el.inner_text().strip()
                href = el.get_attribute("href")
                full_url = "https://www.mdpi.com" + href

                if full_url in read_history:
                    continue

                print(f"[+] 發現新論文: {title[:50]}...")
                
                detail_page = context.new_page()
                detail_page.goto(full_url, wait_until="domcontentloaded", timeout=60000)
                
                pub_date = "未知"
                pub_history_el = detail_page.query_selector(".pubhistory")
                if pub_history_el:
                    match = re.search(r'Published:\s*([\d\w\s]+)', pub_history_el.inner_text())
                    if match: pub_date = match.group(1).strip()

                fetch_time = time.strftime('%Y-%m-%d %H:%M:%S')

                new_papers.append({
                    "title": title, 
                    "url": full_url, 
                    "date": pub_date,
                    "fetch_time": fetch_time
                })
                detail_page.close()
                time.sleep(2)

            if new_papers:
                with open(HISTORY_FILE, "a", encoding="utf-8") as hf:
                    for p in new_papers:
                        hf.write(f"\n---\n## {p['title']}\n")
                        hf.write(f"- URL: {p['url']}\n")
                        hf.write(f"- 論文發布日期: {p['date']}\n")
                        hf.write(f"- 抓取時間: {p['fetch_time']}\n")
                        hf.write(f"- 狀態: [PENDING]\n")
                
                with open(TEMP_TASK, "w", encoding="utf-8") as tf:
                    tf.write("# 今日待處理論文任務\n\n")
                    for p in new_papers:
                        tf.write(f"## {p['title']}\n")
                        tf.write(f"- URL: {p['url']}\n")
                        tf.write(f"- Published: {p['date']}\n")
                        tf.write(f"- 抓取時間: {p['fetch_time']}\n")
                        tf.write(f"- 摘要內容: [PENDING]\n\n")
                print(f"[OK] 已成功建立 temp_task.md，包含 {len(new_papers)} 筆任務。")
            else:
                print("[!] 沒有發現新論文。")

        except Exception as e:
            print(f"[ERROR] {e}")
        finally:
            browser.close()

# --- 模式 2：渲染與推送 (Render & Git) ---
def git_push_auto():
    try:
        os.chdir(REPO_PATH)
        subprocess.run(["git", "add", "."], check=True)
        commit_msg = f"Poster Update: {datetime.now().strftime('%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True)
        
        # 動態獲取當前分支名稱，避免寫死 main
        branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True).stdout.strip()
        subprocess.run(["git", "push", "origin", branch], check=True)
        print("[OK] [Git Push] 網頁已更新並推送到遠端！")
    except Exception as e:
        print(f"[ERROR] [Git] 同步失敗: {e}")

def mode_render():
    if not os.path.exists(SUMMARY_FILE):
        print("[!] 找不到摘要檔，無法渲染網頁。")
        return
    
    with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
        full_content = f.read()

    # 使用寬鬆匹配分割區塊，支援有無冒號的情況
    entries = re.split(r"# 歸檔時間[:：]?\s*", full_content)[1:] 
    if not entries: 
        print("[!] 摘要檔中無有效歸檔內容。")
        return
    
    all_slides_html = ""
    for entry in reversed(entries):
        raw_text = entry.strip()
        lines = raw_text.split('\n')
        archive_time = lines[0].strip() if lines else "Unknown"

        # 優化正則表達式：支援標題後方的多餘空格 (\s*)
        eng_match = re.search(r"## 文獻名稱\s*\n(.*?)\n", raw_text, re.S)
        chi_match = re.search(r"## 文獻中文名稱\s*\n(.*?)\n", raw_text, re.S)
        core_match = re.search(r"### 一句話核心\s*\n(.*?)\n", raw_text, re.S)
        
        eng_title = eng_match.group(1).strip() if eng_match else "RESEARCH"
        chi_title = chi_match.group(1).strip() if chi_match else "未命名研究"
        core_statement = core_match.group(1).strip() if core_match else ""

        # 清理本文，移除已擷取的標題部分
        md_body = re.sub(r"## 文獻(中文)?名稱.*?\n", "", raw_text, flags=re.S)
        md_body = re.sub(r"### 一句話核心.*?\n", "", md_body, flags=re.S)
        
        content_html = markdown.markdown(md_body, extensions=['extra', 'nl2br'])
        content_html = content_html.replace('<strong>', '<strong class="red">').replace('<b>', '<strong class="red">')

        all_slides_html += f"""
        <div class="swiper-slide">
            <div class="poster-card">
                <div class="meta-header">
                    <div>RESEARCH POSTER // ISSUE {datetime.now().strftime('%m%d')}</div>
                    <div class="archive-info">{archive_time}</div>
                </div>
                <div class="scroll-content">
                    <header>
                        <div class="eng-title">{eng_title}</div>
                        <h1>{chi_title.replace('：', ':<br>')}</h1>
                        <div class="core-statement">{core_statement}</div>
                    </header>
                    <main>{content_html}</main>
                    <footer>
                        <div>Hoomie Studio / Academic Flip</div>
                        <div>Slide to Next →</div>
                    </footer>
                </div>
            </div>
        </div>
        """

    style = """
    :root { --bg: #f0f0f0; --card: #ffffff; --text: #1a1a1a; --accent: #e60012; --highlight: #fff176; }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body, html { height: 100%; overflow: hidden; background: var(--bg); font-family: 'Inter', 'Noto Sans TC', sans-serif; }
    .swiper { width: 100%; height: 100%; }
    .swiper-slide { display: flex; justify-content: center; align-items: center; padding: 20px; }
    .poster-card { background: var(--card); width: 100%; max-width: 800px; height: 90vh; display: flex; flex-direction: column; padding: 40px; box-shadow: 0 30px 60px rgba(0,0,0,0.2); border-radius: 4px; }
    .meta-header { display: flex; justify-content: space-between; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 20px; font-size: 0.8rem; font-weight: 800; }
    .scroll-content { flex: 1; overflow-y: auto; padding-right: 15px; }
    .eng-title { font-size: 0.9rem; color: #888; border-left: 5px solid var(--accent); padding-left: 12px; margin-bottom: 15px; }
    h1 { font-family: 'Noto Serif TC', serif; font-size: clamp(1.8rem, 6vw, 3rem); line-height: 1.2; font-weight: 900; margin-bottom: 30px; }
    .core-statement { font-size: 1.3rem; background: #f8f8f8; padding: 25px; border-left: 8px solid #000; margin-bottom: 40px; line-height: 1.6; }
    .red { color: var(--accent) !important; font-weight: 900; }
    main h3 { background: var(--highlight); display: inline-block; padding: 0 8px; font-size: 1.6rem; margin: 30px 0 15px; }
    main p, main li { font-size: 1.3rem; margin-bottom: 20px; line-height: 1.8; text-align: justify; }
    footer { margin-top: 50px; padding-top: 20px; border-top: 1px solid #eee; display: flex; justify-content: space-between; font-size: 0.8rem; color: #bbb; }
    """

    full_html = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Academic Poster Archive</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css" />
        <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@900&family=Inter:wght@400;700&family=Noto+Sans+TC:wght@300;400;700&display=swap" rel="stylesheet">
        <style>{style}</style>
    </head>
    <body>
        <div class="swiper">
            <div class="swiper-wrapper">{all_slides_html}</div>
            <div class="swiper-pagination"></div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>
        <script>
            const swiper = new Swiper('.swiper', {{
                direction: 'horizontal',
                loop: false,
                pagination: {{ el: '.swiper-pagination', clickable: true }},
                mousewheel: {{ forceToAxis: true }},
                grabCursor: true,
                keyboard: true
            }});
        </script>
    </body>
    </html>
    """
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f: 
        f.write(full_html)
    
    print("[OK] index.html 已生成。")
    git_push_auto()

# --- 模式 3：合併摘要 (Merge) ---
def mode_merge():
    target_file = TEMP_RESULT if os.path.exists(TEMP_RESULT) else TEMP_TASK

    if not os.path.exists(target_file):
        print("[!] 暫存檔皆不存在，取消合併。")
        return

    with open(target_file, "r", encoding="utf-8") as f:
        content_to_merge = f.read()

    with open(SUMMARY_FILE, "a", encoding="utf-8") as sf:
        sf.write(f"\n\n# 歸檔時間: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        sf.write(content_to_merge)

    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as hf:
            history = hf.read()
        
        titles = re.findall(r'## (.*?)\n', content_to_merge)
        for title in titles:
            pattern = rf"(## {re.escape(title)}.*?)\\[PENDING\\]"
            history = re.sub(pattern, r"\1[已完成摘要]", history, flags=re.DOTALL)
        
        with open(HISTORY_FILE, "w", encoding="utf-8") as hf:
            hf.write(history)

    for f in [TEMP_TASK, TEMP_RESULT]:
        if os.path.exists(f):
            os.remove(f)
            
    print("[OK] 摘要已歸檔至 paper_summary.md。")
    print("[*] 偵測到合併動作，自動啟動網頁渲染...")
    mode_render()

# --- 主程式入口 ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["collect", "merge", "render"], required=True)
    args = parser.parse_args()

    if args.mode == "collect":
        mode_collect()
    elif args.mode == "merge":
        mode_merge()
    elif args.mode == "render":
        mode_render()

       # python paperbot_v3.py --mode render