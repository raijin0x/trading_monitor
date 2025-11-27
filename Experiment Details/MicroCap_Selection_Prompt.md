## ตัวอย่าง Prompt สำหรับให้ ChatGPT ช่วยคัดหุ้น Micro-Cap

คุณสามารถแก้ไขข้อความด้านล่างนี้แล้วนำไปใช้คุยกับ ChatGPT (หรือ AI อื่น) เพื่อขอไอเดียหุ้น micro-cap:

---

You are an equity analyst focused on **US-listed micro-cap stocks**.

**Task**
Suggest **10 micro-cap stocks** (small market cap, high risk) that:
- Are listed on US exchanges (NYSE / NASDAQ)
- Have sufficient daily liquidity for small retail orders
- Have a clear business model I can understand

For each ticker, provide:
- Ticker
- Company name
- Sector / industry
- 1–2 sentence summary of the business
- 1–2 key reasons it might be interesting (growth, special situation, etc.)
- 1–2 key risks

Constraints:
- This is **idea generation only**, not investment advice.
- I will do my own due diligence before trading.

Output format: a markdown table with columns:  
`Ticker | Name | Sector | Thesis | Risks`

---

> หมายเหตุ: หลังได้รายชื่อหุ้นแล้ว ให้นำไปกรอกในไฟล์ `Candidate_MicroCaps.csv` เพื่อใช้ติดตามต่อ


