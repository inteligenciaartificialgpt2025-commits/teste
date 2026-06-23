"""Automação segura de cliques e teclas para janelas específicas do Windows.

Execute com: python automacao_janelas.py

O programa lista janelas abertas, permite configurar ações em sequência e salva/
carrega rotinas em JSON. A execução acontece em uma thread para não travar a UI.
"""

from __future__ import annotations

import json
import queue
import threading
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import pyautogui
    import pygetwindow as gw
except ImportError as exc:  # Falha cedo com mensagem amigável.
    raise SystemExit(
        "Bibliotecas ausentes. Instale com: pip install pyautogui pygetwindow pywin32"
    ) from exc


pyautogui.FAILSAFE = True  # mover o mouse para o canto superior esquerdo aborta pyautogui

ACTION_TYPES = ("tecla", "combinação", "clique")
STATUS_STOPPED = "parado"
STATUS_RUNNING = "executando"
STATUS_PAUSED = "pausado"
APP_DATA_DIR = Path(os.getenv("APPDATA", Path.home())) / "Automacao Janelas"



@dataclass
class AutomationAction:
    """Representa uma ação configurável da rotina."""

    name: str
    action_type: str
    value: str
    interval: float
    repetitions: int
    order: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AutomationAction":
        return cls(
            name=str(data.get("name", "")),
            action_type=str(data.get("action_type", "tecla")),
            value=str(data.get("value", "")),
            interval=float(data.get("interval", 1)),
            repetitions=int(data.get("repetitions", 1)),
            order=int(data.get("order", 1)),
        )


class WindowManager:
    """Isola operações sobre janelas do Windows."""

    @staticmethod
    def list_windows() -> list[str]:
        titles = [title for title in gw.getAllTitles() if title and title.strip()]
        return sorted(set(titles), key=str.casefold)

    @staticmethod
    def find_window(title: str):
        matches = gw.getWindowsWithTitle(title)
        exact = [window for window in matches if window.title == title]
        return (exact or matches or [None])[0]

    @staticmethod
    def activate_window(title: str):
        window = WindowManager.find_window(title)
        if window is None:
            raise RuntimeError(f"A janela '{title}' foi fechada ou não existe mais.")
        if getattr(window, "isMinimized", False):
            window.restore()
        if not getattr(window, "isActive", False):
            window.activate()
            time.sleep(0.25)
        return window

    @staticmethod
    def point_inside_window(window: Any, x: int, y: int) -> bool:
        return 0 <= x <= window.width and 0 <= y <= window.height


class AutomationWorker:
    """Executa ações em segundo plano com suporte a pausar/parar."""

    def __init__(self, status_callback: Callable[[str], None], error_callback: Callable[[str], None]):
        self.status_callback = status_callback
        self.error_callback = error_callback
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self, window_title: str, actions: list[AutomationAction], continuous: bool) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.pause_event.clear()
        self.thread = threading.Thread(
            target=self._run,
            args=(window_title, sorted(actions, key=lambda a: a.order), continuous),
            daemon=True,
        )
        self.thread.start()

    def pause(self) -> None:
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.status_callback(STATUS_RUNNING)
        else:
            self.pause_event.set()
            self.status_callback(STATUS_PAUSED)

    def stop(self) -> None:
        self.stop_event.set()
        self.pause_event.clear()
        self.status_callback(STATUS_STOPPED)

    def _run(self, window_title: str, actions: list[AutomationAction], continuous: bool) -> None:
        self.status_callback(STATUS_RUNNING)
        try:
            while not self.stop_event.is_set():
                for action in actions:
                    repeats = action.repetitions if action.repetitions > 0 else 1
                    for _ in range(repeats):
                        if self.stop_event.is_set():
                            break
                        self._wait_if_paused()
                        window = WindowManager.activate_window(window_title)
                        self._execute_action(window, action)
                        self._sleep_interruptibly(action.interval)
                    if self.stop_event.is_set():
                        break
                if not continuous:
                    break
        except Exception as exc:  # mostra erro ao usuário sem derrubar UI
            self.error_callback(str(exc))
        finally:
            self.stop_event.set()
            self.status_callback(STATUS_STOPPED)

    def _wait_if_paused(self) -> None:
        while self.pause_event.is_set() and not self.stop_event.is_set():
            time.sleep(0.1)

    def _sleep_interruptibly(self, seconds: float) -> None:
        end = time.monotonic() + max(0, seconds)
        while time.monotonic() < end and not self.stop_event.is_set():
            self._wait_if_paused()
            time.sleep(0.05)

    def _execute_action(self, window: Any, action: AutomationAction) -> None:
        if action.action_type == "tecla":
            pyautogui.press(action.value.strip())
        elif action.action_type == "combinação":
            keys = [key.strip() for key in action.value.replace("+", ",").split(",") if key.strip()]
            if not keys:
                raise ValueError("Combinação de teclas vazia.")
            pyautogui.hotkey(*keys)
        elif action.action_type == "clique":
            try:
                x_text, y_text = action.value.replace(";", ",").split(",", 1)
                x, y = int(x_text.strip()), int(y_text.strip())
            except ValueError as exc:
                raise ValueError("Clique deve usar coordenadas no formato x,y dentro da janela.") from exc
            if not WindowManager.point_inside_window(window, x, y):
                raise ValueError("Coordenada de clique fora dos limites da janela escolhida.")
            pyautogui.click(window.left + x, window.top + y)
        else:
            raise ValueError(f"Tipo de ação inválido: {action.action_type}")


