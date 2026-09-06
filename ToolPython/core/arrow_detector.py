import os
import cv2
import numpy as np
from typing import List, Optional, Dict, Tuple


class ArrowDetector:
    """Robust Computer Vision Detector for FiveM / GTA RP QTE Arrow Minigames."""

    def __init__(self, template_dir: str = "assets/templates", settings: Optional[dict] = None):
        self.template_dir = template_dir
        self.settings = settings or {}
        self.templates: Dict[str, np.ndarray] = {}
        self.load_templates()

    def load_templates(self):
        """Loads tight arrow templates: UP, DOWN, LEFT, RIGHT."""
        mapping = {
            "UP": "arrow_up.png",
            "DOWN": "arrow_down.png",
            "LEFT": "arrow_left.png",
            "RIGHT": "arrow_right.png"
        }
        for direction, filename in mapping.items():
            path = os.path.join(self.template_dir, filename)
            if os.path.exists(path):
                img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    self.templates[direction] = img

    def match_arrow_in_box(self, box_bgr: np.ndarray) -> Tuple[Optional[str], float]:
        """Matches arrow inside a cropped box using red/white binarization and sliding correlation."""
        if not self.templates or box_bgr is None or box_bgr.size == 0:
            return None, 0.0

        r = box_bgr[:, :, 2]
        gray = cv2.cvtColor(box_bgr, cv2.COLOR_BGR2GRAY)
        # Combine bright red arrow and white arrow
        mask = ((r > 185) | (gray > 175)).astype(np.uint8) * 255

        best_score = -1.0
        best_direction = None

        tpl_scale = max(0.5, mask.shape[0] / 29.0)

        for direction, tpl in self.templates.items():
            tw = max(4, int(round(tpl.shape[1] * tpl_scale)))
            th = max(4, int(round(tpl.shape[0] * tpl_scale)))
            scaled_tpl = cv2.resize(tpl, (tw, th)) if abs(tpl_scale - 1.0) > 0.05 else tpl

            if mask.shape[0] < scaled_tpl.shape[0] or mask.shape[1] < scaled_tpl.shape[1]:
                resized = cv2.resize(mask, (max(mask.shape[1], scaled_tpl.shape[1]), max(mask.shape[0], scaled_tpl.shape[0])))
                res = cv2.matchTemplate(resized, scaled_tpl, cv2.TM_CCOEFF_NORMED)
            else:
                res = cv2.matchTemplate(mask, scaled_tpl, cv2.TM_CCOEFF_NORMED)

            _, max_val, _, _ = cv2.minMaxLoc(res)
            if max_val > best_score:
                best_score = max_val
                best_direction = direction

        threshold = min(self.settings.get("arrow_match_threshold", 0.65), 0.60)
        if best_score >= threshold:
            return best_direction, best_score
        return None, best_score

    def find_arrow_row_boxes(self, frame_bgr: np.ndarray) -> List[np.ndarray]:
        """
        Locates the horizontal row of 5 arrow boxes on screen.
        Reconstructs the full 5-box grid even if all boxes are pending (dark) or completed (red).
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return []

        h, w = frame_bgr.shape[:2]
        scale = h / 568.0

        # Strict narrow band where arrow QTE is located (above health/status icons)
        roi_y1 = max(0, min(h - 2, int(h * 0.81)))
        roi_y2 = max(roi_y1 + 1, min(h, int(h * 0.92)))
        roi_x1 = max(0, min(w - 2, int(w * 0.35)))
        roi_x2 = max(roi_x1 + 1, min(w, int(w * 0.65)))

        roi_w = roi_x2 - roi_x1
        roi_h = roi_y2 - roi_y1
        if roi_w <= 50 or roi_h <= 20:
            return []

        roi = frame_bgr[roi_y1:roi_y2, roi_x1:roi_x2]

        r = roi[:, :, 2]
        g = roi[:, :, 1]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        # Dark boxes (pending arrows when minigame starts at 0/5)
        dark_mask = (gray < 70).astype(np.uint8) * 255

        # Red boxes (completed arrows)
        red_mask = ((r.astype(int) - g.astype(int) > 30) & (r > 115)).astype(np.uint8) * 255

        # Combined mask: finds both pending dark boxes and completed red boxes
        combined_mask = cv2.bitwise_or(dark_mask, red_mask)

        contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []
        min_dim = max(12, int(round(15 * scale)))
        max_dim = max(25, int(round(38 * scale)))

        for c in contours:
            x, y, bw, bh = cv2.boundingRect(c)
            if min_dim <= bw <= max_dim and min_dim <= bh <= max_dim:
                candidates.append((x, y, bw, bh))

        avg_y = 0
        avg_h = int(round(23 * scale))
        avg_w = int(round(23 * scale))
        step = 27.25 * scale

        if len(candidates) >= 2:
            # Group by similar Y
            groups = []
            y_tol = max(4, int(round(6 * scale)))
            for b in candidates:
                matched = False
                for grp in groups:
                    if abs(grp[0][1] - b[1]) <= y_tol:
                        grp.append(b)
                        matched = True
                        break
                if not matched:
                    groups.append([b])

            valid_grps = [g for g in groups if len(g) >= 2]
            if valid_grps:
                best_grp = max(valid_grps, key=len)
                best_grp.sort(key=lambda b: b[0])
                avg_y = int(np.mean([b[1] for b in best_grp]))
                avg_h = int(np.mean([b[3] for b in best_grp]))
                avg_w = int(np.mean([b[2] for b in best_grp]))

                if len(best_grp) >= 2:
                    steps = [best_grp[i+1][0] - best_grp[i][0] for i in range(len(best_grp)-1)]
                    median_step = float(np.median(steps))
                    if 18 * scale <= median_step <= 42 * scale:
                        step = median_step

        if avg_y == 0:
            avg_y = int(round(roi_h * 0.55))

        # Horizontal center alignment
        roi_center_x = roi_w / 2.0
        total_span = 4 * step + avg_w
        start_x = roi_center_x - total_span / 2.0

        margin_y = max(2, int(round(3 * scale)))
        margin_x = max(2, int(round(3 * scale)))

        boxes = []
        for i in range(5):
            bx = int(round(start_x + i * step))
            by = avg_y

            x1 = max(0, bx - margin_x)
            y1 = max(0, by - margin_y)
            x2 = min(roi_w, bx + avg_w + margin_x)
            y2 = min(roi_h, by + avg_h + margin_y)

            if x2 <= x1 or y2 <= y1:
                return []

            crop = roi[y1:y2, x1:x2]
            boxes.append(crop)

        return boxes

    def extract_arrow_boxes(self, frame_bgr: np.ndarray) -> List[np.ndarray]:
        return self.find_arrow_row_boxes(frame_bgr)

    def detect_sequence(self, frame_bgr: np.ndarray) -> List[str]:
        """Detect full sequence of 5 arrows from a captured frame."""
        try:
            boxes = self.find_arrow_row_boxes(frame_bgr)
            if len(boxes) != 5:
                return []

            sequence = []
            for box in boxes:
                direction, score = self.match_arrow_in_box(box)
                if direction:
                    sequence.append(direction)
                else:
                    return []

            return sequence if len(sequence) == 5 else []
        except Exception:
            return []
