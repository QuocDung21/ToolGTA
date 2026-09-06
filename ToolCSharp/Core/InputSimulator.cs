using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Threading;

namespace ToolCSharp.Core
{
    public class InputSimulator
    {
        [DllImport("user32.dll", SetLastError = true)]
        private static extern uint SendInput(uint nInputs, INPUT[] pInputs, int cbSize);

        private const int INPUT_KEYBOARD = 1;
        private const uint KEYEVENTF_EXTENDEDKEY = 0x0001;
        private const uint KEYEVENTF_KEYUP = 0x0002;
        private const uint KEYEVENTF_SCANCODE = 0x0008;

        [StructLayout(LayoutKind.Sequential)]
        private struct INPUT
        {
            public uint type;
            public InputUnion u;
        }

        [StructLayout(LayoutKind.Explicit)]
        private struct InputUnion
        {
            [FieldOffset(0)]
            public KEYBDINPUT ki;
            [FieldOffset(0)]
            public MOUSEINPUT mi;
            [FieldOffset(0)]
            public HARDWAREINPUT hi;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct KEYBDINPUT
        {
            public ushort wVk;
            public ushort wScan;
            public uint dwFlags;
            public uint time;
            public IntPtr dwExtraInfo;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct MOUSEINPUT
        {
            public int dx;
            public int dy;
            public uint mouseData;
            public uint dwFlags;
            public uint time;
            public IntPtr dwExtraInfo;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct HARDWAREINPUT
        {
            public uint uMsg;
            public ushort wParamL;
            public ushort wParamH;
        }

        [DllImport("user32.dll")]
        private static extern short VkKeyScan(char ch);

        [DllImport("user32.dll")]
        private static extern uint MapVirtualKey(uint uCode, uint uMapType);

        private static readonly Dictionary<string, (ushort ScanCode, bool Extended)> KeyMap = new(StringComparer.OrdinalIgnoreCase)
        {
            { "UP", (0x48, true) },
            { "DOWN", (0x50, true) },
            { "LEFT", (0x4B, true) },
            { "RIGHT", (0x4D, true) },
            { "W", (0x11, false) },
            { "A", (0x1E, false) },
            { "S", (0x1F, false) },
            { "D", (0x20, false) },
            { "SPACE", (0x39, false) },
            { "SHIFT", (0x2A, false) },
            { "CTRL", (0x1D, false) },
            { "E", (0x12, false) },
            { "0", (0x0B, false) },
            { "1", (0x02, false) },
            { "2", (0x03, false) },
            { "3", (0x04, false) },
            { "4", (0x05, false) },
            { "5", (0x06, false) },
            { "6", (0x07, false) },
            { "7", (0x08, false) },
            { "8", (0x09, false) },
            { "9", (0x0A, false) },
            { "Q", (0x10, false) },
            { "R", (0x13, false) },
            { "T", (0x14, false) },
            { "Y", (0x15, false) },
            { "U", (0x16, false) },
            { "I", (0x17, false) },
            { "O", (0x18, false) },
            { "P", (0x19, false) },
            { "F", (0x21, false) },
            { "G", (0x22, false) },
            { "H", (0x23, false) },
            { "J", (0x24, false) },
            { "K", (0x25, false) },
            { "L", (0x26, false) },
            { "Z", (0x2C, false) },
            { "X", (0x2D, false) },
            { "C", (0x2E, false) },
            { "V", (0x2F, false) },
            { "B", (0x30, false) },
            { "N", (0x31, false) },
            { "M", (0x32, false) }
        };

        public (ushort ScanCode, bool Extended)? GetKeyMapping(string keyName)
        {
            if (string.IsNullOrWhiteSpace(keyName)) return null;

            if (KeyMap.TryGetValue(keyName, out var mapping))
                return mapping;

            if (keyName.Length == 1)
            {
                short vk = VkKeyScan(keyName[0]);
                if (vk != -1)
                {
                    ushort sc = (ushort)MapVirtualKey((uint)(vk & 0xFF), 0);
                    if (sc != 0)
                        return (sc, false);
                }
            }

            return null;
        }

        public int MinPressMs { get; set; } = 65;
        public int MaxPressMs { get; set; } = 115;
        public int MinIntervalMs { get; set; } = 90;
        public int MaxIntervalMs { get; set; } = 160;

        private readonly Random _rand = new();

        private void SendKeyEvent(ushort scanCode, bool extended, bool isKeyUp)
        {
            uint flags = KEYEVENTF_SCANCODE;
            if (extended) flags |= KEYEVENTF_EXTENDEDKEY;
            if (isKeyUp) flags |= KEYEVENTF_KEYUP;

            INPUT[] inputs = new INPUT[1];
            inputs[0] = new INPUT
            {
                type = INPUT_KEYBOARD,
                u = new InputUnion
                {
                    ki = new KEYBDINPUT
                    {
                        wVk = 0,
                        wScan = scanCode,
                        dwFlags = flags,
                        time = 0,
                        dwExtraInfo = IntPtr.Zero
                    }
                }
            };

            SendInput(1, inputs, Marshal.SizeOf(typeof(INPUT)));
        }

        public void PressKey(string keyName, int? customDurationMs = null)
        {
            var mapping = GetKeyMapping(keyName);
            if (!mapping.HasValue)
                throw new ArgumentException($"Unsupported key: {keyName}");

            int duration = customDurationMs ?? _rand.Next(MinPressMs, MaxPressMs + 1);

            // Key Down
            SendKeyEvent(mapping.Value.ScanCode, mapping.Value.Extended, isKeyUp: false);
            Thread.Sleep(duration);
            // Key Up
            SendKeyEvent(mapping.Value.ScanCode, mapping.Value.Extended, isKeyUp: true);
        }

        public void ExecuteSequence(IEnumerable<string> sequence)
        {
            var list = new List<string>(sequence);
            for (int i = 0; i < list.Count; i++)
            {
                PressKey(list[i]);
                if (i < list.Count - 1)
                {
                    int delay = _rand.Next(MinIntervalMs, MaxIntervalMs + 1);
                    Thread.Sleep(delay);
                }
            }
        }
    }
}
