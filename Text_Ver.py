import json
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
from deepdiff import DeepDiff
import pyperclip
import re

def filter_out_debug(obj):
    if isinstance(obj, dict):
        return {k: filter_out_debug(v) for k, v in obj.items() if "debug" not in k.lower()}
    elif isinstance(obj, list):
        return [filter_out_debug(i) for i in obj]
    else:
        return obj

def build_partial_json(base, diff_paths):
    partial = {}
    for path in diff_paths:
        keys = re.findall(r"\['([^]]+)'\]|\[(\d+)\]", path)
        keys = [k[0] if k[0] else int(k[1]) for k in keys]
        current_src = base
        current_partial = partial
        parents = []
        for i, key in enumerate(keys):
            is_last = (i == len(keys) - 1)
            if isinstance(current_src, dict) and key not in current_src:
                break
            if isinstance(current_src, list) and (not isinstance(key, int) or key >= len(current_src)):
                break
            if isinstance(key, int):
                if not isinstance(current_partial, list):
                    if isinstance(current_partial, dict) and not current_partial:
                        new_list = []
                        if parents:
                            parent, parent_key = parents[-1]
                            parent[parent_key] = new_list
                        else:
                            partial = new_list
                        current_partial = new_list
                    else:
                        break
                while len(current_partial) <= key:
                    current_partial.append({})
                if is_last:
                    current_partial[key] = current_src[key]
                else:
                    parents.append((current_partial, key))
                    current_partial = current_partial[key]
                    current_src = current_src[key]
            else:
                if not isinstance(current_partial, dict):
                    break
                if key not in current_partial:
                    current_partial[key] = {}
                if is_last:
                    current_partial[key] = current_src[key]
                else:
                    parents.append((current_partial, key))
                    current_partial = current_partial[key]
                    current_src = current_src[key]
    return partial

def copy_text(widget):
    content = widget.get("1.0", tk.END).strip()
    if content:
        pyperclip.copy(content)
        messagebox.showinfo("คัดลอกแล้ว", "ข้อความถูกคัดลอกไปยังคลิปบอร์ดเรียบร้อยแล้ว")
    else:
        messagebox.showwarning("ว่างเปล่า", "ไม่มีข้อความให้คัดลอก")

def compare_json():
    try:
        base_data = json.loads(text_base.get("1.0", tk.END))
        compare_data = json.loads(text_compare.get("1.0", tk.END))
    except json.JSONDecodeError as e:
        messagebox.showerror("รูปแบบ JSON ไม่ถูกต้อง", str(e))
        return

    base_filtered = filter_out_debug(base_data)
    compare_filtered = filter_out_debug(compare_data)

    diff = DeepDiff(
        base_filtered,
        compare_filtered,
        ignore_order=False,
        report_repetition=True,
        view="tree"
    )

    if not diff:
        label_result.config(text="✅ ไม่มีความแตกต่างระหว่าง JSON ทั้งสองไฟล์")
        text_partial_base.delete("1.0", tk.END)
        text_partial_compare.delete("1.0", tk.END)
        return

    path_list = []
    for section in diff:
        for change in diff[section]:
            if hasattr(change, 'path'):
                path = change.path(output_format='list')
                s = "".join(f"[{p}]" if isinstance(p, int) else f"['{p}']" for p in path)
                path_list.append(s)

    partial_base = build_partial_json(base_filtered, path_list)
    partial_compare = build_partial_json(compare_filtered, path_list)

    text_partial_base.delete("1.0", tk.END)
    text_partial_compare.delete("1.0", tk.END)
    text_partial_base.insert(tk.END, json.dumps(partial_base, indent=2, ensure_ascii=False))
    text_partial_compare.insert(tk.END, json.dumps(partial_compare, indent=2, ensure_ascii=False))

    total_diff = sum(len(diff[section]) for section in diff)
    label_result.config(text=f"🔍 พบความแตกต่างทั้งหมด {total_diff} จุด (เทียบแบบ jsoncompare.org)")

# ==== สร้าง GUI ====
root = tk.Tk()
root.title("🧠 JSON Compare Tool")
root.geometry("1280x900")
root.configure(bg="#f0f2f5")

style = ttk.Style()
style.theme_use('clam')
style.configure("TButton", font=("Segoe UI", 10, "bold"))
style.configure("TLabel", font=("Segoe UI", 11))
style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"))

# ==== JSON Input ====
ttk.Label(root, text="📘 JSON Base (Onlinepro.json)", style="Header.TLabel").pack(pady=(10, 0))
text_base = ScrolledText(root, height=10, width=150, bg="#ffffff", relief="groove", bd=2)
text_base.pack(padx=10, pady=5)

ttk.Label(root, text="📙 JSON Compare (NewPro.json)", style="Header.TLabel").pack(pady=(10, 0))
text_compare = ScrolledText(root, height=10, width=150, bg="#ffffff", relief="groove", bd=2)
text_compare.pack(padx=10, pady=5)

ttk.Button(root, text="🔍 เปรียบเทียบ JSON", command=compare_json).pack(pady=15)

label_result = ttk.Label(root, text="", foreground="green", font=("Segoe UI", 12, "bold"))
label_result.pack()

# ==== แสดงผลต่าง ====
frame_diff = ttk.Frame(root)
frame_diff.pack(padx=10, pady=10, fill="both", expand=True)

# Compare ด้านซ้าย
ttk.Label(frame_diff, text="📂 JSON Compare - ส่วนที่ต่าง", style="Header.TLabel").grid(row=0, column=0, sticky="w", padx=10)
text_partial_compare = ScrolledText(frame_diff, height=20, width=75, bg="#fefefe", relief="ridge", bd=2)
text_partial_compare.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

# Base ด้านขวา
ttk.Label(frame_diff, text="📂 JSON Base - ส่วนที่ต่าง", style="Header.TLabel").grid(row=0, column=1, sticky="w", padx=10)
text_partial_base = ScrolledText(frame_diff, height=20, width=75, bg="#fefefe", relief="ridge", bd=2)
text_partial_base.grid(row=1, column=1, padx=10, pady=(0, 10), sticky="nsew")

frame_diff.grid_columnconfigure(0, weight=1)
frame_diff.grid_columnconfigure(1, weight=1)
frame_diff.grid_rowconfigure(1, weight=1)

# ==== ปุ่มคัดลอก ====
button_frame = ttk.Frame(root)
button_frame.pack(pady=10)

ttk.Button(button_frame, text="📋 Copy Compare Diff", command=lambda: copy_text(text_partial_compare)).grid(row=0, column=0, padx=20)
ttk.Button(button_frame, text="📋 Copy Base Diff", command=lambda: copy_text(text_partial_base)).grid(row=0, column=1, padx=20)

root.mainloop()