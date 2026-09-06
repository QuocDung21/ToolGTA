import ctypes
import time
import random
from typing import Optional

# DirectInput Scancodes
# Reference: DirectX DIK codes
DIK_UP = 0xC8        # Up arrow (Extended 0x48 / 0xC8)
DIK_DOWN = 0xD0      # Down arrow (Extended 0x50 / 0xD0)
DIK_LEFT = 0xCB      # Left arrow (Extended 0x4B / 0xCB)
DIK_RIGHT = 0xCD     # Right arrow (Extended 0x4D / 0xCD)
DIK_E = 0x12
DIK_1 = 0x02
DIK_2 = 0x03
DIK_3 = 0x04
DIK_4 = 0x05
DIK_5 = 0x06

# Windows SendInput Structures
PUL = ctypes.POINTER(ctypes.c_ulong)


class KeyBdInput(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL)
    ]


class HardwareInput(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_short),
        ("wParamH", ctypes.c_ushort)
    ]


class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL)
    ]


class InputUnion(ctypes.Union):
    _fields_ = [
        ("ki", KeyBdInput),
        ("mi", MouseInput),
        ("hi", HardwareInput)
    ]


class Input(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("ii", InputUnion)
    ]


KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001
INPUT_KEYBOARD = 1


KEY_MAP = {
    "UP": (0x48, True),
    "DOWN": (0x50, True),
    "LEFT": (0x4B, True),
    "RIGHT": (0x4D, True),
    "W": (0x11, False),
    "A": (0x1E, False),
    "S": (0x1F, False),
    "D": (0x20, False),
    "SPACE": (0x39, False),
    "SHIFT": (0x2A, False),
    "CTRL": (0x1D, False),
    "E": (0x12, False),
    "1": (0x02, False),
    "2": (0x03, False),
    "3": (0x04, False),
    "4": (0x05, False),
    "5": (0x06, False),
}


class InputSimulator:
    """Simulates hardware keyboard inputs using DirectX Scancodes to bypass FiveM anti-cheat."""

    def __init__(self, min_press_ms: int = 70, max_press_ms: int = 120, min_interval_ms: int = 90, max_interval_ms: int = 160):
        self.min_press_ms = min_press_ms
        self.max_press_ms = max_press_ms
        self.min_interval_ms = min_interval_ms
        self.max_interval_ms = max_interval_ms

    def _send_key(self, scan_code: int, extended: bool, is_down: bool):
        flags = KEYEVENTF_SCANCODE
        if extended:
            flags |= KEYEVENTF_EXTENDEDKEY
        if not is_down:
            flags |= KEYEVENTF_KEYUP

        extra = ctypes.c_ulong(0)
        ii = InputUnion()
        ii.ki = KeyBdInput(0, scan_code, flags, 0, ctypes.pointer(extra))
        x = Input(ctypes.c_ulong(INPUT_KEYBOARD), ii)
        ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

    def press_key(self, key_name: str, duration_sec: Optional[float] = None):
        """Press and release a key with simulated human holding time."""
        key_name = key_name.upper()
        if key_name not in KEY_MAP:
            raise ValueError(f"Unsupported key: {key_name}")

        scan_code, extended = KEY_MAP[key_name]

        if duration_sec is None:
            duration_sec = random.uniform(self.min_press_ms, self.max_press_ms) / 1000.0

        # Key down
        self._send_key(scan_code, extended, is_down=True)
        time.sleep(duration_sec)
        # Key up
        self._send_key(scan_code, extended, is_down=False)

    def execute_sequence(self, keys: list[str]):
        """Execute a sequence of key presses with randomized delays between them."""
        for i, key in enumerate(keys):
            self.press_key(key)
            if i < len(keys) - 1:
                delay = random.uniform(self.min_interval_ms, self.max_interval_ms) / 1000.0
                time.sleep(delay)
