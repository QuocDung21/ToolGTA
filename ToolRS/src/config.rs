use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GeneralSettings {
    #[serde(default = "default_false")]
    pub auto_start: bool,
    #[serde(default = "default_false")]
    pub auto_recast: bool,
    #[serde(default = "default_f1")]
    pub hotkey_start: String,
    #[serde(default = "default_f2")]
    pub hotkey_pause: String,
    #[serde(default = "default_f3")]
    pub hotkey_panic: String,
    #[serde(default = "default_rod_key")]
    pub rod_slot_key: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DelaySettings {
    #[serde(default = "default_min_press")]
    pub min_key_press_ms: u64,
    #[serde(default = "default_max_press")]
    pub max_key_press_ms: u64,
    #[serde(default = "default_min_interval")]
    pub min_interval_ms: u64,
    #[serde(default = "default_max_interval")]
    pub max_interval_ms: u64,
    #[serde(default = "default_reel_wait")]
    pub reel_in_wait_sec: f32,
    #[serde(default = "default_recast_wait")]
    pub recast_wait_sec: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScreenRoiSettings {
    #[serde(default = "default_false")]
    pub use_custom_roi: bool,
    #[serde(default = "default_roi_left")]
    pub left: f32,
    #[serde(default = "default_roi_top")]
    pub top: f32,
    #[serde(default = "default_roi_width")]
    pub width: f32,
    #[serde(default = "default_roi_height")]
    pub height: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DetectionSettings {
    #[serde(default = "default_threshold")]
    pub arrow_match_threshold: f32,
    #[serde(default)]
    pub monitor_id: Option<u32>,
    #[serde(default)]
    pub screen_roi: ScreenRoiSettings,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AntiAfkSettings {
    #[serde(default = "default_true")]
    pub enabled: bool,
    #[serde(default = "default_true")]
    pub random_look_around: bool,
    #[serde(default = "default_min_afk")]
    pub min_actions_before_anti_afk: u32,
    #[serde(default = "default_max_afk")]
    pub max_actions_before_anti_afk: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OverlaySettings {
    #[serde(default = "default_true")]
    pub enabled: bool,
    #[serde(default = "default_overlay_opacity")]
    pub opacity: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct AppConfig {
    #[serde(default)]
    pub general: GeneralSettings,
    #[serde(default)]
    pub delays: DelaySettings,
    #[serde(default)]
    pub detection: DetectionSettings,
    #[serde(default)]
    pub anti_afk: AntiAfkSettings,
    #[serde(default)]
    pub overlay: OverlaySettings,
}

fn default_overlay_opacity() -> f32 { 0.88 }
fn default_false() -> bool { false }
fn default_true() -> bool { true }
fn default_f1() -> String { "f1".to_string() }
fn default_f2() -> String { "f2".to_string() }
fn default_f3() -> String { "f3".to_string() }
fn default_rod_key() -> String { "1".to_string() }
fn default_min_press() -> u64 { 65 }
fn default_max_press() -> u64 { 115 }
fn default_min_interval() -> u64 { 90 }
fn default_max_interval() -> u64 { 160 }
fn default_reel_wait() -> f32 { 4.5 }
fn default_recast_wait() -> f32 { 2.0 }
fn default_threshold() -> f32 { 0.72 }
fn default_roi_left() -> f32 { 0.30 }
fn default_roi_top() -> f32 { 0.78 }
fn default_roi_width() -> f32 { 0.40 }
fn default_roi_height() -> f32 { 0.17 }
fn default_min_afk() -> u32 { 5 }
fn default_max_afk() -> u32 { 12 }

impl Default for GeneralSettings {
    fn default() -> Self {
        Self {
            auto_start: false,
            auto_recast: false,
            hotkey_start: default_f1(),
            hotkey_pause: default_f2(),
            hotkey_panic: default_f3(),
            rod_slot_key: default_rod_key(),
        }
    }
}

impl Default for DelaySettings {
    fn default() -> Self {
        Self {
            min_key_press_ms: default_min_press(),
            max_key_press_ms: default_max_press(),
            min_interval_ms: default_min_interval(),
            max_interval_ms: default_max_interval(),
            reel_in_wait_sec: default_reel_wait(),
            recast_wait_sec: default_recast_wait(),
        }
    }
}

impl Default for ScreenRoiSettings {
    fn default() -> Self {
        Self {
            use_custom_roi: false,
            left: default_roi_left(),
            top: default_roi_top(),
            width: default_roi_width(),
            height: default_roi_height(),
        }
    }
}

impl Default for DetectionSettings {
    fn default() -> Self {
        Self {
            arrow_match_threshold: default_threshold(),
            monitor_id: None,
            screen_roi: ScreenRoiSettings::default(),
        }
    }
}

impl Default for AntiAfkSettings {
    fn default() -> Self {
        Self {
            enabled: true,
            random_look_around: true,
            min_actions_before_anti_afk: default_min_afk(),
            max_actions_before_anti_afk: default_max_afk(),
        }
    }
}

impl Default for OverlaySettings {
    fn default() -> Self {
        Self {
            enabled: true,
            opacity: default_overlay_opacity(),
        }
    }
}

impl AppConfig {
    pub fn load_or_default(path: &str) -> Self {
        if Path::new(path).exists() {
            if let Ok(content) = fs::read_to_string(path) {
                if let Ok(cfg) = serde_json::from_str(&content) {
                    return cfg;
                }
            }
        }
        Self::default()
    }

    pub fn save(&self, path: &str) -> Result<(), std::io::Error> {
        if let Some(parent) = Path::new(path).parent() {
            fs::create_dir_all(parent)?;
        }
        let json = serde_json::to_string_pretty(self)?;
        fs::write(path, json)?;
        Ok(())
    }
}
