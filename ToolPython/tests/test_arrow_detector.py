import os
import sys
import json
import cv2

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.arrow_detector import ArrowDetector


def run_tests():
    config_path = "config/settings.json"
    settings = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            settings = json.load(f).get("detection", {})

    detector = ArrowDetector(template_dir="assets/templates", settings=settings)
    print(f"[*] Loaded templates: {list(detector.templates.keys())}")

    samples_dir = "assets/test_samples"
    if not os.path.exists(samples_dir):
        print(f"[-] Directory {samples_dir} does not exist.")
        return

    sample_files = [f for f in os.listdir(samples_dir) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    if not sample_files:
        print(f"[!] No sample images found in {samples_dir}. Please place sample images there.")
        return

    for fname in sample_files:
        path = os.path.join(samples_dir, fname)
        img = cv2.imread(path)
        if img is None:
            print(f"[-] Failed to read: {fname}")
            continue

        print(f"\n[+] Testing image: {fname} (Shape: {img.shape})")
        boxes = detector.extract_arrow_boxes(img)
        print(f"    Found {len(boxes)} candidate boxes.")

        sequence = detector.detect_sequence(img)
        print(f"    Detected sequence: {sequence}")


if __name__ == "__main__":
    run_tests()
