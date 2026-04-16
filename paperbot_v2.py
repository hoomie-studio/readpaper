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
        time_str = datetime.now().strftime('%m-%d %H:%M')
        commit_msg = f"🤖 Academic Flip Poster: {time_str}"
        subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("✅ [Git Push Completed] 學術海報網頁已更新！")
    except Exception as e:
        print(f"❌ [Git] 同步失敗: {e}")

def mode_render():
    if not os.path.exists(SUMMARY_FILE):
        print(f"[!] 找不到檔案: {SUMMARY_FILE}")
        return

    with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
        full_content = f.read()

    entries = full_content.split("# 歸檔時間:")[1:] 
    if not entries:
        print("[!] 格式不符。")
        return
    
    all_slides_html = ""
    for entry in reversed(entries):
        raw_text = entry.strip()
        archive_time = raw_text.split('\n')[0].strip()

        # 解析欄位
        eng_match = re.search(r"## 文獻名稱\n(.*?)\n", raw_text)
        chi_match = re.search(r"## 文獻中文名稱\n(.*?)\n", raw_text)
        core_match = re.search(r"### 一句話核心\n(.*?)\n", raw_text)
        
        eng_title = eng_match.group(1) if eng_match else "ACADEMIC RESEARCH"
        chi_title = chi_match.group(1) if chi_match else "未命名研究"
        core_statement = core_match.group(1) if core_match else ""

        # 清理並轉換內文
        md_body = re.sub(r"## 文獻(中文)?名稱.*?\n", "", raw_text)
        md_body = re.sub(r"### 一句話核心.*?\n", "", md_body)
        
        # 渲染 Markdown 並將 <strong> 標籤自動替換為紅色粗體樣式
        content_html = markdown.markdown(md_body, extensions=['extra', 'nl2br'])
        content_html = content_html.replace('<strong>', '<strong class="emphasis-red">').replace('<b>', '<strong class="emphasis-red">')

        # 生成單張 Slide HTML
        all_slides_html += f"""
        <div class="swiper-slide">
            <div class="poster-card">
                <div class="meta-line">
                    <span>ACADEMIC POSTER // ARCHIVE {datetime.now().strftime('%Y%m%d')}</span>
                    <span class="red-tag">{archive_time}</span>
                </div>
                
                <div class="scrollable-content">
                    <header>
                        <div class="eng-sub">{eng_title}</div>
                        <h1>{chi_title.replace('：', ':<br>')}</h1>
                        <div class="core-box">{core_statement}</div>
                    </header>
                    
                    <main>
                        {content_html}
                    </main>
                    
                    <footer>
                        <div>Typography Science / Hoomie Studio</div>
                        <div>Slide Right for Next →</div>
                    </footer>
                </div>
            </div>
        </div>
        """

    # --- CSS 樣式設定 ---
    style = """
    :root { 
        --bg-dark: #222222; 
        --paper: #ffffff; 
        --accent: #e60012; 
        --highlight: #fff176;
        --text-main: #1a1a1a;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    html, body { height: 100%; width: 100%; overflow: hidden; background: var(--bg-dark); }

    .swiper { width: 100%; height: 100%; }

    .swiper-slide {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 30px;
    }

    .poster-card {
        background: var(--paper);
        width: 100%;
        max-width: 850px;
        height: 90vh; /* 卡片固定高度 */
        display: flex;
        flex-direction: column;
        padding: 50px;
        box-shadow: 0 40px 100px rgba(0,0,0,0.5);
        border: 1px solid #000;
        position: relative;
    }

    /* 頂部資訊條 */
    .meta-line {
        display: flex;
        justify-content: space-between;
        font-weight: 900;
        font-size: 0.8rem;
        border-bottom: 3px solid #000;
        padding-bottom: 10px;
        margin-bottom: 30px;
        letter-spacing: 1px;
    }
    .red-tag { color: var(--accent); }

    /* 內容滾動區塊 */
    .scrollable-content {
        flex: 1;
        overflow-y: auto;
        padding-right: 20px;
    }
    /* 自定義滾動條 */
    .scrollable-content::-webkit-scrollbar { width: 5px; }
    .scrollable-content::-webkit-scrollbar-thumb { background: #ccc; border-radius: 10px; }

    .eng-sub { color: #888; text-transform: uppercase; font-size: 1rem; border-left: 5px solid var(--accent); padding-left: 15px; margin-bottom: 15px; }
    h1 { font-family: 'Noto Serif TC', serif; font-size: clamp(2rem, 6vw, 3.5rem); line-height: 1.1; font-weight: 900; margin-bottom: 35px; }
    
    .core-box { 
        font-size: 1.5rem; 
        background: #f4f4f4; 
        padding: 30px; 
        border-left: 10px solid #000; 
        margin-bottom: 40px; 
        line-height: 1.5; 
        font-weight: 500;
    }

    /* 統一內文大小與重點顏色 */
    main { font-size: 1.2rem; color: var(--text-main); line-height: 1.8; text-align: justify; }
    main h3 { background: var(--highlight); display: inline-block; padding: 2px 10px; font-size: 1.8rem; margin: 40px 0 20px; font-family: 'Noto Serif TC', serif; }
    main p { margin-bottom: 25px; }
    
    /* 強制紅色粗體樣式 */
    .emphasis-red { color: var(--accent) !important; font-weight: 900; }

    footer { 
        margin-top: 60px; 
        padding-top: 20px; 
        border-top: 1px solid #ddd; 
        display: flex; 
        justify-content: space-between; 
        font-size: 0.8rem; 
        color: #999; 
    }

    /* 手機適配 */
    @media (max-width: 600px) {
        .poster-card { padding: 30px 20px; height: 95vh; }
        h1 { font-size: 1.8rem; }
        .core-box { font-size: 1.2rem; padding: 20px; }
    }
    """

    full_html = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Academic Flip Poster</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css" />
        <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@900&family=Inter:wght@400;700&family=Noto+Sans+TC:wght@300;400;700&display=swap" rel="stylesheet">
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
            const swiper = new Swiper('.swiper', {{
                direction: 'horizontal',
                loop: false,
                grabCursor: true,
                effect: 'creative',
                creativeEffect: {{
                    prev: {{ shadow: true, translate: [0, 0, -400] }},
                    next: {{ translate: ['100%', 0, 0] }},
                }},
                pagination: {{ el: '.swiper-pagination', clickable: true }},
                mousewheel: {{ forceToAxis: true }},
                keyboard: true,
            }});
        </script>
    </body>
    </html>
    """

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(full_html)
    
    print(f"🎨 [Render] 海報渲染完成！")
    git_push_auto()

if __name__ == "__main__":
    mode_render()
        #python paperbot_v2.py --mode render