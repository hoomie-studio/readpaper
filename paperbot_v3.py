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
        print(f"[*] Checking: {JOURNAL_URL}")
        
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

                print(f"[+] Found: {title[:50]}...")
                
                detail_page = context.new_page()
                detail_page.goto(full_url, wait_until="domcontentloaded", timeout=60000)
                
                pub_date = "Unknown"
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
                        hf.write(f"- Date: {p['date']}\n")
                        hf.write(f"- Fetch: {p['fetch_time']}\n")
                        hf.write(f"- Status: [PENDING]\n")
                
                with open(TEMP_TASK, "w", encoding="utf-8") as tf:
                    tf.write("# 今日待處理論文任務\n\n")
                    for p in new_papers:
                        tf.write(f"## {p['title']}\n")
                        tf.write(f"- URL: {p['url']}\n")
                        tf.write(f"- Published: {p['date']}\n")
                        tf.write(f"- Fetch: {p['fetch_time']}\n")
                        tf.write(f"- 摘要內容: [PENDING]\n\n")
                print(f"[OK] temp_task.md created with {len(new_papers)} tasks.")
            else:
                print("[!] No new papers found.")

        except Exception as e:
            print(f"[ERROR] {e}")
        finally:
            browser.close()

# --- 模式 2：渲染與推送 (Render & Git) ---
def git_push_auto():
    """修正 Git 推送邏輯與編碼問題"""
    try:
        os.chdir(REPO_PATH)
        
        # 1. 檢查是否有檔案變動 (避免無意義的 commit 導致報錯)
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
        if not status:
            print("[INFO] No changes to commit, skipping push.")
            return

        # 2. 自動設定 User (解決龍蝦環境可能未登入的問題)
        subprocess.run(["git", "config", "user.name", "PaperBot"], check=False)
        subprocess.run(["git", "config", "user.email", "bot@example.com"], check=False)

        # 3. 執行 Git 指令
        subprocess.run(["git", "add", "."], check=True)
        commit_msg = f"Poster Update: {datetime.now().strftime('%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True, text=True)

        # 4. 動態獲取當前分支名稱 (解決 main/master 不一致問題)
        current_branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], 
                                        capture_output=True, text=True).stdout.strip()
        
        print(f"[*] Pushing to {current_branch}...")
        subprocess.run(["git", "push", "origin", current_branch], check=True)
        print("[OK] GitHub repository updated successfully!")

    except subprocess.CalledProcessError as e:
        # 使用 encode('ascii', 'ignore') 確保錯誤訊息中如果有特殊符號不會導致 Python 崩潰
        err_msg = str(e.stderr if e.stderr else e).encode('ascii', 'ignore').decode('ascii')
        print(f"[ERROR] Git Push Failed: {err_msg}")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {str(e)}")

def mode_render():
    """優化後的 render 函數 - 更穩健解析各種 LLM 輸出格式"""
    if not os.path.exists(SUMMARY_FILE):
        print("[!] Summary file not found.")
        return

    with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
        full_content = f.read()

    # 按歸檔時間切割每一篇論文
    entries = full_content.split("# 歸檔時間:")[1:]
    if not entries:
        print("[!] No entries found in paper_summary.md")
        return

    all_slides_html = ""
    
    for entry in reversed(entries):  # 最新的排最前面
        raw_text = entry.strip()
        
        # === 1. 提取歸檔時間 ===
        archive_time = raw_text.split('\n')[0].strip()
        
        # === 2. 提取各區塊（使用更穩健的方式）===
        def extract_section(title_keyword, next_keywords=None):
            """提取指定標題到下一個標題之間的內容"""
            pattern = rf"(?:^|\n)(?:##|###)\s*{title_keyword}.*?(?=\n(?:##|###)\s*(?:{'|'.join(next_keywords)}|$))"
            match = re.search(pattern, raw_text, re.DOTALL | re.IGNORECASE)
            if match:
                text = match.group(0)
                # 移除標題本身
                text = re.sub(rf"^.*{title_keyword}.*?\n", "", text, flags=re.IGNORECASE)
                return text.strip()
            return ""

        eng_title = extract_section(r"文獻名稱", ["文獻中文名稱", "一句話核心"]).strip()
        chi_title = extract_section(r"文獻中文名稱", ["一句話核心"]).strip()
        core_statement = extract_section(r"一句話核心", ["為什麼要研究這個", "研究動機"]).strip()

        # 提取主體內容（扣除前面已提取的區塊）
        md_body = raw_text
        for keyword in ["文獻名稱", "文獻中文名稱", "一句話核心"]:
            md_body = re.sub(rf".*?{keyword}.*?\n", "", md_body, flags=re.DOTALL | re.IGNORECASE, count=1)

        # === 清理常見 LLM 雜訊 ===
        md_body = re.sub(r'^\s*[-•]\s*', '', md_body, flags=re.MULTILINE)  # 移除多餘的 bullet
        md_body = re.sub(r'\n{3,}', '\n\n', md_body)  # 壓縮多餘空行

        # 轉成 HTML
        content_html = markdown.markdown(md_body, extensions=['extra', 'nl2br'])
        
        # 替換 strong 標籤，加上紅色強調（可自行調整顏色）
        content_html = content_html.replace('<strong>', '<strong class="red">')

        # === 產生單一 slide HTML ===
        all_slides_html += f"""
        <div class="swiper-slide">
            <div class="poster-card">
                <div class="meta-header">
                    <div>RESEARCH POSTER // ISSUE {datetime.now().strftime('%m%d')}</div>
                    <div class="archive-info">{archive_time}</div>
                </div>
                <div class="scroll-content">
                    <header>
                        <div class="eng-title">{eng_title or 'RESEARCH'}</div>
                        <h1>{chi_title or eng_title or '未命名研究'}</h1>
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

    # === 產生完整 HTML（保持你原本的樣式）===
    style = """...（保持你原本的 style，不變）..."""

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

    print(f"[OK] index.html generated successfully with {len(entries)} entries.")
    git_push_auto()

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