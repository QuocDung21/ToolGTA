use image::{GrayImage, RgbImage};
use std::collections::HashMap;
use std::path::Path;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ArrowDirection {
    Up,
    Down,
    Left,
    Right,
}

impl ArrowDirection {
    pub fn as_str(&self) -> &'static str {
        match self {
            ArrowDirection::Up => "UP",
            ArrowDirection::Down => "DOWN",
            ArrowDirection::Left => "LEFT",
            ArrowDirection::Right => "RIGHT",
        }
    }

    pub fn display_icon(&self) -> &'static str {
        match self {
            ArrowDirection::Up => "⬆",
            ArrowDirection::Down => "⬇",
            ArrowDirection::Left => "⬅",
            ArrowDirection::Right => "➡",
        }
    }
}

pub struct ArrowDetector {
    pub templates: HashMap<ArrowDirection, GrayImage>,
    pub threshold: f32,
}

impl ArrowDetector {
    pub fn new(template_dir: &str, threshold: f32) -> Self {
        let mut templates = HashMap::new();
        let mapping = [
            (ArrowDirection::Up, "arrow_up.png"),
            (ArrowDirection::Down, "arrow_down.png"),
            (ArrowDirection::Left, "arrow_left.png"),
            (ArrowDirection::Right, "arrow_right.png"),
        ];

        for (dir, filename) in mapping {
            let path = Path::new(template_dir).join(filename);
            if let Ok(img) = image::open(&path) {
                templates.insert(dir, img.to_luma8());
            }
        }

        Self { templates, threshold }
    }

    /// Fast nearest-neighbor grayscale resize
    fn resize_gray(img: &GrayImage, new_w: u32, new_h: u32) -> GrayImage {
        let (w, h) = img.dimensions();
        if w == new_w && h == new_h {
            return img.clone();
        }
        let src = img.as_raw();
        let mut out = vec![0u8; (new_w * new_h) as usize];
        for y in 0..new_h {
            let src_y = ((y * h) / new_h).min(h - 1) as usize;
            let dst_row = (y * new_w) as usize;
            let src_row = src_y * w as usize;
            for x in 0..new_w {
                let src_x = ((x * w) / new_w).min(w - 1) as usize;
                out[dst_row + x as usize] = src[src_row + src_x];
            }
        }
        GrayImage::from_raw(new_w, new_h, out).unwrap_or_else(|| img.clone())
    }

    /// Match template on a flat 8-bit mask buffer using Normalized Cross-Correlation
    pub fn match_template_raw(mask: &[u8], mask_w: u32, mask_h: u32, tpl: &[u8], tpl_w: u32, tpl_h: u32) -> f32 {
        if mask_w < tpl_w || mask_h < tpl_h {
            return -1.0;
        }

        let num_pixels = (tpl_w * tpl_h) as f32;
        if num_pixels < 1.0 {
            return -1.0;
        }

        // Precompute template mean, diff, and variance
        let mut tpl_sum = 0.0f32;
        for &v in tpl {
            tpl_sum += v as f32;
        }
        let tpl_mean = tpl_sum / num_pixels;

        let mut tpl_var = 0.0f32;
        let mut tpl_diff = Vec::with_capacity(tpl.len());
        for &v in tpl {
            let d = v as f32 - tpl_mean;
            tpl_diff.push(d);
            tpl_var += d * d;
        }

        if tpl_var < 1e-6 {
            return 0.0;
        }

        let out_w = mask_w - tpl_w + 1;
        let out_h = mask_h - tpl_h + 1;
        let mut best_score = -1.0f32;

        for iy in 0..out_h {
            for ix in 0..out_w {
                let mut patch_sum = 0.0f32;
                for py in 0..tpl_h {
                    let r_start = ((iy + py) * mask_w + ix) as usize;
                    for px in 0..tpl_w {
                        patch_sum += mask[r_start + px as usize] as f32;
                    }
                }
                let patch_mean = patch_sum / num_pixels;

                let mut patch_var = 0.0f32;
                let mut cross_sum = 0.0f32;

                for py in 0..tpl_h {
                    let r_start = ((iy + py) * mask_w + ix) as usize;
                    let t_start = (py * tpl_w) as usize;
                    for px in 0..tpl_w {
                        let p_diff = mask[r_start + px as usize] as f32 - patch_mean;
                        patch_var += p_diff * p_diff;
                        cross_sum += p_diff * tpl_diff[t_start + px as usize];
                    }
                }

                let denom = (tpl_var * patch_var).sqrt();
                let score = if denom > 1e-6 { cross_sum / denom } else { -1.0 };
                if score > best_score {
                    best_score = score;
                }
            }
        }

        best_score
    }

