use crate::capture::ScreenCapture;
use crate::config::AppConfig;
use crate::detector::{ArrowDetector, ArrowDirection};
use crate::input::InputSimulator;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};
use rand::Rng;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BotStatus {
    Idle,
    Running,
    Paused,
    Casting,
    WaitingBite,
    SolvingQte,
    ReelingIn,
    TestingScanning,
    TestingDetected,
}

impl BotStatus {
    pub fn as_str(&self) -> &'static str {
        match self {
            BotStatus::Idle => "SẴN SÀNG (IDLE)",
            BotStatus::Running => "ĐANG CHẠY (RUNNING)",
            BotStatus::Paused => "TẠM DỪNG (PAUSED)",
            BotStatus::Casting => "ĐANG QUĂNG CẦN (CASTING)",
            BotStatus::WaitingBite => "CHỜ CÁ CẮN (WAITING BITE)",
            BotStatus::SolvingQte => "ĐANG GIẢI QTE (SOLVING)",
            BotStatus::ReelingIn => "ĐANG THU CẦN (REELING IN)",
            BotStatus::TestingScanning => "TEST: ĐANG QUÉT (SCANNING)",
            BotStatus::TestingDetected => "TEST: ĐÃ PHÁT HIỆN QTE",
        }
    }

    pub fn color_hex(&self) -> &'static str {
        match self {
            BotStatus::Idle => "#a6adc8",
            BotStatus::Running | BotStatus::TestingDetected => "#a6e3a1",
            BotStatus::Paused => "#fab387",
            BotStatus::Casting | BotStatus::TestingScanning => "#89b4fa",
            BotStatus::WaitingBite => "#b4befe",
            BotStatus::SolvingQte => "#f9e2af",
            BotStatus::ReelingIn => "#89dceb",
        }
    }
}

pub struct BotState {
    pub status: BotStatus,
    pub fish_count: u32,
    pub solved_count: u32,
    pub last_sequence: Vec<ArrowDirection>,
    pub logs: Vec<(String, String)>, // (timestamp, message)
    pub is_running: bool,
    pub is_paused: bool,
    pub is_test_mode: bool,
}

impl Default for BotState {
    fn default() -> Self {
        Self {
            status: BotStatus::Idle,
            fish_count: 0,
            solved_count: 0,
            last_sequence: Vec::new(),
            logs: vec![(
                chrono::Local::now().format("%H:%M:%S").to_string(),
                "⚡ AutoFishing Bot Rust Native đã khởi động.".to_string(),
            )],
            is_running: false,
            is_paused: false,
            is_test_mode: false,
        }
    }
}

pub struct BotController {
    pub state: Arc<Mutex<BotState>>,
    pub should_exit: Arc<AtomicBool>,
    pub config: Arc<Mutex<AppConfig>>,
}

impl BotController {
    pub fn new(config: AppConfig) -> Self {
        let state = Arc::new(Mutex::new(BotState::default()));
        let should_exit = Arc::new(AtomicBool::new(false));
        let config = Arc::new(Mutex::new(config));

        let state_clone = Arc::clone(&state);
        let exit_clone = Arc::clone(&should_exit);
        let cfg_clone = Arc::clone(&config);

        // Spawn background worker loop
        thread::spawn(move || {
            Self::worker_loop(state_clone, cfg_clone, exit_clone);
        });

        // Spawn global hotkey listener thread (Windows)
        let state_hk = Arc::clone(&state);
        let exit_hk = Arc::clone(&should_exit);
        thread::spawn(move || {
            Self::hotkey_loop(state_hk, exit_hk);
        });

        Self {
            state,
            should_exit,
            config,
        }
    }

