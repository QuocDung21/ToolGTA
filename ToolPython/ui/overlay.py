import tkinter as tk
from typing import Optional


class FloatingHUD:
    """Draggable, transparent, always-on-top HUD Overlay for GTA RP."""

    def __init__(self, on_close_callback=None):
        self.root: Optional[tk.Toplevel] = None
        self.on_close_callback = on_close_callback
        self._drag_start_x = 0
        self._drag_start_y = 0

    def show(self, master=None):
        if self.root is not None and tk.Toplevel.winfo_exists(self.root):
            self.root.lift()
            return

        self.root = tk.Toplevel(master) if master else tk.Tk()
        self.root.title("AutoFish HUD")
        self.root.geometry("260x100+40+40")
        self.root.overrideredirect(True)  # Frameless for clean gaming overlay
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.88)
        self.root.configure(bg="#11111b")

        # Border frame for neon cyberpunk accent
        border_frame = tk.Frame(self.root, bg="#cba6f7", bd=1)
        border_frame.pack(fill="both", expand=True, padx=1, pady=1)

        main_frame = tk.Frame(border_frame, bg="#181825")
        main_frame.pack(fill="both", expand=True, padx=1, pady=1)

        # Header bar for dragging
        header = tk.Frame(main_frame, bg="#1e1e2e", height=24)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        title_lbl = tk.Label(
            header,
            text=" ⚡ AUTO FISH HUD",
            fg="#cba6f7",
            bg="#1e1e2e",
            font=("Segoe UI", 9, "bold")
        )
        title_lbl.pack(side="left", padx=4)

        close_btn = tk.Label(
            header,
            text="✕ ",
            fg="#f38ba8",
            bg="#1e1e2e",
            font=("Segoe UI", 9, "bold"),
            cursor="hand2"
        )
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self.hide())

        # Content Labels
        self.lbl_status = tk.Label(
            main_frame,
            text="STATUS: READY (F1)",
            fg="#a6adc8",
            bg="#181825",
            font=("Consolas", 10, "bold")
        )
        self.lbl_status.pack(pady=(6, 2))

        self.lbl_details = tk.Label(
            main_frame,
            text="Fish: 0  |  Solved: 0",
            fg="#89dceb",
            bg="#181825",
            font=("Consolas", 9)
        )
        self.lbl_details.pack(pady=1)

        self.lbl_sequence = tk.Label(
            main_frame,
            text="Arrows: [--, --, --, --, --]",
            fg="#f9e2af",
            bg="#181825",
            font=("Consolas", 9)
        )
        self.lbl_sequence.pack(pady=(1, 6))

        # Make window draggable via header
        header.bind("<Button-1>", self._start_drag)
        header.bind("<B1-Motion>", self._on_drag)
        title_lbl.bind("<Button-1>", self._start_drag)
        title_lbl.bind("<B1-Motion>", self._on_drag)

    def _start_drag(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_drag(self, event):
        if self.root:
            x = self.root.winfo_x() + (event.x - self._drag_start_x)
            y = self.root.winfo_y() + (event.y - self._drag_start_y)
            self.root.geometry(f"+{x}+{y}")

    def update_info(self, status: str, color: str = "#a6e3a1", fish_count: int = 0, solved_count: int = 0, sequence: list = None):
        if self.root and tk.Toplevel.winfo_exists(self.root):
            try:
                self.lbl_status.config(text=f"STATUS: {status.upper()}", fg=color)
                self.lbl_details.config(text=f"Fish: {fish_count}  |  Solved: {solved_count}")
                if sequence:
                    seq_str = " ".join([{"UP": "⬆", "DOWN": "⬇", "LEFT": "⬅", "RIGHT": "➡"}.get(k, k) for k in sequence])
                    self.lbl_sequence.config(text=f"Arrows: {seq_str}", fg="#a6e3a1")
                else:
                    self.lbl_sequence.config(text="Arrows: [WAITING]", fg="#6c7086")
            except Exception:
                pass

    def hide(self):
        if self.root and tk.Toplevel.winfo_exists(self.root):
            self.root.destroy()
            self.root = None
            if self.on_close_callback:
                self.on_close_callback()

    def is_visible(self) -> bool:
        return self.root is not None and tk.Toplevel.winfo_exists(self.root)
