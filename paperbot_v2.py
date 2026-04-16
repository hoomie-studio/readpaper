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
    try:
        os.chdir(REPO_PATH)
        subprocess.run(["git", "add", "."], check=True)
        commit_msg = f"🤖 Poster Flip Edition: {datetime.now().strftime('%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("✅ [Git Push Completed] 翻頁版海報已更新！")
    except Exception as e:
        print(f"❌ [Git] 同步失敗: {e}")

def mode_render():
    if not os.path.exists(SUMMARY_FILE): return
    with open(SUMMARY_FILE, "r", encoding="utf-8") as f: full_content = f.read()

    entries = full_content.split("# 歸檔時間:")[1:] 
    if not entries: return
    
    all_slides_html = ""
    for entry in reversed(entries):
        raw_text = entry.strip()
        archive_time = raw_text.split('\n')[0].strip()

        # 解析與文字加強處理
        eng_match = re.search(r"## 文獻名稱\n(.*?)\n", raw_text)
        chi_match = re.search(r"## 文獻中文名稱\n(.*?)\n", raw_text)
        core_match = re.search(r"### 一句話核心\n(.*?)\n", raw_text)
        
        eng_title = eng_match.group(1) if eng_match else "RESEARCH"
        chi_title = chi_match.group(1) if chi_match else "未命名研究"
        core_statement = core_match.group(1) if core_match else ""

        # 清理並轉換內文
        md_body = re.sub(r"## 文獻(中文)?名稱.*?\n", "", raw_text)
        md_body = re.sub(r"### 一句話核心.*?\n", "", md_body)
        
        # 重點自動紅色粗體化：將 **文字** 轉為 <strong class="red">
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
    
    .swiper-slide { 
        display: flex; justify-content: center; align-items: center; 
        padding: 20px; 
    }

    .poster-card {
        background: var(--card);
        width: 100%;
        max-width: 800px;
        height: 90vh; /* 固定高度以支持內部捲動 */
        display: flex;
        flex-direction: column;
        padding: 40px;
        box-shadow: 0 30px 60px rgba(0,0,0,0.2), 0 0 0 1px rgba(0,0,0,0.05); /* 增強對比與邊界感 */
        border-radius: 4px;
        position: relative;
    }

    .meta-header { 
        display: flex; justify-content: space-between; 
        border-bottom: 2px solid #000; padding-bottom: 10px; 
        margin-bottom: 20px; font-size: 0.8rem; font-weight: 800; 
    }

    /* 內部分頁捲動區 */
    .scroll-content {
        flex: 1;
        overflow-y: auto;
        padding-right: 15px;
    }
    .scroll-content::-webkit-scrollbar { width: 6px; }
    .scroll-content::-webkit-scrollbar-thumb { background: #ddd; border-radius: 10px; }

    .eng-title { font-size: 0.9rem; color: #888; border-left: 5px solid var(--accent); padding-left: 12px; margin-bottom: 15px; }
    h1 { font-family: 'Noto Serif TC', serif; font-size: clamp(1.8rem, 6vw, 3rem); line-height: 1.2; font-weight: 900; margin-bottom: 30px; }
    
    .core-statement { font-size: 1.4rem; background: #f8f8f8; padding: 25px; border-left: 8px solid #000; margin-bottom: 40px; line-height: 1.5; }
    
    /* 強調紅色粗體 */
    .red { color: var(--accent) !important; font-weight: 900; }

    main h3 { background: var(--highlight); display: inline-block; padding: 0 8px; font-size: 1.6rem; margin: 30px 0 15px; font-family: 'Noto Serif TC', serif; }
    main p { font-size: 1.2rem; margin-bottom: 20px; line-height: 1.7; text-align: justify; }
    
    footer { margin-top: 50px; padding-top: 20px; border-top: 1px solid #eee; display: flex; justify-content: space-between; font-size: 0.8rem; color: #bbb; }

    .swiper-pagination-bullet-active { background: var(--accent) !important; }
    """

    full_html = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Academic Flip Archive</title>
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
                mousewheel: {{ forceToAxis: true }}, // 允許滑鼠滾輪，但強制軸向
                grabCursor: true,
                keyboard: true
            }});
        </script>
    </body>
    </html>
    """
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f: f.write(full_html)
    git_push_auto()

if __name__ == "__main__": mode_render()
        #python paperbot_v2.py --mode render