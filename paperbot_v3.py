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

# 自動修復連結 (請確認網址正確)
GITHUB_REMOTE_URL = "https://github.com/hoomie-studio/readpaper.git"
JOURNAL_URL = "https://www.mdpi.com/journal/remotesensing"
MAX_ARTICLES = 1

def ensure_directory_exists():
    if not os.path.exists(BASE_PATH):
        os.makedirs(BASE_PATH)

# ==========================================
# 核心功能：格式校驗與自癒系統 (Validation & Fix)
# ==========================================
def validate_and_fix_format(content):
    """
    偵測 AI 產出內容。如果發現遺漏了 '## 文獻名稱' 等關鍵錨點，
    將嘗試根據內容行數自動補回標題，確保 Render 模式不會失效。
    """
    # 定義必要存在的區塊關鍵字
    checks = {
        "eng": "## 文獻名稱",
        "chi": "## 文獻中文名稱",
        "core": "## 一句話核心"
    }
    
    missing = []
    for key, label in checks.items():
        if label not in content:
            missing.append(label)
    
    if not missing:
        return True, content

    print(f"[*] 偵測到格式不完整，缺失標題: {missing}")
    print("[!] 啟動 AI 產出內容自癒程序...")

    # 嘗試修復：如果連標題都沒有，假設前兩行分別是英、中標題
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    
    # 基本防錯：如果內容太短則無法修復
    if len(lines) < 3:
        return False, content

    fixed_content = content
    
    # 如果缺失前兩個核心標題，進行強制補全
    if "## 文獻名稱" in missing and "## 文獻中文名稱" in missing:
        # 排除可能是時間標籤的行
        start_idx = 0
        if lines[0].startswith("# 歸檔時間"):
            start_idx = 1
            
        header_fix = f"## 文獻名稱\n{lines[start_idx]}\n\n## 文獻中文名稱\n{lines[start_idx+1]}\n\n"
        # 移除原本的前兩行內容（因為已經變成標題下的內容了），重新組合
        remaining_body = "\n".join(lines[start_idx+2:])
        fixed_content = f"# 歸檔時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n" + header_fix + remaining_body

    # 檢查修復後是否仍缺失「一句話核心」標題
    if "## 一句話核心" not in fixed_content:
        # 簡單嘗試在第三個段落前補上標題
        fixed_content = fixed_content.replace("\n\n", "\n\n## 一句話核心\n", 1)

    return True, fixed_content

# ==========================================
# 自動化發布：Git Push (具備自我修復功能)
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
        
        result = subprocess.run(["git", "push", "-u", "origin", "main"], capture_output=True)
        print("[Git] Push execution finished.")
    except Exception as e:
        print(f"[Git Error] Sync failed: {str(e)}")