class AutomationApp(tk.Tk):
    """Interface gráfica principal."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Automação de Janelas do Windows")
        self.geometry("980x680")
        self.minsize(900, 600)
        self.actions: list[AutomationAction] = []
        self.ui_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.worker = AutomationWorker(self.enqueue_status, self.enqueue_error)
        self._build_ui()
        self.refresh_windows()
        self.after(100, self.process_ui_queue)

    def _build_ui(self) -> None:
        top = ttk.LabelFrame(self, text="Janela alvo")
        top.pack(fill="x", padx=10, pady=8)
        self.window_var = tk.StringVar()
        self.window_combo = ttk.Combobox(top, textvariable=self.window_var, state="readonly", width=80)
        self.window_combo.pack(side="left", fill="x", expand=True, padx=8, pady=8)
        ttk.Button(top, text="Atualizar janelas", command=self.refresh_windows).pack(side="left", padx=8)

        form = ttk.LabelFrame(self, text="Cadastrar ação")
        form.pack(fill="x", padx=10, pady=8)
        self.fields: dict[str, tk.Variable] = {
            "name": tk.StringVar(),
            "action_type": tk.StringVar(value="tecla"),
            "value": tk.StringVar(),
            "interval": tk.StringVar(value="1"),
            "repetitions": tk.StringVar(value="1"),
            "order": tk.StringVar(value="1"),
        }
        labels = ["Nome", "Tipo", "Valor (tecla, ctrl+c ou x,y)", "Intervalo", "Repetições", "Ordem"]
        keys = ["name", "action_type", "value", "interval", "repetitions", "order"]
        for col, (label, key) in enumerate(zip(labels, keys)):
            ttk.Label(form, text=label).grid(row=0, column=col, sticky="w", padx=5, pady=(6, 0))
            if key == "action_type":
                widget = ttk.Combobox(form, textvariable=self.fields[key], values=ACTION_TYPES, state="readonly", width=14)
            else:
                widget = ttk.Entry(form, textvariable=self.fields[key], width=18)
            widget.grid(row=1, column=col, sticky="ew", padx=5, pady=6)
            form.columnconfigure(col, weight=1)
        ttk.Button(form, text="Adicionar/Atualizar", command=self.add_action).grid(row=1, column=6, padx=8)
        ttk.Button(form, text="Remover selecionada", command=self.remove_selected).grid(row=1, column=7, padx=8)

        table_frame = ttk.LabelFrame(self, text="Rotina configurada")
        table_frame.pack(fill="both", expand=True, padx=10, pady=8)
        columns = ("order", "name", "action_type", "value", "interval", "repetitions")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        headings = {"order": "Ordem", "name": "Nome", "action_type": "Tipo", "value": "Valor", "interval": "Intervalo", "repetitions": "Repetições"}
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=120, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree.bind("<<TreeviewSelect>>", self.load_selected_into_form)

        controls = ttk.Frame(self)
        controls.pack(fill="x", padx=10, pady=8)
        self.continuous_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls, text="Repetir rotina continuamente", variable=self.continuous_var).pack(side="left", padx=5)
        ttk.Button(controls, text="Iniciar", command=self.start).pack(side="left", padx=5)
        ttk.Button(controls, text="Pausar/Continuar", command=self.worker.pause).pack(side="left", padx=5)
        ttk.Button(controls, text="Parar", command=self.worker.stop).pack(side="left", padx=5)
        ttk.Button(controls, text="EMERGÊNCIA", command=self.emergency_stop).pack(side="left", padx=5)
        ttk.Button(controls, text="Salvar JSON", command=self.save_json).pack(side="right", padx=5)
        ttk.Button(controls, text="Carregar JSON", command=self.load_json).pack(side="right", padx=5)

        self.status_var = tk.StringVar(value=STATUS_STOPPED)
        ttk.Label(self, textvariable=self.status_var, anchor="w").pack(fill="x", padx=12, pady=(0, 8))

    def refresh_windows(self) -> None:
        titles = WindowManager.list_windows()
        self.window_combo["values"] = titles
        if titles and not self.window_var.get():
            self.window_var.set(titles[0])

    def add_action(self) -> None:
        try:
            action = AutomationAction(
                name=self.fields["name"].get().strip() or "Sem nome",
                action_type=self.fields["action_type"].get(),
                value=self.fields["value"].get().strip(),
                interval=float(self.fields["interval"].get()),
                repetitions=int(self.fields["repetitions"].get()),
                order=int(self.fields["order"].get()),
            )
            if action.action_type not in ACTION_TYPES or not action.value:
                raise ValueError("Preencha tipo e valor da ação.")
            if action.interval < 0 or action.repetitions < 0:
                raise ValueError("Intervalo e repetições não podem ser negativos.")
        except ValueError as exc:
            messagebox.showerror("Ação inválida", str(exc))
            return
        selected = self.tree.selection()
        if selected:
            index = int(selected[0])
            self.actions[index] = action
        else:
            self.actions.append(action)
        self.redraw_actions()

    def remove_selected(self) -> None:
        for item in sorted(self.tree.selection(), key=int, reverse=True):
            del self.actions[int(item)]
        self.redraw_actions()

    def load_selected_into_form(self, _event: tk.Event) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        action = self.actions[int(selected[0])]
        for key, value in asdict(action).items():
            self.fields[key].set(str(value))

    def redraw_actions(self) -> None:
        self.actions.sort(key=lambda a: a.order)
        self.tree.delete(*self.tree.get_children())
        for index, action in enumerate(self.actions):
            self.tree.insert("", "end", iid=str(index), values=(action.order, action.name, action.action_type, action.value, action.interval, action.repetitions))

    def start(self) -> None:
        if not self.window_var.get():
            messagebox.showerror("Janela alvo", "Escolha uma janela antes de iniciar.")
            return
        if not self.actions:
            messagebox.showerror("Rotina vazia", "Cadastre pelo menos uma ação.")
            return
        self.worker.start(self.window_var.get(), list(self.actions), self.continuous_var.get())

    def emergency_stop(self) -> None:
        self.worker.stop()
        pyautogui.hotkey("esc")

    def save_json(self) -> None:
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialdir=str(APP_DATA_DIR),
        )
        if not path:
            return
        data = {"window_title": self.window_var.get(), "continuous": self.continuous_var.get(), "actions": [asdict(a) for a in self.actions]}
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def load_json(self) -> None:
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")], initialdir=str(APP_DATA_DIR))
        if not path:
            return
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.window_var.set(data.get("window_title", ""))
        self.continuous_var.set(bool(data.get("continuous", False)))
        self.actions = [AutomationAction.from_dict(item) for item in data.get("actions", [])]
        self.redraw_actions()

    def enqueue_status(self, status: str) -> None:
        self.ui_queue.put(("status", status))

    def enqueue_error(self, error: str) -> None:
        self.ui_queue.put(("error", error))

    def process_ui_queue(self) -> None:
        while not self.ui_queue.empty():
            kind, message = self.ui_queue.get_nowait()
            if kind == "status":
                self.status_var.set(f"Status: {message}")
            elif kind == "error":
                messagebox.showerror("Erro na automação", message)
        self.after(100, self.process_ui_queue)


if __name__ == "__main__":
    AutomationApp().mainloop()
