import json
from deepdiff import DeepDiff

def filter_out_debug(obj):
    # ฟังก์ชันกรอง key ที่มี 'debug' ออก (recursively)
    if isinstance(obj, dict):
        return {k: filter_out_debug(v) for k, v in obj.items() if "debug" not in k.lower()}
    elif isinstance(obj, list):
        return [filter_out_debug(i) for i in obj]
    else:
        return obj

# โหลดไฟล์ JSON
with open("./Json_res/Onlinepro.json", "r", encoding="utf-8") as f1:
    base_data = json.load(f1)

with open("./Json_res/NewPro.json", "r", encoding="utf-8") as f2:
    compare_data = json.load(f2)

# กรอง debug ออกก่อนเปรียบเทียบ (ทั้งสองฝั่ง)
base_filtered = filter_out_debug(base_data)
compare_filtered = filter_out_debug(compare_data)

# เปรียบเทียบ
diff = DeepDiff(
    base_filtered,
    compare_filtered,
    ignore_order=False,       # เปรียบเทียบลำดับใน list ด้วย
    report_repetition=True    # รายการซ้ำ ๆ แยกแยะเป็นจุดต่าง ๆ
)

if not diff:
    print("ไม่มีความแตกต่างระหว่างไฟล์ทั้งสอง")
    result_old = {}
    result_new = {}
else:
    # เก็บข้อมูลทั้งสองฝั่งที่กรอง debug ไว้เต็ม ๆ
    result_old = base_filtered
    result_new = compare_filtered

# บันทึกไฟล์
with open("./Json_Compare/Compare_Online.json", "w", encoding="utf-8") as f_old:
    json.dump(result_old, f_old, indent=2, ensure_ascii=False)

with open("./Json_Compare/Compare_Newpro.json", "w", encoding="utf-8") as f_new:
    json.dump(result_new, f_new, indent=2, ensure_ascii=False)

# นับจำนวนความแตกต่างทั้งหมดจาก DeepDiff (รวมทุกประเภท)
diff_count = 0
if diff:
    diff_count = sum(len(changes) for changes in diff.values())

print(f"✅ เปรียบเทียบเสร็จ จำนวนความแตกต่างทั้งหมด (รวมสองไฟล์): {diff_count}")
print("ดูไฟล์ Compare_Online.json และ Compare_Newpro.json")
