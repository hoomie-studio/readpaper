import os
import re
import time
import argparse
from playwright.sync_api import sync_playwright

# --- 配置區 ---
BASE_PATH = r"C:\Users\folow\.openclaw\workspace\downloads"
HISTORY_FILE = os.path.join(BASE_PATH, "paper_history.md")
TEMP_TASK = os.path.join(BASE_PATH, "temp_task.md")
# 新增：定義結果暫存檔路徑，配合雙暫存檔流程
TEMP_RESULT = os.path.join(BASE_PATH, "temp_result.md")
SUMMARY_FILE = os.path.join(BASE_PATH, "paper_summary.md")
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

# --- 模式 1：採集與建立任務 ---
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
        print(f"[*] 正在檢查清單: {JOURNAL_URL}")
        
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

                print(f"[+] 發現新論文: {title[:50]}...")
                
                detail_page = context.new_page()
                detail_page.goto(full_url, wait_until="domcontentloaded", timeout=60000)
                
                pub_date = "未知"
                pub_history_el = detail_page.query_selector(".pubhistory")
                if pub_history_el:
                    match = re.search(r'Published:\s*([\d\w\s]+)', pub_history_el.inner_text())
                    if match: pub_date = match.group(1).strip()

                # 加入目前時間作為抓取時間
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
                # 寫入歷史索引 (HISTORY_FILE)
                with open(HISTORY_FILE, "a", encoding="utf-8") as hf:
                    for p in new_papers:
                        hf.write(f"\n---\n## {p['title']}\n")
                        hf.write(f"- URL: {p['url']}\n")
                        hf.write(f"- 論文發布日期: {p['date']}\n")
                        hf.write(f"- 抓取時間: {p['fetch_time']}\n")
                        hf.write(f"- 狀態: [PENDING]\n")
                
                # 建立 LLM 專用任務檔 (TEMP_TASK)
                with open(TEMP_TASK, "w", encoding="utf-8") as tf:
                    tf.write("# 今日待處理論文任務\n\n")
                    for p in new_papers:
                        tf.write(f"## {p['title']}\n")
                        tf.write(f"- URL: {p['url']}\n")
                        tf.write(f"- Published: {p['date']}\n")
                        tf.write(f"- 抓取時間: {p['fetch_time']}\n")
                        tf.write(f"- 摘要內容: [PENDING]\n\n")
                print(f"[OK] 已成功建立 temp_task.md，包含 {len(new_papers)} 筆任務。")
            else:
                print("[!] 沒有發現新論文。")

        except Exception as e:
            print(f"[ERROR] {e}")
        finally:
            browser.close()

# --- 模式 2：合併摘要與清理 ---
def mode_merge():
    # 優先檢查 LLM 輸出的結果暫存檔
    if not os.path.exists(TEMP_RESULT):
        print("[!] 找不到 temp_result.md，嘗試檢查 temp_task.md...")
        target_file = TEMP_TASK
    else:
        target_file = TEMP_RESULT

    if not os.path.exists(target_file):
        print("[!] 暫存檔皆不存在，取消合併。")
        return

    with open(target_file, "r", encoding="utf-8") as f:
        content_to_merge = f.read()

    # 1. 將內容追加到長期摘要檔 (SUMMARY_FILE)
    with open(SUMMARY_FILE, "a", encoding="utf-8") as sf:
        sf.write(f"\n\n# 歸檔時間: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        sf.write(content_to_merge)

    # 2. 更新歷史索引檔案狀態 (HISTORY_FILE)
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as hf:
            history = hf.read()
        
        # 從暫存檔提取標題
        titles = re.findall(r'## (.*?)\n', content_to_merge)
        for title in titles:
            pattern = rf"(## {re.escape(title)}.*?)\[PENDING\]"
            history = re.sub(pattern, r"\1[已完成摘要]", history, flags=re.DOTALL)
        
        with open(HISTORY_FILE, "w", encoding="utf-8") as hf:
            hf.write(history)

    # 3. 清理所有暫存
    for f in [TEMP_TASK, TEMP_RESULT]:
        if os.path.exists(f):
            os.remove(f)
            
    print("[OK] 摘要已歸檔至 paper_summary.md，暫存檔已刪除。")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["collect", "merge"], required=True)
    args = parser.parse_args()

    if args.mode == "collect":
        mode_collect()
    elif args.mode == "merge":
        mode_merge()

#python paperbot.py --mode collect