using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using OpenCvSharp;
using ToolCSharp.Models;

namespace ToolCSharp.Core
{
    public class AutoFishingBot : IDisposable
    {
        [DllImport("user32.dll")]
        private static extern short GetAsyncKeyState(int vKey);

        private const int VK_F1 = 0x70;
        private const int VK_F2 = 0x71;
        private const int VK_F3 = 0x72;
        private const int VK_F4 = 0x73;

        public AppSettings Settings { get; private set; }
        public string ConfigPath { get; set; }

        public ScreenCapture ScreenCapture { get; }
        public ArrowDetector Detector { get; }
        public InputSimulator Simulator { get; }
        public AntiAfk AntiAfk { get; }
        public MovementKeyChecker KeyChecker { get; }

        public bool IsRunning { get; private set; }
        public bool IsPaused { get; private set; }
        private bool _isAlive = true;

        private Thread? _workerThread;
        private Thread? _hotkeyThread;

        public int FishCount { get; private set; }
        public int SolvedCount { get; private set; }
        public DateTime? StartTime { get; private set; }

        private bool _needInitialCast = false;
        private DateTime _lastBiteWaitTime = DateTime.MinValue;
        private DateTime _lastHeartbeatTime = DateTime.MinValue;

        public event Action<string, string>? LogEmitted;
        public event Action<string, string>? StatusChanged;
        public event Action<int, int>? StatsUpdated;
        public event Action<List<string>>? SequenceDetected;

        private static readonly HttpClient HttpClient = new();

        public AutoFishingBot(string configPath = "config/settings.json")
        {
            ConfigPath = configPath;
            Settings = LoadSettings();

            ScreenCapture = new ScreenCapture();
            Detector = new ArrowDetector("assets/templates", Settings.Detection);
            Detector.OnDebugLog = msg => Log(msg, "info");
            Simulator = new InputSimulator
            {
                MinPressMs = Settings.Delays.MinKeyPressMs,
                MaxPressMs = Settings.Delays.MaxKeyPressMs,
                MinIntervalMs = Settings.Delays.MinIntervalMs,
                MaxIntervalMs = Settings.Delays.MaxIntervalMs
            };
            AntiAfk = new AntiAfk(Simulator)
            {
                Enabled = Settings.AntiAfk.Enabled,
                MinActions = Settings.AntiAfk.MinActions,
                MaxActions = Settings.AntiAfk.MaxActions
            };
            KeyChecker = new MovementKeyChecker(Simulator, Log);
        }

        public AppSettings LoadSettings()
        {
            if (File.Exists(ConfigPath))
            {
                try
                {
                    string json = File.ReadAllText(ConfigPath);
                    return JsonSerializer.Deserialize<AppSettings>(json) ?? new AppSettings();
                }
                catch { }
            }
            return new AppSettings();
        }

        public void ReloadConfig()
        {
            Settings = LoadSettings();
            Detector.Settings = Settings.Detection;
            Detector.LoadTemplates();

            Simulator.MinPressMs = Settings.Delays.MinKeyPressMs;
            Simulator.MaxPressMs = Settings.Delays.MaxKeyPressMs;
            Simulator.MinIntervalMs = Settings.Delays.MinIntervalMs;
            Simulator.MaxIntervalMs = Settings.Delays.MaxIntervalMs;

            AntiAfk.Enabled = Settings.AntiAfk.Enabled;
            AntiAfk.MinActions = Settings.AntiAfk.MinActions;
            AntiAfk.MaxActions = Settings.AntiAfk.MaxActions;

            Log("Configuration reloaded successfully.", "success");
        }

        public void Start()
        {
            _isAlive = true;

            // Start Hotkey monitor thread
            _hotkeyThread = new Thread(HotkeyLoop) { IsBackground = true };
            _hotkeyThread.Start();

            // Start main worker loop
            _workerThread = new Thread(WorkerLoop) { IsBackground = true };
            _workerThread.Start();

            Log("Auto Fishing Bot initialized. Ready for commands.", "info");
        }

        public static int ParseVirtualKey(string keyName, int defaultVk)
        {
            if (string.IsNullOrWhiteSpace(keyName)) return defaultVk;
            string k = keyName.Trim().ToUpperInvariant();
            if (k.StartsWith("F") && int.TryParse(k[1..], out int fNum) && fNum >= 1 && fNum <= 24)
            {
                return 0x6F + fNum; // F1 = 0x70, F2 = 0x71, ..., F12 = 0x7B
            }
            return k switch
            {
                "INSERT" or "INS" => 0x2D,
                "DELETE" or "DEL" => 0x2E,
                "HOME" => 0x24,
                "END" => 0x23,
                "PAGEUP" or "PGUP" => 0x21,
                "PAGEDOWN" or "PGDN" => 0x22,
                "PAUSE" => 0x13,
                "SCROLLLOCK" or "SCROLL" => 0x91,
                "NUMPAD0" => 0x60,
                "NUMPAD1" => 0x61,
                "NUMPAD2" => 0x62,
                "NUMPAD3" => 0x63,
                "NUMPAD4" => 0x64,
                "NUMPAD5" => 0x65,
                "NUMPAD6" => 0x66,
                "NUMPAD7" => 0x67,
                "NUMPAD8" => 0x68,
                "NUMPAD9" => 0x69,
                _ => defaultVk
            };
        }

