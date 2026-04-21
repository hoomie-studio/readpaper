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
# 自動取得腳本所在的絕對路徑，解決 OpenClaw 執行時的路徑錯位問題
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_PATH = SCRIPT_DIR 

# 強制將 HTML 產出在與 .git 同層的目錄，確保 Git 能掃描到變更
OUTPUT_HTML = os.path.join(REPO_PATH, "index.html")

# 其他資料存放路徑
BASE_PATH = r"C:\Users\folow\.openclaw\workspace\downloads"
HISTORY_FILE = os.path.join(BASE_PATH, "paper_history.md")
TEMP_TASK = os.path.join(BASE_PATH, "temp_task.md")
TEMP_RESULT = os.path.join(BASE_PATH, "temp_result.md")
SUMMARY_FILE = os.path.join(BASE_PATH, "paper_summary.md")

# GitHub 遠端資訊
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
    將嘗試根據內容行數自動補回標題，確保渲染模式不會失效。
    """
    checks = {
        "eng": "## 文獻名稱",
        "chi": "## 文獻中文名稱",
        "core": "## 一句話核心"
    }
    
    missing = [label for label in checks.values() if label not in content]
    
    if not missing:
        return True, content

    print(f"[*] 偵測到格式不完整，缺失標題: {missing}")
    
    # 嘗試修復邏輯
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    if len(lines) < 3:
        return False, content

    fixed_content = content
    
    # 如果缺失前兩個核心標題，進行強制補全（假設前兩行為英中標題）
    if "## 文獻名稱" in missing and "## 文獻中文名稱" in missing:
        start_idx = 0
        if lines[0].startswith("# 歸檔時間"):
            start_idx = 1
            
        header_fix = f"## 文獻名稱\n{lines[start_idx]}\n\n## 文獻中文名稱\n{lines[start_idx+1]}\n\n"
        remaining_body = "\n".join(lines[start_idx+2:])
        fixed_content = f"# 歸檔時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n" + header_fix + remaining_body

    # 補強「一句話核心」錨點
    if "## 一句話核心" not in fixed_content:
        # 尋找內容中可能的斷句點嘗試插入標題
        fixed_content = fixed_content.replace("\n\n", "\n\n## 一句話核心\n", 1)

    return True, fixed_content

# ==========================================
# 自動化發布：Git Push
# ==========================================
def git_push_auto():
    try:
        # 強制切換到真正的 Git 倉庫目錄
        os.chdir(REPO_PATH)
        if not os.path.exists(".git"):
            subprocess.run(["git", "init"], check=True)

        remote_check = subprocess.run(["git", "remote"], capture_output=True, text=True)
        if "origin" not in remote_check.stdout:
            subprocess.run(["git", "remote", "add", "origin", GITHUB_REMOTE_URL], check=True)
        
        subprocess.run(["git", "branch", "-M", "main"], check=True)
        subprocess.run(["git", "add", "."], check=True)
        
        commit_msg = f"Auto-Update: {datetime.now().strftime('%m-%d %H:%M')}"
        # 使用 capture_output 防止 Git 提示資訊干擾主程式日誌
        subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True)
        
        print(f"[*] 正在推送到 GitHub: {GITHUB_REMOTE_URL}")
        subprocess.run(["git", "push", "-u", "origin", "main"], capture_output=True)
        print("[Git] 自動同步完成。")
    except Exception as e:
        print(f"[Git Error] 同步失敗: {str(e)}")

# ==========================================
# 模式 1：採集 (Collect)
# ==========================================
def mode_collect():
    ensure_directory_exists()
    new_papers = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) 
        page = browser.new_page()
        print(f"[*] 掃描期刊中: {JOURNAL_URL}")
        
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
                print(f"[OK] 任務清單已產生: {TEMP_TASK}")
        except Exception as e:
            print(f"[Error] 採集失敗: {e}")
        finally:
            browser.close()

# ==========================================
# 模式 2：渲染 (Render) - 格式容錯強化
# ==========================================
def mode_render():
    if not os.path.exists(SUMMARY_FILE):
        print("[!] 找不到摘要文件。")
        return
    
    with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
        full_content = f.read()

    # 分割各篇文獻
    entries = re.split(r"# 歸檔時間[:：]?\s*\d{4}-\d{2}-\d{2}.*?\n", full_content)
    entries = [e.strip() for e in entries if e.strip()]
    if not entries: return
    entries.reverse() 
    
    all_slides_html = ""
    for entry in entries:
        # 使用強化的正則表達式，增加對 ## 或 ### 的容錯
        eng_match = re.search(r"(?:#+)\s*文獻名稱\s*\n(.*?)\n", entry)
        chi_match = re.search(r"(?:#+)\s*文獻中文名稱\s*\n(.*?)\n", entry)
        core_match = re.search(r"(?:#+)\s*一句話核心\s*\n(.*?)\n", entry)
        
        eng_title = eng_match.group(1).strip() if eng_match else "RESEARCH PAPER"
        chi_title = chi_match.group(1).strip() if chi_match else "未命名研究"
        core_statement = core_match.group(1).strip() if core_match else "點擊查看詳情"

        # 移除已處理的標題，保留正文進行 Markdown 轉換
        md_body = re.sub(r"(?:#+)\s*文獻(中文)?名稱.*?\n(.*?)\n", "", entry)
        md_body = re.sub(r"(?:#+)\s*一句話核心.*?\n(.*?)\n", "", md_body)
        
        content_html = markdown.markdown(md_body, extensions=['extra', 'nl2br'])

        # 保留 Humankind Art 排版風格
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

    # 保留原始 CSS 樣式
    style = """
    :root { --hk-bg: #f8f8f8; --hk-black: #0a0a0a; --hk-red: #ff3b30; --hk-gray: #e0e0e0; --serif: 'Noto Serif TC', serif; --sans: 'Noto Sans TC', sans-serif; }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body, html { height: 100%; overflow: hidden; background: var(--hk-bg); color: var(--hk-black); font-family: var(--sans); }
    .swiper { width: 100%; height: 100vh; }
    .hk-container { width: 100%; height: 100%; padding: 60px; display: flex; flex-direction: column; position: relative; z-index: 1; }
    .hk-background-text { position: absolute; top: -5%; right: -5%; font-size: 25vw; font-weight: 900; color: rgba(0,0,0,0.03); z-index: 0; pointer-events: none; }
    .hk-grid { display: grid; grid-template-columns: 1.2fr 1fr; gap: 80px; z-index: 1; flex-grow: 1; min-height: 0; margin-bottom: 30px; }
    .hk-main-title { font-family: var(--serif); font-size: clamp(2rem, 4vw, 4.5rem); line-height: 1.1; font-weight: 900; letter-spacing: -2px; margin-bottom: 15px; }
    .hk-eng-subtitle { font-size: 0.9rem; color: #888; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 40px; }
    .hk-core-statement { display: flex; gap: 20px; align-items: flex-start; }
    .hk-label { background: var(--hk-black); color: #fff; padding: 4px 10px; font-size: 0.7rem; font-weight: 900; transform: rotate(-90deg) translateX(-5px); }
    .hk-core-statement p { font-size: 1.3rem; font-family: var(--serif); line-height: 1.4; font-weight: 700; }
    .hk-right-col { position: relative; overflow-y: auto; padding-right: 25px; scrollbar-width: thin; scrollbar-color: var(--hk-black) transparent; }
    h3 { font-family: var(--serif); font-size: 1.5rem; margin: 30px 0 15px; border-bottom: 2px solid var(--hk-black); display: inline-block; }
    p { font-size: 1.05rem; line-height: 1.8; margin-bottom: 20px; text-align: justify; }
    strong { color: var(--hk-red); font-weight: 700; }
    li { font-size: 1.05rem; padding: 12px 0; border-bottom: 1px solid var(--hk-gray); display: flex; gap: 10px; line-height: 1.6; }
    li::before { content: '→'; font-weight: 900; color: var(--hk-red); flex-shrink: 0; }
    .hk-footer { flex-shrink: 0; display: flex; justify-content: space-between; align-items: flex-end; border-top: 1px solid #000; padding-top: 20px; z-index: 2; background: var(--hk-bg); }
    .hk-logo { font-weight: 900; letter-spacing: 2px; font-size: 1.1rem; }
    .hk-logo span { color: var(--hk-red); }
    .hk-scroll-hint { font-size: 0.8rem; letter-spacing: 3px; font-weight: 700; }
    """
    
    full_html = f"""<!DOCTYPE html><html lang="zh-TW"><head><meta charset="UTF-8"><title>Paper Archive</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css" />
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@700;900&family=Noto+Sans+TC:wght@300;400;700&display=swap" rel="stylesheet">
    <style>{style}</style></head><body><div class="swiper"><div class="swiper-wrapper">{all_slides_html}</div></div>
    <script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>
    <script>const swiper = new Swiper('.swiper', {{ mousewheel: true, speed: 800 }});</script></body></html>"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"[Render] {OUTPUT_HTML} 更新成功。")
    git_push_auto()

# ==========================================
# 模式 3：合併 (Merge)
# ==========================================
def mode_merge():
    target_file = TEMP_RESULT if os.path.exists(TEMP_RESULT) else TEMP_TASK
    if not os.path.exists(target_file):
        print("[!] 無待處理文件。")
        return

    with open(target_file, "r", encoding="utf-8") as f:
        raw_content = f.read()

    # 執行格式偵測與修復
    success, final_content = validate_and_fix_format(raw_content)
    
    if not success:
        print("[Error] 內容解析失敗且無法修復，合併中斷。")
        return

    with open(SUMMARY_FILE, "a", encoding="utf-8") as sf:
        sf.write(f"\n\n# 歸檔時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        sf.write(final_content)

    # 清理暫存檔案
    for f in [TEMP_TASK, TEMP_RESULT]:
        if os.path.exists(f): os.remove(f)
            
    print("[Merge] 合併成功，啟動渲染程序...")
    mode_render()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["collect", "merge", "render"], required=True)
    args = parser.parse_args()
    if args.mode == "collect": mode_collect()
    elif args.mode == "merge": mode_merge()
    elif args.mode == "render": mode_render()

       # python paperbot_v3.py --mode render