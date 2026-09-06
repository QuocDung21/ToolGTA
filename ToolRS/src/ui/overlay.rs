use crate::bot::BotStatus;
use crate::detector::ArrowDirection;
use eframe::egui::{self, Color32, RichText, Stroke};

pub fn render_overlay(
    ctx: &egui::Context,
    status: BotStatus,
    fish_count: u32,
    solved_count: u32,
    sequence: &[ArrowDirection],
    last_log: Option<&str>,
    opacity: f32,
    is_open: &mut bool,
) {
    let alpha = (opacity.clamp(0.2, 1.0) * 255.0) as u8;
    let bg_color = Color32::from_rgba_unmultiplied(17, 17, 27, alpha);
    let border_color = match status {
        BotStatus::Running | BotStatus::TestingDetected => Color32::from_rgb(166, 227, 161),
        BotStatus::Paused => Color32::from_rgb(250, 179, 135),
        BotStatus::Casting | BotStatus::TestingScanning => Color32::from_rgb(137, 180, 250),
        BotStatus::SolvingQte => Color32::from_rgb(249, 226, 175),
        _ => Color32::from_rgb(108, 112, 134),
    };

    let viewport_id = egui::ViewportId::from_hash_of("in_game_overlay_hud");
    ctx.show_viewport_immediate(
        viewport_id,
        egui::ViewportBuilder::default()
            .with_title("AUTOFISH OVERLAY")
            .with_inner_size([340.0, 180.0])
            .with_min_inner_size([280.0, 150.0])
            .with_always_on_top()
            .with_decorations(false)
            .with_transparent(true),
        |ctx, _class| {
            egui::CentralPanel::default()
                .frame(
                    egui::Frame::none()
                        .fill(bg_color)
                        .stroke(Stroke::new(1.5_f32, border_color))
                        .rounding(10.0)
                        .inner_margin(10.0),
                )
                .show(ctx, |ui| {
                    // Header Bar (Title & Quick Close)
                    ui.horizontal(|ui| {
                        let header_resp = ui.add(
                            egui::Label::new(
                                RichText::new("⚡ AUTOFISH HUD (Kéo để di chuyển)")
                                    .color(Color32::from_rgb(203, 166, 247))
                                    .strong()
                                    .size(12.0),
                            )
                            .sense(egui::Sense::drag()),
                        );
                        if header_resp.dragged() {
                            ctx.send_viewport_cmd_to(viewport_id, egui::ViewportCommand::StartDrag);
                        }

                        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                            if ui
                                .button(RichText::new("❌").color(Color32::from_rgb(243, 139, 168)).size(11.0))
                                .clicked()
                            {
                                *is_open = false;
                            }

                            // Status badge
                            ui.label(
                                RichText::new(format!("● {}", status.as_str()))
                                    .color(border_color)
                                    .size(11.0)
                                    .strong(),
                            );
                        });
                    });

                    ui.separator();
                    ui.add_space(2.0);

                    // Stats Row: Fish & Solved
                    ui.horizontal(|ui| {
                        ui.label(
                            RichText::new(format!("🐟 Cá: {}", fish_count))
                                .color(Color32::from_rgb(137, 220, 235))
                                .strong()
                                .size(13.0),
                        );
                        ui.label(RichText::new("•").color(Color32::from_rgb(108, 112, 134)));
                        ui.label(
                            RichText::new(format!("⚡ QTE: {}", solved_count))
                                .color(Color32::from_rgb(166, 227, 161))
                                .strong()
                                .size(13.0),
                        );
                    });

                    ui.add_space(4.0);

                    // Sequence Box
                    egui::Frame::none()
                        .fill(Color32::from_rgba_unmultiplied(30, 30, 46, alpha))
                        .rounding(6.0)
                        .inner_margin(egui::Margin::symmetric(8.0, 5.0))
                        .show(ui, |ui| {
                            ui.horizontal(|ui| {
                                if sequence.is_empty() {
                                    ui.label(
                                        RichText::new("Chờ QTE...")
                                            .color(Color32::from_rgb(147, 153, 178))
                                            .size(13.0)
                                            .monospace(),
                                    );
                                } else {
                                    let seq_str = sequence
                                        .iter()
                                        .map(|d| format!("{} {}", d.display_icon(), d.as_str()))
                                        .collect::<Vec<_>>()
                                        .join("  ");
                                    ui.label(
                                        RichText::new(seq_str)
                                            .color(Color32::from_rgb(166, 227, 161))
                                            .size(14.0)
                                            .strong()
                                            .monospace(),
                                    );
                                }
                            });
                        });

                    ui.add_space(4.0);

                    // Last Log Row
                    if let Some(log) = last_log {
                        ui.label(
                            RichText::new(format!("📝 {}", log))
                                .color(Color32::from_rgb(186, 194, 222))
                                .size(11.0)
                                .monospace(),
                        );
                    }
                });
        },
    );
}
