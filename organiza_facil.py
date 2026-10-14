"""Organiza Fácil - organizador local de arquivos.

Versão 0.2.0. O aplicativo funciona offline, organiza somente os arquivos
diretamente dentro da pasta escolhida e mantém a última operação para desfazer.
"""

from __future__ import annotations

import json
import os
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


APP_TITLE = "Organiza Fácil"
APP_VERSION = "0.2.0"

DEFAULT_FILE_GROUPS = {
    "Imagens": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".tif", ".tiff", ".ico"},
    "Documentos": {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".csv", ".ppt", ".pptx", ".md"},
    "Videos": {".mp4", ".mkv", ".mov", ".avi", ".webm", ".wmv", ".m4v"},
    "Audios": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"},
    "Compactados": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"},
    "Instaladores": {".exe", ".msi", ".apk", ".deb", ".rpm"},
    "Codigo": {".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".java", ".c", ".cpp", ".h", ".json", ".xml", ".sql", ".ps1", ".bat"},
}

APP_FILE_NAMES = {
    "organiza_facil.py",
    "organiza_facil.exe",
    "executar_organiza_facil.bat",
}


def application_data_dir() -> Path:
    """Return a user-writable folder for settings and the last undo record."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "OrganizaFacil"
    return Path.home() / ".organiza_facil"


def normalize_extension(value: str) -> str | None:
    extension = value.strip().lower()
    if not extension:
        return None
    if not extension.startswith("."):
        extension = "." + extension
    return extension


def parse_extensions(value: str) -> set[str]:
    return {
        extension
        for extension in (normalize_extension(item) for item in value.replace(";", ",").split(","))
        if extension
    }


def copy_groups(groups: dict[str, set[str]]) -> dict[str, set[str]]:
    return {name: set(extensions) for name, extensions in groups.items()}


def load_groups() -> dict[str, set[str]]:
    groups = copy_groups(DEFAULT_FILE_GROUPS)
    config_file = application_data_dir() / "config.json"
    try:
        data = json.loads(config_file.read_text(encoding="utf-8"))
        saved_groups = data.get("groups", {})
        if isinstance(saved_groups, dict):
            loaded = {}
            for name, extensions in saved_groups.items():
                if isinstance(name, str) and isinstance(extensions, list):
                    normalized = parse_extensions(",".join(str(item) for item in extensions))
                    if name.strip() and normalized:
                        loaded[name.strip()] = normalized
            if loaded:
                groups = loaded
    except (OSError, ValueError, TypeError):
        pass
    return groups


def save_groups(groups: dict[str, set[str]]) -> None:
    config_dir = application_data_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    payload = {"groups": {name: sorted(extensions) for name, extensions in groups.items()}}
    (config_dir / "config.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def classify_file(file_path: Path, groups: dict[str, set[str]] | None = None) -> str:
    active_groups = groups if groups is not None else DEFAULT_FILE_GROUPS
    suffix = file_path.suffix.lower()
    for group, extensions in active_groups.items():
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
        self.title(f"{APP_TITLE} {APP_VERSION}")
        self.geometry("900x600")
        self.minsize(760, 500)

        self.selected_folder = tk.StringVar(value="")
        self.status_text = tk.StringVar(value="Escolha uma pasta para começar.")
        self.summary_text = tk.StringVar(value="Nenhuma pasta selecionada.")
        self.last_moves: list[tuple[Path, Path]] = self._load_history()
        self.preview_rows: list[tuple[Path, str, Path]] = []
        self.file_groups = load_groups()

        self._configure_style()
        self._build_ui()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Segoe UI", 17, "bold"))
        style.configure("Version.TLabel", foreground="#666666", font=("Segoe UI", 9))
        style.configure("Hint.TLabel", foreground="#555555", font=("Segoe UI", 9))
        style.configure("Status.TLabel", padding=(8, 5), font=("Segoe UI", 9))
        style.configure("Toolbar.TButton", padding=(9, 5))

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=18)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(3, weight=1)

        header = ttk.Frame(outer)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text=APP_TITLE, style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text=f"v{APP_VERSION}  •  local", style="Version.TLabel").grid(row=0, column=1, sticky="w", padx=(10, 0), pady=(5, 0))

        folder_frame = ttk.LabelFrame(outer, text="Pasta")
        folder_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        folder_frame.columnconfigure(0, weight=1)
        ttk.Entry(folder_frame, textvariable=self.selected_folder, state="readonly").grid(row=0, column=0, sticky="ew", padx=(10, 8), pady=10)
        ttk.Button(folder_frame, text="Escolher...", command=self.choose_folder).grid(row=0, column=1, padx=(0, 10), pady=10)

        toolbar = ttk.Frame(outer)
        toolbar.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        ttk.Button(toolbar, text="Pré-visualizar", style="Toolbar.TButton", command=self.preview).pack(side="left")
        ttk.Button(toolbar, text="Organizar agora", style="Toolbar.TButton", command=self.organize).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Desfazer última", style="Toolbar.TButton", command=self.undo_last).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Categorias...", style="Toolbar.TButton", command=self.open_categories).pack(side="left", padx=(6, 0))
        ttk.Label(toolbar, textvariable=self.summary_text, style="Hint.TLabel").pack(side="right")

        list_frame = ttk.LabelFrame(outer, text="Arquivos encontrados")
        list_frame.grid(row=3, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        columns = ("arquivo", "categoria", "destino")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="none")
        self.tree.heading("arquivo", text="Arquivo")
        self.tree.heading("categoria", text="Categoria")
        self.tree.heading("destino", text="Destino")
        self.tree.column("arquivo", width=370, anchor="w")
        self.tree.column("categoria", width=160, anchor="w")
        self.tree.column("destino", width=250, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 8), pady=8)
        self.tree.configure(yscrollcommand=scrollbar.set)

        ttk.Label(outer, textvariable=self.status_text, style="Status.TLabel", anchor="w").grid(row=4, column=0, sticky="ew", pady=(10, 0))

    def choose_folder(self) -> None:
        chosen = filedialog.askdirectory(title="Escolha a pasta que deseja organizar")
        if not chosen:
            return
        self.selected_folder.set(chosen)
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
            category = classify_file(item, self.file_groups)
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
        self.summary_text.set(f"{len(self.preview_rows)} arquivo(s)")
        self.status_text.set("Pré-visualização atualizada. Nada foi movido.")

    def organize(self) -> None:
        source = self._source_folder()
        if source is None:
            return
        rows = self._build_preview(source)
        if not rows:
            self.preview_rows = []
            self._clear_tree()
            self.summary_text.set("Nenhum arquivo")
            self.status_text.set("Não encontrei arquivos para organizar nesta pasta.")
            return

        confirm = messagebox.askyesno(
            APP_TITLE,
            f"Organizar {len(rows)} arquivo(s) agora?\n\nSubpastas não serão alteradas e arquivos existentes não serão sobrescritos.",
        )
        if not confirm:
            return

        moved: list[tuple[Path, Path]] = []
        errors: list[str] = []
        for item, _category, target_folder in rows:
            try:
                target_folder.mkdir(exist_ok=True)
                destination = safe_destination(target_folder, item.name)
                shutil.move(str(item), str(destination))
                moved.append((item, destination))
            except (OSError, shutil.Error) as exc:
                errors.append(f"{item.name}: {exc}")

        self.last_moves = moved
        self._save_history()
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
                if destination.exists() and not original.exists():
                    original.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(destination), str(original))
                    restored += 1
                elif destination.exists() and original.exists():
                    errors.append(f"{original.name}: o arquivo original já existe")
            except (OSError, shutil.Error) as exc:
                errors.append(f"{destination.name}: {exc}")

        self.last_moves = []
        self._save_history()
        self.preview()
        if errors:
            messagebox.showwarning(APP_TITLE, "Alguns arquivos não puderam ser restaurados:\n\n" + "\n".join(errors[:8]))
        self.status_text.set(f"Desfeito: {restored} arquivo(s) restaurado(s).")

    def _load_history(self) -> list[tuple[Path, Path]]:
        history_file = application_data_dir() / "last_operation.json"
        try:
            raw = json.loads(history_file.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                return [(Path(item["original"]), Path(item["destination"])) for item in raw if isinstance(item, dict) and "original" in item and "destination" in item]
        except (OSError, ValueError, TypeError, KeyError):
            pass
        return []

    def _save_history(self) -> None:
        config_dir = application_data_dir()
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
            payload = [{"original": str(original), "destination": str(destination)} for original, destination in self.last_moves]
            (config_dir / "last_operation.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            self.status_text.set("A operação foi concluída, mas o histórico não pôde ser salvo.")

    def open_categories(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Categorias")
        dialog.geometry("700x460")
        dialog.minsize(620, 380)
        dialog.transient(self)
        dialog.grab_set()

        container = ttk.Frame(dialog, padding=16)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=2)
        container.rowconfigure(1, weight=1)

        ttk.Label(container, text="Categorias", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Label(container, text="Extensões", font=("Segoe UI", 12, "bold")).grid(row=0, column=1, sticky="w", padx=(18, 0), pady=(0, 8))

        list_frame = ttk.Frame(container)
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        category_list = tk.Listbox(list_frame, exportselection=False, activestyle="none")
        category_list.grid(row=0, column=0, sticky="nsew")
        list_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=category_list.yview)
        list_scroll.grid(row=0, column=1, sticky="ns")
        category_list.configure(yscrollcommand=list_scroll.set)

        editor = ttk.Frame(container)
        editor.grid(row=1, column=1, sticky="nsew", padx=(18, 0))
        editor.columnconfigure(0, weight=1)
        name_var = tk.StringVar()
        extensions_var = tk.StringVar()
        ttk.Label(editor, text="Nome da pasta").grid(row=0, column=0, sticky="w")
        ttk.Entry(editor, textvariable=name_var).grid(row=1, column=0, sticky="ew", pady=(4, 12))
        ttk.Label(editor, text="Extensões separadas por vírgula").grid(row=2, column=0, sticky="w")
        extensions_entry = ttk.Entry(editor, textvariable=extensions_var)
        extensions_entry.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        ttk.Label(editor, text="Exemplo: pdf, docx, txt", style="Hint.TLabel").grid(row=4, column=0, sticky="w", pady=(4, 0))

        def load_selected(_event=None) -> None:
            selection = category_list.curselection()
            if not selection:
                return
            name = category_list.get(selection[0])
            name_var.set(name)
            extensions_var.set(", ".join(sorted(self.file_groups[name])))

        def refresh_list(select_name: str | None = None) -> None:
            category_list.delete(0, tk.END)
            names = list(self.file_groups.keys())
            for name in names:
                category_list.insert(tk.END, name)
            if select_name in names:
                index = names.index(select_name)
            elif names:
                index = 0
            else:
                index = None
            if index is not None:
                category_list.selection_set(index)
                category_list.activate(index)
                category_list.see(index)
                load_selected()
            else:
                name_var.set("")
                extensions_var.set("")

        def save_category() -> None:
            old_selection = category_list.curselection()
            old_name = category_list.get(old_selection[0]) if old_selection else None
            new_name = name_var.get().strip()
            extensions = parse_extensions(extensions_var.get())
            if not new_name or not extensions:
                messagebox.showwarning("Categorias", "Informe um nome e pelo menos uma extensão.", parent=dialog)
                return
            if new_name != old_name and new_name in self.file_groups:
                messagebox.showwarning("Categorias", "Já existe uma categoria com esse nome.", parent=dialog)
                return
            if old_name and old_name in self.file_groups:
                del self.file_groups[old_name]
            self.file_groups[new_name] = extensions
            save_groups(self.file_groups)
            refresh_list(new_name)
            self.status_text.set("Categorias atualizadas.")

        def new_category() -> None:
            category_list.selection_clear(0, tk.END)
            name_var.set("")
            extensions_var.set("")
            extensions_entry.focus_set()

        def delete_category() -> None:
            selection = category_list.curselection()
            if not selection:
                return
            name = category_list.get(selection[0])
            if not messagebox.askyesno("Categorias", f"Excluir a categoria '{name}'?", parent=dialog):
                return
            del self.file_groups[name]
            if self.file_groups:
                save_groups(self.file_groups)
            else:
                self.file_groups = copy_groups(DEFAULT_FILE_GROUPS)
                save_groups(self.file_groups)
            refresh_list()

        def reset_categories() -> None:
            if not messagebox.askyesno("Categorias", "Restaurar as categorias padrão?", parent=dialog):
                return
            self.file_groups = copy_groups(DEFAULT_FILE_GROUPS)
            save_groups(self.file_groups)
            refresh_list()

        category_list.bind("<<ListboxSelect>>", load_selected)
        refresh_list()

        buttons = ttk.Frame(container)
        buttons.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        ttk.Button(buttons, text="Nova", command=new_category).pack(side="left")
        ttk.Button(buttons, text="Salvar", command=save_category).pack(side="left", padx=(6, 0))
        ttk.Button(buttons, text="Excluir", command=delete_category).pack(side="left", padx=(6, 0))
        ttk.Button(buttons, text="Restaurar padrões", command=reset_categories).pack(side="left", padx=(6, 0))
        ttk.Button(buttons, text="Fechar", command=dialog.destroy).pack(side="right")


def main() -> None:
    app = OrganizaFacil()
    app.mainloop()


if __name__ == "__main__":
    main()
