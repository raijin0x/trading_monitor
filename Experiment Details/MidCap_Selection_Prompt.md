## ตัวอย่าง Prompt สำหรับให้ ChatGPT ช่วยคัดหุ้น Mid-Cap (ไทย/อังกฤษ)

คุณสามารถคัดลอกข้อความด้านล่างนี้ไปใช้คุยกับ ChatGPT (หรือ AI อื่น) เพื่อขอไอเดียหุ้น **mid-cap** โดยตรง แล้วนำผลลัพธ์มาใช้กับระบบในโฟลเดอร์นี้

---

You are an equity analyst focused on **US-listed mid-cap stocks**.

**Task**  
Suggest **10 mid-cap stocks** that:
- Are listed on US exchanges (NYSE / NASDAQ)
- Have a market capitalization roughly in the **$2–10B** range (mid-cap)
- Have **sufficient daily liquidity** (e.g., at least ~$5M average daily dollar volume)
- Have a clear, understandable business model

For each ticker, provide:
- Ticker  
- Company name  
- Sector / industry  
- Market cap (approximate)  
- 1–2 sentence summary of the business  
- 1–2 key reasons it might be interesting (growth, quality, special situation, etc.)  
- 1–2 key risks  

**Constraints**
- This is **idea generation only**, not investment advice.  
- I will do my own due diligence before trading.  
- Avoid ultra-illiquid names and anything with obvious red flags (e.g., imminent delisting, ongoing fraud investigations).

**Output format**: a markdown table with columns:  
`Ticker | Name | Sector | MarketCap | Thesis | Risks`

---

> หมายเหตุ (ภาษาไทย):
> - หลังได้รายชื่อหุ้น mid-cap แล้ว แนะนำให้คุณ:
>   - เลือกตัวที่สนใจจริง ๆ 5–20 ตัว
>   - บันทึกลงไฟล์ `Experiment Details/Candidate_MicroCaps.csv` (หรือสร้างไฟล์ใหม่สำหรับ mid-cap เช่น `Candidate_MidCaps.csv`)
>   - ถ้าจะให้ `trading_script.py` ติดตามผลเทียบ S&P ให้ใส่ ticker เหล่านี้ใน `tickers.json` หรือใช้เป็น universe สำหรับการเทรดจริงของคุณ


