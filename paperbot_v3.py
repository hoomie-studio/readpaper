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
        return set(re.findall(r'https://www\.mdpi\.com/\d+-\d+/\d+/\d+/\d+', content))

# ====================== 模式 1：採集論文 ======================
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

                print(f"[+] Found: {title[:60]}...")

                detail_page = context.new_page()
                detail_page.goto(full_url, wait_until="domcontentloaded", timeout=60000)

                pub_date = "Unknown"
                pub_history_el = detail_page.query_selector(".pubhistory")
                if pub_history_el:
                    match = re.search(r'Published:\s*([\d\w\s,]+)', pub_history_el.inner_text())
                    if match:
                        pub_date = match.group(1).strip()

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

                print(f"[OK] temp_task.md 已建立，共 {len(new_papers)} 篇待處理。")
            else:
                print("[!] 沒有找到新論文。")

        except Exception as e:
            print(f"[ERROR] {e}")
        finally:
            browser.close()

# ====================== 模式 2：優化後的 Render（重點加強） ======================
def mode_render():
    """優化版 render：更穩健解析各種 LLM 輸出的 Markdown 格式"""
    if not os.path.exists(SUMMARY_FILE):
        print("[!] Summary file not found.")
        return

    with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
        full_content = f.read()

    # 按歸檔時間切割每一篇
    entries = full_content.split("# 歸檔時間:")[1:]
    if not entries:
        print("[!] 沒有找到可渲染的條目")
        return

    all_slides_html = ""

    for entry in reversed(entries):
        raw_text = entry.strip()

        # 提取歸檔時間
        archive_time = raw_text.split('\n')[0].strip()

        # 穩健提取各區塊
        def extract_section(start_kw, end_kws=None):
            if end_kws is None:
                end_kws = ["為什麼要研究這個", "他們做了什麼", "驚人發現", "這對我有什麼意義"]
            pattern = rf"(?:^|\n)(?:##|###)\s*{start_kw}.*?(?=\n(?:##|###)\s*(?:{'|'.join(end_kws)}|$))"
            match = re.search(pattern, raw_text, re.DOTALL | re.IGNORECASE)
            if match:
                text = match.group(0)
                text = re.sub(rf"^.*{start_kw}.*?\n", "", text, flags=re.IGNORECASE)
                return text.strip()
            return ""

        eng_title = extract_section(r"文獻名稱", ["文獻中文名稱", "一句話核心"])
        chi_title = extract_section(r"文獻中文名稱", ["一句話核心"])
        core_statement = extract_section(r"一句話核心", ["為什麼要研究這個", "研究動機"])

        # 提取主體內容
        md_body = raw_text
        for kw in ["文獻名稱", "文獻中文名稱", "一句話核心", "論文來源 URL", "抓取時間"]:
            md_body = re.sub(rf".*?{kw}.*?\n", "", md_body, flags=re.DOTALL | re.IGNORECASE, count=1)

        # 清理雜訊
        md_body = re.sub(r'^\s*[-•]\s*', '', md_body, flags=re.MULTILINE)
        md_body = re.sub(r'\n{3,}', '\n\n', md_body)

        content_html = markdown.markdown(md_body, extensions=['extra', 'nl2br'])
        content_html = content_html.replace('<strong>', '<strong class="red">')

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

    # Swiper 樣式（現代雜誌風）
    style = """
    :root { --bg: #f8f5f0; --card: #ffffff; --text: #1a1a1a; --accent: #2EB98F; --highlight: #fff8e1; }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body, html { height: 100%; overflow: hidden; background: var(--bg); font-family: 'Noto Sans TC', system-ui, sans-serif; }
    .swiper { width: 100%; height: 100%; }
    .swiper-slide { display: flex; justify-content: center; align-items: center; padding: 30px; }
    .poster-card { background: var(--card); width: 100%; max-width: 820px; height: 92vh; display: flex; flex-direction: column; padding: 45px; box-shadow: 0 25px 60px rgba(0,0,0,0.12); border-radius: 16px; }
    .meta-header { display: flex; justify-content: space-between; border-bottom: 2px solid #ddd; padding-bottom: 12px; margin-bottom: 25px; font-size: 0.85rem; color: #666; }
    .scroll-content { flex: 1; overflow-y: auto; padding-right: 20px; }
    .eng-title { font-size: 0.95rem; color: #888; border-left: 5px solid var(--accent); padding-left: 14px; margin-bottom: 12px; }
    h1 { font-size: clamp(1.9rem, 5.5vw, 2.8rem); line-height: 1.25; font-weight: 700; margin-bottom: 28px; color: #1f1f1f; }
    .core-statement { font-size: 1.25rem; background: #f8f9f5; padding: 28px; border-left: 7px solid var(--accent); margin-bottom: 40px; line-height: 1.65; color: #333; }
    .red { color: #e60012 !important; font-weight: 700; }
    main h3 { background: var(--highlight); display: inline-block; padding: 4px 12px; font-size: 1.45rem; margin: 32px 0 16px; border-radius: 4px; }
    main p, main li { font-size: 1.22rem; margin-bottom: 18px; line-height: 1.75; text-align: justify; }
    footer { margin-top: 45px; padding-top: 18px; border-top: 1px solid #eee; display: flex; justify-content: space-between; font-size: 0.85rem; color: #999; }
    """

    full_html = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Academic Poster Archive</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css" />
        <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@700;900&family=Noto+Sans+TC:wght@400;500;700&display=swap" rel="stylesheet">
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

    print(f"[OK] index.html 已成功生成，共 {len(entries)} 篇論文。")
    git_push_auto()

