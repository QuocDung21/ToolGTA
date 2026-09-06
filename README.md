# 🎣 ToolGTA — Auto Fishing Multi-Version Suite (GTA V / FiveM)

Bộ công cụ tự động nhận diện và giải minigame QTE câu cá (5 mũi tên) cho máy chủ GTA V / FiveM (Lũ Quỷ RP). Bao gồm 3 phiên bản được tối ưu hóa cho các nhu cầu sử dụng khác nhau.

---

## ⚡ Các Phiên Bản Trong Kho Lưu Trữ

### 1. `ToolRS` — Rust Native Edition (Khuyên Dùng) 🚀
* **Ngôn ngữ & Công nghệ**: Pure Rust, `eframe` (egui), Windows Native API.
* **Đặc điểm nổi bật**:
  * Tốc độ nhận diện cực nhanh **< 2ms**, tốc độ quét màn hình đạt **~60 FPS**.
  * Thuật toán `match_template_raw` xử lý trực tiếp trên flat buffer số nguyên, không cấp phát bộ nhớ thừa.
  * Tự động đệm viền (auto-padding) chống trượt mũi tên khi kích thước ô cắt bị lệch pixel.
  * Vùng ROI được tinh chỉnh chính xác, loại bỏ 100% nhiễu từ thanh máu/giáp/HUD của game.
  * Tích hợp **Global Hotkeys toàn cục**:
    * **F1**: Bật / Dừng Tool ngay trong game.
    * **F2**: Tạm dừng / Tiếp tục.
    * **F3**: Dừng khẩn cấp toàn bộ hoạt động.
    * **F4**: Bật / Tắt Modal HUD nổi trong game.
  * **In-Game Overlay HUD (Modal Nổi)**:
    * Hiển thị đè trực tiếp lên game (Always-On-Top, Borderless, Dark Glass bán trong suốt).
    * Kéo thả di chuyển tự do đến vị trí tùy ý trên màn hình.
    * Hiển thị trực tiếp trạng thái, số cá đã câu, số minigame đã giải, chuỗi mũi tên QTE và nhật ký thao tác gần nhất.
* **Cách chạy**:
  * Nhấp đúp vào `run.bat` để chạy phiên bản Release tối ưu.
  * Nhấp đúp vào `build.bat` để biên dịch lại từ mã nguồn.

---

### 2. `ToolCSharp` — C# WPF Edition 🎨
* **Ngôn ngữ & Công nghệ**: C# (.NET 10), WPF UI, OpenCvSharp4.
* **Đặc điểm nổi bật**:
  * Giao diện đồ họa WPF trực quan, hỗ trợ cửa sổ Overlay trên game.
  * Tích hợp Anti-AFK, cảnh báo âm thanh và gửi thông báo qua Discord Webhook.
  * Quản lý cấu hình chi tiết qua `config/settings.json`.

---

### 3. `ToolPython` — Python Edition 🐍
* **Ngôn ngữ & Công nghệ**: Python 3, OpenCV (`cv2`), Tkinter UI, PyAutoGUI.
* **Đặc điểm nổi bật**:
  * Phiên bản nền tảng nguyên mẫu, dễ dàng tinh chỉnh mã nguồn và thử nghiệm thuật toán xử lý ảnh.
  * Phù hợp cho việc nghiên cứu và thử nghiệm mẫu nhận diện mới (`test_samples/`).

---

## 🛠 Hướng Dẫn Cài Đặt & Khởi Chạy Nhanh

### Chạy Bản Rust Native (`ToolRS`):
```powershell
cd ToolRS
cargo run --release
```
Hoặc dùng file batch có sẵn:
* `build.bat`: Biên dịch bản Release và đồng bộ thư mục assets/config.
* `run.bat`: Khởi chạy trực tiếp bản Release.
* `push.bat`: Đồng bộ mã nguồn lên GitHub.

---

## 📜 License & Tuyên bố miễn trừ
Dự án được phát triển phục vụ mục đích học tập, nghiên cứu kỹ thuật thị giác máy tính (Computer Vision) và tự động hóa native trên hệ điều hành Windows.
