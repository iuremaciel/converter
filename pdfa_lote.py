"""PDF/A Lote - desktop batch-conversion front end for Windows."""
from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import tempfile
import webbrowser
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP_DIR = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent
if APP_DIR.is_file():
    APP_DIR = APP_DIR.parent
SETTINGS = APP_DIR / "pdfa_lote_config.json"
PROFILES = ["1b", "2b", "3b"]


def load_settings():
    try:
        return json.loads(SETTINGS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"verapdf": ""}


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
        ttk.Button(top, text="Licença", command=self._license_dialog).pack(side="right", anchor="s", pady=5)
        ttk.Button(top, text="Validador opcional", command=self._settings_dialog).pack(side="right", anchor="s", padx=(0, 8), pady=5)
        ttk.Label(root, text="Converta PDFs em lote para PDF/A-1b, 2b ou 3b. Ghostscript já vem incluído no pacote.", style="Sub.TLabel").pack(anchor="w", pady=(2, 18))

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
        win = tk.Toplevel(self); win.title("Validação PDF/A"); win.configure(bg="#f4f6fa"); win.resizable(False, False)
        win.transient(self); win.grab_set()
        box = ttk.Frame(win, padding=20); box.pack(fill="both", expand=True)
        ttk.Label(box, text="Ghostscript já está incluído e faz as conversões PDF/A-1b, 2b e 3b.", wraplength=580).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(box, text="veraPDF (validador opcional)").grid(row=1, column=0, sticky="w", pady=(13, 0))
        validator = tk.StringVar(value=self.settings.get("verapdf", ""))
        ttk.Entry(box, textvariable=validator, width=64).grid(row=2, column=0, sticky="ew", pady=5)
        ttk.Button(box, text="Procurar…", command=lambda: validator.set(filedialog.askopenfilename(title="Executável do veraPDF"))).grid(row=2, column=1, padx=(7, 0))
        ttk.Label(box, text="Sem validação, o app informa ‘Convertido; falta validar’. Para confirmar formalmente a conformidade, configure o veraPDF.", wraplength=590, style="Sub.TLabel").grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))
        def save():
            self.settings = {"verapdf": validator.get().strip()}
            SETTINGS.write_text(json.dumps(self.settings, indent=2, ensure_ascii=False), encoding="utf-8")
            win.destroy()
        ttk.Button(box, text="Salvar configurações", command=save).grid(row=4, column=1, sticky="e", pady=(16, 0))

    def _license_dialog(self):
        messagebox.showinfo(
            "Licença e avisos legais",
            "PDF/A Lote — Copyright (C) 2026 iuremaciel.\n\n"
            "Este programa é distribuído sem qualquer garantia, sob a GNU Affero General Public License versão 3 (AGPL-3.0). "
            "Você pode redistribuí-lo e modificá-lo conforme os termos dessa licença.\n\n"
            "A cópia da licença está no arquivo LICENSE junto ao aplicativo. "
            "O pacote também inclui Ghostscript da Artifex; consulte TERCEIROS.md para os avisos e o código-fonte correspondente."
        )

    def _start(self):
        if not self.files:
            messagebox.showinfo("PDF/A Lote", "Adicione pelo menos um PDF."); return
        dest = Path(self.outdir.get().strip()) if self.outdir.get().strip() else self.files[0].parent / "PDF-A"
        try: dest.mkdir(parents=True, exist_ok=True)
        except OSError as e: messagebox.showerror("Pasta de destino", str(e)); return
        profile = self.profile.get()
        gs, gs_root = self._find_ghostscript()
        if not gs:
            messagebox.showerror("Ghostscript ausente", "Não encontrei o Ghostscript incluído neste pacote. Extraia o ZIP completo e execute PDF-A-Lote.exe pela pasta extraída.")
            return
        overwrite = self.overwrite.get()
        self.convert_btn.configure(state="disabled")
        self.progress.configure(maximum=len(self.files), value=0)
        for i in range(len(self.files)):
            self.table.set(str(i), "status", "Na fila")
        thread = threading.Thread(target=self._worker, args=(dest, profile, gs, gs_root, overwrite), daemon=True)
        thread.start()

    def _find_ghostscript(self):
        bundled = APP_DIR / "vendor" / "ghostscript"
        if bundled.exists():
            for exe in bundled.rglob("gswin64c.exe"):
                root = exe.parent.parent
                if (root / "iccprofiles" / "default_rgb.icc").is_file() and (root / "lib" / "PDFA_def.ps").is_file():
                    return exe, root
        for name in ("gswin64c", "gswin32c", "gs"):
            path = shutil.which(name)
            if path:
                exe = Path(path)
                root = exe.parent.parent
                if (root / "iccprofiles" / "default_rgb.icc").is_file() and (root / "lib" / "PDFA_def.ps").is_file():
                    return exe, root
        return None, None

    def _worker(self, dest, profile, gs, gs_root, overwrite):
        files = list(self.files)
        validator = self.settings.get("verapdf", "").strip()
        for i, src in enumerate(files):
            if not src: continue
            target = dest / f"{src.stem}_PDFA-{profile}.pdf"
            self.events.put(("row", i, "Convertendo…", ""))
            try:
                if target.exists() and not overwrite:
                    raise FileExistsError(f"O destino já existe: {target.name}")
                # Deriva o ficheiro de definição do exemplo oficial e aponta para o ICC empacotado.
                template = (gs_root / "lib" / "PDFA_def.ps").read_text(encoding="latin-1")
                icc = (gs_root / "iccprofiles" / "default_rgb.icc").resolve()
                with tempfile.NamedTemporaryFile("w", suffix="_PDFA_def.ps", encoding="latin-1", delete=False) as f:
                    def_path = Path(f.name)
                    import re
                    template, count = re.subn(r"\([^)]*\.icc\)", "(" + icc.as_posix() + ")", template, count=1, flags=re.IGNORECASE)
                    if count != 1:
                        raise RuntimeError("Não consegui preparar o perfil ICC do Ghostscript.")
                    f.write(template)
                command = [str(gs), "-dBATCH", "-dNOPAUSE", "-dSAFER", f"--permit-file-read={icc}", f"-dPDFA={profile[0]}", "-dPDFACompatibilityPolicy=2", "-sColorConversionStrategy=RGB", "-sDEVICE=pdfwrite", f"-sOutputFile={target}", str(def_path), str(src)]
                env = os.environ.copy()
                env["GS_LIB"] = os.pathsep.join(str(p) for p in (gs_root / "lib", gs_root / "Resource" / "Init", gs_root / "Resource") if p.exists())
                result = subprocess.run(command, capture_output=True, text=True, timeout=900, env=env)
                def_path.unlink(missing_ok=True)
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
