import os
import re
import markdown
import argparse
import subprocess
from datetime import datetime
import webbrowser

# --- 基礎路徑設定 ---
SUMMARY_FILE = r"C:\Users\folow\.openclaw\workspace\downloads\paper_summary.md" # 龍蝦輸出的轉譯結果
OUTPUT_HTML = "index.html"       # 最終生成的 GitHub Pages 首頁
REPO_PATH = os.getcwd()          # 預設為目前執行目錄

def git_push_auto():
    """自動化 Git 同步流程"""
    try:
        print("🔍 [Git] 正在偵測檔案變更...")
        os.chdir(REPO_PATH)
        
        # 1. Add
        subprocess.run(["git", "add", "."], check=True)
        
        # 2. Commit
        time_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        commit_msg = f"🤖 Auto-Update Poster: {time_str}"
        # 即使沒有變更也不會中斷程式
        subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True)
        
        # 3. Push
        print(f"🚀 [Git] 正在推送到遠端倉庫...")
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("✅ [Git Push Completed] 網頁已即時更新！")
    except Exception as e:
        print(f"❌ [Git] 同步失敗: {e}")

def mode_render():
    """解析 Markdown 並生成具備 Swiper 翻頁功能的 HTML"""
    if not os.path.exists(SUMMARY_FILE):
        print(f"[!] 找不到來源檔案: {SUMMARY_FILE}")
        return

    with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
        full_content = f.read()

    # 1. 根據「# 歸檔時間:」分割多篇文獻
    # 使用正則表達式保留分割標誌後的內容
    raw_entries = re.split(r"# 歸檔時間:", full_content)
    # 過濾掉第一個空字串
    raw_entries = [e.strip() for e in raw_entries if e.strip()]

    if not raw_entries:
        print("[!] 檔案內容不完整，請確認 Markdown 包含 '# 歸檔時間:' 標記。")
        return

    all_slides_html = ""
    
    # 2. 循環解析每一筆文獻並生成 Swiper Slide
    for entry in reversed(raw_entries): # 最新的排在最前面
        lines = entry.split('\n')
        archive_time = lines[0].strip()
        body = "\n".join(lines[1:])

        # 解析關鍵欄位
        eng_title = re.search(r"## 文獻名稱\n(.*?)\n", entry)
        chi_title = re.search(r"## 文獻中文名稱\n(.*?)\n", entry)
        core_match = re.search(r"### 一句話核心\n(.*?)\n", entry)
        
        e_title = eng_title.group(1) if eng_title else "Academic Research"
        c_title = chi_title.group(1) if chi_title else "未命名研究"
        core_st = core_match.group(1) if core_match else "載入中..."

        # 清理並轉換內文
        md_content = re.sub(r"## 文獻名稱\n.*?\n", "", entry)
        md_content = re.sub(r"## 文獻中文名稱\n.*?\n", "", md_content)
        md_content = re.sub(r"### 一句話核心\n.*?\n", "", md_content)
        content_html = markdown.markdown(md_content, extensions=['extra', 'nl2br'])

        # 生成單個 Slide HTML
        slide = f"""
        <div class="swiper-slide">
            <div class="container">
                <div class="meta-header">
                    <div>RESEARCH POSTER // ISSUE {datetime.now().strftime('%m%d')}</div>
                    <div class="archive-info">ARCHIVE: {archive_time}</div>
                </div>
                <header>
                    <div class="eng-title">{e_title}</div>
                    <h1>{c_title.replace('對', '<br>對')}</h1>
                    <div class="core-statement">{core_st.replace('：', '：<br>')}</div>
                </header>
                <main>{content_html}</main>
                <footer>
                    <div>Typography Lab / Academic Morning</div>
                    <div>© {datetime.now().year} ReadPaper Poster Design</div>
                </footer>
            </div>
        </div>
        """
        all_slides_html += slide

    # 3. 組合完整的 HTML 模板 (加入 Swiper.js)
    full_html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Academic FlipBook</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css" />
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@900&family=Inter:wght@400;700&family=Noto+Sans+TC:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        :root {{ --bg-color: #ffffff; --text-color: #000000; --accent-color: #e60012; --highlight-color: #fff176; }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ background: #111; font-family: 'Inter', 'Noto Sans TC', sans-serif; height: 100vh; overflow: hidden; }}
        
        .swiper {{ width: 100%; height: 100%; }}
        .swiper-slide {{ 
            display: flex; justify-content: center; align-items: flex-start; 
            overflow-y: auto; background: #f0f0f0; padding: 20px;
        }}

        .container {{ 
            background: #fff; max-width: 850px; width: 100%; padding: 40px 25px; 
            box-shadow: 0 10px 50px rgba(0,0,0,0.2); min-height: 100%;
        }}
        
        .meta-header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 30px; font-weight: 700; font-size: 0.8rem; }}
        .archive-info {{ color: var(--accent-color); }}
        .eng-title {{ font-size: 1rem; color: #888; border-left: 4px solid var(--accent-color); padding-left: 10px; margin-bottom: 15px; }}
        h1 {{ font-family: 'Noto Serif TC', serif; font-size: clamp(2rem, 8vw, 3.5rem); line-height: 1.1; font-weight: 900; margin-bottom: 30px; }}
        .core-statement {{ font-size: 1.4rem; background: #f8f8f8; padding: 25px; border-left: 8px solid #000; margin-bottom: 40px; line-height: 1.5; }}
        h3 {{ background: var(--highlight-color); display: inline-block; padding: 0 8px; font-size: 1.8rem; margin: 40px 0 20px; font-family: 'Noto Serif TC', serif; }}
        p {{ font-size: 1.25rem; margin-bottom: 20px; line-height: 1.8; text-align: justify; }}
        li {{ font-size: 1.2rem; margin-bottom: 10px; }}
        footer {{ margin-top: 60px; padding-top: 20px; border-top: 1px solid #000; display: flex; justify-content: space-between; font-size: 0.8rem; color: #777; }}

        @media (min-width: 900px) {{ .container {{ padding: 60px 70px; }} }}
    </style>
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
            pagination: {{ el: '.swiper-pagination', clickable: true }},
            mousewheel: true,
            keyboard: true,
            grabCursor: true,
            effect: 'creative',
            creativeEffect: {{
                prev: {{ shadow: true, translate: [0, 0, -400] }},
                next: {{ translate: ['100%', 0, 0] }},
            }},
        }});
    </script>
</body>
</html>
    """

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(full_html)
    
    print(f"🎨 [OK] {len(raw_entries)} 篇海報已整合至翻頁系統")
    
    # 觸發 Git 自動上傳
    git_push_auto()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["render"], default="render")
    args = parser.parse_args()
    if args.mode == "render":
        mode_render()

        #python paperbot_v2.py --mode render