        private void HotkeyLoop()
        {
            bool startWasDown = false;
            bool pauseWasDown = false;
            bool panicWasDown = false;
            bool f4WasDown = false;

            while (_isAlive)
            {
                int vkStart = ParseVirtualKey(Settings.General.HotkeyStart, 0x70);
                int vkPause = ParseVirtualKey(Settings.General.HotkeyPause, 0x71);
                int vkPanic = ParseVirtualKey(Settings.General.HotkeyPanic, 0x72);

                bool startIsDown = (GetAsyncKeyState(vkStart) & 0x8000) != 0;
                bool pauseIsDown = (GetAsyncKeyState(vkPause) & 0x8000) != 0;
                bool panicIsDown = (GetAsyncKeyState(vkPanic) & 0x8000) != 0;
                bool f4IsDown = (GetAsyncKeyState(VK_F4) & 0x8000) != 0;

                if (startIsDown && !startWasDown)
                {
                    ToggleRunning();
                }
                if (pauseIsDown && !pauseWasDown)
                {
                    TogglePause();
                }
                if (panicIsDown && !panicWasDown)
                {
                    PanicExit();
                }
                if (f4IsDown && !f4WasDown)
                {
                    KeyChecker.ToggleMonitoring();
                }

                startWasDown = startIsDown;
                pauseWasDown = pauseIsDown;
                panicWasDown = panicIsDown;
                f4WasDown = f4IsDown;

                Thread.Sleep(20);
            }
        }

        public void ToggleRunning()
        {
            IsRunning = !IsRunning;
            if (IsRunning)
            {
                StartTime ??= DateTime.Now;
                Log("🟢 Tool ĐÃ BẬT: Đang lắng nghe màn hình. Bạn hãy tự quăng cần trong game, Tool sẽ tự động giải 5 mũi tên ngay khi minigame xuất hiện!", "success");
                StatusChanged?.Invoke("ĐANG LẮNG NGHE", "#a6e3a1");
                _needInitialCast = Settings.General.AutoRecast;
                _lastBiteWaitTime = DateTime.Now;
                _lastHeartbeatTime = DateTime.Now;
            }
            else
            {
                Log("🔴 Tool ĐÃ DỪNG.", "warning");
                StatusChanged?.Invoke("STOPPED", "#f38ba8");
                _needInitialCast = false;
            }
        }

        public void TogglePause()
        {
            if (!IsRunning) return;
            IsPaused = !IsPaused;
            if (IsPaused)
            {
                Log("Bot paused.", "warning");
                StatusChanged?.Invoke("PAUSED", "#fab387");
            }
            else
            {
                Log("Bot resumed.", "success");
                StatusChanged?.Invoke("ĐANG LẮNG NGHE", "#a6e3a1");
            }
        }

        public void PanicExit()
        {
            Log("EMERGENCY PANIC KEY (F3) TRIGGERED! Stopping bot...", "error");
            IsRunning = false;
            _isAlive = false;
            StatusChanged?.Invoke("PANIC STOP", "#f38ba8");
            PlayAlertSound();
            _ = SendDiscordAlertAsync("🚨 **[PANIC STOP]** Phím khẩn cấp F3 đã được kích hoạt! Bot đã dừng ngay lập tức.");
        }

