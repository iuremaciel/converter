"""PDF/A Lote - desktop batch-conversion front end for Windows."""
from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import shlex

APP_DIR = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent
if APP_DIR.is_file():
    APP_DIR = APP_DIR.parent
SETTINGS = APP_DIR / "pdfa_lote_config.json"
PROFILES = ["1b", "1a", "2b", "2u", "2a", "3b", "3u", "3a", "4", "4e", "4f"]
GS_PROFILES = {"1b", "2b", "3b"}


def load_settings():
    try:
        return json.loads(SETTINGS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"converter": "", "args": "--profile {profile} --input {input} --output {output}", "verapdf": "", "gs_def": ""}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF/A Lote")
        self.geometry("1000x690")
        self.minsize(820, 570)
        self.configure(bg="#f4f6fa")
        self.files: list[Path] = []
        self.events: queue.Queue = queue.Queue()
        self.settings = load_settings()
        self.profile = tk.StringVar(value="2b")
        self.outdir = tk.StringVar(value="")
        self.overwrite = tk.BooleanVar(value=False)
        self._style()
        self._build()
        self.after(120, self._poll)

    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TFrame", background="#f4f6fa")
        s.configure("Card.TFrame", background="#ffffff")
        s.configure("TLabel", background="#f4f6fa", foreground="#182235", font=("Segoe UI", 10))
        s.configure("Card.TLabel", background="#ffffff", foreground="#182235", font=("Segoe UI", 10))
        s.configure("Title.TLabel", font=("Segoe UI", 23, "bold"), foreground="#14213d")
        s.configure("Sub.TLabel", foreground="#617089", font=("Segoe UI", 10))
        s.configure("Treeview", font=("Segoe UI", 10), rowheight=31, background="white", fieldbackground="white")
        s.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        s.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=(15, 9))
        s.configure("TButton", padding=(10, 7))

    def _build(self):
        root = ttk.Frame(self, padding=(28, 22, 28, 20)); root.pack(fill="both", expand=True)
        top = ttk.Frame(root); top.pack(fill="x")
        ttk.Label(top, text="PDF/A Lote", style="Title.TLabel").pack(side="left")
        ttk.Button(top, text="Configurar motor", command=self._settings_dialog).pack(side="right", anchor="s", pady=5)
        ttk.Label(root, text="Converta vários PDFs de uma vez e confira a conformidade de cada resultado.", style="Sub.TLabel").pack(anchor="w", pady=(2, 18))

        card = ttk.Frame(root, style="Card.TFrame", padding=16); card.pack(fill="both", expand=True)
        bar = ttk.Frame(card, style="Card.TFrame"); bar.pack(fill="x", pady=(0, 12))
        ttk.Button(bar, text="＋  Adicionar PDFs", command=self._add).pack(side="left")
        ttk.Button(bar, text="Adicionar pasta", command=self._add_folder).pack(side="left", padx=8)
        ttk.Button(bar, text="Remover selecionados", command=self._remove).pack(side="left")
        self.count = ttk.Label(bar, text="0 arquivos", style="Card.TLabel"); self.count.pack(side="right")

        cols = ("file", "size", "status")
        self.table = ttk.Treeview(card, columns=cols, show="headings", selectmode="extended")
        self.table.heading("file", text="ARQUIVO PDF"); self.table.heading("size", text="TAMANHO"); self.table.heading("status", text="STATUS")
        self.table.column("file", width=600, anchor="w"); self.table.column("size", width=100, anchor="e"); self.table.column("status", width=180, anchor="w")
        self.table.pack(fill="both", expand=True)
        self.table.tag_configure("ok", foreground="#16734a"); self.table.tag_configure("bad", foreground="#b42318")

        controls = ttk.Frame(root); controls.pack(fill="x", pady=(15, 0))
        ttk.Label(controls, text="Formato de saída").grid(row=0, column=0, sticky="w")
        self.combo = ttk.Combobox(controls, textvariable=self.profile, values=PROFILES, state="readonly", width=11)
        self.combo.grid(row=1, column=0, sticky="w", pady=(5, 0))
        ttk.Label(controls, text="Ex.: PDF/A-2b").grid(row=1, column=1, sticky="w", padx=(10, 0))
        ttk.Label(controls, text="Pasta de destino").grid(row=0, column=2, sticky="w", padx=(28, 0))
        dest = ttk.Frame(controls); dest.grid(row=1, column=2, sticky="ew", padx=(28, 0), pady=(5, 0))
        ttk.Entry(dest, textvariable=self.outdir).pack(side="left", fill="x", expand=True)
        ttk.Button(dest, text="Escolher…", command=self._choose_out).pack(side="left", padx=(6, 0))
        controls.columnconfigure(2, weight=1)
        bottom = ttk.Frame(root); bottom.pack(fill="x", pady=(17, 0))
        ttk.Checkbutton(bottom, text="Substituir arquivos existentes", variable=self.overwrite).pack(side="left")
        self.progress = ttk.Progressbar(bottom, mode="determinate", length=170)
        self.progress.pack(side="right", padx=(12, 0))
        self.convert_btn = ttk.Button(bottom, text="Converter lote", style="Accent.TButton", command=self._start)
        self.convert_btn.pack(side="right")
        self.status = ttk.Label(root, text="Pronto. Adicione PDFs para começar.", style="Sub.TLabel")
        self.status.pack(anchor="w", pady=(12, 0))
        ttk.Label(root, text="A aprovação de conformidade depende da validação do arquivo gerado. Conversão concluída não significa PDF/A válido.", style="Sub.TLabel").pack(anchor="w", pady=(4, 0))

    def _add(self):
        for f in filedialog.askopenfilenames(title="Selecionar PDFs", filetypes=[("Arquivos PDF", "*.pdf")]):
            self._append(Path(f))

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Selecionar pasta com PDFs")
        if folder:
            for f in sorted(Path(folder).glob("*.pdf")):
                self._append(f)

    def _append(self, p):
        p = p.resolve()
        if p not in self.files and p.is_file():
            self.files.append(p)
            self.table.insert("", "end", iid=str(len(self.files)-1), values=(p.name, self._size(p.stat().st_size), "Aguardando"))
            self._refresh_count()

    def _size(self, n):
        return f"{n/1048576:.2f} MB" if n >= 1048576 else f"{n/1024:.0f} KB"

    def _refresh_count(self):
        self.count.configure(text=f"{len(self.files)} arquivo(s)")

    def _remove(self):
        for iid in self.table.selection():
            index = int(iid)
            self.files[index] = None
            self.table.delete(iid)
        self.files = [f for f in self.files if f is not None]
        self._rebuild_table(); self._refresh_count()

    def _rebuild_table(self):
        for i in self.table.get_children(): self.table.delete(i)
        for i, p in enumerate(self.files):
            self.table.insert("", "end", iid=str(i), values=(p.name, self._size(p.stat().st_size), "Aguardando"))

    def _choose_out(self):
        folder = filedialog.askdirectory(title="Pasta para os PDFs convertidos")
        if folder: self.outdir.set(folder)

    def _settings_dialog(self):
        win = tk.Toplevel(self); win.title("Motor de conversão e validação"); win.configure(bg="#f4f6fa"); win.resizable(False, False)
        win.transient(self); win.grab_set()
        box = ttk.Frame(win, padding=20); box.pack(fill="both", expand=True)
        ttk.Label(box, text="Motor completo (executável)").grid(row=0, column=0, sticky="w")
        conv = tk.StringVar(value=self.settings.get("converter", ""))
        ttk.Entry(box, textvariable=conv, width=64).grid(row=1, column=0, sticky="ew", pady=5)
        ttk.Button(box, text="Procurar…", command=lambda: conv.set(filedialog.askopenfilename(title="Executável do conversor"))).grid(row=1, column=1, padx=(7, 0))
        ttk.Label(box, text="Argumentos (tokens separados por espaço; use os marcadores abaixo)").grid(row=2, column=0, sticky="w", pady=(12, 0))
        args = tk.StringVar(value=self.settings.get("args", "--profile {profile} --input {input} --output {output}"))
        ttk.Entry(box, textvariable=args, width=80).grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)
        ttk.Label(box, text="Marcadores: {profile}, {input}, {output}. O conversor precisa aceitar argumentos de linha de comando.", style="Sub.TLabel").grid(row=4, column=0, columnspan=2, sticky="w")
        ttk.Label(box, text="veraPDF (validador opcional)").grid(row=5, column=0, sticky="w", pady=(13, 0))
        validator = tk.StringVar(value=self.settings.get("verapdf", ""))
        ttk.Entry(box, textvariable=validator, width=64).grid(row=6, column=0, sticky="ew", pady=5)
        ttk.Button(box, text="Procurar…", command=lambda: validator.set(filedialog.askopenfilename(title="Executável do veraPDF"))).grid(row=6, column=1, padx=(7, 0))
        ttk.Label(box, text="Arquivo PDFA_def.ps do Ghostscript (com perfil ICC válido)").grid(row=7, column=0, sticky="w", pady=(12, 0))
        gsdef = tk.StringVar(value=self.settings.get("gs_def", ""))
        ttk.Entry(box, textvariable=gsdef, width=64).grid(row=8, column=0, sticky="ew", pady=5)
        ttk.Button(box, text="Procurar…", command=lambda: gsdef.set(filedialog.askopenfilename(title="Arquivo PDFA_def.ps", filetypes=[("PostScript", "*.ps"), ("Todos", "*.*")]))).grid(row=8, column=1, padx=(7, 0))
        ttk.Label(box, text="Ghostscript só converte diretamente para 1b, 2b e 3b. Os demais perfis exigem um motor completo configurado aqui. A conversão Ghostscript requer PDFA_def.ps configurado com um ICC válido.", wraplength=590, style="Sub.TLabel").grid(row=9, column=0, columnspan=2, sticky="w", pady=(8, 0))
        def save():
            self.settings = {"converter": conv.get().strip(), "args": args.get().strip(), "verapdf": validator.get().strip(), "gs_def": gsdef.get().strip()}
            SETTINGS.write_text(json.dumps(self.settings, indent=2, ensure_ascii=False), encoding="utf-8")
            win.destroy()
        ttk.Button(box, text="Salvar configurações", command=save).grid(row=8, column=1, sticky="e", pady=(16, 0))

    def _start(self):
        if not self.files:
            messagebox.showinfo("PDF/A Lote", "Adicione pelo menos um PDF."); return
        dest = Path(self.outdir.get().strip()) if self.outdir.get().strip() else self.files[0].parent / "PDF-A"
        try: dest.mkdir(parents=True, exist_ok=True)
        except OSError as e: messagebox.showerror("Pasta de destino", str(e)); return
        profile = self.profile.get()
        exe = self.settings.get("converter", "").strip()
        gs = shutil.which("gswin64c") or shutil.which("gswin32c") or shutil.which("gs")
        if exe and Path(exe).is_file():
            mode = "external"
        elif profile in GS_PROFILES and gs and Path(self.settings.get("gs_def", "")).is_file():
            mode = "ghostscript"
        else:
            messagebox.showerror("Motor não configurado", "Configure um conversor de PDF/A em 'Configurar motor'. O Ghostscript pode ser usado automaticamente apenas nos perfis 1b, 2b e 3b, com o arquivo PDFA_def.ps configurado e um perfil ICC válido.")
            return
        overwrite = self.overwrite.get()
        self.convert_btn.configure(state="disabled")
        self.progress.configure(maximum=len(self.files), value=0)
        for i in range(len(self.files)):
            self.table.set(str(i), "status", "Na fila")
        thread = threading.Thread(target=self._worker, args=(dest, profile, mode, exe, gs, overwrite), daemon=True)
        thread.start()

    def _worker(self, dest, profile, mode, exe, gs, overwrite):
        files = list(self.files); args_template = self.settings.get("args", "--profile {profile} --input {input} --output {output}")
        validator = self.settings.get("verapdf", "").strip()
        for i, src in enumerate(files):
            if not src: continue
            target = dest / f"{src.stem}_PDFA-{profile}.pdf"
            self.events.put(("row", i, "Convertendo…", ""))
            try:
                if target.exists() and not overwrite:
                    raise FileExistsError(f"O destino já existe: {target.name}")
                if mode == "external":
                    template = args_template.replace("{profile}", profile).replace("{input}", str(src)).replace("{output}", str(target))
                    command = [exe, *shlex.split(template)]
                else:
                    # Respect Ghostscript's published PDF/A limits. Its success is provisional until validator passes.
                    command = [gs, "-dBATCH", "-dNOPAUSE", "-dSAFER", f"-dPDFA={profile[0]}", "-dPDFACompatibilityPolicy=2", "-sColorConversionStrategy=RGB", "-sDEVICE=pdfwrite", f"-sOutputFile={target}", self.settings["gs_def"], str(src)]
                result = subprocess.run(command, capture_output=True, text=True, timeout=900)
                if result.returncode != 0 or not target.is_file():
                    raise RuntimeError((result.stderr or result.stdout or "Conversor terminou com erro")[-1000:])
                if validator and Path(validator).is_file():
                    v = subprocess.run([validator, "-f", profile, "--format", "xml", str(target)], capture_output=True, text=True, timeout=300)
                    import xml.etree.ElementTree as ET
                    report = ET.fromstring(v.stdout)
                    verdicts = [x.attrib.get("isCompliant", "").lower() for x in report.iter() if x.tag.endswith("validationReport")]
                    if v.returncode == 0 and verdicts and all(x == "true" for x in verdicts):
                        label = "PDF/A validado"
                    else:
                        raise RuntimeError("Arquivo convertido, mas reprovado ou não confirmado pelo veraPDF. " + (v.stdout + "\n" + v.stderr)[-700:])
                else:
                    label = "Convertido; falta validar"
                self.events.put(("row", i, label, "ok"))
            except Exception as e:
                self.events.put(("row", i, "Falhou: " + str(e)[:180], "bad"))
            self.events.put(("progress", i + 1, len(files)))
        self.events.put(("done",))

    def _poll(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "row":
                    _, i, msg, tag = event
                    if str(i) in self.table.get_children():
                        self.table.set(str(i), "status", msg); self.table.item(str(i), tags=(tag,) if tag else ())
                elif event[0] == "progress":
                    _, value, total = event; self.progress.configure(value=value); self.status.configure(text=f"Processados {value} de {total} arquivo(s).")
                elif event[0] == "done":
                    self.convert_btn.configure(state="normal"); self.status.configure(text="Lote finalizado. Confira o status individual de cada arquivo.")
        except queue.Empty:
            pass
        self.after(120, self._poll)


if __name__ == "__main__":
    App().mainloop()
