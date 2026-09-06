using System.Text.Json.Serialization;

namespace ToolCSharp.Models
{
    public class AppSettings
    {
        [JsonPropertyName("general")]
        public GeneralSettings General { get; set; } = new();

        [JsonPropertyName("delays")]
        public DelaySettings Delays { get; set; } = new();

        [JsonPropertyName("detection")]
        public DetectionSettings Detection { get; set; } = new();

        [JsonPropertyName("anti_afk")]
        public AntiAfkSettings AntiAfk { get; set; } = new();

        [JsonPropertyName("alerts")]
        public AlertSettings Alerts { get; set; } = new();
    }

    public class GeneralSettings
    {
        [JsonPropertyName("auto_start")]
        public bool AutoStart { get; set; } = false;

        [JsonPropertyName("auto_recast")]
        public bool AutoRecast { get; set; } = false;

        [JsonPropertyName("hotkey_start")]
        public string HotkeyStart { get; set; } = "F1";

        [JsonPropertyName("hotkey_pause")]
        public string HotkeyPause { get; set; } = "F2";

        [JsonPropertyName("hotkey_panic")]
        public string HotkeyPanic { get; set; } = "F3";

        [JsonPropertyName("rod_slot_key")]
        public string RodSlotKey { get; set; } = "1";
    }

    public class DelaySettings
    {
        [JsonPropertyName("min_key_press_ms")]
        public int MinKeyPressMs { get; set; } = 65;

        [JsonPropertyName("max_key_press_ms")]
        public int MaxKeyPressMs { get; set; } = 115;

        [JsonPropertyName("min_interval_ms")]
        public int MinIntervalMs { get; set; } = 90;

        [JsonPropertyName("max_interval_ms")]
        public int MaxIntervalMs { get; set; } = 160;

        [JsonPropertyName("reel_in_wait_sec")]
        public double ReelInWaitSec { get; set; } = 4.5;

        [JsonPropertyName("recast_wait_sec")]
        public double RecastWaitSec { get; set; } = 2.0;
    }

    public class DetectionSettings
    {
        [JsonPropertyName("arrow_match_threshold")]
        public double ArrowMatchThreshold { get; set; } = 0.72;

        [JsonPropertyName("red_hsv_lower1")]
        public int[] RedHsvLower1 { get; set; } = [0, 100, 100];

        [JsonPropertyName("red_hsv_upper1")]
        public int[] RedHsvUpper1 { get; set; } = [10, 255, 255];

        [JsonPropertyName("red_hsv_lower2")]
        public int[] RedHsvLower2 { get; set; } = [170, 100, 100];

        [JsonPropertyName("red_hsv_upper2")]
        public int[] RedHsvUpper2 { get; set; } = [180, 255, 255];
    }

    public class AntiAfkSettings
    {
        [JsonPropertyName("enabled")]
        public bool Enabled { get; set; } = true;

        [JsonPropertyName("min_actions")]
        public int MinActions { get; set; } = 5;

        [JsonPropertyName("max_actions")]
        public int MaxActions { get; set; } = 12;
    }

    public class AlertSettings
    {
        [JsonPropertyName("discord_webhook_url")]
        public string DiscordWebhookUrl { get; set; } = "";

        [JsonPropertyName("sound_alarm_on_fail")]
        public bool SoundAlarmOnFail { get; set; } = true;
    }
}
