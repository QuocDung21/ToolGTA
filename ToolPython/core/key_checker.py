import time
import threading
import ctypes
from typing import Callable, Optional

# Win32 GetAsyncKeyState
GetAsyncKeyState = ctypes.windll.user32.GetAsyncKeyState


class MovementKeyChecker:
    """Monitors in-game movement keys and tests simulation with debug logging."""

    WATCHED_KEYS = [
        {"name": "W", "vk": 0x57, "scancode": 0x11, "extended": False},
        {"name": "A", "vk": 0x41, "scancode": 0x1E, "extended": False},
        {"name": "S", "vk": 0x53, "scancode": 0x1F, "extended": False},
        {"name": "D", "vk": 0x44, "scancode": 0x20, "extended": False},
        {"name": "UP", "vk": 0x26, "scancode": 0x48, "extended": True},
        {"name": "DOWN", "vk": 0x28, "scancode": 0x50, "extended": True},
        {"name": "LEFT", "vk": 0x25, "scancode": 0x4B, "extended": True},
        {"name": "RIGHT", "vk": 0x27, "scancode": 0x4D, "extended": True},
        {"name": "SPACE", "vk": 0x20, "scancode": 0x39, "extended": False},
        {"name": "SHIFT", "vk": 0x10, "scancode": 0x2A, "extended": False},
        {"name": "E", "vk": 0x45, "scancode": 0x12, "extended": False},
    ]

    def __init__(self, simulator, log_callback: Callable[[str, str], None]):
        self.simulator = simulator
        self.log = log_callback
        self.is_monitoring = False
        self._thread: Optional[threading.Thread] = None
        self.on_state_change: Optional[Callable[[bool], None]] = None

    def toggle_monitoring(self):
        self.is_monitoring = not self.is_monitoring
        if self.is_monitoring:
            self.log("🟢 [KEY_CHECK] Bắt đầu theo dõi nút di chuyển (W, A, S, D, Mũi tên). Bấm F4 để dừng.", "success")
            self._start_thread()
        else:
            self.log("🔴 [KEY_CHECK] Đã dừng theo dõi nút di chuyển.", "warning")

        if self.on_state_change:
            self.on_state_change(self.is_monitoring)

    def _start_thread(self):
        if self._thread and self._thread.is_alive():
            return

        def loop():
            key_states = {}
            for k in self.WATCHED_KEYS:
                key_states[k["vk"]] = {"was_down": False, "press_time": 0.0}

            while self.is_monitoring:
                for k in self.WATCHED_KEYS:
                    vk = k["vk"]
                    is_down = bool(GetAsyncKeyState(vk) & 0x8000)
                    state = key_states[vk]

                    if is_down and not state["was_down"]:
                        # Key pressed down
                        state["press_time"] = time.time()
                        ext_str = ", Extended" if k["extended"] else ""
                        self.log(f"[KEY_CHECK] ⬇️ Bấm phím '{k['name']}' (VK: 0x{vk:02X}, DirectX Scancode: 0x{k['scancode']:02X}{ext_str})", "info")

                    elif not is_down and state["was_down"]:
                        # Key released up
                        duration = int((time.time() - state["press_time"]) * 1000)
                        self.log(f"[KEY_CHECK] ⬆️ Nhả phím '{k['name']}' | Giữ phím: {duration}ms", "highlight")

                    state["was_down"] = is_down

                time.sleep(0.01)

        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def test_simulate_movement(self):
        """Simulate a test sequence of movement keys to check game reception."""
        def task():
            self.log("🎮 [TEST_MOVE] Bắt đầu kiểm tra gửi phím di chuyển vào game...", "info")
            keys = ["W", "A", "S", "D", "UP", "DOWN", "LEFT", "RIGHT"]
            for k in keys:
                from core.input_simulator import KEY_MAP
                scancode, ext = KEY_MAP.get(k, (0, False))
                self.log(f"[TEST_MOVE] ➡️ Gửi thử phím '{k}' (Scancode: 0x{scancode:02X}, Ext: {ext}, Giữ: 120ms)...", "info")
                try:
                    self.simulator.press_key(k, duration_sec=0.12)
                    self.log(f"[TEST_MOVE] ✔️ Phím '{k}' đã gửi thành công!", "success")
                except Exception as e:
                    self.log(f"[TEST_MOVE] ❌ Lỗi gửi phím '{k}': {e}", "error")
                time.sleep(0.2)
            self.log("🎮 [TEST_MOVE] Hoàn thành bài kiểm tra gửi phím di chuyển!", "success")

        threading.Thread(target=task, daemon=True).start()
