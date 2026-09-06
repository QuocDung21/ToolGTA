use image::RgbImage;
use xcap::Monitor;

pub struct ScreenCapture {
    monitor: Option<Monitor>,
}

impl ScreenCapture {
    pub fn new() -> Self {
        let mut cap = Self { monitor: None };
        cap.refresh_monitor();
        cap
    }

    pub fn refresh_monitor(&mut self) {
        let monitors = Monitor::all().unwrap_or_default();
        self.monitor = monitors.into_iter().find(|m| m.is_primary().unwrap_or(false)).or_else(|| {
            Monitor::all().ok().and_then(|ms| ms.into_iter().next())
        });
    }

    pub fn capture_full(&mut self) -> Option<RgbImage> {
        if self.monitor.is_none() {
            self.refresh_monitor();
        }

        // Try capture with cached monitor
        let result = if let Some(ref m) = self.monitor {
            m.capture_image().ok()
        } else {
            None
        };

        // If capture failed, refresh monitor and retry once (handles desktop switch/resolution change/handle invalidation)
        let rgba = match result {
            Some(r) => r,
            None => {
                self.refresh_monitor();
                let m = self.monitor.as_ref()?;
                m.capture_image().ok()?
            }
        };

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
}


