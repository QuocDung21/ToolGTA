use std::thread;
use std::time::Duration;
use rand::Rng;

#[derive(Debug, Clone, Copy)]
pub struct KeyMapping {
    pub scancode: u16,
    pub extended: bool,
}

pub fn get_key_scancode(key: &str) -> Option<KeyMapping> {
    match key.to_uppercase().as_str() {
        "UP" => Some(KeyMapping { scancode: 0x48, extended: true }),
        "DOWN" => Some(KeyMapping { scancode: 0x50, extended: true }),
        "LEFT" => Some(KeyMapping { scancode: 0x4B, extended: true }),
        "RIGHT" => Some(KeyMapping { scancode: 0x4D, extended: true }),
        "W" => Some(KeyMapping { scancode: 0x11, extended: false }),
        "A" => Some(KeyMapping { scancode: 0x1E, extended: false }),
        "S" => Some(KeyMapping { scancode: 0x1F, extended: false }),
        "D" => Some(KeyMapping { scancode: 0x20, extended: false }),
        "SPACE" => Some(KeyMapping { scancode: 0x39, extended: false }),
        "SHIFT" => Some(KeyMapping { scancode: 0x2A, extended: false }),
        "CTRL" => Some(KeyMapping { scancode: 0x1D, extended: false }),
        "E" => Some(KeyMapping { scancode: 0x12, extended: false }),
        "1" => Some(KeyMapping { scancode: 0x02, extended: false }),
        "2" => Some(KeyMapping { scancode: 0x03, extended: false }),
        "3" => Some(KeyMapping { scancode: 0x04, extended: false }),
        "4" => Some(KeyMapping { scancode: 0x05, extended: false }),
        "5" => Some(KeyMapping { scancode: 0x06, extended: false }),
        _ => None,
    }
}

pub struct InputSimulator {
    pub min_press_ms: u64,
    pub max_press_ms: u64,
    pub min_interval_ms: u64,
    pub max_interval_ms: u64,
}

impl InputSimulator {
    pub fn new(min_press_ms: u64, max_press_ms: u64, min_interval_ms: u64, max_interval_ms: u64) -> Self {
        Self {
            min_press_ms,
            max_press_ms,
            min_interval_ms,
            max_interval_ms,
        }
    }

    #[cfg(target_os = "windows")]
    fn send_key_raw(scancode: u16, extended: bool, is_down: bool) {
        use windows::Win32::UI::Input::KeyboardAndMouse::{
            SendInput, INPUT, INPUT_KEYBOARD, KEYBDINPUT, KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP,
            KEYEVENTF_SCANCODE,
        };

        let mut flags = KEYEVENTF_SCANCODE;
        if extended {
            flags |= KEYEVENTF_EXTENDEDKEY;
        }
        if !is_down {
            flags |= KEYEVENTF_KEYUP;
        }

        let input = INPUT {
            r#type: INPUT_KEYBOARD,
            Anonymous: windows::Win32::UI::Input::KeyboardAndMouse::INPUT_0 {
                ki: KEYBDINPUT {
                    wVk: windows::Win32::UI::Input::KeyboardAndMouse::VIRTUAL_KEY(0),
                    wScan: scancode,
                    dwFlags: flags,
                    time: 0,
                    dwExtraInfo: 0,
                },
            },
        };

        unsafe {
            SendInput(&[input], std::mem::size_of::<INPUT>() as i32);
        }
    }

    #[cfg(not(target_os = "windows"))]
    fn send_key_raw(_scancode: u16, _extended: bool, _is_down: bool) {
        // macOS / Linux mock simulation
    }

    pub fn press_key(&self, key_name: &str, duration_ms: Option<u64>) {
        if let Some(mapping) = get_key_scancode(key_name) {
            let dur = duration_ms.unwrap_or_else(|| {
                rand::thread_rng().gen_range(self.min_press_ms..=self.max_press_ms)
            });

            Self::send_key_raw(mapping.scancode, mapping.extended, true);
            thread::sleep(Duration::from_millis(dur));
            Self::send_key_raw(mapping.scancode, mapping.extended, false);
        }
    }

    pub fn execute_sequence(&self, keys: &[&str]) {
        for (i, &key) in keys.iter().enumerate() {
            self.press_key(key, None);
            if i < keys.len() - 1 {
                let interval = rand::thread_rng().gen_range(self.min_interval_ms..=self.max_interval_ms);
                thread::sleep(Duration::from_millis(interval));
            }
        }
    }
}
