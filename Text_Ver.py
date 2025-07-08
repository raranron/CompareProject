import json
import tkinter as tk
from tkinter import Tk, Text, Button, Label, Frame, END, messagebox
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

            # ตรวจสอบว่ามี key/index ใน current_src หรือไม่
            if isinstance(current_src, dict):
                if key not in current_src:
                    break
            elif isinstance(current_src, list):
                if not (isinstance(key, int) and 0 <= key < len(current_src)):
                    break
            else:
                break

            if isinstance(key, int):
                if not isinstance(current_partial, list):
                    if isinstance(current_partial, dict) and not current_partial:
                        new_list = []
                        if parents:
                            parent, parent_key = parents[-1]
                            parent[parent_key] = new_list
                            current_partial = new_list
                        else:
                            partial = []
                            current_partial = partial
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

def copy_text(text_widget):
    text = text_widget.get("1.0", END).strip()
    if text:
        pyperclip.copy(text)
        messagebox.showinfo("คัดลอกแล้ว", "ข้อความถูกคัดลอกไปยังคลิปบอร์ดเรียบร้อยแล้ว")
    else:
        messagebox.showwarning("ว่างเปล่า", "ไม่มีข้อความให้คัดลอก")

def compare_json():
    try:
        base_data = json.loads(text_base.get("1.0", END))
        compare_data = json.loads(text_compare.get("1.0", END))
    except json.JSONDecodeError as e:
        messagebox.showerror("ข้อผิดพลาด JSON", f"รูปแบบ JSON ไม่ถูกต้อง:\n{e}")
        return

    base_filtered = filter_out_debug(base_data)
    compare_filtered = filter_out_debug(compare_data)

    diff = DeepDiff(base_filtered, compare_filtered, ignore_order=True)

    if not diff:
        label_result.config(text="✅ ไม่มีความแตกต่างระหว่าง JSON ทั้งสองไฟล์")
        text_partial_base.delete("1.0", END)
        text_partial_compare.delete("1.0", END)
        return

    changed_paths = []
    for key in ["values_changed", "dictionary_item_added", "iterable_item_added", "type_changes"]:
        changes = diff.get(key, {})
        if hasattr(changes, "keys"):
            changed_paths.extend(changes.keys())
        else:
            changed_paths.extend(changes)

    partial_base = build_partial_json(base_filtered, changed_paths)
    partial_compare = build_partial_json(compare_filtered, changed_paths)

    text_partial_base.delete("1.0", END)
    text_partial_compare.delete("1.0", END)

    text_partial_base.insert(END, json.dumps(partial_base, indent=2, ensure_ascii=False))
    text_partial_compare.insert(END, json.dumps(partial_compare, indent=2, ensure_ascii=False))

    diff_count = sum(len(diff.get(k, {})) for k in diff)
    label_result.config(text=f"🔍 พบความแตกต่างทั้งหมด {diff_count} จุด")

def paste_text(event=None):
    try:
        clipboard = root.clipboard_get()
        widget = root.focus_get()
        if isinstance(widget, ScrolledText):
            widget.insert(tk.INSERT, clipboard)
    except:
        pass

def show_context_menu(event):
    context_menu.tk_popup(event.x_root, event.y_root)

root = Tk()
root.title("JSON Compare - แสดงส่วนต่างแบบ Partial JSON")
root.geometry("1200x900")

# Input JSON Base
Label(root, text="📘 JSON Base (Onlinepro.json)", font=("Arial", 12, "bold")).pack()
text_base = ScrolledText(root, height=10, width=140)
text_base.pack(pady=5)

# Input JSON Compare
Label(root, text="📙 JSON Compare (NewPro.json)", font=("Arial", 12, "bold")).pack()
text_compare = ScrolledText(root, height=10, width=140)
text_compare.pack(pady=5)

Button(root, text="🔍 เปรียบเทียบ JSON", command=compare_json, height=2, width=20).pack(pady=10)

label_result = Label(root, text="", fg="green", font=("Arial", 14))
label_result.pack()

frame_diff = Frame(root)
frame_diff.pack(pady=10)

# Partial Base JSON
Label(frame_diff, text="📂 JSON Base - ส่วนที่ต่าง", font=("Arial", 12, "bold")).grid(row=0, column=0)
text_partial_base = ScrolledText(frame_diff, height=20, width=70)
text_partial_base.grid(row=1, column=0, padx=10)
Button(frame_diff, text="📋 Copy Base Diff", command=lambda: copy_text(text_partial_base)).grid(row=2, column=0, pady=5)

# Partial Compare JSON
Label(frame_diff, text="📂 JSON Compare - ส่วนที่ต่าง", font=("Arial", 12, "bold")).grid(row=0, column=1)
text_partial_compare = ScrolledText(frame_diff, height=20, width=70)
text_partial_compare.grid(row=1, column=1, padx=10)
Button(frame_diff, text="📋 Copy Compare Diff", command=lambda: copy_text(text_partial_compare)).grid(row=2, column=1, pady=5)

# สร้างเมนูคลิกขวา
context_menu = tk.Menu(root, tearoff=0)
context_menu.add_command(label="วาง (Paste)", command=lambda: root.focus_get().event_generate('<<Paste>>'))

# ผูกเมนูคลิกขวาและ Ctrl+V ให้กับ text widget ทั้งสอง
text_base.bind("<Button-3>", show_context_menu)
text_compare.bind("<Button-3>", show_context_menu)
root.bind_all("<Control-v>", paste_text)

root.mainloop()
