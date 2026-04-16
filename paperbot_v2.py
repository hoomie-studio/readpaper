import os
import re
import markdown
import argparse
import subprocess
from datetime import datetime

# --- 基礎路徑設定 ---
SUMMARY_FILE = r"C:\Users\folow\.openclaw\workspace\downloads\paper_summary.md" 
OUTPUT_HTML = "index.html"
REPO_PATH = os.getcwd()

def git_push_auto():
    """自動化 Git 同步流程"""
    try:
        print("🔍 [Git] 正在偵測檔案變更...")
        os.chdir(REPO_PATH)
        subprocess.run(["git", "add", "."], check=True)
        time_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        commit_msg = f"🤖 Auto-Update Poster: {time_str}"
        subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True)
        print(f"🚀 [Git] 正在推送到遠端倉庫...")
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("✅ [Git Push Completed] 網頁已即時更新！")
    except Exception as e:
        print(f"❌ [Git] 同步失敗: {e}")

def mode_render():
    if not os.path.exists(SUMMARY_FILE):
        print(f"[!] 找不到檔案: {SUMMARY_FILE}")
        return

    with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
        full_content = f.read()

    # 1. 提取所有歸檔內容
    entries = full_content.split("# 歸檔時間:")[1:] 
    if not entries:
        print("[!] 檔案內容格式不符。")
        return
    
    # 2. 循環解析每一篇摘要，生成卡片 HTML
    all_cards_html = ""
    for entry in reversed(entries): # 最新鮮的排在最前面
        raw_text = entry.strip()
        archive_time = raw_text.split('\n')[0].strip()

        # 解析欄位
        eng_match = re.search(r"## 文獻名稱\n(.*?)\n", raw_text)
        chi_match = re.search(r"## 文獻中文名稱\n(.*?)\n", raw_text)
        core_match = re.search(r"### 一句話核心\n(.*?)\n", raw_text)
        
        eng_title = eng_match.group(1) if eng_match else "ACADEMIC PUBLICATION"
        chi_title = chi_match.group(1) if chi_match else "未命名研究"
        core_statement = core_match.group(1) if core_match else "內容讀取中..."

        # 清理並轉換內文 MD
        md_body = re.sub(r"## 文獻(中文)?名稱.*?\n", "", raw_text)
        md_body = re.sub(r"### 一句話核心.*?\n", "", md_body)
        content_html = markdown.markdown(md_body, extensions=['extra', 'nl2br'])

        # 單個卡片的 HTML 結構
        card_html = f"""
        <div class="poster-card">
            <div class="meta-header">
                <div>RESEARCH POSTER // ACADEMIC ARCHIVE</div>
                <div class="archive-info">ARCHIVE: {archive_time}</div>
            </div>
            <header>
                <div class="eng-title">{eng_title}</div>
                <h1>{chi_title.replace('：', ':<br>')}</h1>
                <div class="core-statement">{core_statement}</div>
            </header>
            <main>{content_html}</main>
            <footer>
                <div>Typography Science / ResearchMaster</div>
                <div>© {datetime.now().year} Hoomie Studio</div>
            </footer>
        </div>
        """
        all_cards_html += card_html

    # 3. 定義全局樣式 (確保高度自動捲動)
    style = """
    :root { --bg: #ffffff; --text: #1a1a1a; --accent: #e60012; --highlight: #fff176; }
    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
        font-family: 'Inter', 'Noto Sans TC', sans-serif;
        background-color: #f4f4f4;
        display: flex;
        flex-direction: column;
        align-items: center;
        min-height: 100vh;
        padding: 40px 20px;
    }

    .poster-card {
        background-color: var(--bg);
        max-width: 850px;
        width: 100%;
        padding: 60px 50px;
        margin-bottom: 60px; /* 卡片之間的間距 */
        box-shadow: 0 20px 50px rgba(0,0,0,0.1);
        height: auto; /* 核心修正：高度自動 */
        overflow: visible;
    }

    .meta-header { display: flex; justify-content: space-between; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 40px; font-size: 0.85rem; font-weight: 700; }
    .archive-info { color: var(--accent); }
    .eng-title { font-size: 1rem; color: #888; border-left: 5px solid var(--accent); padding-left: 12px; margin-bottom: 15px; }
    h1 { font-family: 'Noto Serif TC', serif; font-size: clamp(2rem, 7vw, 3.5rem); line-height: 1.2; font-weight: 900; margin-bottom: 35px; }
    .core-statement { font-size: 1.5rem; background: #f8f8f8; padding: 35px; border-left: 10px solid #000; margin-bottom: 50px; line-height: 1.6; }
    
    main h3 { background: var(--highlight); display: inline-block; padding: 0 10px; font-size: 1.8rem; margin: 40px 0 20px; font-family: 'Noto Serif TC', serif; }
    main p { font-size: 1.25rem; margin-bottom: 25px; line-height: 1.8; text-align: justify; }
    main li { font-size: 1.2rem; margin-bottom: 10px; line-height: 1.6; }

    footer { margin-top: 80px; padding-top: 20px; border-top: 1px solid #ddd; display: flex; justify-content: space-between; font-size: 0.9rem; color: #888; }

    @media (max-width: 600px) { .poster-card { padding: 40px 20px; } h1 { font-size: 2rem; } }
    """

    full_html = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Academic Poster Archive</title>
        <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@900&family=Inter:wght@400;700&family=Noto+Sans+TC:wght@300;400;700&display=swap" rel="stylesheet">
        <style>{style}</style>
    </head>
    <body>
        {all_cards_html}
    </body>
    </html>
    """

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(full_html)
    
    print(f"✅ [Render] 已生成長海報網頁：{OUTPUT_HTML}")
    git_push_auto()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="render")
    args = parser.parse_args()
    if args.mode == "render": mode_render()
        #python paperbot_v2.py --mode render