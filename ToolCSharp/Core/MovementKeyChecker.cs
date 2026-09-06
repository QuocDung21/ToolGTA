using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Threading;
using System.Threading.Tasks;

namespace ToolCSharp.Core
{
    public class MovementKeyChecker
    {
        [DllImport("user32.dll")]
        private static extern short GetAsyncKeyState(int vKey);

        private readonly InputSimulator _simulator;
        private readonly Action<string, string> _logAction;
        private bool _isMonitoring = false;
        private Thread? _monitorThread;

        public bool IsMonitoring => _isMonitoring;
        public event Action<bool>? MonitoringStateChanged;

        private class KeyStateInfo
        {
            public string Name { get; set; } = "";
            public int VKey { get; set; }
            public ushort ScanCode { get; set; }
            public bool Extended { get; set; }
            public bool WasDown { get; set; }
            public Stopwatch Timer { get; set; } = new();
        }

        private readonly List<KeyStateInfo> _watchedKeys = new()
        {
            new KeyStateInfo { Name = "W", VKey = 0x57, ScanCode = 0x11, Extended = false },
            new KeyStateInfo { Name = "A", VKey = 0x41, ScanCode = 0x1E, Extended = false },
            new KeyStateInfo { Name = "S", VKey = 0x53, ScanCode = 0x1F, Extended = false },
            new KeyStateInfo { Name = "D", VKey = 0x44, ScanCode = 0x20, Extended = false },
            new KeyStateInfo { Name = "UP", VKey = 0x26, ScanCode = 0x48, Extended = true },
            new KeyStateInfo { Name = "DOWN", VKey = 0x28, ScanCode = 0x50, Extended = true },
            new KeyStateInfo { Name = "LEFT", VKey = 0x25, ScanCode = 0x4B, Extended = true },
            new KeyStateInfo { Name = "RIGHT", VKey = 0x27, ScanCode = 0x4D, Extended = true },
            new KeyStateInfo { Name = "SPACE", VKey = 0x20, ScanCode = 0x39, Extended = false },
            new KeyStateInfo { Name = "SHIFT", VKey = 0x10, ScanCode = 0x2A, Extended = false },
            new KeyStateInfo { Name = "E", VKey = 0x45, ScanCode = 0x12, Extended = false },
        };

        public MovementKeyChecker(InputSimulator simulator, Action<string, string> logAction)
        {
            _simulator = simulator;
            _logAction = logAction;
        }

        public void ToggleMonitoring()
        {
            _isMonitoring = !_isMonitoring;
            if (_isMonitoring)
            {
                _logAction("🟢 [KEY_CHECK] Bắt đầu theo dõi nút di chuyển trong game (W, A, S, D, Mũi tên). Nhấn F4 để dừng.", "success");
                StartMonitoringThread();
            }
            else
            {
                _logAction("🔴 [KEY_CHECK] Đã dừng theo dõi nút di chuyển.", "warning");
            }
            MonitoringStateChanged?.Invoke(_isMonitoring);
        }

        private void StartMonitoringThread()
        {
            if (_monitorThread != null && _monitorThread.IsAlive) return;

            _monitorThread = new Thread(() =>
            {
                while (_isMonitoring)
                {
                    foreach (var k in _watchedKeys)
                    {
                        bool isDown = (GetAsyncKeyState(k.VKey) & 0x8000) != 0;

                        if (isDown && !k.WasDown)
                        {
                            // Key Pressed Down
                            k.Timer.Restart();
                            string extStr = k.Extended ? ", Extended" : "";
                            _logAction($"[KEY_CHECK] ⬇️ Bấm phím '{k.Name}' (VK: 0x{k.VKey:X2}, DirectX Scancode: 0x{k.ScanCode:X2}{extStr})", "info");
                        }
                        else if (!isDown && k.WasDown)
                        {
                            // Key Released Up
                            k.Timer.Stop();
                            long duration = k.Timer.ElapsedMilliseconds;
                            _logAction($"[KEY_CHECK] ⬆️ Nhả phím '{k.Name}' | Giữ phím: {duration}ms", "highlight");
                        }

                        k.WasDown = isDown;
                    }

                    Thread.Sleep(10);
                }
            })
            {
                IsBackground = true
            };
            _monitorThread.Start();
        }

        public void TestSimulateMovement()
        {
            Task.Run(() =>
            {
                _logAction("🎮 [TEST_MOVE] Bắt đầu kiểm tra gửi phím di chuyển vào game...", "info");
                string[] testKeys = { "W", "A", "S", "D", "UP", "DOWN", "LEFT", "RIGHT" };

                foreach (var key in testKeys)
                {
                    var mapping = _simulator.GetKeyMapping(key);
                    ushort sc = mapping?.ScanCode ?? 0;
                    bool ext = mapping?.Extended ?? false;

                    _logAction($"[TEST_MOVE] ➡️ Gửi thử phím '{key}' (Scancode: 0x{sc:X2}, Ext: {ext}, Giữ: 120ms)...", "info");
                    try
                    {
                        _simulator.PressKey(key, 120);
                        _logAction($"[TEST_MOVE] ✔️ Phím '{key}' đã gửi thành công!", "success");
                    }
                    catch (Exception ex)
                    {
                        _logAction($"[TEST_MOVE] ❌ Lỗi gửi phím '{key}': {ex.Message}", "error");
                    }
                    Thread.Sleep(200);
                }

                _logAction("🎮 [TEST_MOVE] Hoàn thành bài kiểm tra gửi phím di chuyển!", "success");
            });
        }
    }
}
