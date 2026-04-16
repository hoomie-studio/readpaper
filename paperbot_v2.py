import os
import re
import markdown
import argparse
import subprocess
from datetime import datetime

# --- 配置區 ---
# 請確保路徑正確
SUMMARY_FILE = r"C:\Users\folow\.openclaw\workspace\downloads\paper_summary.md" 
OUTPUT_HTML = "index.html"
REPO_PATH = os.getcwd()

def git_push_auto():
    try:
        os.chdir(REPO_PATH)
        subprocess.run(["git", "add", "."], check=True)
        commit_msg = f"🤖 Optimized Poster: {datetime.now().strftime('%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("✅ [Git Push] 網頁已同步至 GitHub Pages")
    except Exception as e:
        print(f"❌ [Git] 同步失敗: {e}")

def mode_render():
    if not os.path.exists(SUMMARY_FILE):
        print(f"找不到檔案: {SUMMARY_FILE}")
        return

    with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
        full_content = f.read()

    # 針對你的 MD 格式：使用 "---" 或 "## " 作為文章分割點
    # 這裡採用更穩健的分割方式：尋找包含 URL 或標題的區塊
    entries = re.split(r'\n---\n', full_content)
    
    all_slides_html = ""
    for entry in reversed(entries):
        raw_text = entry.strip()
        if not raw_text: continue

        # 1. 提取標題 (相容 ## Title 或單純第一行)
        title_match = re.search(r"## (.*?)\n", raw_text)
        eng_title = title_match.group(1) if title_match else "New Research"
        
        # 2. 提取中文標題 (針對第二篇文章格式)
        chi_match = re.search(r"## 文獻中文名稱\n(.*?)\n", raw_text)
        chi_title = chi_match.group(1) if chi_match else eng_title

        # 3. 提取一句話核心 (相容於「內文摘要」下方或直接出現的格式)
        core_match = re.search(r"一句話核心[:：]\s*(.*?)\n", raw_text)
        core_statement = core_match.group(1) if core_match else "深入解析中..."

        # 4. 清理正文 (移除已提取的標題與核心句，避免重複顯示)
        md_body = re.sub(r"## .*?\n", "", raw_text)
        md_body = re.sub(r"### 一句話核心.*?\n", "", md_body)
        md_body = re.sub(r"\*\*一句話核心\*\*.*?\n", "", md_body)
        
        # 轉換 HTML 並將所有粗體標籤替換為紅色粗體
        content_html = markdown.markdown(md_body, extensions=['extra', 'nl2br'])
        content_html = content_html.replace('<strong>', '<strong class="red">').replace('<b>', '<strong class="red">')

        all_slides_html += f"""
        <div class="swiper-slide">
            <div class="poster-card">
                <div class="meta-header">
                    <div>RESEARCH POSTER // {datetime.now().strftime('%Y%m%d')}</div>
                    <div class="archive-info">ACADEMIC ARCHIVE</div>
                </div>
                <div class="scroll-content">
                    <header>
                        <div class="eng-title">{eng_title}</div>
                        <h1>{chi_title.split('—')[0]}</h1>
                        <div class="core-statement">{core_statement}</div>
                    </header>
                    <main>{content_html}</main>
                    <footer>
                        <div>Slide to View More Papers →</div>
                        <div>Hoomie Studio Archive</div>
                    </footer>
                </div>
            </div>
        </div>
        """

    style = """
    :root { --bg: #eef1f5; --card: #ffffff; --text: #1a1a1a; --accent: #e60012; --highlight: #fff176; }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body, html { height: 100%; overflow: hidden; background: var(--bg); font-family: 'Inter', 'Noto Sans TC', sans-serif; }
    
    .swiper { width: 100%; height: 100%; }
    .swiper-slide { display: flex; justify-content: center; align-items: center; padding: 15px; }

    /* 增強對比的卡片設計 */
    .poster-card {
        background: var(--card);
        width: 100%; max-width: 800px; height: 92vh;
        display: flex; flex-direction: column;
        padding: 45px;
        box-shadow: 0 40px 80px rgba(0,0,0,0.15), 0 0 1px rgba(0,0,0,0.2);
        border-radius: 8px;
        border-top: 6px solid var(--accent);
    }

    .meta-header { display: flex; justify-content: space-between; border-bottom: 1px solid #ddd; padding-bottom: 10px; margin-bottom: 25px; font-size: 0.75rem; font-weight: 800; color: #999; }
    .scroll-content { flex: 1; overflow-y: auto; padding-right: 10px; }
    .scroll-content::-webkit-scrollbar { width: 4px; }
    .scroll-content::-webkit-scrollbar-thumb { background: #eee; }

    .eng-title { font-size: 0.85rem; color: #777; margin-bottom: 10px; line-height: 1.4; }
    h1 { font-family: 'Noto Serif TC', serif; font-size: clamp(1.8rem, 6vw, 2.8rem); line-height: 1.2; font-weight: 900; margin-bottom: 25px; color: #000; }
    
    .core-statement { font-size: 1.3rem; background: #fff9f9; padding: 25px; border-left: 6px solid var(--accent); margin-bottom: 40px; line-height: 1.6; color: #444; }
    
    .red { color: var(--accent) !important; font-weight: 800; }

    main h3 { background: var(--highlight); display: inline-block; padding: 0 6px; font-size: 1.5rem; margin: 35px 0 15px; font-family: 'Noto Serif TC', serif; }
    
    /* 統一內文字體大小 */
    main p, main li { font-size: 1.3rem; margin-bottom: 20px; line-height: 1.8; text-align: justify; color: #333; }
    main ul, main ol { margin-bottom: 30px; padding-left: 20px; }
    
    footer { margin-top: 40px; padding-top: 20px; border-top: 1px dotted #eee; display: flex; justify-content: space-between; font-size: 0.75rem; color: #ccc; }
    .swiper-pagination-bullet-active { background: var(--accent) !important; }
    """

    full_html = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Academic Morning Post</title>
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
                pagination: {{ el: '.swiper-pagination', clickable: true }},
                grabCursor: true,
                keyboard: true,
                mousewheel: {{ forceToAxis: true }}
            }});
        </script>
    </body>
    </html>
    """
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f: f.write(full_html)
    git_push_auto()

if __name__ == "__main__":
    mode_render()
        #python paperbot_v2.py --mode render