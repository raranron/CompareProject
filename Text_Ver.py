import json
import tkinter as tk
from tkinter import ttk, messagebox
import pyperclip
import re
from deepdiff import DeepDiff

# ----------------- JSON Utility -----------------
def remove_description(obj):
    if isinstance(obj, dict):
        obj.pop("description", None)
        for v in obj.values():
            remove_description(v)
    elif isinstance(obj, list):
        for item in obj:
            remove_description(item)

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

def reorder_and_format_promos(base_data, compare_data):
    def extract_promos(data):
        return {promo["promoNumber"]: promo for promo in data.get("promoInfo", []) if "promoNumber" in promo}

    base_promos = extract_promos(base_data)
    compare_promos = extract_promos(compare_data)
    all_keys = sorted(set(base_promos) | set(compare_promos),
                      key=lambda x: (x not in base_promos or x not in compare_promos, str(x)))

    def format_promos(promos, keys):
        out = []
        for key in keys:
            if key in promos:
                out.append(f"========== promoNumber: {key} ==========")
                out.append(json.dumps(promos[key], indent=2, ensure_ascii=False))
                out.append("")
        return out

    def format_other_fields(data):
        return [f"\"{k}\": {json.dumps(v, indent=2, ensure_ascii=False)}\n" for k, v in data.items() if k != "promoInfo"]

    base_output = format_promos(base_promos, all_keys) + format_other_fields(base_data)
    compare_output = format_promos(compare_promos, all_keys) + format_other_fields(compare_data)

    return ("\n".join(base_output).strip(), "\n".join(compare_output).strip())

# ----------------- GUI Utility -----------------
def copy_text(widget):
    content = widget.get("1.0", tk.END).strip()
    if content:
        try:
            root.clipboard_clear()
            root.clipboard_append(content)
            messagebox.showinfo("คัดลอกแล้ว", "ข้อความถูกคัดลอกไปยังคลิปบอร์ดเรียบร้อยแล้ว")
        except Exception as e:
            messagebox.showerror("ผิดพลาด", f"ไม่สามารถคัดลอกข้อความได้:\n{e}")
    else:
        messagebox.showwarning("ว่างเปล่า", "ไม่มีข้อความให้คัดลอก")

def add_right_click_menu(widget):
    menu = tk.Menu(widget, tearoff=0, bg="#2e2e2e", fg="#f8f8f2")
    menu.add_command(label="วาง (Paste)", command=lambda: widget.event_generate("<<Paste>>"))
    def popup(event):
        menu.tk_popup(event.x_root, event.y_root)
    widget.bind("<Button-3>", popup)

def bind_scroll(widget):
    widget.bind("<Enter>", lambda e: widget.bind_all("<MouseWheel>", lambda ev: widget.yview_scroll(int(-1*(ev.delta/120)), "units")))
    widget.bind("<Leave>", lambda e: widget.unbind_all("<MouseWheel>"))

def bind_paste_shortcuts(widget):
    def do_paste(event):
        widget.event_generate("<<Paste>>")
        return "break"
    widget.bind("<Control-v>", do_paste)
    widget.bind("<Control-V>", do_paste)
    widget.bind("<Shift-Insert>", do_paste)
    widget.bind("<Control-Insert>", do_paste)

def highlight_promo_lines(text_widget):
    text_widget.tag_configure("highlight", foreground="#00ff00", font=("Segoe UI", 10, "bold"))
    start = "1.0"
    while True:
        start = text_widget.search(r"^=+ promoNumber: .* =+$", start, stopindex=tk.END, regexp=True)
        if not start:
            break
        end = f"{start} lineend"
        text_widget.tag_add("highlight", start, end)
        start = end

def compare_json():
    try:
        base_data = json.loads(text_base.get("1.0", tk.END))
        compare_data = json.loads(text_compare.get("1.0", tk.END))
    except json.JSONDecodeError as e:
        messagebox.showerror("รูปแบบ JSON ไม่ถูกต้อง", str(e))
        return

    remove_description(base_data)
    remove_description(compare_data)

    base_filtered = filter_out_debug(base_data)
    compare_filtered = filter_out_debug(compare_data)

    diff = DeepDiff(base_filtered, compare_filtered, ignore_order=False, report_repetition=True, view="tree")

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

    base_result, compare_result = reorder_and_format_promos(partial_base, partial_compare)

    text_partial_base.delete("1.0", tk.END)
    text_partial_compare.delete("1.0", tk.END)
    text_partial_base.insert(tk.END, base_result)
    text_partial_compare.insert(tk.END, compare_result)

    # ไฮไลท์ promoNumber lines
    highlight_promo_lines(text_partial_base)
    highlight_promo_lines(text_partial_compare)

    total_diff = sum(len(diff[section]) for section in diff)
    label_result.config(text=f"🔍 พบความแตกต่างทั้งหมด {total_diff} จุด (เทียบแบบ jsoncompare.org)")

# ----------------- GUI -----------------
root = tk.Tk()
root.title("🧠 JSON Compare Tool")
root.attributes("-fullscreen", True)

is_fullscreen = True

