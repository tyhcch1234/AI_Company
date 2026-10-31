# AI 旗艦模型競賽 · 每日追蹤

比較十間最大規模 AI 實驗室的旗艦模型，資料驅動、每日更新。

🔗 https://tyhcch1234.github.io/AI_Company/

## 這頁答什麼

- 各家**旗艦模型**是哪一個、幾時出、上下文多長
- **API 定價**（每百萬 token，標準價）
- **模態**支援與**開源**程度
- 第三方獨立評測 **Artificial Analysis Intelligence Index v5** 分數
- 每日自動抓取的**產業新聞**

## 檔案

| 檔案 | 作用 |
| --- | --- |
| `index.html` | 整個網站（HTML + CSS + JS 內嵌），無外部依賴、無 CDN |
| `data.json` | 人工核對的模型規格快照 |
| `news.json` | 每日新聞，由工作流自動產生 |
| `scripts/update_news.py` | 抓 Google News RSS，只用標準庫 |
| `.github/workflows/daily.yml` | 每日 00:30（香港時間）更新新聞 |

## 更新節奏

- **新聞：每日自動。** 只有內容有變才 commit，避免無謂的 Pages 重建。
- **模型規格：人工。** 新旗艦推出時更新 `data.json` 並改 `snapshot` 日期。
  價格與上下文長度寧可落後一日，也不可以錯。

## 手動更新規格

`data.json` → `companies[]`，每間公司一個物件：

```json
{
  "id": "openai",
  "name": "OpenAI",
  "region": "美國",
  "hq": "舊金山",
  "flagship": "GPT-6 Astra",
  "release": "2026 年旗艦",
  "context": 1050000,
  "priceIn": 10,
  "priceOut": 50,
  "modality": "文字、圖像 → 文字",
  "open": false,
  "openNote": "閉源",
  "index": 57,
  "indexModel": "GPT-6 Astra (Max)",
  "acumen": "一句話定位",
  "lineup": [{ "name": "GPT-6.1 Sol", "note": "$2 / $10，1.05M 上下文" }],
  "source": "https://developers.openai.com/api/docs/models"
}
```

未知的數值填 `null`，頁面會顯示「—」，不會當成 0 參與排序或畫圖。

同時記得更新 `releases[]`（時間線）與 `snapshot`（頁首日期）。

## 本地預覽

```
python3 -m http.server 8000
# http://localhost:8000/
```

必須用 http 開啟；直接開 `file://` 會被瀏覽器阻擋 JSON 讀取。

## 資料來源

官方文件：OpenAI Models、Claude 模型總覽、Gemini API 定價、xAI Models、DeepSeek 定價、
Mistral Models、Microsoft AI、AWS Nova。
第三方評測：Artificial Analysis Intelligence Index v5（2026-10-27 更新）。

價格為標準價，未計促銷、批次或 cache 折扣。
