using System;
using System.Threading;

namespace ToolCSharp.Core
{
    public class AntiAfk
    {
        private readonly InputSimulator _simulator;
        private readonly Random _rand = new();
        private int _actionCount = 0;

        public bool Enabled { get; set; } = true;
        public int MinActions { get; set; } = 5;
        public int MaxActions { get; set; } = 12;

        public AntiAfk(InputSimulator simulator)
        {
            _simulator = simulator;
        }

        public void TriggerIfNeeded()
        {
            if (!Enabled) return;

            _actionCount++;
            int threshold = _rand.Next(MinActions, MaxActions + 1);
            if (_actionCount >= threshold)
            {
                PerformAntiAfk();
                _actionCount = 0;
            }
        }

        public void PerformAntiAfk()
        {
            Thread.Sleep(_rand.Next(300, 750));
            string key = _rand.Next(0, 2) == 0 ? "LEFT" : "RIGHT";
            _simulator.PressKey(key, _rand.Next(40, 80));
        }
    }
}
