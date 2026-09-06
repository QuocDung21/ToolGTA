import mss
import numpy as np
import cv2
from typing import Optional, Tuple, Dict, Any


class ScreenCapture:
    """High-speed screen capturing utility using MSS."""

    def __init__(self):
        self.sct = mss.mss()
        self.primary_monitor = self.sct.monitors[1]  # 1 is primary monitor (0 is all monitors)

    def capture_full(self) -> np.ndarray:
        """Capture entire primary monitor and return BGR numpy array."""
        raw = self.sct.grab(self.primary_monitor)
        # Convert BGRA to BGR
        frame = np.array(raw, dtype=np.uint8)[:, :, :3]
        return np.ascontiguousarray(frame)

    def capture_roi(self, bbox: Dict[str, int]) -> np.ndarray:
        """
        Capture specific bounding box.
        bbox format: {'left': int, 'top': int, 'width': int, 'height': int}
        """
        raw = self.sct.grab(bbox)
        frame = np.array(raw, dtype=np.uint8)[:, :, :3]
        return np.ascontiguousarray(frame)

    def get_relative_bbox(self, rel_left: float, rel_top: float, rel_width: float, rel_height: float) -> Dict[str, int]:
        """Convert relative screen coordinates (0.0 to 1.0) to absolute pixel bbox."""
        mon = self.primary_monitor
        left = int(mon["left"] + rel_left * mon["width"])
        top = int(mon["top"] + rel_top * mon["height"])
        width = int(rel_width * mon["width"])
        height = int(rel_height * mon["height"])
        return {"left": left, "top": top, "width": width, "height": height}

    def close(self):
        self.sct.close()
