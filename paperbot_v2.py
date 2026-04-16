import os
import re
import argparse
import webbrowser
import markdown
from datetime import datetime

# --- 路徑配置 ---
BASE_PATH = r"C:\Users\folow\.openclaw\workspace\downloads"
SUMMARY_FILE = os.path.join(BASE_PATH, "paper_summary.md")
OUTPUT_HTML = os.path.join(BASE_PATH, "final_mobile_poster.html")

def mode_render():
    if not os.path.exists(SUMMARY_FILE):
        print(f"[!] 找不到檔案: {SUMMARY_FILE}")
        return

    with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
        full_content = f.read()

    # 提取最後一筆歸檔內容
    entries = full_content.split("# 歸檔時間:")
    if len(entries) < 2:
        print("[!] 檔案內容格式不符，請確認 Markdown 包含歸檔標記。")
        return
    
    last_raw = entries[-1].strip()
    archive_time = last_raw.split('\n')[0].strip()

    # 解析關鍵欄位 (針對你提供的 MD 格式)
    eng_title_match = re.search(r"## 文獻名稱\n(.*?)\n", last_raw)
    chi_title_match = re.search(r"## 文獻中文名稱\n(.*?)\n", last_raw)
    core_match = re.search(r"### 一句話核心\n(.*?)\n", last_raw)
    
    eng_title = eng_title_match.group(1) if eng_title_match else "Urban Agglomerations & GPP Sensitivity"
    chi_title = chi_title_match.group(1) if chi_title_match else "未命名研究"
    core_statement = core_match.group(1) if core_match else "內容加載中..."

    # 清理內文 Markdown
    md_body = re.sub(r"## 文獻名稱\n.*?\n", "", last_raw)
    md_body = re.sub(r"## 文獻中文名稱\n.*?\n", "", md_body)
    md_body = re.sub(r"### 一句話核心\n.*?\n", "", md_body)
    
    # 轉換 Markdown 為 HTML
    content_html = markdown.markdown(md_body, extensions=['extra', 'nl2br'])

    # 定義 CSS 樣式 (融合 Typography Lab + 手機優先 + 放大字體)
    style = """
    :root {
        --bg-color: #ffffff;
        --text-color: #000000;
        --accent-color: #e60012; 
        --highlight-color: #fff176; 
        --border-color: #000000;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
        font-family: 'Inter', 'Noto Sans TC', sans-serif;
        background-color: #f0f0f0; 
        color: var(--text-color);
        line-height: 1.8;
        display: flex;
        justify-content: center;
    }

    .container {
        background-color: var(--bg-color);
        max-width: 850px;
        width: 100%;
        padding: 40px 25px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }

    .meta-header {
        display: flex;
        flex-direction: column;
        border-bottom: 2px solid var(--border-color);
        padding-bottom: 15px;
        margin-bottom: 40px;
        font-size: 0.9rem;
        letter-spacing: 1px;
        font-weight: 700;
    }

    .archive-info { color: var(--accent-color); margin-top: 5px; }

    header { margin-bottom: 50px; }

    .eng-title {
        font-size: 1.1rem;
        font-weight: 500;
        color: #888;
        margin-bottom: 15px;
        text-transform: uppercase;
        border-left: 5px solid var(--accent-color);
        padding-left: 12px;
    }

    h1 {
        font-family: 'Noto Serif TC', serif;
        font-size: clamp(2.4rem, 9vw, 4rem); 
        line-height: 1.15;
        font-weight: 900;
        letter-spacing: -1.5px;
        margin-bottom: 35px;
    }

    .core-statement {
        font-size: 1.6rem;
        font-weight: 400;
        line-height: 1.5;
        background: #f8f8f8;
        padding: 35px;
        border-radius: 4px;
        border-left: 10px solid var(--text-color);
        margin-bottom: 60px;
    }

    .core-statement strong { color: var(--accent-color); font-weight: 900; }

    /* 大標題樣式：黃色螢光筆 */
    h3 {
        font-family: 'Noto Serif TC', serif;
        font-size: 1.9rem;
        margin: 50px 0 20px 0;
        font-weight: 700;
        display: inline-block;
        background: var(--highlight-color);
        padding: 0 10px;
        line-height: 1.4;
    }

    /* 內文放大 */
    p {
        font-size: 1.3rem; 
        margin-bottom: 25px;
        text-align: justify;
        color: #222;
    }

    /* 小重點：紅色粗體 */
    strong, b {
        color: var(--accent-color);
        font-weight: 700;
    }

    ul, ol { margin-bottom: 40px; padding-left: 20px; }
    li { 
        font-size: 1.25rem; 
        padding: 10px 0; 
        border-bottom: 1px dotted #ddd; 
    }

    footer {
        margin-top: 100px;
        padding-top: 30px;
        border-top: 1px solid #000;
        display: flex;
        flex-direction: column;
        gap: 15px;
        font-size: 0.95rem;
        color: #555;
    }

    @media (min-width: 900px) {
        .container { padding: 80px 70px; }
        .meta-header { flex-direction: row; justify-content: space-between; }
        footer { flex-direction: row; justify-content: space-between; }
    }
    """

    full_html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Poster - {chi_title}</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@900&family=Inter:wght@400;700&family=Noto+Sans+TC:wght@300;400;700&display=swap" rel="stylesheet">
    <style>{style}</style>
</head>
<body>
    <div class="container">
        <div class="meta-header">
            <div>RESEARCH POSTER // ACADEMIC ARCHIVE</div>
            <div class="archive-info">CODE: {datetime.now().strftime('%Y%m%d')} // {archive_time}</div>
        </div>

        <header>
            <div class="eng-title">{eng_title}</div>
            <h1>{chi_title.replace('對', '<br>對')}</h1>
            <div class="core-statement">
                {core_statement.replace('：', '：<br>')}
            </div>
        </header>

        <main>
            {content_html}
        </main>

        <footer>
            <div>Typography Science / Urban Studies</div>
            <div>© 2026 Academic Research Typography Design</div>
        </footer>
    </div>
</body>
</html>
    """

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(full_html)
    
    print(f"[OK] 響應式大字體海報已生成: {OUTPUT_HTML}")
    webbrowser.open(f"file://{os.path.abspath(OUTPUT_HTML)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["render"], default="render")
    args = parser.parse_args()
    if args.mode == "render":
        mode_render()


        #python paperbot_v2.py --mode render