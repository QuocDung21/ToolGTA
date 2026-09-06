using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Media;
using System.Windows.Threading;
using Microsoft.Win32;
using ToolCSharp.Core;
using ToolCSharp.UI;

namespace ToolCSharp
{
    public partial class MainWindow : Window
    {
        private readonly AutoFishingBot _bot;
        private readonly OverlayWindow _overlay;
        private readonly DispatcherTimer _uptimeTimer;

        public MainWindow()
        {
            InitializeComponent();

            _bot = new AutoFishingBot("config/settings.json");
            _overlay = new OverlayWindow
            {
                OnClosedCallback = () => ChkOverlay.IsChecked = false
            };

            // Wire Bot Callbacks
            _bot.LogEmitted += OnBotLog;
            _bot.StatusChanged += OnBotStatusChanged;
            _bot.StatsUpdated += OnBotStatsUpdated;
            _bot.SequenceDetected += OnBotSequenceDetected;
            _bot.KeyChecker.MonitoringStateChanged += isMonitoring =>
            {
                Dispatcher.Invoke(() =>
                {
                    if (isMonitoring)
                    {
                        BtnKeyCheck.Content = "⏹  DỪNG THEO DÕI NÚT (F4)";
                        BtnKeyCheck.Background = (Brush)new BrushConverter().ConvertFromString("#D97706")!;
                    }
                    else
                    {
                        BtnKeyCheck.Content = "🎮  BẬT THEO DÕI NÚT DI CHUYỂN (F4)";
                        BtnKeyCheck.Background = (Brush)new BrushConverter().ConvertFromString("#45475A")!;
                    }
                });
            };

            // Uptime Timer
            _uptimeTimer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(1) };
            _uptimeTimer.Tick += UptimeTimer_Tick;
            _uptimeTimer.Start();

            // Load UI Data
            LoadConfigToUi();
            RefreshTemplateBadges();

            // Start Bot background service
            _bot.Start();

            if (!IsAdministrator())
            {
                _bot.Log("⚠️ CẢNH BÁO: Tool chưa được chạy với quyền Administrator!", "warning");
                _bot.Log("👉 Nếu FiveM chạy quyền Admin, Windows sẽ chặn phím tự động. Khuyên dùng: Chuột phải -> 'Run as administrator'.", "warning");
            }
            else
            {
                _bot.Log("🛡️ Quyền Administrator: ĐÃ BẬT (Full quyền gửi phím phần cứng DirectX)", "success");
            }
        }

        private static bool IsAdministrator()
        {
            using var identity = System.Security.Principal.WindowsIdentity.GetCurrent();
            var principal = new System.Security.Principal.WindowsPrincipal(identity);
            return principal.IsInRole(System.Security.Principal.WindowsBuiltInRole.Administrator);
        }

        private void OnBotLog(string message, string level)
        {
            Dispatcher.Invoke(() =>
            {
                string time = DateTime.Now.ToString("HH:mm:ss");
                TxtLogs.AppendText($"[{time}] [{level.ToUpper()}] {message}\n");
                TxtLogs.ScrollToEnd();
            });
        }

        private void OnBotStatusChanged(string status, string hexColor)
        {
            Dispatcher.Invoke(() =>
            {
                TxtMainStatus.Text = $"● {status.ToUpper()}";
                try
                {
                    TxtMainStatus.Foreground = (Brush)new BrushConverter().ConvertFromString(hexColor)!;
                }
                catch { }

                string hk = _bot.Settings.General.HotkeyStart.ToUpperInvariant();
                if (status.Equals("RUNNING", StringComparison.OrdinalIgnoreCase))
                {
                    BtnToggleStart.Content = $"⏹  DỪNG BOT ({hk})";
                    BtnToggleStart.Background = (Brush)new BrushConverter().ConvertFromString("#DC2626")!;
                }
                else
                {
                    BtnToggleStart.Content = $"▶  BẮT ĐẦU ({hk})";
                    BtnToggleStart.Background = (Brush)new BrushConverter().ConvertFromString("#2E7D32")!;
                }

                _overlay.UpdateInfo(status, hexColor, _bot.FishCount, _bot.SolvedCount);
            });
        }

