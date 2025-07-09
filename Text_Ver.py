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

    diff = DeepDiff(base_filtered, compare_filtered, ignore_order=False, report_repetition=True, view="tree")

    if not diff:
        label_result.config(text="✅ ไม่มีความแตกต่างระหว่าง JSON ทั้งสองไฟล์")
        text_partial_base.delete("1.0", END)
        text_partial_compare.delete("1.0", END)
        return

    path_list = []
    for section in diff:
        for change in diff[section]:
            if hasattr(change, 'path'):
                path = change.path(output_format='list')
                s = ""
                for p in path:
                    s += f"[{p}]" if isinstance(p, int) else f"['{p}']"
                path_list.append(s)

    partial_base = build_partial_json(base_filtered, path_list)
    partial_compare = build_partial_json(compare_filtered, path_list)

    text_partial_base.delete("1.0", END)
    text_partial_compare.delete("1.0", END)
    text_partial_base.insert(END, json.dumps(partial_base, indent=2, ensure_ascii=False))
    text_partial_compare.insert(END, json.dumps(partial_compare, indent=2, ensure_ascii=False))

    diff_count = sum(len(diff[section]) for section in diff)
    label_result.config(text=f"🔍 พบความแตกต่างทั้งหมด {diff_count} จุด (แบบ jsoncompare.org)")

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

# GUI Setup
root = Tk()
root.title("🧠 JSON Compare - แสดงความแตกต่างแบบ jsoncompare.org")
root.geometry("1200x900")

Label(root, text="📘 JSON Base (Onlinepro.json)", font=("Arial", 12, "bold")).pack()
text_base = ScrolledText(root, height=10, width=140)
text_base.pack(pady=5)

Label(root, text="📙 JSON Compare (NewPro.json)", font=("Arial", 12, "bold")).pack()
text_compare = ScrolledText(root, height=10, width=140)
text_compare.pack(pady=5)

Button(root, text="🔍 เปรียบเทียบ JSON", command=compare_json, height=2, width=20).pack(pady=10)

label_result = Label(root, text="", fg="green", font=("Arial", 14))
label_result.pack()

frame_diff = Frame(root)
frame_diff.pack(padx=10, pady=10, fill="both", expand=True)

# 🔁 สลับฝั่ง
Label(frame_diff, text="📂 JSON Compare - ส่วนที่ต่าง", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w")
text_partial_compare = ScrolledText(frame_diff, height=20, width=70)
text_partial_compare.grid(row=1, column=0, padx=10, pady=(0,10), sticky="nsew")

Label(frame_diff, text="📂 JSON Base - ส่วนที่ต่าง", font=("Arial", 12, "bold")).grid(row=0, column=1, sticky="w")
text_partial_base = ScrolledText(frame_diff, height=20, width=70)
text_partial_base.grid(row=1, column=1, padx=10, pady=(0,10), sticky="nsew")

frame_diff.grid_columnconfigure(0, weight=1)
frame_diff.grid_columnconfigure(1, weight=1)
frame_diff.grid_rowconfigure(1, weight=1)

# Copy buttons
button_frame = Frame(frame_diff)
button_frame.grid(row=2, column=0, columnspan=2, pady=5)

btn_copy_compare = Button(button_frame, text="📋 Copy Compare Diff", command=lambda: copy_text(text_partial_compare))
btn_copy_compare.grid(row=0, column=0, padx=20, pady=5)

btn_copy_base = Button(button_frame, text="📋 Copy Base Diff", command=lambda: copy_text(text_partial_base))
btn_copy_base.grid(row=0, column=1, padx=20, pady=5)

# Paste context menu
context_menu = tk.Menu(root, tearoff=0)
context_menu.add_command(label="วาง (Paste)", command=lambda: root.focus_get().event_generate('<<Paste>>'))
text_base.bind("<Button-3>", show_context_menu)
text_compare.bind("<Button-3>", show_context_menu)
root.bind_all("<Control-v>", paste_text)

root.mainloop()
