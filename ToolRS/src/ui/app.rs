use crate::bot::{BotController, BotStatus};
use crate::config::AppConfig;
use crate::ui::overlay::render_overlay;
use eframe::egui::{self, Color32, RichText, ScrollArea, Stroke};

#[derive(PartialEq)]
enum ActiveTab {
    Dashboard,
    Settings,
}

pub struct AutoFishApp {
    bot: BotController,
    active_tab: ActiveTab,
    overlay_open: bool,
}

impl AutoFishApp {
    pub fn new(cc: &eframe::CreationContext<'_>) -> Self {
        Self::configure_fonts(&cc.egui_ctx);
        let config = AppConfig::load_or_default("config/settings.json");
        let overlay_open = config.overlay.enabled;
        let bot = BotController::new(config);

        Self {
            bot,
            active_tab: ActiveTab::Dashboard,
            overlay_open,
        }
    }

    fn configure_fonts(ctx: &egui::Context) {
        use egui::{FontData, FontDefinitions, FontFamily};

        let mut fonts = FontDefinitions::default();

        // Nhúng trực tiếp font Roboto hỗ trợ 100% tiếng Việt có dấu Unicode
        fonts.font_data.insert(
            "roboto".to_owned(),
            FontData::from_static(include_bytes!("../../assets/fonts/Roboto-Regular.ttf")).into(),
        );
        fonts.font_data.insert(
            "roboto-medium".to_owned(),
            FontData::from_static(include_bytes!("../../assets/fonts/Roboto-Medium.ttf")).into(),
        );

        fonts
            .families
            .entry(FontFamily::Proportional)
            .or_default()
            .insert(0, "roboto".to_owned());

        fonts
            .families
            .entry(FontFamily::Monospace)
            .or_default()
            .push("roboto".to_owned());

        ctx.set_fonts(fonts);
    }

    fn apply_cyberpunk_theme(ctx: &egui::Context) {
        let mut visuals = egui::Visuals::dark();
        visuals.panel_fill = Color32::from_rgb(17, 17, 27); // #11111b
        visuals.window_fill = Color32::from_rgb(24, 24, 37); // #181825
        visuals.extreme_bg_color = Color32::from_rgb(30, 30, 46); // #1e1e2e
        visuals.widgets.noninteractive.bg_fill = Color32::from_rgb(24, 24, 37);
        visuals.widgets.inactive.bg_fill = Color32::from_rgb(30, 30, 46);
        visuals.widgets.hovered.bg_fill = Color32::from_rgb(49, 50, 68);
        visuals.widgets.active.bg_fill = Color32::from_rgb(69, 71, 90);
        visuals.override_text_color = Some(Color32::from_rgb(205, 214, 244));
        ctx.set_visuals(visuals);
    }
}

