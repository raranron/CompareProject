import json
from deepdiff import DeepDiff

# โหลดไฟล์ JSON
with open("json-beautifier (1).json", "r", encoding="utf-8") as f1:
    base_data = json.load(f1)

with open("json-without-debug.json", "r", encoding="utf-8") as f2:
    compare_data = json.load(f2)

# ดึง promoInfo โดยใช้ promoNumber เป็น key
base_promos = {p["promoNumber"]: p for p in base_data.get("promoInfo", [])}
compare_promos = {p["promoNumber"]: p for p in compare_data.get("promoInfo", [])}

# สร้าง dict เพื่อเก็บผลลัพธ์
differences = {}

# เปรียบเทียบทีละ promo
for promo_num, base_promo in base_promos.items():
    compare_promo = compare_promos.get(promo_num)
    if not compare_promo:
        differences[promo_num] = {
            "status": "มีเฉพาะใน base file",
            "base_json": base_promo
        }
    else:
        diff = DeepDiff(base_promo, compare_promo, ignore_order=True)
        if diff:
            differences[promo_num] = {
                "status": "ข้อมูลแตกต่างกัน",
                "diff": diff.to_dict()
            }

# ตรวจสอบว่า promo ไหนอยู่แค่ใน compare
for promo_num, compare_promo in compare_promos.items():
    if promo_num not in base_promos:
        differences[promo_num] = {
            "status": "มีเฉพาะใน compare file",
            "compare_json": compare_promo
        }

# บันทึกผลลัพธ์ลงไฟล์
with open("json_diff_result.json", "w", encoding="utf-8") as output:
    json.dump(differences, output, indent=2, ensure_ascii=False)

print("เปรียบเทียบเสร็จสิ้น ✅")
print("ดูผลลัพธ์ในไฟล์: json_diff_result.json")
