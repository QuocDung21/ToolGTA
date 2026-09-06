import os
import sys
import cv2
import numpy as np

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.arrow_detector import ArrowDetector


def auto_extract_templates_from_sample(image_path: str, known_labels: list[str]):
    """
    Given a sample image and its known arrow sequence (e.g. ['DOWN', 'LEFT', 'DOWN', 'UP', 'RIGHT']),
    extract each arrow box and save standard templates to assets/templates/.
    """
    detector = ArrowDetector()
    img = cv2.imread(image_path)
    if img is None:
        print(f"[-] Could not open {image_path}")
        return

    boxes = detector.extract_arrow_boxes(img)
    print(f"[*] Found {len(boxes)} boxes in {image_path}")

    if len(boxes) != len(known_labels):
        print(f"[!] Warning: Found {len(boxes)} boxes, expected {len(known_labels)}.")
        # If more or less, still extract up to min length
    
    out_dir = "assets/templates"
    os.makedirs(out_dir, exist_ok=True)

    extracted = set()
    for idx, (box, label) in enumerate(zip(boxes, known_labels)):
        filename = f"arrow_{label.lower()}.png"
        out_path = os.path.join(out_dir, filename)
        if label not in extracted:
            cv2.imwrite(out_path, box)
            print(f"[+] Saved template: {out_path} from box {idx}")
            extracted.add(label)

    print(f"[+] Extracted templates for: {list(extracted)}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        img_file = sys.argv[1]
    else:
        img_file = "assets/test_samples/sample_boat.png"

    sample_labels = ["DOWN", "LEFT", "DOWN", "UP", "RIGHT"]
    auto_extract_templates_from_sample(img_file, sample_labels)