def toggle_fullscreen(event=None):
    global is_fullscreen
    is_fullscreen = not is_fullscreen
    root.attributes("-fullscreen", is_fullscreen)

def exit_fullscreen(event=None):
    global is_fullscreen
    is_fullscreen = False
    root.attributes("-fullscreen", False)

root.bind("<F11>", toggle_fullscreen)
root.bind("<Escape>", exit_fullscreen)

DARK_BG = "#2e2e2e"
DARK_TEXT = "#f8f8f2"
TEXTBOX_BG = "#1e1e1e"
HIGHLIGHT = "#3c3f41"

root.configure(bg=DARK_BG)

style = ttk.Style()
style.theme_use("clam")
style.configure("TFrame", background=DARK_BG)
style.configure("TLabel", background=DARK_BG, foreground=DARK_TEXT)
style.configure("Header.TLabel", font=("Segoe UI", 13, "bold"), background=DARK_BG, foreground=DARK_TEXT)
style.configure("TButton", background=HIGHLIGHT, foreground="#ffffff", relief="flat", padding=6)
style.map("TButton", background=[("active", "#505354")], foreground=[("active", "#ffffff")])
style.configure("TLabelframe", background=DARK_BG, foreground=DARK_TEXT)
style.configure("TLabelframe.Label", background=DARK_BG, foreground=DARK_TEXT)

root.grid_rowconfigure(1, weight=1)
root.grid_columnconfigure(0, weight=1)

ttk.Label(root, text="🧠 JSON Compare Tool", style="Header.TLabel").grid(row=0, column=0, pady=(10, 5))

frame_input = ttk.Frame(root)
frame_input.grid(row=1, column=0, sticky="nsew", padx=10)
frame_input.grid_columnconfigure(0, weight=1)
frame_input.grid_columnconfigure(1, weight=1)
frame_input.grid_rowconfigure(0, weight=1)

frame_compare = ttk.Frame(frame_input)
frame_compare.grid(row=0, column=0, padx=(0,5), sticky="nsew")
ttk.Label(frame_compare, text="📙 JSON Compare (NewPro.json)", style="Header.TLabel").pack(anchor="w")
text_compare = tk.Text(frame_compare, bg=TEXTBOX_BG, fg=DARK_TEXT, insertbackground="white", relief="groove")
text_compare.pack(fill="both", expand=True)
add_right_click_menu(text_compare)
bind_scroll(text_compare)
bind_paste_shortcuts(text_compare)

frame_base = ttk.Frame(frame_input)
frame_base.grid(row=0, column=1, padx=(5,0), sticky="nsew")
ttk.Label(frame_base, text="📘 JSON Base (Onlinepro.json)", style="Header.TLabel").pack(anchor="w")
text_base = tk.Text(frame_base, bg=TEXTBOX_BG, fg=DARK_TEXT, insertbackground="white", relief="groove")
text_base.pack(fill="both", expand=True)
add_right_click_menu(text_base)
bind_scroll(text_base)
bind_paste_shortcuts(text_base)

ttk.Button(root, text="🔍 เปรียบเทียบ JSON", command=compare_json).grid(row=2, column=0, pady=10)

label_result = ttk.Label(root, text="", foreground="#66ff99", background=DARK_BG, font=("Segoe UI", 12, "bold"))
label_result.grid(row=3, column=0, pady=5)

frame_copy = ttk.Frame(root)
frame_copy.grid(row=4, column=0)
ttk.Button(frame_copy, text="📋 Copy Compare Diff", command=lambda: copy_text(text_partial_compare)).pack(side="left", padx=15)
ttk.Button(frame_copy, text="📋 Copy Base Diff", command=lambda: copy_text(text_partial_base)).pack(side="left", padx=15)

frame_output = ttk.Frame(root)
frame_output.grid(row=5, column=0, sticky="nsew", padx=10, pady=(0,10))
frame_output.grid_columnconfigure(0, weight=1)
frame_output.grid_columnconfigure(1, weight=1)
frame_output.grid_rowconfigure(0, weight=1)

frame_diff_compare = ttk.Frame(frame_output)
frame_diff_compare.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
ttk.Label(frame_diff_compare, text="📙 JSON Compare - Differences", style="Header.TLabel").pack(anchor="w")
text_partial_compare = tk.Text(frame_diff_compare, bg=TEXTBOX_BG, fg=DARK_TEXT, insertbackground="white", relief="ridge")
text_partial_compare.pack(fill="both", expand=True)
add_right_click_menu(text_partial_compare)
bind_scroll(text_partial_compare)
bind_paste_shortcuts(text_partial_compare)

frame_diff_base = ttk.Frame(frame_output)
frame_diff_base.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
ttk.Label(frame_diff_base, text="📘 JSON Base - Differences", style="Header.TLabel").pack(anchor="w")
text_partial_base = tk.Text(frame_diff_base, bg=TEXTBOX_BG, fg=DARK_TEXT, insertbackground="white", relief="ridge")
text_partial_base.pack(fill="both", expand=True)
add_right_click_menu(text_partial_base)
bind_scroll(text_partial_base)
bind_paste_shortcuts(text_partial_base)

root.mainloop()