# ==========================================
# 模式 1：採集 (Collect)
# ==========================================
def mode_collect():
    ensure_directory_exists()
    new_papers = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) 
        page = browser.new_page()
        print(f"[*] Scanning MDPI: {JOURNAL_URL}")
        
        try:
            page.goto(JOURNAL_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector("a.title-link", timeout=30000)
            elements = page.query_selector_all("a.title-link")
            
            for el in elements:
                if len(new_papers) >= MAX_ARTICLES: break
                title = el.inner_text().strip()
                href = el.get_attribute("href")
                full_url = "https://www.mdpi.com" + href
                new_papers.append({"title": title, "url": full_url})

            if new_papers:
                with open(TEMP_TASK, "w", encoding="utf-8") as tf:
                    for p_item in new_papers:
                        tf.write(f"## {p_item['title']}\n- URL: {p_item['url']}\n- [PENDING]\n")
                print(f"[OK] Task created: {TEMP_TASK}")
        except Exception as e:
            print(f"[Error] Collect: {e}")
        finally:
            browser.close()

# ==========================================
# 模式 2：渲染 (Render) - 保留 Humankind 風格
# ==========================================
def mode_render():
    if not os.path.exists(SUMMARY_FILE):
        print("[!] Summary file not found.")
        return
    
    with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
        full_content = f.read()

    entries = re.split(r"# 歸檔時間[:：]?\s*\d{4}-\d{2}-\d{2}.*?\n", full_content)
    entries = [e.strip() for e in entries if e.strip()]
    if not entries: return
    entries.reverse() 
    
    all_slides_html = ""
    for entry in entries:
        # 強化的正則抓取 (相容於 ## 或 ###)
        eng_match = re.search(r"(?:#+)\s*文獻名稱\s*\n(.*?)\n", entry)
        chi_match = re.search(r"(?:#+)\s*文獻中文名稱\s*\n(.*?)\n", entry)
        core_match = re.search(r"(?:#+)\s*一句話核心\s*\n(.*?)\n", entry)
        
        eng_title = eng_match.group(1).strip() if eng_match else "RESEARCH PAPER"
        chi_title = chi_match.group(1).strip() if chi_match else "未命名研究"
        core_statement = core_match.group(1).strip() if core_match else "點擊查看詳情"

        # 清洗正文
        md_body = re.sub(r"(?:#+)\s*文獻(中文)?名稱.*?\n(.*?)\n", "", entry)
        md_body = re.sub(r"(?:#+)\s*一句話核心.*?\n(.*?)\n", "", md_body)
        
        content_html = markdown.markdown(md_body, extensions=['extra', 'nl2br'])

        # 這裡套用你原本要求的 Humankind Art 排版
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
                        <div class="hk-content-wrapper">{content_html}</div>
                    </div>
                </div>
                <div class="hk-footer">
                    <div class="hk-logo">HUMANKIND <span>×</span> GEOMATICS</div>
                    <div class="hk-scroll-hint">SCROLL TO DISCOVER —</div>
                </div>
            </div>
        </div>"""

    # 保留你最愛的 CSS 樣式
    style = """
    :root { --hk-bg: #f8f8f8; --hk-black: #0a0a0a; --hk-red: #ff3b30; --hk-gray: #e0e0e0; --serif: 'Noto Serif TC', serif; --sans: 'Noto Sans TC', sans-serif; }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body, html { height: 100%; overflow: hidden; background: var(--hk-bg); color: var(--hk-black); font-family: var(--sans); }
    .swiper { width: 100%; height: 100vh; }
    .hk-container { width: 100%; height: 100%; padding: 60px; display: flex; flex-direction: column; position: relative; }
    .hk-background-text { position: absolute; top: -5%; right: -5%; font-size: 25vw; font-weight: 900; color: rgba(0,0,0,0.03); z-index: 0; }
    .hk-grid { display: grid; grid-template-columns: 1.2fr 1fr; gap: 80px; z-index: 1; flex-grow: 1; min-height: 0; }
    .hk-main-title { font-family: var(--serif); font-size: clamp(2rem, 4vw, 4.5rem); line-height: 1.1; font-weight: 900; margin-bottom: 15px; }
    .hk-core-statement { display: flex; gap: 20px; align-items: flex-start; }
    .hk-label { background: var(--hk-black); color: #fff; padding: 4px 10px; font-size: 0.7rem; font-weight: 900; transform: rotate(-90deg) translateX(-5px); }
    .hk-core-statement p { font-size: 1.3rem; font-family: var(--serif); line-height: 1.4; font-weight: 700; }
    .hk-right-col { overflow-y: auto; padding-right: 20px; }
    h3 { font-family: var(--serif); font-size: 1.5rem; margin: 30px 0 15px; border-bottom: 2px solid var(--hk-black); display: inline-block; }
    p { font-size: 1.05rem; line-height: 1.8; margin-bottom: 20px; text-align: justify; }
    strong { color: var(--hk-red); font-weight: 700; }
    .hk-footer { flex-shrink: 0; display: flex; justify-content: space-between; border-top: 1px solid #000; padding-top: 20px; }
    .hk-logo { font-weight: 900; letter-spacing: 2px; }
    .hk-logo span { color: var(--hk-red); }
    """
    
    full_html = f"""<!DOCTYPE html><html lang="zh-TW"><head><meta charset="UTF-8">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css" />
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@900&family=Noto+Sans+TC:wght@400;700&display=swap" rel="stylesheet">
    <style>{style}</style></head><body><div class="swiper"><div class="swiper-wrapper">{all_slides_html}</div></div>
    <script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>
    <script>const swiper = new Swiper('.swiper', {{ mousewheel: true, speed: 800 }});</script></body></html>"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"[Render] {OUTPUT_HTML} updated.")
    git_push_auto()

# ==========================================
# 模式 3：合併 (Merge) - 整合檢核與自癒
# ==========================================
def mode_merge():
    target_file = TEMP_RESULT if os.path.exists(TEMP_RESULT) else TEMP_TASK
    if not os.path.exists(target_file):
        print("[!] No files to merge.")
        return

    with open(target_file, "r", encoding="utf-8") as f:
        raw_content = f.read()

    # 執行格式自檢與修正 (New!)
    success, final_content = validate_and_fix_format(raw_content)
    
    if not success:
        print("[Error] 內容過短或損壞，無法修復格式，合併失敗。")
        return

    with open(SUMMARY_FILE, "a", encoding="utf-8") as sf:
        sf.write(f"\n\n# 歸檔時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        sf.write(final_content)

    # 清理暫存
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