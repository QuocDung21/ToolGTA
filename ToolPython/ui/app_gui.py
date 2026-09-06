import os
import sys
import json
import time
import threading
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

# Ensure root dir in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import AutoFishingBot
from ui.overlay import FloatingHUD
from core.extract_templates import auto_extract_templates_from_sample


class FishingToolApp(ctk.CTk):
    """Modern Cyberpunk GUI for GTA RP Auto Fishing Tool."""

    def __init__(self):
        super().__init__()

        # Appearance & Theme
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.title("⚡ LŨ QUỶ RP - AUTO FISHING TOOL PRO")
        self.geometry("900x720")
        self.minsize(860, 680)
        self.configure(fg_color="#11111b")

        # Initialize Bot & Overlay
        self.bot = AutoFishingBot()
        self.hud = FloatingHUD(on_close_callback=self._on_hud_closed)

        # Hook callbacks
        self.bot.on_log = self._handle_bot_log
        self.bot.on_status_change = self._handle_bot_status
        self.bot.on_stats_update = self._handle_bot_stats
        self.bot.on_sequence_detected = self._handle_bot_sequence
        self.bot.key_checker.on_state_change = self._on_key_checker_state_changed

        self.start_timer = None
        self._uptime_running = False

        # Build UI
        self._build_header()
        self._build_tabs()
        self._build_footer()

        # Start bot background listener & hotkeys
        self.bot.register_hotkeys()
        self.bot.start_background_loop()

        # Periodic check for templates & uptime
        self._start_uptime_loop()
        self._refresh_template_status()

    # ================= UI BUILDERS =================
    def _build_header(self):
        header_frame = ctk.CTkFrame(self, fg_color="#181825", corner_radius=10)
        header_frame.pack(fill="x", padx=16, pady=(14, 8))

        # Title & Subtitle
        left_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        left_box.pack(side="left", padx=16, pady=10)

        title_lbl = ctk.CTkLabel(
            left_box,
            text="🎣 AUTO FISHING BOT — LŨ QUỶ RP",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#cba6f7"
        )
        title_lbl.pack(anchor="w")

        sub_lbl = ctk.CTkLabel(
            left_box,
            text="Thị giác máy tính OpenCV • DirectX Hardware Scancode • Chống Ban Tự Động",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#a6adc8"
        )
        sub_lbl.pack(anchor="w")

        # Live Status Badge
        right_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        right_box.pack(side="right", padx=16, pady=10)

        self.badge_status = ctk.CTkLabel(
            right_box,
            text="● SẴN SÀNG (IDLE)",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color="#a6adc8",
            fg_color="#1e1e2e",
            corner_radius=8,
            padx=14,
            pady=6
        )
        self.badge_status.pack()

    def _build_tabs(self):
        self.tabview = ctk.CTkTabview(
            self,
            fg_color="#181825",
            segmented_button_fg_color="#11111b",
            segmented_button_selected_color="#89b4fa",
            segmented_button_selected_hover_color="#b4befe",
            segmented_button_unselected_color="#1e1e2e",
            segmented_button_unselected_hover_color="#313244",
            text_color="#cdd6f4",
            corner_radius=12
        )
        self.tabview.pack(fill="both", expand=True, padx=16, pady=6)

        self.tab_dash = self.tabview.add("  📊 Bảng Điều Khiển  ")
        self.tab_cfg = self.tabview.add("  ⚙️ Phím & Độ Trễ  ")
        self.tab_vision = self.tabview.add("  👁️ Thị Giác & Mẫu  ")
        self.tab_stealth = self.tabview.add("  🛡️ Chống Ban & Cảnh Báo  ")

        self._build_tab_dashboard()
        self._build_tab_config()
        self._build_tab_vision()
        self._build_tab_stealth()

        # Load initial values from settings.json once all widgets exist
        self._load_settings_into_ui()

    # --------------- TAB 1: DASHBOARD ---------------
    def _build_tab_dashboard(self):
        dash = self.tab_dash

        # Stats Cards Row
        stats_frame = ctk.CTkFrame(dash, fg_color="transparent")
        stats_frame.pack(fill="x", padx=10, pady=(6, 10))
        stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.card_fish = self._create_stat_card(stats_frame, 0, "🎣 Cá Đã Câu", "0", "#a6e3a1")
        self.card_solved = self._create_stat_card(stats_frame, 1, "⚡ QTE Thành Công", "0", "#89dceb")
        self.card_uptime = self._create_stat_card(stats_frame, 2, "⏱️ Thời Gian Chạy", "00:00:00", "#f9e2af")
        self.card_rate = self._create_stat_card(stats_frame, 3, "🎯 Tỉ Lệ Chuẩn", "100%", "#cba6f7")

        # Action Buttons Row
        btn_row = ctk.CTkFrame(dash, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=4)

        self.btn_toggle = ctk.CTkButton(
            btn_row,
            text="▶  BẮT ĐẦU (F1)",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color="#2e7d32",
            hover_color="#388e3c",
            height=42,
            corner_radius=8,
            command=self._on_click_toggle_start
        )
        self.btn_toggle.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_pause = ctk.CTkButton(
            btn_row,
            text="⏸  TẠM DỪNG (F2)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#d97706",
            hover_color="#f59e0b",
            height=42,
            corner_radius=8,
            command=self._on_click_toggle_pause
        )
        self.btn_pause.pack(side="left", fill="x", expand=True, padx=6)

        self.btn_panic = ctk.CTkButton(
            btn_row,
            text="🚨  KHẨN CẤP (F3)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#dc2626",
            hover_color="#ef4444",
            height=42,
            corner_radius=8,
            command=self._on_click_panic
        )
        self.btn_panic.pack(side="left", fill="x", expand=True, padx=(6, 0))

        # Key Check & HUD Row
        sub_row = ctk.CTkFrame(dash, fg_color="transparent")
        sub_row.pack(fill="x", padx=10, pady=8)

        self.btn_key_check = ctk.CTkButton(
            sub_row,
            text="🎮  Check Nút Di Chuyển (F4)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#45475a",
            hover_color="#585b70",
            height=32,
            command=self._on_toggle_key_check
        )
        self.btn_key_check.pack(side="left", padx=(0, 8))

        self.btn_test_move = ctk.CTkButton(
            sub_row,
            text="🚀  Test Gửi Phím",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#313244",
            hover_color="#45475a",
            height=32,
            command=self._on_test_move
        )
        self.btn_test_move.pack(side="left", padx=(0, 14))

        self.switch_hud = ctk.CTkSwitch(
            sub_row,
            text="Bật HUD Mini trên game",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#cdd6f4",
            command=self._on_toggle_hud
        )
        self.switch_hud.pack(side="right")

        # Arrows Preview Card
        arrow_box = ctk.CTkFrame(dash, fg_color="#11111b", corner_radius=8)
        arrow_box.pack(fill="x", padx=10, pady=(2, 8))

        lbl_arr_title = ctk.CTkLabel(
            arrow_box,
            text="DÃY MŨI TÊN NHẬN DIỆN GẦN NHẤT:",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color="#89b4fa"
        )
        lbl_arr_title.pack(anchor="w", padx=12, pady=(6, 2))

        self.lbl_arrows_display = ctk.CTkLabel(
            arrow_box,
            text="[  CHƯA PHÁT HIỆN MINIGAME  ]",
            font=ctk.CTkFont(family="Consolas", size=16, weight="bold"),
            text_color="#6c7086"
        )
        self.lbl_arrows_display.pack(padx=12, pady=(2, 8))

        # Live Console Logs
        log_header = ctk.CTkFrame(dash, fg_color="transparent")
        log_header.pack(fill="x", padx=10, pady=(4, 2))

        lbl_log = ctk.CTkLabel(
            log_header,
            text="Nhật Ký Hoạt Động Trực Tiếp (Live Console):",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#cdd6f4"
        )
        lbl_log.pack(side="left")

        btn_clear_log = ctk.CTkButton(
            log_header,
            text="Xóa log",
            width=65,
            height=24,
            fg_color="#313244",
            hover_color="#45475a",
            font=ctk.CTkFont(size=11),
            command=self._clear_logs
        )
        btn_clear_log.pack(side="right", padx=(4, 0))

        btn_open_dir = ctk.CTkButton(
            log_header,
            text="📁 Thư Mục Log",
            width=90,
            height=24,
            fg_color="#313244",
            hover_color="#45475a",
            font=ctk.CTkFont(size=11),
            command=self._open_log_dir
        )
        btn_open_dir.pack(side="right", padx=(4, 0))

        btn_open_log = ctk.CTkButton(
            log_header,
            text="📄 Mở File Log",
            width=85,
            height=24,
            fg_color="#313244",
            hover_color="#45475a",
            font=ctk.CTkFont(size=11),
            command=self._open_log_file
        )
        btn_open_log.pack(side="right", padx=(4, 0))

        self.txt_logs = ctk.CTkTextbox(
            dash,
            fg_color="#11111b",
            text_color="#cdd6f4",
            font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=8
        )
        self.txt_logs.pack(fill="both", expand=True, padx=10, pady=(2, 8))

    def _create_stat_card(self, parent, col, title, value, color):
        card = ctk.CTkFrame(parent, fg_color="#1e1e2e", corner_radius=8)
        card.grid(row=0, column=col, padx=4, pady=2, sticky="nsew")

        lbl_title = ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#a6adc8"
        )
        lbl_title.pack(anchor="w", padx=10, pady=(6, 1))

        lbl_val = ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(family="Consolas", size=18, weight="bold"),
            text_color=color
        )
        lbl_val.pack(anchor="w", padx=10, pady=(1, 6))
        return lbl_val

    # --------------- TAB 2: CONFIG ---------------
    def _build_tab_config(self):
        cfg = self.tab_cfg

        scroll = ctk.CTkScrollableFrame(cfg, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=8)

        # Keys Group
        self._create_section_label(scroll, "⌨️ CẤU HÌNH PHÍM BẤM")
        keys_card = ctk.CTkFrame(scroll, fg_color="#1e1e2e", corner_radius=8)
        keys_card.pack(fill="x", pady=(4, 12))

        self.entry_rod_key = self._create_setting_row(keys_card, "Phím Cần Câu (Slot túi đồ):", "1")
        self.entry_hk_start = self._create_setting_row(keys_card, "Phím Tắt Bật/Tắt Bot:", "F1")
        self.entry_hk_pause = self._create_setting_row(keys_card, "Phím Tắt Tạm Dừng Bot:", "F2")
        self.entry_hk_panic = self._create_setting_row(keys_card, "Phím Tắt Khẩn Cấp (Panic Exit):", "F3")

        # Delays Group
        self._create_section_label(scroll, "⏳ ĐỘ TRỄ MÔ PHỎNG NGƯỜI THẬT (CHỐNG PHÁT HIỆN)")
        delays_card = ctk.CTkFrame(scroll, fg_color="#1e1e2e", corner_radius=8)
        delays_card.pack(fill="x", pady=(4, 12))

        self.entry_min_press = self._create_setting_row(delays_card, "Thời gian giữ phím tối thiểu (ms):", "65")
        self.entry_max_press = self._create_setting_row(delays_card, "Thời gian giữ phím tối đa (ms):", "115")
        self.entry_min_interval = self._create_setting_row(delays_card, "Khoảng cách giữa các phím tối thiểu (ms):", "90")
        self.entry_max_interval = self._create_setting_row(delays_card, "Khoảng cách giữa các phím tối đa (ms):", "160")
        self.entry_reel_wait = self._create_setting_row(delays_card, "Thời gian kéo cá lên (giây):", "4.5")
        self.entry_recast_wait = self._create_setting_row(delays_card, "Thời gian chờ trước khi quăng lại (giây):", "2.0")

        # Buttons
        btn_box = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_box.pack(fill="x", pady=10)

        btn_save = ctk.CTkButton(
            btn_box,
            text="💾  LƯU CẤU HÌNH",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#89b4fa",
            text_color="#11111b",
            hover_color="#b4befe",
            command=self._save_settings
        )
        btn_save.pack(side="left", padx=(0, 8))

        btn_reload = ctk.CTkButton(
            btn_box,
            text="🔄  TẢI LẠI TỪ FILE",
            fg_color="#313244",
            hover_color="#45475a",
            command=self._load_settings_into_ui
        )
        btn_reload.pack(side="left")

    def _create_section_label(self, parent, text):
        lbl = ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#89b4fa"
        )
        lbl.pack(anchor="w", pady=(8, 2))

    def _create_setting_row(self, parent, label_text, default_val):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=6)

        lbl = ctk.CTkLabel(row, text=label_text, font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#cdd6f4")
        lbl.pack(side="left")

        entry = ctk.CTkEntry(row, width=120, fg_color="#11111b", text_color="#cdd6f4", corner_radius=6)
        entry.pack(side="right")
        entry.insert(0, str(default_val))
        return entry

    # --------------- TAB 3: VISION & TEMPLATES ---------------
    def _build_tab_vision(self):
        v = self.tab_vision

        scroll = ctk.CTkScrollableFrame(v, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=8)

        self._create_section_label(scroll, "🎯 TRẠNG THÁI 4 MẪU MŨI TÊN (TEMPLATES)")
        tpl_card = ctk.CTkFrame(scroll, fg_color="#1e1e2e", corner_radius=8)
        tpl_card.pack(fill="x", pady=(4, 12))
        tpl_card.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.lbl_tpl_up = self._create_tpl_badge(tpl_card, 0, "⬆ MŨI TÊN LÊN\n(arrow_up.png)")
        self.lbl_tpl_down = self._create_tpl_badge(tpl_card, 1, "⬇ MŨI TÊN XUỐNG\n(arrow_down.png)")
        self.lbl_tpl_left = self._create_tpl_badge(tpl_card, 2, "⬅ MŨI TÊN TRÁI\n(arrow_left.png)")
        self.lbl_tpl_right = self._create_tpl_badge(tpl_card, 3, "➡ MŨI TÊN PHẢI\n(arrow_right.png)")

        # Template Extraction & Import Tools
        self._create_section_label(scroll, "📷 CÔNG CỤ TRÍCH XUẤT MẪU TỰ ĐỘNG")
        tool_card = ctk.CTkFrame(scroll, fg_color="#1e1e2e", corner_radius=8)
        tool_card.pack(fill="x", pady=(4, 12))

        desc_lbl = ctk.CTkLabel(
            tool_card,
            text="Chọn bức ảnh chụp màn hình minigame câu cá (ví dụ: sample_boat.png).\nTool sẽ tự động lọc màu đỏ, cắt 5 ô và trích xuất chuẩn 4 template!",
            justify="left",
            font=ctk.CTkFont(size=12),
            text_color="#a6adc8"
        )
        desc_lbl.pack(anchor="w", padx=12, pady=(10, 8))

        btn_box = ctk.CTkFrame(tool_card, fg_color="transparent")
        btn_box.pack(fill="x", padx=12, pady=(0, 12))

        btn_pick_img = ctk.CTkButton(
            btn_box,
            text="📁  Chọn Ảnh Mẫu & Tự Động Trích Xuất Template",
            fg_color="#cba6f7",
            text_color="#11111b",
            hover_color="#d5bdfc",
            font=ctk.CTkFont(weight="bold"),
            command=self._on_extract_templates_dialog
        )
        btn_pick_img.pack(side="left", padx=(0, 8))

        btn_test_det = ctk.CTkButton(
            btn_box,
            text="🔍  Chạy Thử Nghiệm Nhận Diện",
            fg_color="#313244",
            hover_color="#45475a",
            command=self._on_run_test_detector
        )
        btn_test_det.pack(side="left")

        # Threshold Slider
        self._create_section_label(scroll, "🎚️ ĐỘ NHẠY SO KHỚP (MATCH THRESHOLD)")
        slider_card = ctk.CTkFrame(scroll, fg_color="#1e1e2e", corner_radius=8)
        slider_card.pack(fill="x", pady=(4, 12))

        self.slider_thresh = ctk.CTkSlider(
            slider_card,
            from_=0.50,
            to=0.95,
            number_of_steps=45,
            command=self._on_thresh_change
        )
        self.slider_thresh.set(0.72)
        self.slider_thresh.pack(fill="x", padx=16, pady=(12, 4))

        self.lbl_thresh_val = ctk.CTkLabel(
            slider_card,
            text="Ngưỡng hiện tại: 0.72 (Khuyến nghị: 0.65 - 0.75)",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#89dceb"
        )
        self.lbl_thresh_val.pack(pady=(0, 10))

    def _create_tpl_badge(self, parent, col, title):
        card = ctk.CTkFrame(parent, fg_color="#11111b", corner_radius=6)
        card.grid(row=0, column=col, padx=6, pady=8, sticky="nsew")

        lbl_title = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=10), text_color="#a6adc8")
        lbl_title.pack(pady=(6, 2))

        lbl_status = ctk.CTkLabel(card, text="[KIỂM TRA...]", font=ctk.CTkFont(size=11, weight="bold"), text_color="#f9e2af")
        lbl_status.pack(pady=(2, 6))
        return lbl_status

    def _on_thresh_change(self, val):
        self.lbl_thresh_val.configure(text=f"Ngưỡng hiện tại: {val:.2f} (Khuyến nghị: 0.65 - 0.75)")
        self.bot.detector.settings["arrow_match_threshold"] = float(val)

    # --------------- TAB 4: STEALTH & ALERTS ---------------
    def _build_tab_stealth(self):
        s = self.tab_stealth

        scroll = ctk.CTkScrollableFrame(s, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=8)

        # Anti-AFK
        self._create_section_label(scroll, "🛡️ CƠ CHẾ CHỐNG AFK & HÀNH VI NGƯỜI THẬT")
        afk_card = ctk.CTkFrame(scroll, fg_color="#1e1e2e", corner_radius=8)
        afk_card.pack(fill="x", pady=(4, 12))

        self.switch_anti_afk = ctk.CTkSwitch(
            afk_card,
            text="Bật tính năng Anti-AFK (Nhấp nhẹ phím / lắc góc nhìn)",
            font=ctk.CTkFont(size=12),
            text_color="#cdd6f4"
        )
        self.switch_anti_afk.pack(anchor="w", padx=14, pady=(12, 6))
        self.switch_anti_afk.select()

        # Webhook
        self._create_section_label(scroll, "🔔 CẢNH BÁO TỪ XA QUA DISCORD WEBHOOK")
        hook_card = ctk.CTkFrame(scroll, fg_color="#1e1e2e", corner_radius=8)
        hook_card.pack(fill="x", pady=(4, 12))

        lbl_desc = ctk.CTkLabel(
            hook_card,
            text="Gửi thông báo về điện thoại kèm ảnh chụp màn hình khi bị admin gọi, gặp lỗi hoặc bot ngắt khẩn cấp.",
            justify="left",
            font=ctk.CTkFont(size=11),
            text_color="#a6adc8"
        )
        lbl_desc.pack(anchor="w", padx=14, pady=(10, 4))

        row_wh = ctk.CTkFrame(hook_card, fg_color="transparent")
        row_wh.pack(fill="x", padx=14, pady=6)

        self.entry_webhook = ctk.CTkEntry(
            row_wh,
            placeholder_text="https://discord.com/api/webhooks/...",
            fg_color="#11111b",
            text_color="#cdd6f4",
            corner_radius=6
        )
        self.entry_webhook.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_test_wh = ctk.CTkButton(
            row_wh,
            text="Test Gửi",
            width=80,
            fg_color="#313244",
            hover_color="#45475a",
            command=self._on_test_webhook
        )
        btn_test_wh.pack(side="right")

        # Sound alert
        self.switch_sound = ctk.CTkSwitch(
            hook_card,
            text="Phát còi báo động (Beep / Alarm) khi gặp sự cố",
            font=ctk.CTkFont(size=12),
            text_color="#cdd6f4"
        )
        self.switch_sound.pack(anchor="w", padx=14, pady=(6, 12))
        self.switch_sound.select()

    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=16, pady=(4, 8))

        info_lbl = ctk.CTkLabel(
            footer,
            text="💡 Mẹo: Nhấn F1 trong game để bắt đầu. Hãy chắc chắn cần câu đã trang bị vào slot tương ứng.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#6c7086"
        )
        info_lbl.pack(side="left")

    # ================= EVENT HANDLERS & LOGIC =================
    def _on_click_toggle_start(self):
        self.bot.toggle_running()

    def _on_click_toggle_pause(self):
        self.bot.toggle_pause()

    def _on_click_panic(self):
        self.bot.panic_exit()

    def _on_toggle_key_check(self):
        self.bot.key_checker.toggle_monitoring()

    def _on_test_move(self):
        self.bot.key_checker.test_simulate_movement()

    def _on_key_checker_state_changed(self, is_monitoring: bool):
        def update_ui():
            if is_monitoring:
                self.btn_key_check.configure(
                    text="⏹  Dừng Check Phím (F4)",
                    fg_color="#a6e3a1",
                    text_color="#11111b",
                    hover_color="#94e2d5"
                )
            else:
                self.btn_key_check.configure(
                    text="🎮  Check Nút Di Chuyển (F4)",
                    fg_color="#45475a",
                    text_color="#cdd6f4",
                    hover_color="#585b70"
                )
        self.after(0, update_ui)

    def _on_toggle_hud(self):
        if self.switch_hud.get():
            self.hud.show(self)
        else:
            self.hud.hide()

    def _on_hud_closed(self):
        self.switch_hud.deselect()

    def _handle_bot_log(self, msg: str, level: str):
        now = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{now}] {msg}\n"
        self.after(0, lambda: self._append_log(formatted, level))

    def _append_log(self, text: str, level: str):
        self.txt_logs.insert("end", text)
        self.txt_logs.see("end")

    def _clear_logs(self):
        self.txt_logs.delete("1.0", "end")

    def _open_log_file(self):
        try:
            os.makedirs("logs", exist_ok=True)
            log_path = os.path.abspath(os.path.join("logs", f"debug_{time.strftime('%Y-%m-%d')}.log"))
            if not os.path.exists(log_path):
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Log initialized.\n")
            os.startfile(log_path)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể mở file log: {e}")

    def _open_log_dir(self):
        try:
            os.makedirs("logs", exist_ok=True)
            log_dir = os.path.abspath("logs")
            os.startfile(log_dir)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể mở thư mục log: {e}")

    def _handle_bot_status(self, status: str, color: str):
        self.after(0, lambda: self._update_ui_status(status, color))

    def _update_ui_status(self, status: str, color: str):
        self.badge_status.configure(text=f"● {status.upper()}", text_color=color)
        if status.upper() == "RUNNING":
            self.btn_toggle.configure(text="⏹  DỪNG BOT (F1)", fg_color="#dc2626", hover_color="#ef4444")
            self._uptime_running = True
        elif status.upper() in ["STOPPED", "IDLE", "PANIC STOP"]:
            self.btn_toggle.configure(text="▶  BẮT ĐẦU (F1)", fg_color="#2e7d32", hover_color="#388e3c")
            self._uptime_running = False

        self.hud.update_info(status, color, self.bot.fish_count, self.bot.solved_count)

    def _handle_bot_stats(self, fish: int, solved: int):
        self.after(0, lambda: self._update_ui_stats(fish, solved))

    def _update_ui_stats(self, fish: int, solved: int):
        self.card_fish.configure(text=str(fish))
        self.card_solved.configure(text=str(solved))
        self.hud.update_info(self.badge_status.cget("text").replace("● ", ""), fish_count=fish, solved_count=solved)

    def _handle_bot_sequence(self, sequence: list):
        arrow_map = {"UP": "⬆ LÊN", "DOWN": "⬇ XUỐNG", "LEFT": "⬅ TRÁI", "RIGHT": "➡ PHẢI"}
        pretty_seq = "   ".join([f"[{arrow_map.get(k, k)}]" for k in sequence])
        self.after(0, lambda: self.lbl_arrows_display.configure(text=pretty_seq, text_color="#a6e3a1"))
        self.hud.update_info("SOLVING", "#f9e2af", sequence=sequence)

    def _start_uptime_loop(self):
        def loop():
            while True:
                if self._uptime_running and self.bot.start_time:
                    elapsed = int(time.time() - self.bot.start_time)
                    hrs = elapsed // 3600
                    mins = (elapsed % 3600) // 60
                    secs = elapsed % 60
                    time_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
                    self.after(0, lambda s=time_str: self.card_uptime.configure(text=s))
                time.sleep(1.0)

        t = threading.Thread(target=loop, daemon=True)
        t.start()

    def _refresh_template_status(self):
        tpls = self.bot.detector.templates
        mapping = [
            ("UP", self.lbl_tpl_up),
            ("DOWN", self.lbl_tpl_down),
            ("LEFT", self.lbl_tpl_left),
            ("RIGHT", self.lbl_tpl_right),
        ]
        for key, lbl in mapping:
            if key in tpls:
                lbl.configure(text="[✔ ĐÃ CÓ MẪU]", text_color="#a6e3a1")
            else:
                lbl.configure(text="[✖ CHƯA CÓ]", text_color="#f38ba8")

    def _on_extract_templates_dialog(self):
        file_path = filedialog.askopenfilename(
            title="Chọn Ảnh Mẫu Minigame Câu Cá",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp")]
        )
        if not file_path:
            return

        def task():
            self._handle_bot_log(f"Bắt đầu trích xuất template từ: {os.path.basename(file_path)}...", "info")
            try:
                # Default sample labels based on surveyed layout
                sample_labels = ["DOWN", "LEFT", "DOWN", "UP", "RIGHT"]
                auto_extract_templates_from_sample(file_path, sample_labels)
                self.bot.detector.load_templates()
                self.after(0, self._refresh_template_status)
                self._handle_bot_log("Trích xuất template thành công!", "success")
                messagebox.showinfo("Thành công", "Đã trích xuất và lưu 4 mẫu mũi tên thành công vào assets/templates/!")
            except Exception as e:
                self._handle_bot_log(f"Lỗi khi trích xuất: {e}", "error")
                messagebox.showerror("Lỗi", f"Không thể trích xuất template: {e}")

        threading.Thread(target=task, daemon=True).start()

    def _on_run_test_detector(self):
        def task():
            self._handle_bot_log("Đang chạy kiểm thử nhận diện...", "info")
            samples_dir = "assets/test_samples"
            if not os.path.exists(samples_dir) or not os.listdir(samples_dir):
                self._handle_bot_log("Không có ảnh nào trong assets/test_samples/. Vui lòng bỏ ảnh vào đó để test.", "warning")
                return

            import cv2
            for f in os.listdir(samples_dir):
                if f.lower().endswith((".png", ".jpg", ".jpeg")):
                    p = os.path.join(samples_dir, f)
                    img = cv2.imread(p)
                    if img is not None:
                        seq = self.bot.detector.detect_sequence(img)
                        self._handle_bot_log(f"Ảnh {f} -> Nhận diện: {seq}", "success" if seq else "warning")

        threading.Thread(target=task, daemon=True).start()

    def _on_test_webhook(self):
        url = self.entry_webhook.get().strip()
        if not url:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập URL Discord Webhook!")
            return

        def task():
            try:
                import requests
                payload = {
                    "content": "🎣 **[FiveM Tool Auto Fish]** Test Discord Webhook thành công! Bot đã sẵn sàng hoạt động."
                }
                res = requests.post(url, json=payload, timeout=5)
                if res.status_code in [200, 204]:
                    self._handle_bot_log("Gửi test Discord Webhook thành công!", "success")
                    messagebox.showinfo("Thành công", "Gửi test Discord Webhook thành công!")
                else:
                    self._handle_bot_log(f"Lỗi Webhook: Mã {res.status_code}", "error")
            except Exception as e:
                self._handle_bot_log(f"Lỗi gửi Webhook: {e}", "error")

        threading.Thread(target=task, daemon=True).start()

    def _save_settings(self):
        try:
            cfg = self.bot.settings
            cfg.setdefault("general", {})["rod_slot_key"] = self.entry_rod_key.get().strip()
            cfg["general"]["hotkey_start"] = self.entry_hk_start.get().strip().lower()
            cfg["general"]["hotkey_pause"] = self.entry_hk_pause.get().strip().lower()
            cfg["general"]["hotkey_panic"] = self.entry_hk_panic.get().strip().lower()

            cfg.setdefault("delays", {})["min_key_press_ms"] = int(self.entry_min_press.get())
            cfg["delays"]["max_key_press_ms"] = int(self.entry_max_press.get())
            cfg["delays"]["min_interval_ms"] = int(self.entry_min_interval.get())
            cfg["delays"]["max_interval_ms"] = int(self.entry_max_interval.get())
            cfg["delays"]["reel_in_wait_sec"] = float(self.entry_reel_wait.get())
            cfg["delays"]["recast_wait_sec"] = float(self.entry_recast_wait.get())

            cfg.setdefault("anti_afk", {})["enabled"] = bool(self.switch_anti_afk.get())
            cfg.setdefault("alerts", {})["discord_webhook_url"] = self.entry_webhook.get().strip()
            cfg["alerts"]["sound_alarm_on_fail"] = bool(self.switch_sound.get())

            with open(self.bot.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)

            self.bot.reload_config()
            self.bot.register_hotkeys()
            messagebox.showinfo("Thành công", "Đã lưu cài đặt và nạp lại cấu hình thành công!")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi lưu cấu hình: {e}")

    def _load_settings_into_ui(self):
        cfg = self.bot.settings
        gen = cfg.get("general", {})
        delays = cfg.get("delays", {})
        alerts = cfg.get("alerts", {})

        self.entry_rod_key.delete(0, "end")
        self.entry_rod_key.insert(0, gen.get("rod_slot_key", "1"))

        self.entry_hk_start.delete(0, "end")
        self.entry_hk_start.insert(0, gen.get("hotkey_start", "f1").upper())

        self.entry_hk_pause.delete(0, "end")
        self.entry_hk_pause.insert(0, gen.get("hotkey_pause", "f2").upper())

        self.entry_hk_panic.delete(0, "end")
        self.entry_hk_panic.insert(0, gen.get("hotkey_panic", "f3").upper())

        self.entry_min_press.delete(0, "end")
        self.entry_min_press.insert(0, str(delays.get("min_key_press_ms", 65)))

        self.entry_max_press.delete(0, "end")
        self.entry_max_press.insert(0, str(delays.get("max_key_press_ms", 115)))

        self.entry_min_interval.delete(0, "end")
        self.entry_min_interval.insert(0, str(delays.get("min_interval_ms", 90)))

        self.entry_max_interval.delete(0, "end")
        self.entry_max_interval.insert(0, str(delays.get("max_interval_ms", 160)))

        self.entry_reel_wait.delete(0, "end")
        self.entry_reel_wait.insert(0, str(delays.get("reel_in_wait_sec", 4.5)))

        self.entry_recast_wait.delete(0, "end")
        self.entry_recast_wait.insert(0, str(delays.get("recast_wait_sec", 2.0)))

        self.entry_webhook.delete(0, "end")
        self.entry_webhook.insert(0, alerts.get("discord_webhook_url", ""))


def launch_gui():
    app = FishingToolApp()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
