import os
import sys
import time
import json
import random
import threading
import keyboard
import cv2
from typing import Callable, Optional, List

from core.screen_capture import ScreenCapture
from core.arrow_detector import ArrowDetector
from core.input_simulator import InputSimulator
from core.anti_afk import AntiAFK
from core.key_checker import MovementKeyChecker

# Enable system DPI awareness
try:
    import ctypes
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass


class AutoFishingBot:
    """State machine controller for auto fishing with event callbacks."""

    def __init__(self, config_path: str = "config/settings.json"):
        self.config_path = config_path
        self.settings = self.load_settings()

        self.screen_capture = ScreenCapture()
        self.detector = ArrowDetector(
            template_dir="assets/templates",
            settings=self.settings.get("detection", {})
        )
        delays = self.settings.get("delays", {})
        self.simulator = InputSimulator(
            min_press_ms=delays.get("min_key_press_ms", 70),
            max_press_ms=delays.get("max_key_press_ms", 120),
            min_interval_ms=delays.get("min_interval_ms", 90),
            max_interval_ms=delays.get("max_interval_ms", 160)
        )
        self.anti_afk = AntiAFK(self.simulator)
        self.key_checker = MovementKeyChecker(self.simulator, self.log)

        self.running = False
        self.paused = False
        self.is_alive = True
        self.worker_thread: Optional[threading.Thread] = None

        self._need_initial_cast = False
        self._last_bite_time = 0.0

        # Statistics
        self.fish_count = 0
        self.solved_count = 0
        self.start_time = None

        # Callbacks for GUI / Overlay
        self.on_log: Optional[Callable[[str, str], None]] = None
        self.on_status_change: Optional[Callable[[str, str], None]] = None
        self.on_stats_update: Optional[Callable[[int, int], None]] = None
        self.on_sequence_detected: Optional[Callable[[List[str]], None]] = None

    def log(self, message: str, level: str = "info"):
        print(f"[{level.upper()}] {message}")
        if self.on_log:
            try:
                self.on_log(message, level)
            except Exception:
                pass

        try:
            os.makedirs("logs", exist_ok=True)
            log_path = os.path.join("logs", f"debug_{time.strftime('%Y-%m-%d')}.log")
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] [{level.upper()}] {message}\n")
        except Exception:
            pass

    def update_status(self, status: str, color: str = "#a6adc8"):
        if self.on_status_change:
            try:
                self.on_status_change(status, color)
            except Exception:
                pass

    def load_settings(self) -> dict:
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def reload_config(self):
        self.settings = self.load_settings()
        self.detector.settings = self.settings.get("detection", {})
        self.detector.load_templates()
        delays = self.settings.get("delays", {})
        self.simulator.min_press_ms = delays.get("min_key_press_ms", 70)
        self.simulator.max_press_ms = delays.get("max_key_press_ms", 120)
        self.simulator.min_interval_ms = delays.get("min_interval_ms", 90)
        self.simulator.max_interval_ms = delays.get("max_interval_ms", 160)
        self.log("Configuration reloaded successfully.", "success")

    def register_hotkeys(self):
        try:
            k_start = self.settings.get("general", {}).get("hotkey_start", "f1")
            k_pause = self.settings.get("general", {}).get("hotkey_pause", "f2")
            k_panic = self.settings.get("general", {}).get("hotkey_panic", "f3")

            if hasattr(self, "_hotkey_handlers"):
                for h in self._hotkey_handlers:
                    try:
                        keyboard.remove_hotkey(h)
                    except Exception:
                        pass
            self._hotkey_handlers = []

            h1 = keyboard.add_hotkey(k_start, self.toggle_running)
            h2 = keyboard.add_hotkey(k_pause, self.toggle_pause)
            h3 = keyboard.add_hotkey(k_panic, self.panic_exit)
            h4 = keyboard.add_hotkey("f4", self.key_checker.toggle_monitoring)
            self._hotkey_handlers.extend([h1, h2, h3, h4])
            self.log(f"Hotkeys registered: [{k_start.upper()}: Start/Stop] [{k_pause.upper()}: Pause] [{k_panic.upper()}: Panic] [F4: Key Check]", "info")
        except Exception as e:
            self.log(f"Failed to register hotkeys: {e}", "warning")

    def start_background_loop(self):
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.is_alive = True
            self.worker_thread = threading.Thread(target=self._loop, daemon=True)
            self.worker_thread.start()

    def _loop(self):
        while self.is_alive:
            if self.running and not self.paused:
                self.run_loop_step()
            time.sleep(0.04)

    def toggle_running(self):
        self.running = not self.running
        if self.running:
            if self.start_time is None:
                self.start_time = time.time()
            self.log("Bot started running.", "success")
            self.update_status("RUNNING", "#a6e3a1")
            self._need_initial_cast = True
            self._last_bite_time = time.time()
        else:
            self.log("Bot stopped.", "warning")
            self.update_status("STOPPED", "#f38ba8")
            self._need_initial_cast = False

    def toggle_pause(self):
        if not self.running:
            return
        self.paused = not self.paused
        if self.paused:
            self.log("Bot paused.", "warning")
            self.update_status("PAUSED", "#fab387")
        else:
            self.log("Bot resumed.", "success")
            self.update_status("RUNNING", "#a6e3a1")

    def panic_exit(self):
        self.log("EMERGENCY PANIC KEY TRIGGERED! Stopping all operations...", "error")
        self.running = False
        self.is_alive = False
        self.update_status("PANIC STOP", "#f38ba8")
        self.screen_capture.close()

    def run_loop_step(self):
        """Single iteration of fishing state machine."""
        try:
            # 0. Initial cast if just started
            if self._need_initial_cast:
                self._need_initial_cast = False
                rod_key = self.settings.get("general", {}).get("rod_slot_key", "1")
                self.log(f"🎣 Bắt đầu câu: Quăng cần câu (phím '{rod_key}')...", "info")
                self.update_status("CASTING", "#b4befe")
                self.simulator.press_key(rod_key)
                time.sleep(2.5)
                self.log("⏳ Đang chờ cá cắn câu (canh minigame QTE)...", "info")
                self.update_status("WAITING BITE", "#a6e3a1")
                self._last_bite_time = time.time()

            # 1. Capture screen
            frame = self.screen_capture.capture_full()

            # 2. Check for minigame arrows
            sequence = self.detector.detect_sequence(frame)
            if sequence and len(sequence) == 5:
                start_solve = time.time()
                self.log(f"🎯 Phát hiện minigame câu cá! Mũi tên: {sequence}", "highlight")
                if self.on_sequence_detected:
                    self.on_sequence_detected(sequence)

                self.update_status("SOLVING QTE", "#f9e2af")

                # Human reaction delay before keypresses
                time.sleep(random.uniform(0.12, 0.22))
                self.simulator.execute_sequence(sequence)
                solve_duration = int((time.time() - start_solve) * 1000)
                self.log(f"⚡ Giải QTE thành công trong {solve_duration}ms!", "success")

                self.solved_count += 1
                self.fish_count += 1
                if self.on_stats_update:
                    self.on_stats_update(self.fish_count, self.solved_count)

                # Reel-in wait
                self.update_status("REELING IN", "#89dceb")
                reel_wait = self.settings.get("delays", {}).get("reel_in_wait_sec", 4.5)
                time.sleep(reel_wait)

                # Anti-AFK check
                if self.settings.get("anti_afk", {}).get("enabled", True):
                    self.anti_afk.trigger_if_needed()

                # Recast rod
                rod_key = self.settings.get("general", {}).get("rod_slot_key", "1")
                recast_wait = self.settings.get("delays", {}).get("recast_wait_sec", 2.0)
                time.sleep(recast_wait)
                self.log(f"🎣 Quăng lại cần câu với phím '{rod_key}'...", "info")
                self.update_status("CASTING", "#b4befe")
                self.simulator.press_key(rod_key)
                time.sleep(2.5)
                self._last_bite_time = time.time()
                self.update_status("WAITING BITE", "#a6e3a1")

            elif self._last_bite_time > 0 and (time.time() - self._last_bite_time) > 50:
                self.log("⏳ Quá 50s chưa có cá cắn, tự động quăng lại cần câu...", "warning")
                rod_key = self.settings.get("general", {}).get("rod_slot_key", "1")
                self.update_status("RECASTING", "#b4befe")
                self.simulator.press_key(rod_key)
                time.sleep(2.5)
                self._last_bite_time = time.time()
                self.update_status("WAITING BITE", "#a6e3a1")

        except Exception as e:
            self.log(f"Error during loop step: {e}", "error")
            time.sleep(0.5)

    def stop(self):
        self.running = False
        self.is_alive = False
        self.screen_capture.close()
        self.update_status("IDLE", "#a6adc8")
        self.log("Bot stopped completely.", "info")


if __name__ == "__main__":
    if "--cli" in sys.argv:
        bot = AutoFishingBot()
        bot.register_hotkeys()
        bot.start_background_loop()
        print("Bot running in CLI mode. Press Ctrl+C to exit.")
        try:
            while bot.is_alive:
                time.sleep(1)
        except KeyboardInterrupt:
            bot.stop()
    else:
        from ui.app_gui import launch_gui
        launch_gui()
