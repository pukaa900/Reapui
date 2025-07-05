#!/usr/bin/env python3
"""Fa'aoga Tkinter ma pyttsx3 mo le tusiupu TTS."""

import tkinter as tk
from tkinter import ttk
import uuid
import re
import os
import pyttsx3
import pyperclip
import ttkbootstrap as tb

# ── Fesuia'iga autu ─────────────────────────────────────────────────────────
engine = pyttsx3.init()

# ── Galuega mo le tautala ─────────────────────────────────────────────────
def fai_tautala(lang_code: str, tusitusiga: str, sefe: bool = False) -> None:
    """Fa'alogo pe sefe le faila leo."""
    if not tusitusiga.strip():
        print("Leai se tusitusiga.")
        return
    # seti le faila pe a sefe
    faila = f"{re.sub(r'[^\w\-]+', '_', tusitusiga) or 'clip'}_{uuid.uuid4().hex[:8]}.wav"
    if sefe:
        engine.save_to_file(tusitusiga, faila)
        engine.runAndWait()
        print(f"Ua sefe i le {faila}")
    else:
        engine.say(tusitusiga)
        engine.runAndWait()

# ── Fonotaga fa'aogaina ───────────────────────────────────────────────────
root = tb.Window(themename="vapor")
root.title("REA TTS")
root.geometry("600x400")
root.resizable(True, True)

# ── Vaega mo le uluai gagana ───────────────────────────────────────────────
lang_label = ttk.Label(root, text="Tulafono o le gagana:")
lang_label.pack(anchor="w", padx=10, pady=(10, 0))
lang_var = tk.StringVar(value="en")
lang_entry = ttk.Entry(root, textvariable=lang_var)
lang_entry.pack(fill="x", padx=10)

# ── Vaega mo le tusitusiga ─────────────────────────────────────────────────
txt_label = ttk.Label(root, text="Tusitusiga e tautala:")
txt_label.pack(anchor="w", padx=10, pady=(10, 0))
text_frame = ttk.Frame(root)
text_frame.pack(fill="both", expand=True, padx=10)
text_scroll = ttk.Scrollbar(text_frame)
text_scroll.pack(side="right", fill="y")
text_box = tk.Text(text_frame, wrap="word", yscrollcommand=text_scroll.set)
text_box.insert("1.0", "Tusitusiga iinei")
text_box.pack(side="left", fill="both", expand=True)
text_scroll.config(command=text_box.yview)

# ── Galuega kopi/ta'ai ─────────────────────────────────────────────────────
text_box.bind("<Control-c>", lambda e: pyperclip.copy(text_box.get("sel.first", "sel.last")))
text_box.bind("<Control-v>", lambda e: text_box.insert(tk.INSERT, pyperclip.paste()))
lang_entry.bind("<Control-c>", lambda e: pyperclip.copy(lang_entry.selection_get()))
lang_entry.bind("<Control-v>", lambda e: lang_entry.insert(tk.INSERT, pyperclip.paste()))

# ── Uili o faamau ─────────────────────────────────────────────────────────
btn_frame = ttk.Frame(root)
btn_frame.pack(pady=10)

def faalogo():
    fai_tautala(lang_var.get(), text_box.get("1.0", "end"), sefe=False)

def sefe():
    fai_tautala(lang_var.get(), text_box.get("1.0", "end"), sefe=True)

speak_btn = ttk.Button(btn_frame, text="Fa'alogo", command=faalogo)
speak_btn.pack(side="left", padx=5)

save_btn = ttk.Button(btn_frame, text="Sefe", command=sefe)
save_btn.pack(side="left", padx=5)

root.mainloop()