    #[cfg(target_os = "windows")]
    fn hotkey_loop(state: Arc<Mutex<BotState>>, exit: Arc<AtomicBool>) {
        use windows::Win32::UI::Input::KeyboardAndMouse::{GetAsyncKeyState, VK_F1, VK_F2, VK_F3};
        let mut f1_was_down = false;
        let mut f2_was_down = false;
        let mut f3_was_down = false;

        while !exit.load(Ordering::Relaxed) {
            unsafe {
                let f1_is_down = (GetAsyncKeyState(VK_F1.0 as i32) as u16 & 0x8000) != 0;
                let f2_is_down = (GetAsyncKeyState(VK_F2.0 as i32) as u16 & 0x8000) != 0;
                let f3_is_down = (GetAsyncKeyState(VK_F3.0 as i32) as u16 & 0x8000) != 0;

                if f1_is_down && !f1_was_down {
                    Self::toggle_running_internal(&state);
                }
                if f2_is_down && !f2_was_down {
                    Self::toggle_pause_internal(&state);
                }
                if f3_is_down && !f3_was_down {
                    Self::panic_exit_internal(&state);
                }

                f1_was_down = f1_is_down;
                f2_was_down = f2_is_down;
                f3_was_down = f3_is_down;
            }
            thread::sleep(Duration::from_millis(25));
        }
    }

    #[cfg(not(target_os = "windows"))]
    fn hotkey_loop(_state: Arc<Mutex<BotState>>, _exit: Arc<AtomicBool>) {}

    pub fn add_log(state: &Arc<Mutex<BotState>>, msg: &str) {
        if let Ok(mut s) = state.lock() {
            let time_str = chrono::Local::now().format("%H:%M:%S").to_string();
            s.logs.push((time_str, msg.to_string()));
            if s.logs.len() > 300 {
                s.logs.remove(0);
            }
        }
    }

    fn toggle_running_internal(state: &Arc<Mutex<BotState>>) {
        if let Ok(mut s) = state.lock() {
            if s.is_test_mode {
                s.is_test_mode = false;
            }
            s.is_running = !s.is_running;
            let time_str = chrono::Local::now().format("%H:%M:%S").to_string();
            if s.is_running {
                s.status = BotStatus::Running;
                s.logs.push((time_str, "🟢 Tool ĐÃ BẬT: Đang lắng nghe màn hình. Hãy quăng cần trong game, Tool sẽ tự động giải 5 mũi tên!".to_string()));
            } else {
                s.status = BotStatus::Idle;
                s.logs.push((time_str, "⏹ Bot đã dừng.".to_string()));
            }
        }
    }

    pub fn toggle_running(&self) {
        Self::toggle_running_internal(&self.state);
    }

    fn toggle_pause_internal(state: &Arc<Mutex<BotState>>) {
        if let Ok(mut s) = state.lock() {
            if s.is_running {
                s.is_paused = !s.is_paused;
                s.status = if s.is_paused { BotStatus::Paused } else { BotStatus::Running };
                let msg = if s.is_paused { "⏸ Bot tạm dừng.".to_string() } else { "▶ Bot tiếp tục chạy.".to_string() };
                let time_str = chrono::Local::now().format("%H:%M:%S").to_string();
                s.logs.push((time_str, msg));
            }
        }
    }

    pub fn toggle_pause(&self) {
        Self::toggle_pause_internal(&self.state);
    }

    fn panic_exit_internal(state: &Arc<Mutex<BotState>>) {
        if let Ok(mut s) = state.lock() {
            s.is_running = false;
            s.is_test_mode = false;
            s.status = BotStatus::Idle;
            let time_str = chrono::Local::now().format("%H:%M:%S").to_string();
            s.logs.push((time_str, "🚨 KHẨN CẤP (F3): Dừng toàn bộ hoạt động!".to_string()));
        }
    }

    pub fn panic_exit(&self) {
        Self::panic_exit_internal(&self.state);
    }

    pub fn toggle_test_mode(&self) {
        if let Ok(mut s) = self.state.lock() {
            s.is_test_mode = !s.is_test_mode;
            let time_str = chrono::Local::now().format("%H:%M:%S").to_string();
            if s.is_test_mode {
                s.is_running = false;
                s.is_paused = false;
                s.status = BotStatus::TestingScanning;
                s.logs.push((time_str, "🎯 [TEST VIDEO] Đã BẬT quét màn hình! Hãy phát video để xem log nhận diện.".to_string()));
            } else {
                s.status = BotStatus::Idle;
                s.logs.push((time_str, "⏹ [TEST VIDEO] Đã TẮT chế độ test.".to_string()));
            }
        }
    }