        private void OnBotStatsUpdated(int fish, int solved)
        {
            Dispatcher.Invoke(() =>
            {
                TxtFishCount.Text = fish.ToString();
                TxtSolvedCount.Text = solved.ToString();
                _overlay.UpdateInfo(TxtMainStatus.Text.Replace("● ", ""), "#A6E3A1", fish, solved);
            });
        }

        private void OnBotSequenceDetected(List<string> sequence)
        {
            Dispatcher.Invoke(() =>
            {
                var formatted = sequence.ConvertAll(s => s switch
                {
                    "UP" => "[⬆ LÊN]",
                    "DOWN" => "[⬇ XUỐNG]",
                    "LEFT" => "[⬅ TRÁI]",
                    "RIGHT" => "[➡ PHẢI]",
                    _ => $"[{s}]"
                });
                TxtSequenceDisplay.Text = string.Join("   ", formatted);
                TxtSequenceDisplay.Foreground = (Brush)new BrushConverter().ConvertFromString("#A6E3A1")!;
                _overlay.UpdateInfo("SOLVING", "#F9E2AF", _bot.FishCount, _bot.SolvedCount, sequence);
            });
        }

        private void UptimeTimer_Tick(object? sender, EventArgs e)
        {
            if (_bot.IsRunning && _bot.StartTime.HasValue)
            {
                TimeSpan elapsed = DateTime.Now - _bot.StartTime.Value;
                TxtUptime.Text = elapsed.ToString(@"hh\:mm\:ss");
            }
        }

        private void RefreshTemplateBadges()
        {
            var tpls = _bot.Detector.Templates;
            UpdateBadge(TxtTplUp, tpls.ContainsKey("UP"));
            UpdateBadge(TxtTplDown, tpls.ContainsKey("DOWN"));
            UpdateBadge(TxtTplLeft, tpls.ContainsKey("LEFT"));
            UpdateBadge(TxtTplRight, tpls.ContainsKey("RIGHT"));
        }

        private void UpdateBadge(System.Windows.Controls.TextBlock tb, bool hasTemplate)
        {
            if (hasTemplate)
            {
                tb.Text = "[✔ ĐÃ CÓ MẪU]";
                tb.Foreground = (Brush)new BrushConverter().ConvertFromString("#A6E3A1")!;
            }
            else
            {
                tb.Text = "[✖ CHƯA CÓ]";
                tb.Foreground = (Brush)new BrushConverter().ConvertFromString("#F38BA8")!;
            }
        }

        // ---------------- Event Handlers ----------------
        private void BtnToggleStart_Click(object sender, RoutedEventArgs e)
        {
            _bot.ToggleRunning();
        }

        private void BtnTogglePause_Click(object sender, RoutedEventArgs e)
        {
            _bot.TogglePause();
        }

        private void BtnPanic_Click(object sender, RoutedEventArgs e)
        {
            _bot.PanicExit();
        }

        private void BtnKeyCheck_Click(object sender, RoutedEventArgs e)
        {
            _bot.KeyChecker.ToggleMonitoring();
        }

        private void BtnTestMove_Click(object sender, RoutedEventArgs e)
        {
            _bot.KeyChecker.TestSimulateMovement();
        }

        private void ChkOverlay_Click(object sender, RoutedEventArgs e)
        {
            if (ChkOverlay.IsChecked == true)
            {
                _overlay.Show();
            }
            else
            {
                _overlay.Hide();
            }
        }

        private void BtnClearLog_Click(object sender, RoutedEventArgs e)
        {
            TxtLogs.Clear();
        }

