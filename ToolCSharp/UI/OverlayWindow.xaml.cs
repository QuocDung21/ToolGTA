using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;

namespace ToolCSharp.UI
{
    public partial class OverlayWindow : Window
    {
        public Action? OnClosedCallback { get; set; }

        public OverlayWindow()
        {
            InitializeComponent();
        }

        private void Window_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            if (e.ButtonState == MouseButtonState.Pressed)
            {
                DragMove();
            }
        }

        private void CloseButton_Click(object sender, RoutedEventArgs e)
        {
            Hide();
            OnClosedCallback?.Invoke();
        }

        public void UpdateInfo(string status, string hexColor, int fishCount, int solvedCount, List<string>? sequence = null)
        {
            Dispatcher.Invoke(() =>
            {
                TxtStatus.Text = $"STATUS: {status.ToUpper()}";
                try
                {
                    TxtStatus.Foreground = (Brush)new BrushConverter().ConvertFromString(hexColor)!;
                }
                catch { }

                TxtDetails.Text = $"Fish: {fishCount}  |  Solved: {solvedCount}";

                if (sequence != null && sequence.Count > 0)
                {
                    var arrows = sequence.ConvertAll(s => s switch
                    {
                        "UP" => "⬆",
                        "DOWN" => "⬇",
                        "LEFT" => "⬅",
                        "RIGHT" => "➡",
                        _ => s
                    });
                    TxtArrows.Text = $"Arrows: {string.Join(" ", arrows)}";
                    TxtArrows.Foreground = (Brush)new BrushConverter().ConvertFromString("#A6E3A1")!;
                }
                else
                {
                    TxtArrows.Text = "Arrows: [WAITING]";
                    TxtArrows.Foreground = (Brush)new BrushConverter().ConvertFromString("#6C7086")!;
                }
            });
        }
    }
}
