"""Organiza Fácil - organizador local de arquivos.

Aplicativo desktop sem dependências externas. Ele organiza somente os arquivos
da pasta escolhida, sem entrar em subpastas, e permite desfazer a última ação.
"""

from __future__ import annotations

import shutil
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


APP_TITLE = "Organiza Fácil"

FILE_GROUPS = {
    "Imagens": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".tif", ".tiff", ".ico"},
    "Documentos": {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".csv", ".ppt", ".pptx", ".md"},
    "Videos": {".mp4", ".mkv", ".mov", ".avi", ".webm", ".wmv", ".m4v"},
    "Audios": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"},
    "Compactados": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"},
    "Instaladores": {".exe", ".msi", ".apk", ".deb", ".rpm"},
    "Codigo": {".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".java", ".c", ".cpp", ".h", ".json", ".xml", ".sql", ".ps1", ".bat"},
}

APP_FILE_NAMES = {"organiza_facil.py", "executar_organiza_facil.bat"}


def classify_file(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    for group, extensions in FILE_GROUPS.items():
        if suffix in extensions:
            return group
    return "Outros"


def safe_destination(folder: Path, original_name: str) -> Path:
    """Return a destination that will never overwrite an existing file."""
    candidate = folder / original_name
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    counter = 1
    while True:
        candidate = folder / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


class OrganizaFacil(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("900x610")
        self.minsize(760, 500)
        self.configure(bg="#f4f6f8")

        self.selected_folder = tk.StringVar(value="")
        self.status_text = tk.StringVar(value="Escolha uma pasta para começar.")
        self.summary_text = tk.StringVar(value="Nenhuma pasta selecionada.")
        self.last_moves: list[tuple[Path, Path]] = []
        self.preview_rows: list[tuple[Path, str, Path]] = []

        self._configure_style()
        self._build_ui()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#f4f6f8")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("Title.TLabel", background="#f4f6f8", foreground="#182230", font=("Segoe UI", 22, "bold"))
        style.configure("Subtitle.TLabel", background="#f4f6f8", foreground="#536273", font=("Segoe UI", 10))
        style.configure("CardTitle.TLabel", background="#ffffff", foreground="#182230", font=("Segoe UI", 11, "bold"))
        style.configure("Body.TLabel", background="#ffffff", foreground="#3c4a5a", font=("Segoe UI", 9))
        style.configure("Status.TLabel", background="#e9eef3", foreground="#3c4a5a", padding=(10, 6), font=("Segoe UI", 9))
        style.configure("Primary.TButton", font=("Segoe UI", 9, "bold"), padding=(12, 7))
        style.configure("TButton", padding=(10, 6))

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=24)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text=APP_TITLE, style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            outer,
            text="Organize arquivos por tipo, com pré-visualização e desfazer.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(2, 18))

        folder_card = ttk.Frame(outer, style="Card.TFrame", padding=16)
        folder_card.pack(fill="x", pady=(0, 14))
        ttk.Label(folder_card, text="1. Escolha a pasta", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(
            folder_card,
            text="O aplicativo analisa apenas os arquivos diretamente dentro da pasta escolhida. Subpastas não são alteradas.",
            style="Body.TLabel",
        ).pack(anchor="w", pady=(4, 10))

        folder_row = ttk.Frame(folder_card, style="Card.TFrame")
        folder_row.pack(fill="x")
        ttk.Entry(folder_row, textvariable=self.selected_folder, state="readonly").pack(side="left", fill="x", expand=True)
        ttk.Button(folder_row, text="Escolher pasta", command=self.choose_folder).pack(side="left", padx=(10, 0))

        action_card = ttk.Frame(outer, style="Card.TFrame", padding=16)
        action_card.pack(fill="x", pady=(0, 14))
        ttk.Label(action_card, text="2. Confira e organize", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(
            action_card,
            text="Nada é movido na pré-visualização. Arquivos com o mesmo nome recebem um novo nome, sem sobrescrever o original.",
            style="Body.TLabel",
        ).pack(anchor="w", pady=(4, 10))
        button_row = ttk.Frame(action_card, style="Card.TFrame")
        button_row.pack(fill="x")
        ttk.Button(button_row, text="Pré-visualizar", style="Primary.TButton", command=self.preview).pack(side="left")
        ttk.Button(button_row, text="Organizar agora", command=self.organize).pack(side="left", padx=(8, 0))
        ttk.Button(button_row, text="Desfazer última organização", command=self.undo_last).pack(side="left", padx=(8, 0))
        ttk.Label(button_row, textvariable=self.summary_text, style="Body.TLabel").pack(side="right")

        list_card = ttk.Frame(outer, style="Card.TFrame", padding=12)
        list_card.pack(fill="both", expand=True)
        ttk.Label(list_card, text="Pré-visualização", style="CardTitle.TLabel").pack(anchor="w", padx=4, pady=(2, 8))

        tree_frame = ttk.Frame(list_card, style="Card.TFrame")
        tree_frame.pack(fill="both", expand=True)
        columns = ("arquivo", "categoria", "destino")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="none")
        self.tree.heading("arquivo", text="Arquivo")
        self.tree.heading("categoria", text="Categoria")
        self.tree.heading("destino", text="Pasta de destino")
        self.tree.column("arquivo", width=310, anchor="w")
        self.tree.column("categoria", width=150, anchor="w")
        self.tree.column("destino", width=230, anchor="w")
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        ttk.Label(self, textvariable=self.status_text, style="Status.TLabel", anchor="w").pack(fill="x", side="bottom")

    def choose_folder(self) -> None:
        chosen = filedialog.askdirectory(title="Escolha a pasta que deseja organizar")
        if not chosen:
            return
        self.selected_folder.set(chosen)
        self.last_moves = []
        self.preview_rows = []
        self._clear_tree()
        self.summary_text.set("Pronto para analisar.")
        self.status_text.set("Pasta selecionada. Clique em Pré-visualizar.")

    def _clear_tree(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _source_folder(self) -> Path | None:
        value = self.selected_folder.get().strip()
        if not value:
            messagebox.showinfo(APP_TITLE, "Escolha uma pasta antes de continuar.")
            return None
        folder = Path(value)
        if not folder.exists() or not folder.is_dir():
            messagebox.showerror(APP_TITLE, "A pasta selecionada não está disponível.")
            return None
        return folder

    def _build_preview(self, source: Path) -> list[tuple[Path, str, Path]]:
        rows = []
        for item in sorted(source.iterdir(), key=lambda path: path.name.lower()):
            if not item.is_file() or item.name in APP_FILE_NAMES:
                continue
            category = classify_file(item)
            target = source / category
            rows.append((item, category, target))
        return rows

    def preview(self) -> None:
        source = self._source_folder()
        if source is None:
            return
        self.preview_rows = self._build_preview(source)
        self._clear_tree()
        for item, category, target in self.preview_rows:
            self.tree.insert("", "end", values=(item.name, category, target.name))
        self.summary_text.set(f"{len(self.preview_rows)} arquivo(s) encontrado(s).")
        self.status_text.set("Pré-visualização atualizada. Nada foi movido.")

    def organize(self) -> None:
        source = self._source_folder()
        if source is None:
            return
        rows = self._build_preview(source)
        if not rows:
            self.preview_rows = []
            self._clear_tree()
            self.summary_text.set("Nenhum arquivo para organizar.")
            self.status_text.set("Não encontrei arquivos compatíveis nesta pasta.")
            return

        confirm = messagebox.askyesno(
            APP_TITLE,
            f"Organizar {len(rows)} arquivo(s) agora?\n\nO aplicativo não altera subpastas e não sobrescreve arquivos existentes.",
        )
        if not confirm:
            return

        moved: list[tuple[Path, Path]] = []
        errors: list[str] = []
        for item, category, target_folder in rows:
            try:
                target_folder.mkdir(exist_ok=True)
                destination = safe_destination(target_folder, item.name)
                shutil.move(str(item), str(destination))
                moved.append((item, destination))
            except (OSError, shutil.Error) as exc:
                errors.append(f"{item.name}: {exc}")

        self.last_moves = moved
        self.preview()
        if errors:
            messagebox.showwarning(APP_TITLE, "Alguns arquivos não puderam ser movidos:\n\n" + "\n".join(errors[:8]))
        self.status_text.set(f"Organização concluída: {len(moved)} arquivo(s) movido(s).")

    def undo_last(self) -> None:
        if not self.last_moves:
            messagebox.showinfo(APP_TITLE, "Não há uma organização recente para desfazer.")
            return

        restored = 0
        errors: list[str] = []
        for original, destination in reversed(self.last_moves):
            try:
                if destination.exists():
                    shutil.move(str(destination), str(original))
                    restored += 1
            except (OSError, shutil.Error) as exc:
                errors.append(f"{destination.name}: {exc}")

        self.last_moves = []
        self.preview()
        if errors:
            messagebox.showwarning(APP_TITLE, "Alguns arquivos não puderam ser restaurados:\n\n" + "\n".join(errors[:8]))
        self.status_text.set(f"Desfeito: {restored} arquivo(s) restaurado(s).")


def main() -> None:
    app = OrganizaFacil()
    app.mainloop()


if __name__ == "__main__":
    main()