impl eframe::App for AutoFishApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        Self::apply_cyberpunk_theme(ctx);
        // Continuous repaint for live logs and status
        ctx.request_repaint_after(std::time::Duration::from_millis(50));

        let (status, fish, solved, seq, logs, is_run, is_paused, is_test) = {
            if let Ok(mut s) = self.bot.state.lock() {
                if s.overlay_toggle_requested {
                    s.overlay_toggle_requested = false;
                    self.overlay_open = !self.overlay_open;
                }
                (
                    s.status,
                    s.fish_count,
                    s.solved_count,
                    s.last_sequence.clone(),
                    s.logs.clone(),
                    s.is_running,
                    s.is_paused,
                    s.is_test_mode,
                )
            } else {
                (BotStatus::Idle, 0, 0, Vec::new(), Vec::new(), false, false, false)
            }
        };

        // Render In-Game Overlay HUD window
        if self.overlay_open {
            let opacity = if let Ok(cfg) = self.bot.config.lock() {
                cfg.overlay.opacity
            } else {
                0.88
            };
            let last_log = logs.last().map(|(_, msg)| msg.as_str());
            render_overlay(
                ctx,
                status,
                fish,
                solved,
                &seq,
                last_log,
                opacity,
                &mut self.overlay_open,
            );
        }

        egui::CentralPanel::default().show(ctx, |ui| {
            // HEADER BAR
            egui::Frame::none()
                .fill(Color32::from_rgb(24, 24, 37))
                .inner_margin(12.0)
                .rounding(8.0)
                .show(ui, |ui| {
                    ui.horizontal(|ui| {
                        ui.vertical(|ui| {
                            ui.heading(
                                RichText::new("🎣 AUTO FISHING BOT — LŨ QUỶ RP (RUST NATIVE)")
                                    .color(Color32::from_rgb(203, 166, 247))
                                    .strong(),
                            );
                            ui.label(
                                RichText::new("⚡ Pure Rust SIMD Vision • Native Windows DXGI • < 3ms Latency")
                                    .color(Color32::from_rgb(166, 173, 200))
                                    .size(11.0),
                            );
                        });

                        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                            let badge_color = match status {
                                BotStatus::Running | BotStatus::TestingDetected => Color32::from_rgb(166, 227, 161),
                                BotStatus::Paused => Color32::from_rgb(250, 179, 135),
                                BotStatus::Casting | BotStatus::TestingScanning => Color32::from_rgb(137, 180, 250),
                                _ => Color32::from_rgb(166, 173, 200),
                            };

                            egui::Frame::none()
                                .fill(Color32::from_rgb(30, 30, 46))
                                .inner_margin(egui::Margin::symmetric(14.0, 6.0))
                                .rounding(6.0)
                                .stroke(Stroke::new(1.0_f32, badge_color))
                                .show(ui, |ui| {
                                    ui.label(
                                        RichText::new(format!("● {}", status.as_str()))
                                            .color(badge_color)
                                            .strong(),
                                    );
                                });
                        });
                    });
                });

            ui.add_space(8.0);

            // TAB SELECTOR
            ui.horizontal(|ui| {
                ui.selectable_value(&mut self.active_tab, ActiveTab::Dashboard, "📊 BẢNG ĐIỀU KHIỂN");
                ui.selectable_value(&mut self.active_tab, ActiveTab::Settings, "⚙️ CÀI ĐẶT");
            });

            ui.separator();
            ui.add_space(6.0);

            match self.active_tab {
                ActiveTab::Dashboard => {
                    // MAIN ACTION BUTTONS
                    ui.horizontal(|ui| {
                        let toggle_text = if is_run { "⏹ DỪNG BOT (F1)" } else { "▶ BẮT ĐẦU (F1)" };
                        let toggle_color = if is_run { Color32::from_rgb(220, 38, 38) } else { Color32::from_rgb(46, 125, 50) };
                        if ui.add_sized([180.0, 38.0], egui::Button::new(RichText::new(toggle_text).strong().color(Color32::WHITE)).fill(toggle_color)).clicked() {
                            self.bot.toggle_running();
                        }

                        let pause_text = if is_paused { "▶ TIẾP TỤC (F2)" } else { "⏸ TẠM DỪNG (F2)" };
                        if ui.add_sized([150.0, 38.0], egui::Button::new(RichText::new(pause_text).strong()).fill(Color32::from_rgb(217, 119, 6))).clicked() {
                            self.bot.toggle_pause();
                        }

                        if ui.add_sized([150.0, 38.0], egui::Button::new(RichText::new("🚨 KHẨN CẤP (F3)").strong().color(Color32::WHITE)).fill(Color32::from_rgb(185, 28, 28))).clicked() {
                            self.bot.panic_exit();
                        }

                        // TEST VIDEO BUTTON
                        let test_text = if is_test { "⏹ DỪNG TEST VIDEO" } else { "🎯 TEST QUÉT VIDEO" };
                        let test_color = if is_test { Color32::from_rgb(243, 139, 168) } else { Color32::from_rgb(137, 180, 250) };
                        if ui.add_sized([180.0, 38.0], egui::Button::new(RichText::new(test_text).strong().color(Color32::from_rgb(17, 17, 27))).fill(test_color)).clicked() {
                            self.bot.toggle_test_mode();
                        }
                    });

                    ui.add_space(6.0);
                    ui.horizontal(|ui| {
                        if let Ok(mut cfg) = self.bot.config.lock() {
                            if ui.checkbox(&mut cfg.general.auto_recast, RichText::new("🔄 Tự động quăng lại cần (Auto Recast)").color(Color32::from_rgb(203, 166, 247)).strong()).changed() {
                                let _ = cfg.save("config/settings.json");
                            }
                        }

                        let overlay_label = if self.overlay_open { "🖥️ Ẩn HUD Nổi Trong Game" } else { "🖥️ Hiện HUD Nổi Trong Game" };
                        let overlay_btn_color = if self.overlay_open { Color32::from_rgb(137, 220, 235) } else { Color32::from_rgb(49, 50, 68) };
                        let overlay_txt_color = if self.overlay_open { Color32::from_rgb(17, 17, 27) } else { Color32::from_rgb(205, 214, 244) };
                        if ui.add(egui::Button::new(RichText::new(overlay_label).color(overlay_txt_color).strong()).fill(overlay_btn_color)).clicked() {
                            self.overlay_open = !self.overlay_open;
                            if let Ok(mut cfg) = self.bot.config.lock() {
                                cfg.overlay.enabled = self.overlay_open;
                                let _ = cfg.save("config/settings.json");
                            }
                        }

                        ui.label(RichText::new("💡 Phím nóng: F1 (Start/Stop) • F2 (Pause) • F3 (Panic) • F4 (Bật/Tắt HUD)").color(Color32::from_rgb(186, 194, 222)).size(11.0));
                    });

                    ui.add_space(6.0);

                    // STATS ROW
                    ui.horizontal(|ui| {
                        egui::Frame::none()
                            .fill(Color32::from_rgb(24, 24, 37))
                            .inner_margin(10.0)
                            .rounding(6.0)
                            .show(ui, |ui| {
                                ui.label(RichText::new("🐟 CÁ ĐÃ CÂU:").color(Color32::from_rgb(166, 173, 200)));
                                ui.heading(RichText::new(format!("{}", fish)).color(Color32::from_rgb(137, 220, 235)).strong());
                            });

                        egui::Frame::none()
                            .fill(Color32::from_rgb(24, 24, 37))
                            .inner_margin(10.0)
                            .rounding(6.0)
                            .show(ui, |ui| {
                                ui.label(RichText::new("⚡ MINIGAME ĐÃ GIẢI:").color(Color32::from_rgb(166, 173, 200)));
                                ui.heading(RichText::new(format!("{}", solved)).color(Color32::from_rgb(166, 227, 161)).strong());
                            });
                    });

                    ui.add_space(8.0);

                    // ARROWS PREVIEW CARD
                    egui::Frame::none()
                        .fill(Color32::from_rgb(24, 24, 37))
                        .inner_margin(12.0)
                        .rounding(8.0)
                        .stroke(Stroke::new(1.0_f32, Color32::from_rgb(49, 50, 68)))
                        .show(ui, |ui| {
                            ui.label(RichText::new("DÃY MŨI TÊN NHẬN DIỆN GẦN NHẤT:").color(Color32::from_rgb(137, 180, 250)).strong().size(12.0));
                            ui.add_space(4.0);

                            if seq.is_empty() {
                                ui.label(RichText::new("[  CHƯA PHÁT HIỆN MINIGAME  ]").color(Color32::from_rgb(108, 112, 134)).size(16.0).monospace());
                            } else {
                                let display = seq.iter().map(|d| format!("{} {}", d.display_icon(), d.as_str())).collect::<Vec<_>>().join("     ");
                                ui.label(RichText::new(format!("[  {}  ]", display)).color(Color32::from_rgb(166, 227, 161)).size(18.0).strong().monospace());
                            }
                        });

                    ui.add_space(8.0);

                    // LIVE CONSOLE LOGS
                    ui.label(RichText::new("Nhật Ký Hoạt Động Trực Tiếp (Live Console):").strong());
                    egui::Frame::none()
                        .fill(Color32::from_rgb(17, 17, 27))
                        .inner_margin(8.0)
                        .rounding(6.0)
                        .stroke(Stroke::new(1.0_f32, Color32::from_rgb(49, 50, 68)))
                        .show(ui, |ui| {
                            ScrollArea::vertical()
                                .max_height(240.0)
                                .auto_shrink([false; 2])
                                .stick_to_bottom(true)
                                .show(ui, |ui| {
                                    for (t, msg) in &logs {
                                        ui.horizontal(|ui| {
                                            ui.label(RichText::new(format!("[{}]", t)).color(Color32::from_rgb(108, 112, 134)).monospace());
                                            if msg.contains("PHÁT HIỆN") || msg.contains("thành công") {
                                                ui.label(RichText::new(msg).color(Color32::from_rgb(166, 227, 161)).monospace());
                                            } else if msg.contains("Dừng") || msg.contains("KHẨN CẤP") {
                                                ui.label(RichText::new(msg).color(Color32::from_rgb(243, 139, 168)).monospace());
                                            } else {
                                                ui.label(RichText::new(msg).color(Color32::from_rgb(205, 214, 244)).monospace());
                                            }
                                        });
                                    }
                                });
                        });
                }
                ActiveTab::Settings => {
                    ui.heading("⚙️ Cấu Hình Thông Số Bot");
                    ui.add_space(8.0);

                    if let Ok(mut cfg) = self.bot.config.lock() {
                        ui.group(|ui| {
                            ui.checkbox(&mut cfg.general.auto_recast, RichText::new("Tự Động Quăng Lại Cần (Auto Recast)").strong());
                            ui.label(RichText::new("ℹ Nếu tắt: Tool chỉ lắng nghe màn hình và tự động giải minigame, người chơi tự quăng cần.").size(11.0).color(Color32::from_rgb(166, 173, 200)));

                            ui.add_space(6.0);
                            ui.label(RichText::new("Phím Quăng Cần (Slot):").strong());
                            ui.text_edit_singleline(&mut cfg.general.rod_slot_key);

                            ui.add_space(6.0);
                            ui.label(RichText::new("Độ nhạy nhận diện (Threshold 0.50 - 0.90):").strong());
                            ui.add(egui::Slider::new(&mut cfg.detection.arrow_match_threshold, 0.50..=0.90));

                            ui.add_space(6.0);
                            ui.label(RichText::new("Độ trễ giữ phím (ms):").strong());
                            ui.horizontal(|ui| {
                                ui.label("Tối thiểu:");
                                ui.add(egui::Slider::new(&mut cfg.delays.min_key_press_ms, 40..=150));
                                ui.label("Tối đa:");
                                ui.add(egui::Slider::new(&mut cfg.delays.max_key_press_ms, 80..=250));
                            });

                            ui.add_space(6.0);
                            ui.label(RichText::new("Thời gian chờ kéo cá (giây):").strong());
                            ui.add(egui::Slider::new(&mut cfg.delays.reel_in_wait_sec, 2.0..=8.0));

                            ui.add_space(6.0);
                            ui.label(RichText::new("Thời gian nghỉ trước khi quăng lại cần (giây):").strong());
                            ui.add(egui::Slider::new(&mut cfg.delays.recast_wait_sec, 0.5..=6.0));
                        });

                        ui.add_space(8.0);
                        ui.group(|ui| {
                            ui.label(RichText::new("🖥️ Cấu Hình In-Game Overlay (HUD Nổi)").strong());
                            if ui.checkbox(&mut cfg.overlay.enabled, "Bật HUD nổi khi khởi động").changed() {
                                self.overlay_open = cfg.overlay.enabled;
                            }
                            ui.horizontal(|ui| {
                                ui.label("Độ mờ nền HUD (Opacity):");
                                ui.add(egui::Slider::new(&mut cfg.overlay.opacity, 0.2..=1.0));
                            });
                        });

                        ui.add_space(10.0);
                        if ui.button(RichText::new("💾 Lưu Cài Đặt").strong()).clicked() {
                            let _ = cfg.save("config/settings.json");
                            BotController::add_log(&self.bot.state, "✅ Cài đặt đã được lưu thành công.");
                        }
                    }
                }
            }
        });
    }
}