    fn worker_loop(state: Arc<Mutex<BotState>>, config: Arc<Mutex<AppConfig>>, exit: Arc<AtomicBool>) {
        let mut capture = ScreenCapture::new();
        let mut detector = ArrowDetector::new("assets/templates", 0.65);
        if detector.templates.is_empty() {
            detector = ArrowDetector::new("../assets/templates", 0.65);
        }
        if detector.templates.is_empty() {
            Self::add_log(&state, "⚠️ CẢNH BÁO: Không tìm thấy ảnh mẫu mũi tên trong thư mục assets/templates!");
        } else {
            Self::add_log(&state, &format!("⚡ Đã sẵn sàng: Đã nạp {} mẫu mũi tên nhận diện.", detector.templates.len()));
        }

        let mut simulator = InputSimulator::new(65, 115, 90, 160);

        let mut last_test_detect = Instant::now();
        let mut last_bite_time = Instant::now();
        let mut need_initial_cast = false;
        let mut last_heartbeat = Instant::now();

        while !exit.load(Ordering::Relaxed) {
            let (is_run, is_paused, is_test) = {
                if let Ok(s) = state.lock() {
                    (s.is_running, s.is_paused, s.is_test_mode)
                } else {
                    (false, false, false)
                }
            };

            if is_test {
                // TEST VIDEO MODE: Chụp & nhận diện màn hình không gửi phím
                let t0 = Instant::now();
                if let Some(frame) = capture.capture_full() {
                    let cap_ms = t0.elapsed().as_secs_f32() * 1000.0;
                    let t1 = Instant::now();
                    let seq = detector.detect_sequence(&frame);
                    let det_ms = t1.elapsed().as_secs_f32() * 1000.0;

                    if seq.len() == 5 {
                        if last_test_detect.elapsed() > Duration::from_millis(1500) {
                            last_test_detect = Instant::now();
                            let seq_str = seq.iter().map(|d| format!("[{} {}]", d.display_icon(), d.as_str())).collect::<Vec<_>>().join(" ");
                            let log_msg = format!("🔥 [TEST VIDEO] PHÁT HIỆN MINIGAME: {} | Chụp: {:.1}ms | Nhận diện: {:.1}ms", seq_str, cap_ms, det_ms);

                            if let Ok(mut s) = state.lock() {
                                s.solved_count += 1;
                                s.last_sequence = seq;
                                s.status = BotStatus::TestingDetected;
                                let time_str = chrono::Local::now().format("%H:%M:%S").to_string();
                                s.logs.push((time_str, log_msg));
                            }
                        }
                    } else if last_test_detect.elapsed() > Duration::from_millis(2000) {
                        if let Ok(mut s) = state.lock() {
                            s.status = BotStatus::TestingScanning;
                        }
                    }
                }
                thread::sleep(Duration::from_millis(15));
            } else if is_run && !is_paused {
                // Lấy thông số cấu hình thời gian thực
                let (auto_recast, rod_key, reel_wait, recast_wait, threshold, min_press, max_press, min_int, max_int) = {
                    config.lock().map(|c| (
                        c.general.auto_recast,
                        c.general.rod_slot_key.clone(),
                        c.delays.reel_in_wait_sec,
                        c.delays.recast_wait_sec,
                        c.detection.arrow_match_threshold,
                        c.delays.min_key_press_ms,
                        c.delays.max_key_press_ms,
                        c.delays.min_interval_ms,
                        c.delays.max_interval_ms,
                    )).unwrap_or((false, "1".to_string(), 4.5, 2.0, 0.65, 65, 115, 90, 160))
                };

                detector.threshold = threshold;
                simulator.min_press_ms = min_press;
                simulator.max_press_ms = max_press;
                simulator.min_interval_ms = min_int;
                simulator.max_interval_ms = max_int;

                // Nếu bật auto_recast: quăng cần lúc vừa nhấn Bắt Đầu
                if auto_recast && need_initial_cast {
                    need_initial_cast = false;
                    Self::add_log(&state, &format!("🎣 Bắt đầu câu: Quăng cần câu (phím '{}')...", rod_key));
                    if let Ok(mut s) = state.lock() {
                        s.status = BotStatus::Casting;
                    }
                    simulator.press_key(&rod_key, None);
                    thread::sleep(Duration::from_millis(2500));
                    if let Ok(mut s) = state.lock() {
                        s.status = BotStatus::WaitingBite;
                    }
                    last_bite_time = Instant::now();
                } else if !auto_recast && need_initial_cast {
                    need_initial_cast = false;
                    if let Ok(mut s) = state.lock() {
                        s.status = BotStatus::WaitingBite;
                    }
                    last_bite_time = Instant::now();
                }

                // Heartbeat thông báo định kỳ mỗi 15 giây
                if last_heartbeat.elapsed() > Duration::from_secs(15) {
                    last_heartbeat = Instant::now();
                    Self::add_log(&state, "🎧 [LẮNG NGHE] Đang canh màn hình... Chờ minigame xuất hiện.");
                }

                if let Some(frame) = capture.capture_full() {
                    let seq = detector.detect_sequence(&frame);
                    if seq.len() == 5 {
                        let seq_strs: Vec<&str> = seq.iter().map(|d| d.as_str()).collect();
                        let pretty = seq.iter().map(|d| format!("[{} {}]", d.display_icon(), d.as_str())).collect::<Vec<_>>().join(" ");
                        Self::add_log(&state, &format!("🎯 Phát hiện minigame câu cá! Mũi tên: {}", pretty));

                        if let Ok(mut s) = state.lock() {
                            s.status = BotStatus::SolvingQte;
                            s.last_sequence = seq.clone();
                        }

                        // Human reaction delay
                        thread::sleep(Duration::from_millis(rand::thread_rng().gen_range(120..200)));
                        simulator.execute_sequence(&seq_strs);

                        Self::add_log(&state, "⚡ Giải QTE thành công!");
                        if let Ok(mut s) = state.lock() {
                            s.solved_count += 1;
                            s.fish_count += 1;
                        }

                        // Chờ 2 giây để giao diện minigame trên màn hình game tắt hẳn
                        thread::sleep(Duration::from_millis(2000));

                        if auto_recast {
                            // Tự động kéo cá và quăng lại cần
                            if let Ok(mut s) = state.lock() {
                                s.status = BotStatus::ReelingIn;
                            }
                            Self::add_log(&state, "🐟 Đang kéo cá lên...");
                            thread::sleep(Duration::from_secs_f32(reel_wait));

                            thread::sleep(Duration::from_secs_f32(recast_wait));

                            Self::add_log(&state, &format!("🎣 Quăng lại cần câu với phím '{}'...", rod_key));
                            if let Ok(mut s) = state.lock() {
                                s.status = BotStatus::Casting;
                            }
                            simulator.press_key(&rod_key, None);
                            thread::sleep(Duration::from_millis(2500));
                            if let Ok(mut s) = state.lock() {
                                s.status = BotStatus::WaitingBite;
                            }
                            last_bite_time = Instant::now();
                        } else {
                            // Chế độ lắng nghe: không tự ý cất cần, tiếp tục chờ lượt câu tiếp theo
                            if let Ok(mut s) = state.lock() {
                                s.status = BotStatus::WaitingBite;
                            }
                            Self::add_log(&state, "🎧 Đã giải xong lượt! Bạn hãy tự quăng cần lượt tiếp theo, Tool đang tiếp tục lắng nghe.");
                            last_bite_time = Instant::now();
                        }
                        last_heartbeat = Instant::now();
                    } else if auto_recast && last_bite_time.elapsed() > Duration::from_secs(50) {
                        Self::add_log(&state, "⏳ Quá 50s chưa có cá, tự động quăng lại cần câu...");
                        simulator.press_key(&rod_key, None);
                        thread::sleep(Duration::from_millis(2500));
                        last_bite_time = Instant::now();
                    }
                }
                thread::sleep(Duration::from_millis(15));
            } else {
                need_initial_cast = true;
                thread::sleep(Duration::from_millis(80));
            }
        }
    }
}
