use image::{RgbImage, RgbaImage};
use xcap::Monitor;

#[derive(Debug, Clone)]
pub struct MonitorInfo {
    pub id: u32,
    pub name: String,
    pub width: u32,
    pub height: u32,
    pub is_primary: bool,
}

impl MonitorInfo {
    pub fn display_label(&self, index: usize) -> String {
        let primary_tag = if self.is_primary { " [Chính]" } else { "" };
        format!(
            "Màn hình {}: {} ({}x{}){}",
            index + 1,
            self.name,
            self.width,
            self.height,
            primary_tag
        )
    }
}

pub struct ScreenCapture {
    monitors: Vec<Monitor>,
    last_active_id: Option<u32>,
}

impl ScreenCapture {
    pub fn new() -> Self {
        let mut cap = Self {
            monitors: Vec::new(),
            last_active_id: None,
        };
        cap.refresh_monitors();
        cap
    }

    pub fn list_monitors() -> Vec<MonitorInfo> {
        Monitor::all()
            .unwrap_or_default()
            .into_iter()
            .filter_map(|m| {
                let id = m.id().ok()?;
                let name = m.name().unwrap_or_else(|_| format!("Monitor {}", id));
                let width = m.width().unwrap_or(0);
                let height = m.height().unwrap_or(0);
                let is_primary = m.is_primary().unwrap_or(false);
                Some(MonitorInfo {
                    id,
                    name,
                    width,
                    height,
                    is_primary,
                })
            })
            .collect()
    }

    pub fn refresh_monitors(&mut self) {
        self.monitors = Monitor::all().unwrap_or_default();
    }

    pub fn set_active_monitor(&mut self, id: u32) {
        self.last_active_id = Some(id);
    }

    fn rgba_to_rgb(rgba: RgbaImage) -> Option<RgbImage> {
        let (w, h) = rgba.dimensions();
        let raw = rgba.into_raw();
        let mut rgb_raw = Vec::with_capacity((w * h * 3) as usize);

        for chunk in raw.chunks_exact(4) {
            rgb_raw.push(chunk[0]); // R
            rgb_raw.push(chunk[1]); // G
            rgb_raw.push(chunk[2]); // B
        }

        RgbImage::from_raw(w, h, rgb_raw)
    }

    fn ordered_monitors(&self, target_monitor_id: Option<u32>) -> Vec<Monitor> {
        if let Some(target_id) = target_monitor_id {
            let matched: Vec<Monitor> = self
                .monitors
                .iter()
                .filter(|m| m.id().ok() == Some(target_id))
                .cloned()
                .collect();
            if !matched.is_empty() {
                return matched;
            }
        }

        let mut list = self.monitors.clone();
        if let Some(active_id) = self.last_active_id {
            if let Some(pos) = list.iter().position(|m| m.id().ok() == Some(active_id)) {
                if pos > 0 {
                    let m = list.remove(pos);
                    list.insert(0, m);
                }
            }
        }
        list
    }

    fn capture_ordered(&self, targets: &[Monitor]) -> Vec<(u32, RgbImage)> {
        let mut frames = Vec::with_capacity(targets.len());
        for m in targets {
            let id = m.id().unwrap_or(0);
            if let Ok(rgba) = m.capture_image() {
                if let Some(rgb) = Self::rgba_to_rgb(rgba) {
                    frames.push((id, rgb));
                }
            }
        }
        frames
    }

    /// Capture target monitor (if specified and found) or all monitors.
    /// Automatically refreshes monitor handles once if capture fails or target is missing.
    pub fn capture_targets(&mut self, target_monitor_id: Option<u32>) -> Vec<(u32, RgbImage)> {
        if self.monitors.is_empty() {
            self.refresh_monitors();
        }

        let targets = self.ordered_monitors(target_monitor_id);
        let frames = self.capture_ordered(&targets);

        if !frames.is_empty() {
            return frames;
        }

        // Refresh monitor handles and retry once (handles desktop switch/resolution change/display plug-unplug)
        self.refresh_monitors();
        let targets = self.ordered_monitors(target_monitor_id);
        self.capture_ordered(&targets)
    }

    pub fn capture_full(&mut self) -> Option<RgbImage> {
        self.capture_targets(None).into_iter().next().map(|(_, img)| img)
    }
}