        private void BtnOpenLogFile_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                string path = Path.GetFullPath(_bot.GetCurrentLogFile());
                if (!File.Exists(path))
                {
                    File.WriteAllText(path, $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss}] Log file initialized.\n");
                }
                System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
                {
                    FileName = path,
                    UseShellExecute = true
                });
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Không thể mở file log: {ex.Message}", "Lỗi", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void BtnOpenLogDir_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                string dir = Path.GetFullPath(_bot.LogDirectory);
                Directory.CreateDirectory(dir);
                System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
                {
                    FileName = dir,
                    UseShellExecute = true
                });
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Không thể mở thư mục log: {ex.Message}", "Lỗi", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void SliderThreshold_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            if (TxtThresholdVal != null)
            {
                TxtThresholdVal.Text = $"Ngưỡng hiện tại: {e.NewValue:F2} (Khuyến nghị: 0.65 - 0.75)";
                if (_bot != null)
                {
                    _bot.Detector.Settings.ArrowMatchThreshold = e.NewValue;
                }
            }
        }

        private void BtnSaveConfig_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                var cfg = _bot.Settings;
                cfg.General.RodSlotKey = TbRodKey.Text.Trim();
                cfg.General.AutoRecast = ChkAutoRecast.IsChecked ?? false;
                cfg.General.HotkeyStart = TbHkStart.Text.Trim();
                cfg.General.HotkeyPause = TbHkPause.Text.Trim();
                cfg.General.HotkeyPanic = TbHkPanic.Text.Trim();

                cfg.Delays.MinKeyPressMs = int.Parse(TbMinPress.Text.Trim());
                cfg.Delays.MaxKeyPressMs = int.Parse(TbMaxPress.Text.Trim());
                cfg.Delays.MinIntervalMs = int.Parse(TbMinInterval.Text.Trim());
                cfg.Delays.MaxIntervalMs = int.Parse(TbMaxInterval.Text.Trim());
                cfg.Delays.ReelInWaitSec = double.Parse(TbReelWait.Text.Trim());
                cfg.Delays.RecastWaitSec = double.Parse(TbRecastWait.Text.Trim());

                cfg.AntiAfk.Enabled = ChkAntiAfk.IsChecked ?? true;
                cfg.Alerts.DiscordWebhookUrl = TbWebhookUrl.Text.Trim();
                cfg.Alerts.SoundAlarmOnFail = ChkSoundAlarm.IsChecked ?? true;

                Directory.CreateDirectory(Path.GetDirectoryName(_bot.ConfigPath) ?? "config");
                string json = JsonSerializer.Serialize(cfg, new JsonSerializerOptions { WriteIndented = true });
                File.WriteAllText(_bot.ConfigPath, json);

                _bot.ReloadConfig();
                LoadConfigToUi();
                MessageBox.Show("Đã lưu cấu hình thành công!", "Thông Báo", MessageBoxButton.OK, MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Lỗi lưu cấu hình: {ex.Message}", "Lỗi", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void BtnReloadConfig_Click(object sender, RoutedEventArgs e)
        {
            _bot.ReloadConfig();
            LoadConfigToUi();
        }

        private void LoadConfigToUi()
        {
            var cfg = _bot.Settings;
            TbRodKey.Text = cfg.General.RodSlotKey;
            ChkAutoRecast.IsChecked = cfg.General.AutoRecast;
            TbHkStart.Text = cfg.General.HotkeyStart;
            TbHkPause.Text = cfg.General.HotkeyPause;
            TbHkPanic.Text = cfg.General.HotkeyPanic;

            TbMinPress.Text = cfg.Delays.MinKeyPressMs.ToString();
            TbMaxPress.Text = cfg.Delays.MaxKeyPressMs.ToString();
            TbMinInterval.Text = cfg.Delays.MinIntervalMs.ToString();
            TbMaxInterval.Text = cfg.Delays.MaxIntervalMs.ToString();
            TbReelWait.Text = cfg.Delays.ReelInWaitSec.ToString("F1");
            TbRecastWait.Text = cfg.Delays.RecastWaitSec.ToString("F1");

            ChkAntiAfk.IsChecked = cfg.AntiAfk.Enabled;
            TbWebhookUrl.Text = cfg.Alerts.DiscordWebhookUrl;
            ChkSoundAlarm.IsChecked = cfg.Alerts.SoundAlarmOnFail;
            SliderThreshold.Value = cfg.Detection.ArrowMatchThreshold;

            BtnToggleStart.Content = $"▶  BẮT ĐẦU ({cfg.General.HotkeyStart.ToUpperInvariant()})";
            BtnTogglePause.Content = $"⏸  TẠM DỪNG ({cfg.General.HotkeyPause.ToUpperInvariant()})";
            BtnPanic.Content = $"🚨  KHẨN CẤP ({cfg.General.HotkeyPanic.ToUpperInvariant()})";
        }

        private void BtnExtractTemplates_Click(object sender, RoutedEventArgs e)
        {
            OpenFileDialog dlg = new OpenFileDialog
            {
                Title = "Chọn ảnh mẫu minigame câu cá (ví dụ: sample_boat.png)",
                Filter = "Image Files (*.png;*.jpg;*.jpeg)|*.png;*.jpg;*.jpeg"
            };

            if (dlg.ShowDialog() == true)
            {
                Task.Run(() =>
                {
                    try
                    {
                        string[] sampleLabels = { "DOWN", "LEFT", "DOWN", "UP", "RIGHT" };
                        _bot.Detector.ExtractTemplatesFromSample(dlg.FileName, sampleLabels);
                        Dispatcher.Invoke(() =>
                        {
                            RefreshTemplateBadges();
                            MessageBox.Show("Trích xuất 4 mẫu template mũi tên thành công vào assets/templates/!", "Thành Công", MessageBoxButton.OK, MessageBoxImage.Information);
                        });
                    }
                    catch (Exception ex)
                    {
                        Dispatcher.Invoke(() =>
                        {
                            MessageBox.Show($"Lỗi khi trích xuất: {ex.Message}", "Lỗi", MessageBoxButton.OK, MessageBoxImage.Error);
                        });
                    }
                });
            }
        }

        private void BtnTestDetector_Click(object sender, RoutedEventArgs e)
        {
            Task.Run(() =>
            {
                string samplesDir = "assets/test_samples";
                if (!Directory.Exists(samplesDir) || Directory.GetFiles(samplesDir).Length == 0)
                {
                    _bot.Log("Không có ảnh trong assets/test_samples/. Hãy copy ảnh vào để test.", "warning");
                    return;
                }

                foreach (var file in Directory.GetFiles(samplesDir, "*.*"))
                {
                    if (file.EndsWith(".png", StringComparison.OrdinalIgnoreCase) ||
                        file.EndsWith(".jpg", StringComparison.OrdinalIgnoreCase))
                    {
                        using var img = OpenCvSharp.Cv2.ImRead(file);
                        if (!img.Empty())
                        {
                            var seq = _bot.Detector.DetectSequence(img);
                            _bot.Log($"File {Path.GetFileName(file)} -> Nhận diện: [{string.Join(", ", seq)}]", seq.Count > 0 ? "success" : "warning");
                        }
                    }
                }
            });
        }

        private async void BtnTestWebhook_Click(object sender, RoutedEventArgs e)
        {
            string url = TbWebhookUrl.Text.Trim();
            if (string.IsNullOrWhiteSpace(url))
            {
                MessageBox.Show("Vui lòng nhập URL Discord Webhook!", "Cảnh Báo", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            try
            {
                await _bot.SendDiscordAlertAsync("🎣 **[FiveM Tool Auto Fish C#]** Test Discord Webhook thành công!");
                MessageBox.Show("Đã gửi test Discord Webhook thành công!", "Thông Báo", MessageBoxButton.OK, MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Lỗi gửi Webhook: {ex.Message}", "Lỗi", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        protected override void OnClosed(EventArgs e)
        {
            _overlay.Close();
            _bot.Dispose();
            base.OnClosed(e);
            Environment.Exit(0);
        }
    }
}