pub mod bot;
pub mod capture;
pub mod config;
pub mod detector;
pub mod input;
pub mod ui;

use eframe::egui;
use ui::AutoFishApp;

fn main() -> eframe::Result<()> {
    let native_options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([880.0, 680.0])
            .with_min_inner_size([820.0, 620.0])
            .with_title("⚡ LŨ QUỶ RP - AUTO FISHING TOOL PRO (RUST NATIVE)"),
        ..Default::default()
    };

    eframe::run_native(
        "AutoFishingToolRust",
        native_options,
        Box::new(|cc| Ok(Box::new(AutoFishApp::new(cc)))),
    )
}