    /// Match an arrow inside a cropped box with auto-padding
    pub fn match_arrow_in_box(&self, box_rgb: &RgbImage) -> (Option<ArrowDirection>, f32) {
        if self.templates.is_empty() || box_rgb.width() < 8 || box_rgb.height() < 8 {
            return (None, 0.0);
        }

        let (w, h) = box_rgb.dimensions();
        let raw = box_rgb.as_raw();
        let num_pixels = (w * h) as usize;
        let mut mask = vec![0u8; num_pixels];

        for i in 0..num_pixels {
            let r = raw[i * 3];
            let g = raw[i * 3 + 1];
            let b = raw[i * 3 + 2];
            let gray = ((77 * r as u32 + 150 * g as u32 + 29 * b as u32) >> 8) as u8;
            if r > 185 || gray > 175 {
                mask[i] = 255;
            }
        }

        let tpl_scale = (h as f32 / 29.0).max(0.5);
        let mut best_dir = None;
        let mut best_score = -1.0f32;

        for (&dir, tpl) in &self.templates {
            let tw = (tpl.width() as f32 * tpl_scale).round().max(4.0) as u32;
            let th = (tpl.height() as f32 * tpl_scale).round().max(4.0) as u32;
            let scaled_tpl = Self::resize_gray(tpl, tw, th);

            // Safe padding if crop is slightly smaller than scaled template
            let target_w = w.max(tw);
            let target_h = h.max(th);

            let (cur_mask, cur_w, cur_h) = if target_w > w || target_h > h {
                let mut padded = vec![0u8; (target_w * target_h) as usize];
                let off_x = (target_w - w) / 2;
                let off_y = (target_h - h) / 2;
                for row in 0..h {
                    let s_start = (row * w) as usize;
                    let d_start = ((row + off_y) * target_w + off_x) as usize;
                    padded[d_start..d_start + w as usize].copy_from_slice(&mask[s_start..s_start + w as usize]);
                }
                (padded, target_w, target_h)
            } else {
                (mask.clone(), w, h)
            };

            let score = Self::match_template_raw(&cur_mask, cur_w, cur_h, scaled_tpl.as_raw(), tw, th);
            if score > best_score {
                best_score = score;
                best_dir = Some(dir);
            }
        }

        let threshold = self.threshold.min(0.60);
        if best_score >= threshold {
            (best_dir, best_score)
        } else {
            (None, best_score)
        }
    }