# ====================== Git 推送 ======================
def git_push_auto():
    try:
        os.chdir(REPO_PATH)
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
        if not status:
            print("[INFO] 沒有變更，跳過推送。")
            return

        subprocess.run(["git", "config", "user.name", "PaperBot"], check=False)
        subprocess.run(["git", "config", "user.email", "bot@example.com"], check=False)

        subprocess.run(["git", "add", "."], check=True)
        commit_msg = f"Poster Update: {datetime.now().strftime('%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True, text=True)

        current_branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], 
                                        capture_output=True, text=True).stdout.strip()

        print(f"[*] Pushing to {current_branch}...")
        subprocess.run(["git", "push", "origin", current_branch], check=True)
        print("[OK] GitHub 已成功更新！")

    except subprocess.CalledProcessError as e:
        err_msg = str(e.stderr if e.stderr else e).encode('ascii', 'ignore').decode('ascii')
        print(f"[ERROR] Git Push 失敗: {err_msg}")
    except Exception as e:
        print(f"[ERROR] 意外錯誤: {e}")

# ====================== 模式 3：合併 ======================
def mode_merge():
    target_file = TEMP_RESULT if os.path.exists(TEMP_RESULT) else TEMP_TASK

    if not os.path.exists(target_file):
        print("[!] Temporary task file not found.")
        return

    with open(target_file, "r", encoding="utf-8") as f:
        content_to_merge = f.read()

    with open(SUMMARY_FILE, "a", encoding="utf-8") as sf:
        sf.write(f"\n\n# 歸檔時間: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        sf.write(content_to_merge)

    # 更新 history 狀態
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as hf:
            history = hf.read()

        titles = re.findall(r'## (.*?)\n', content_to_merge)
        for title in titles:
            pattern = rf"(## {re.escape(title)}.*?)\[PENDING\]"
            history = re.sub(pattern, r"\1[已完成摘要]", history, flags=re.DOTALL)

        with open(HISTORY_FILE, "w", encoding="utf-8") as hf:
            hf.write(history)

    # 清理暫存檔
    for f in [TEMP_TASK, TEMP_RESULT]:
        if os.path.exists(f):
            os.remove(f)

    print("[OK] 已合併至 paper_summary.md")
    print("[*] 開始生成 HTML...")
    mode_render()

# ====================== 主程式 ======================
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