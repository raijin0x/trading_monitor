## วิธีเริ่มต้นพอร์ตของคุณเอง (โฟลเดอร์ `Start Your Own`)

โฟลเดอร์นี้ออกแบบให้เทียบเคียงกับโฟลเดอร์ `Start Your Own` ในโปรเจกต์ต้นฉบับ  
[`ChatGPT-Micro-Cap-Experiment`](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment/tree/main/Start%20Your%20Own)

ใช้เป็นโฟลเดอร์เก็บข้อมูลพอร์ตของคุณเอง แยกจากไฟล์ระบบหลัก

### 1. ไฟล์หลักในโฟลเดอร์นี้

- `Daily Updates.csv`  
  เก็บผลสรุปพอร์ตในแต่ละวัน (รวมแถว `TOTAL` สำหรับมูลค่าพอร์ตและเงินสด)

- `Trade Log.csv`  
  เก็บประวัติการซื้อ–ขายทุกรายการ (MANUAL BUY/SELL, STOPLOSS ฯลฯ)

ทั้งสองไฟล์จะถูกเขียนและอัปเดตอัตโนมัติโดย `trading_script.py`

### 2. วิธีรันให้ใช้โฟลเดอร์นี้เป็น data-dir

จากโฟลเดอร์โปรเจกต์ `Fuki-MicroCap-Bot`:

```bash
python trading_script.py --data-dir "Start Your Own"
```

รันครั้งแรก:
- ถ้ายังไม่มีข้อมูลใน `Daily Updates.csv` ระบบจะถามจำนวนเงินเริ่มต้น (starting equity)
- ใส่ตัวเลข เช่น `10000` แล้วกด Enter

หลังจากนั้นทุกครั้งที่รันจะ:
- โหลดสถานะล่าสุดจาก `Start Your Own/Daily Updates.csv`
- อัปเดตมูลค่าพอร์ต, ตรวจ stop-loss, บันทึกผลลงไฟล์เดิม