        private void WorkerLoop()
        {
            var rand = new Random();

            while (_isAlive)
            {
                if (IsRunning && !IsPaused)
                {
                    try
                    {
                        if (Settings.General.AutoRecast && _needInitialCast)
                        {
                            _needInitialCast = false;
                            string rodKey = Settings.General.RodSlotKey;
                            Log($"🎣 Bắt đầu câu: Quăng cần câu (phím '{rodKey}')...", "info");
                            StatusChanged?.Invoke("CASTING", "#b4befe");
                            Simulator.PressKey(rodKey);
                            Thread.Sleep(2500);
                            Log("⏳ Đang chờ cá cắn câu (canh minigame QTE)...", "info");
                            StatusChanged?.Invoke("WAITING BITE", "#a6e3a1");
                            _lastBiteWaitTime = DateTime.Now;
                        }

                        using Mat frame = ScreenCapture.CaptureFull();

                        if ((DateTime.Now - _lastHeartbeatTime).TotalSeconds >= 15)
                        {
                            _lastHeartbeatTime = DateTime.Now;
                            Log($"🎧 [LẮNG NGHE] Đang canh màn hình ({frame.Width}x{frame.Height}px)... Chờ minigame xuất hiện.", "info");
                        }

                        var sequence = Detector.DetectSequence(frame);

                        if (sequence.Count == 5)
                        {
                            var sw = Stopwatch.StartNew();
                            Log($"🎯 Phát hiện minigame câu cá! Mũi tên: [{string.Join(", ", sequence)}]", "highlight");
                            SequenceDetected?.Invoke(sequence);
                            StatusChanged?.Invoke("GIẢI QTE", "#f9e2af");

                            // Human reaction delay
                            Thread.Sleep(rand.Next(120, 200));

                            Simulator.ExecuteSequence(sequence);
                            sw.Stop();
                            Log($"⚡ Giải QTE thành công trong {sw.ElapsedMilliseconds}ms!", "success");

                            SolvedCount++;
                            FishCount++;
                            StatsUpdated?.Invoke(FishCount, SolvedCount);

                            // Chờ game đóng minigame
                            Thread.Sleep(2000);

                            if (Settings.General.AutoRecast)
                            {
                                // Kéo cá lên
                                StatusChanged?.Invoke("REELING IN", "#89dceb");
                                Thread.Sleep((int)(Settings.Delays.ReelInWaitSec * 1000));

                                // Anti-AFK
                                AntiAfk.TriggerIfNeeded();

                                // Quăng lại cần
                                Thread.Sleep((int)(Settings.Delays.RecastWaitSec * 1000));
                                string rodKey = Settings.General.RodSlotKey;
                                Log($"🎣 Quăng lại cần câu với phím '{rodKey}'...", "info");
                                StatusChanged?.Invoke("CASTING", "#b4befe");
                                Simulator.PressKey(rodKey);
                                Thread.Sleep(2500);
                                _lastBiteWaitTime = DateTime.Now;
                                StatusChanged?.Invoke("WAITING BITE", "#a6e3a1");
                            }
                            else
                            {
                                StatusChanged?.Invoke("ĐANG LẮNG NGHE", "#a6e3a1");
                                Log("🎧 Đã giải xong lượt! Bạn có thể tự quăng cần lượt tiếp theo, Tool đang tiếp tục lắng nghe.", "info");
                            }
                            _lastHeartbeatTime = DateTime.Now;
                        }
                        else if (Settings.General.AutoRecast && (DateTime.Now - _lastBiteWaitTime).TotalSeconds > 50 && _lastBiteWaitTime > DateTime.MinValue)
                        {
                            Log("⏳ Quá 50s chưa có cá cắn, tự động quăng lại cần câu...", "warning");
                            string rodKey = Settings.General.RodSlotKey;
                            StatusChanged?.Invoke("RECASTING", "#b4befe");
                            Simulator.PressKey(rodKey);
                            Thread.Sleep(2500);
                            _lastBiteWaitTime = DateTime.Now;
                            StatusChanged?.Invoke("WAITING BITE", "#a6e3a1");
                        }
                    }
                    catch (Exception ex)
                    {
                        Log($"Loop error: {ex.Message}", "error");
                        Thread.Sleep(500);
                    }
                }
                Thread.Sleep(30);
            }
        }

        public void PlayAlertSound()
        {
            if (Settings.Alerts.SoundAlarmOnFail)
            {
                Task.Run(() =>
                {
                    try { Console.Beep(1000, 400); Console.Beep(800, 400); } catch { }
                });
            }
        }

        public async Task SendDiscordAlertAsync(string message)
        {
            string url = Settings.Alerts.DiscordWebhookUrl;
            if (string.IsNullOrWhiteSpace(url)) return;

            try
            {
                var payload = new { content = message };
                string json = JsonSerializer.Serialize(payload);
                using var content = new StringContent(json, Encoding.UTF8, "application/json");
                await HttpClient.PostAsync(url, content);
            }
            catch (Exception ex)
            {
                Log($"Webhook send failed: {ex.Message}", "error");
            }
        }

        private static readonly object LogFileLock = new();
        public string LogDirectory { get; } = "logs";

        public string GetCurrentLogFile()
        {
            Directory.CreateDirectory(LogDirectory);
            return Path.Combine(LogDirectory, $"debug_{DateTime.Now:yyyy-MM-dd}.log");
        }

        public void Log(string message, string level)
        {
            LogEmitted?.Invoke(message, level);

            try
            {
                string logFile = GetCurrentLogFile();
                string timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff");
                string line = $"[{timestamp}] [{level.ToUpper()}] {message}{Environment.NewLine}";

                lock (LogFileLock)
                {
                    File.AppendAllText(logFile, line);
                }
            }
            catch { }
        }

        public void Dispose()
        {
            _isAlive = false;
            ScreenCapture.Dispose();
            Detector.Dispose();
        }
    }
}
