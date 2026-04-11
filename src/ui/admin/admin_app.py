#!/usr/bin/env python3

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from src.contexts.configuration.application.game_rules import (
    RULE_SECTIONS,
    get_rule_value,
    load_rules,
    reset_rules_file,
    save_rules,
    set_rule_value,
)
from src.contexts.configuration.infrastructure.app_paths import (
    delete_save_files,
    get_app_legacy_save_path,
    get_rules_path,
    get_save_path,
    get_legacy_save_path,
)


class AdminApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Admin - Mina dos Servos Eternos")
        self.geometry("920x760")
        self.minsize(820, 620)

        self._vars: dict[str, tk.StringVar] = {}
        self._scroll_canvas: tk.Canvas | None = None
        self._form_frame: ttk.Frame | None = None

        self._build_layout()
        self._load_form(load_rules())

    def _build_layout(self):
        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)

        header = ttk.Frame(container)
        header.pack(fill="x")

        ttk.Label(
            header,
            text="Painel de administracao",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            header,
            text="Edite regras dinamicas do jogo. As alteracoes valem no proximo inicio do jogo.",
        ).pack(anchor="w", pady=(4, 0))

        paths_frame = ttk.LabelFrame(container, text="Arquivos")
        paths_frame.pack(fill="x", pady=(14, 10))
        ttk.Label(paths_frame, text=f"Regras:  {get_rules_path()}").pack(anchor="w", padx=10, pady=(8, 2))
        ttk.Label(paths_frame, text=f"Banco SQLite: {get_save_path()}").pack(anchor="w", padx=10, pady=2)
        ttk.Label(paths_frame, text=f"Save legado app: {get_app_legacy_save_path()}").pack(anchor="w", padx=10, pady=2)
        ttk.Label(paths_frame, text=f"Save legado local: {get_legacy_save_path()}").pack(anchor="w", padx=10, pady=(2, 8))

        actions_top = ttk.Frame(container)
        actions_top.pack(fill="x", pady=(0, 10))
        ttk.Button(actions_top, text="Salvar regras", command=self._save).pack(side="left")
        ttk.Button(actions_top, text="Recarregar", command=self._reload).pack(side="left", padx=(8, 0))
        ttk.Button(actions_top, text="Restaurar padrao", command=self._reset_rules).pack(side="left", padx=(8, 0))
        ttk.Button(actions_top, text="Resetar progresso", command=self._reset_progress).pack(side="right")

        canvas_wrap = ttk.Frame(container)
        canvas_wrap.pack(fill="both", expand=True)

        canvas = tk.Canvas(canvas_wrap, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_wrap, orient="vertical", command=canvas.yview)
        form_frame = ttk.Frame(canvas, padding=(2, 2, 8, 2))

        form_frame.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas_window = canvas.create_window((0, 0), window=form_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _resize_form(event):
            canvas.itemconfigure(canvas_window, width=event.width)

        canvas.bind("<Configure>", _resize_form)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._scroll_canvas = canvas
        self._form_frame = form_frame

        self.bind_all("<MouseWheel>", self._on_mousewheel)

        for section in RULE_SECTIONS:
            box = ttk.LabelFrame(form_frame, text=section["title"], padding=12)
            box.pack(fill="x", pady=(0, 10))

            for row, field in enumerate(section["fields"]):
                path = field["path"]
                var = tk.StringVar()
                self._vars[path] = var

                ttk.Label(box, text=field["label"]).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=4)
                entry = ttk.Entry(box, textvariable=var, width=18)
                entry.grid(row=row, column=1, sticky="w", pady=4)

                details = f"min {field['min']:g} | max {field['max']:g}"
                ttk.Label(box, text=details).grid(row=row, column=2, sticky="w", pady=4)

            box.columnconfigure(0, weight=1)

        actions_bottom = ttk.Frame(container)
        actions_bottom.pack(fill="x", pady=(10, 0))
        ttk.Button(actions_bottom, text="Salvar regras", command=self._save).pack(side="left")
        ttk.Button(actions_bottom, text="Fechar", command=self.destroy).pack(side="right")

    def _on_mousewheel(self, event):
        if self._scroll_canvas is None:
            return
        self._scroll_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _load_form(self, rules: dict):
        for path, var in self._vars.items():
            value = get_rule_value(rules, path)
            var.set(self._format_value(value))

    def _reload(self):
        self._load_form(load_rules())

    def _format_value(self, value):
        if isinstance(value, float):
            return f"{value:g}"
        return str(value)

    def _collect_rules(self) -> dict:
        draft = load_rules()

        for section in RULE_SECTIONS:
            for field in section["fields"]:
                path = field["path"]
                raw = self._vars[path].get().strip().replace(",", ".")
                if not raw:
                    raise ValueError(f"O campo '{field['label']}' nao pode ficar vazio.")

                try:
                    value = float(raw)
                except ValueError as exc:
                    raise ValueError(f"O campo '{field['label']}' precisa ser numerico.") from exc

                value = max(field["min"], min(field["max"], value))
                if field["type"] == "int":
                    value = int(round(value))
                set_rule_value(draft, path, value)

        return draft

    def _save(self):
        try:
            rules = self._collect_rules()
        except ValueError as exc:
            messagebox.showerror("Valor invalido", str(exc), parent=self)
            return

        saved = save_rules(rules)
        self._load_form(saved)
        messagebox.showinfo("Regras salvas", "As regras foram salvas com sucesso.", parent=self)

    def _reset_rules(self):
        if not messagebox.askyesno(
            "Restaurar padrao",
            "Deseja restaurar todas as regras dinamicas para o padrao?",
            parent=self,
        ):
            return

        rules = reset_rules_file()
        self._load_form(rules)
        messagebox.showinfo("Padrao restaurado", "As regras padrao foram restauradas.", parent=self)

    def _reset_progress(self):
        if not messagebox.askyesno(
            "Resetar progresso",
            "Isso apaga o save atual do jogo. Deseja continuar?",
            parent=self,
        ):
            return

        removed = delete_save_files()
        if removed:
            detalhes = "\n".join(str(path) for path in removed)
            message = f"Progresso apagado.\n\nArquivos removidos:\n{detalhes}"
        else:
            message = "Nenhum save foi encontrado para remover."
        messagebox.showinfo("Reset concluido", message, parent=self)


def main():
    app = AdminApp()
    app.mainloop()


if __name__ == "__main__":
    main()