    /// Extract 5 arrow boxes from full frame using proven narrow ROI
    pub fn extract_arrow_boxes(&self, frame: &RgbImage) -> Vec<RgbImage> {
        let (w, h) = frame.dimensions();
        if w < 100 || h < 100 {
            return Vec::new();
        }

        let scale = h as f32 / 568.0;

        // Strict narrow band matching proven C# implementation (avoids GTA HUD/health bar noise)
        let roi_y1 = ((h as f32 * 0.81).round() as u32).min(h.saturating_sub(2));
        let roi_y2 = ((h as f32 * 0.92).round() as u32).clamp(roi_y1 + 1, h);
        let roi_x1 = ((w as f32 * 0.35).round() as u32).min(w.saturating_sub(2));
        let roi_x2 = ((w as f32 * 0.65).round() as u32).clamp(roi_x1 + 1, w);

        let roi_w = roi_x2.saturating_sub(roi_x1);
        let roi_h = roi_y2.saturating_sub(roi_y1);
        if roi_w <= 50 || roi_h <= 20 {
            return Vec::new();
        }

        // Create binary mask for dark or red boxes in ROI
        let frame_raw = frame.as_raw();
        let stride = (w * 3) as usize;
        let mut mask = vec![0u8; (roi_w * roi_h) as usize];

        for y in 0..roi_h {
            let fy = (roi_y1 + y) as usize;
            let m_row = (y * roi_w) as usize;
            for x in 0..roi_w {
                let fx = (roi_x1 + x) as usize;
                let idx = fy * stride + fx * 3;
                let r = frame_raw[idx] as i32;
                let g = frame_raw[idx + 1] as i32;
                let b = frame_raw[idx + 2] as i32;
                let gray = (77 * r + 150 * g + 29 * b) >> 8;

                let is_dark = gray < 70;
                let is_red = (r - g > 30) && (r > 115);
                if is_dark || is_red {
                    mask[m_row + x as usize] = 255;
                }
            }
        }

        let min_dim = (15.0 * scale).round().max(12.0) as u32;
        let max_dim = (38.0 * scale).round().max(25.0) as u32;

        let mut visited = vec![false; (roi_w * roi_h) as usize];
        let mut candidates: Vec<(u32, u32, u32, u32)> = Vec::new();
        let mut queue = Vec::with_capacity(512);

        for y in 0..roi_h {
            for x in 0..roi_w {
                let idx = (y * roi_w + x) as usize;
                if visited[idx] || mask[idx] == 0 {
                    continue;
                }

                queue.clear();
                queue.push((x, y));
                visited[idx] = true;
                let (mut min_x, mut max_x) = (x, x);
                let (mut min_y, mut max_y) = (y, y);

                while let Some((cx, cy)) = queue.pop() {
                    min_x = min_x.min(cx);
                    max_x = max_x.max(cx);
                    min_y = min_y.min(cy);
                    max_y = max_y.max(cy);

                    for (dx, dy) in [(-1, 0), (1, 0), (0, -1), (0, 1)] {
                        let nx = cx as i32 + dx;
                        let ny = cy as i32 + dy;
                        if nx >= 0 && nx < roi_w as i32 && ny >= 0 && ny < roi_h as i32 {
                            let n_idx = (ny as u32 * roi_w + nx as u32) as usize;
                            if !visited[n_idx] && mask[n_idx] > 0 {
                                visited[n_idx] = true;
                                queue.push((nx as u32, ny as u32));
                            }
                        }
                    }
                }

                let bw = max_x - min_x + 1;
                let bh = max_y - min_y + 1;
                if bw >= min_dim && bw <= max_dim && bh >= min_dim && bh <= max_dim {
                    candidates.push((min_x, min_y, bw, bh));
                }
            }
        }

        let mut avg_y = 0;
        let avg_h = (23.0 * scale).round() as u32;
        let avg_w = (23.0 * scale).round() as u32;
        let mut step = 27.25 * scale;

        if candidates.len() >= 2 {
            let y_tol = (6.0 * scale).round().max(4.0) as u32;
            let mut groups: Vec<Vec<(u32, u32, u32, u32)>> = Vec::new();
            for b in candidates {
                let mut matched = false;
                for grp in &mut groups {
                    if (grp[0].1 as i32 - b.1 as i32).abs() <= y_tol as i32 {
                        grp.push(b);
                        matched = true;
                        break;
                    }
                }
                if !matched {
                    groups.push(vec![b]);
                }
            }

            let valid_grps: Vec<&Vec<(u32, u32, u32, u32)>> = groups.iter().filter(|g| g.len() >= 2).collect();
            if let Some(best_grp) = valid_grps.into_iter().max_by_key(|g| g.len()) {
                let mut sorted = best_grp.clone();
                sorted.sort_by_key(|b| b.0);

                let sum_y: u32 = sorted.iter().map(|b| b.1).sum();
                avg_y = sum_y / sorted.len() as u32;

                if sorted.len() >= 2 {
                    let mut steps = Vec::new();
                    for i in 0..sorted.len() - 1 {
                        steps.push((sorted[i + 1].0 - sorted[i].0) as f32);
                    }
                    steps.sort_by(|a, b| a.partial_cmp(b).unwrap());
                    let med = steps[steps.len() / 2];
                    if med >= 18.0 * scale && med <= 42.0 * scale {
                        step = med;
                    }
                }
            }
        }

        if avg_y == 0 {
            avg_y = (roi_h as f32 * 0.55).round() as u32;
        }

        let roi_center_x = roi_w as f32 / 2.0;
        let total_span = 4.0 * step + avg_w as f32;
        let start_x = roi_center_x - total_span / 2.0;

        let margin_y = (3.0 * scale).round().max(2.0) as u32;
        let margin_x = (3.0 * scale).round().max(2.0) as u32;

        let mut boxes = Vec::with_capacity(5);
        for i in 0..5 {
            let bx = (start_x + i as f32 * step).round() as i32;
            let by = avg_y as i32;

            let x1 = (bx - margin_x as i32).max(0) as u32;
            let y1 = (by - margin_y as i32).max(0) as u32;
            let x2 = ((bx + avg_w as i32 + margin_x as i32) as u32).min(roi_w);
            let y2 = ((by + avg_h as i32 + margin_y as i32) as u32).min(roi_h);

            if x2 <= x1 || y2 <= y1 {
                return Vec::new();
            }

            let crop_w = x2 - x1;
            let crop_h = y2 - y1;
            let mut crop_data = Vec::with_capacity((crop_w * crop_h * 3) as usize);
            for cy in 0..crop_h {
                let fy = (roi_y1 + y1 + cy) as usize;
                let fx_start = (roi_x1 + x1) as usize;
                let src_idx = fy * stride + fx_start * 3;
                crop_data.extend_from_slice(&frame_raw[src_idx..src_idx + (crop_w * 3) as usize]);
            }

            if let Some(crop) = RgbImage::from_raw(crop_w, crop_h, crop_data) {
                boxes.push(crop);
            } else {
                return Vec::new();
            }
        }

        boxes
    }

    /// Detect sequence of 5 arrows from frame
    pub fn detect_sequence(&self, frame: &RgbImage) -> Vec<ArrowDirection> {
        let boxes = self.extract_arrow_boxes(frame);
        if boxes.len() != 5 {
            return Vec::new();
        }

        let mut seq = Vec::with_capacity(5);
        for b in &boxes {
            let (dir, _) = self.match_arrow_in_box(b);
            if let Some(d) = dir {
                seq.push(d);
            } else {
                return Vec::new();
            }
        }

        if seq.len() == 5 {
            seq
        } else {
            Vec::new()
        }
    }
}

