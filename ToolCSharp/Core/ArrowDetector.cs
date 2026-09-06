using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using OpenCvSharp;
using ToolCSharp.Models;

namespace ToolCSharp.Core
{
    public class ArrowDetector : IDisposable
    {
        public DetectionSettings Settings { get; set; }
        public string TemplateDir { get; set; }
        public Dictionary<string, Mat> Templates { get; } = new(StringComparer.OrdinalIgnoreCase);
        public Action<string>? OnDebugLog { get; set; }

        public ArrowDetector(string templateDir = "assets/templates", DetectionSettings? settings = null)
        {
            TemplateDir = templateDir;
            Settings = settings ?? new DetectionSettings();
            LoadTemplates();
        }

        public void LoadTemplates()
        {
            foreach (var kvp in Templates)
            {
                kvp.Value.Dispose();
            }
            Templates.Clear();

            var mapping = new Dictionary<string, string>
            {
                { "UP", "arrow_up.png" },
                { "DOWN", "arrow_down.png" },
                { "LEFT", "arrow_left.png" },
                { "RIGHT", "arrow_right.png" }
            };

            foreach (var item in mapping)
            {
                string path = Path.Combine(TemplateDir, item.Value);
                if (File.Exists(path))
                {
                    Mat tpl = Cv2.ImRead(path, ImreadModes.Grayscale);
                    if (!tpl.Empty())
                    {
                        Templates[item.Key] = tpl;
                    }
                }
            }
        }

        public (string? Direction, double Score) MatchArrowInBox(Mat boxBgr)
        {
            if (Templates.Count == 0 || boxBgr.Empty()) return (null, 0.0);

            try
            {
                Mat[] channels = Cv2.Split(boxBgr);
                using Mat r = channels[2];
                channels[0].Dispose();
                channels[1].Dispose();

                using Mat gray = new Mat();
                Cv2.CvtColor(boxBgr, gray, ColorConversionCodes.BGR2GRAY);

                // Binarize red arrow and white arrow
                using Mat maskR = new Mat();
                using Mat maskW = new Mat();
                Cv2.Threshold(r, maskR, 185, 255, ThresholdTypes.Binary);
                Cv2.Threshold(gray, maskW, 175, 255, ThresholdTypes.Binary);

                using Mat mask = new Mat();
                Cv2.BitwiseOr(maskR, maskW, mask);

                double bestScore = -1.0;
                string? bestDirection = null;

                double tplScale = Math.Max(0.5, (double)mask.Height / 29.0);
                foreach (var kvp in Templates)
                {
                    Mat tpl = kvp.Value;
                    int tplW = Math.Max(4, (int)Math.Round(tpl.Width * tplScale));
                    int tplH = Math.Max(4, (int)Math.Round(tpl.Height * tplScale));

                    using Mat scaledTpl = new Mat();
                    if (Math.Abs(tplScale - 1.0) > 0.05)
                        Cv2.Resize(tpl, scaledTpl, new Size(tplW, tplH));
                    else
                        tpl.CopyTo(scaledTpl);

                    using Mat matched = new Mat();
                    if (mask.Width < scaledTpl.Width || mask.Height < scaledTpl.Height)
                    {
                        using Mat resizedMask = new Mat();
                        Cv2.Resize(mask, resizedMask, new Size(Math.Max(mask.Width, scaledTpl.Width), Math.Max(mask.Height, scaledTpl.Height)));
                        Cv2.MatchTemplate(resizedMask, scaledTpl, matched, TemplateMatchModes.CCoeffNormed);
                    }
                    else
                    {
                        Cv2.MatchTemplate(mask, scaledTpl, matched, TemplateMatchModes.CCoeffNormed);
                    }

                    Cv2.MinMaxLoc(matched, out _, out double maxVal, out _, out _);
                    if (maxVal > bestScore)
                    {
                        bestScore = maxVal;
                        bestDirection = kvp.Key;
                    }
                }

                double threshold = Math.Min(Settings.ArrowMatchThreshold, 0.60);
                if (bestScore >= threshold)
                {
                    return (bestDirection, bestScore);
                }

                return (null, bestScore);
            }
            catch
            {
                return (null, 0.0);
            }
        }

        public List<Mat> FindArrowRowBoxes(Mat frameBgr)
        {
            if (frameBgr == null || frameBgr.Empty()) return new List<Mat>();

            try
            {
                int h = frameBgr.Height;
                int w = frameBgr.Width;
                double scale = h / 568.0;

                // Strict narrow band where arrow QTE is located (above health/status icons)
                int roiY1 = Math.Clamp((int)(h * 0.81), 0, h - 2);
                int roiY2 = Math.Clamp((int)(h * 0.92), roiY1 + 1, h);
                int roiX1 = Math.Clamp((int)(w * 0.35), 0, w - 2);
                int roiX2 = Math.Clamp((int)(w * 0.65), roiX1 + 1, w);

                int roiW = roiX2 - roiX1;
                int roiH = roiY2 - roiY1;
                if (roiW <= 50 || roiH <= 20) return new List<Mat>();

                Rect roiRect = new Rect(roiX1, roiY1, roiW, roiH);
                using Mat roi = new Mat(frameBgr, roiRect);

                using Mat gray = new Mat();
                Cv2.CvtColor(roi, gray, ColorConversionCodes.BGR2GRAY);

                // Dark boxes (pending arrows when minigame starts at 0/5)
                using Mat darkMask = new Mat();
                Cv2.Threshold(gray, darkMask, 70, 255, ThresholdTypes.BinaryInv);

                // Red boxes (completed arrows)
                Mat[] channels = Cv2.Split(roi);
                using Mat b = channels[0];
                using Mat g = channels[1];
                using Mat r = channels[2];

                using Mat diff = new Mat();
                Cv2.Subtract(r, g, diff);
                using Mat m1 = new Mat();
                Cv2.Threshold(diff, m1, 30, 255, ThresholdTypes.Binary);
                using Mat m2 = new Mat();
                Cv2.Threshold(r, m2, 115, 255, ThresholdTypes.Binary);
                using Mat redMask = new Mat();
                Cv2.BitwiseAnd(m1, m2, redMask);

                // Combined mask: finds both pending dark boxes and completed red boxes
                using Mat combinedMask = new Mat();
                Cv2.BitwiseOr(darkMask, redMask, combinedMask);

                Cv2.FindContours(combinedMask, out Point[][] contours, out _, RetrievalModes.External, ContourApproximationModes.ApproxSimple);

                var candidates = new List<Rect>();
                int minDim = Math.Max(12, (int)Math.Round(15 * scale));
                int maxDim = Math.Max(25, (int)Math.Round(38 * scale));

                foreach (var c in contours)
                {
                    Rect rect = Cv2.BoundingRect(c);
                    if (rect.Width >= minDim && rect.Width <= maxDim && rect.Height >= minDim && rect.Height <= maxDim)
                    {
                        candidates.Add(rect);
                    }
                }

                int avgY = 0;
                int avgH = (int)Math.Round(23 * scale);
                int avgW = (int)Math.Round(23 * scale);
                double step = 27.25 * scale;

                if (candidates.Count >= 2)
                {
                    // Group by similar Y
                    var groups = new List<List<Rect>>();
                    int yTol = Math.Max(4, (int)Math.Round(6 * scale));
                    foreach (var rect in candidates)
                    {
                        bool matched = false;
                        foreach (var grp in groups)
                        {
                            if (Math.Abs(grp[0].Y - rect.Y) <= yTol)
                            {
                                grp.Add(rect);
                                matched = true;
                                break;
                            }
                        }
                        if (!matched)
                        {
                            groups.Add(new List<Rect> { rect });
                        }
                    }

                    var validGrps = groups.Where(g => g.Count >= 2).ToList();
                    if (validGrps.Count > 0)
                    {
                        var bestGrp = validGrps.OrderByDescending(g => g.Count).First().OrderBy(r => r.X).ToList();
                        avgY = (int)bestGrp.Average(rect => rect.Y);
                        avgH = (int)bestGrp.Average(rect => rect.Height);
                        avgW = (int)bestGrp.Average(rect => rect.Width);

                        if (bestGrp.Count >= 2)
                        {
                            var steps = new List<double>();
                            for (int i = 0; i < bestGrp.Count - 1; i++)
                            {
                                steps.Add(bestGrp[i + 1].X - bestGrp[i].X);
                            }
                            steps.Sort();
                            double medianStep = steps[steps.Count / 2];
                            if (medianStep >= 18 * scale && medianStep <= 42 * scale)
                            {
                                step = medianStep;
                            }
                        }
                    }
                }

                if (avgY == 0)
                {
                    // Fallback to geometric center of the ROI
                    avgY = (int)Math.Round(roiH * 0.55);
                }

                // Center alignment
                double roiCenterX = roiW / 2.0;
                double totalSpan = 4 * step + avgW;
                double startX = roiCenterX - totalSpan / 2.0;

                int marginY = Math.Max(2, (int)Math.Round(3 * scale));
                int marginX = Math.Max(2, (int)Math.Round(3 * scale));

                var boxes = new List<Mat>();
                for (int i = 0; i < 5; i++)
                {
                    int bx = (int)Math.Round(startX + i * step);
                    int by = avgY;

                    int x1 = Math.Max(0, bx - marginX);
                    int y1 = Math.Max(0, by - marginY);
                    int x2 = Math.Min(roi.Width, bx + avgW + marginX);
                    int y2 = Math.Min(roi.Height, by + avgH + marginY);

                    // Safety bounds checking
                    if (x2 <= x1 || y2 <= y1)
                    {
                        foreach (var mat in boxes) mat.Dispose();
                        return new List<Mat>();
                    }

                    Rect cropRect = new Rect(x1, y1, x2 - x1, y2 - y1);
                    boxes.Add(new Mat(roi, cropRect).Clone());
                }

                return boxes;
            }
            catch
            {
                return new List<Mat>();
            }
        }

        public List<string> DetectSequence(Mat frameBgr)
        {
            if (frameBgr == null || frameBgr.Empty()) return new List<string>();

            try
            {
                var boxes = FindArrowRowBoxes(frameBgr);
                if (boxes.Count != 5)
                {
                    foreach (var b in boxes) b.Dispose();
                    return new List<string>();
                }

                var sequence = new List<string>();
                var scores = new List<double>();
                foreach (var box in boxes)
                {
                    var (dir, sc) = MatchArrowInBox(box);
                    if (!string.IsNullOrEmpty(dir))
                    {
                        sequence.Add(dir);
                        scores.Add(sc);
                    }
                    box.Dispose();
                }

                if (sequence.Count == 5)
                {
                    return sequence;
                }
                else if (sequence.Count >= 2)
                {
                    OnDebugLog?.Invoke($"🔍 Nhận diện {sequence.Count}/5 mũi tên: [{string.Join(", ", sequence)}] (Scores: {string.Join(", ", scores.Select(s => s.ToString("F2")))})");
                }

                return new List<string>();
            }
            catch
            {
                return new List<string>();
            }
        }

        public void ExtractTemplatesFromSample(string sampleImagePath, string[] knownLabels)
        {
            if (!File.Exists(sampleImagePath))
                throw new FileNotFoundException("Sample image not found", sampleImagePath);

            using Mat img = Cv2.ImRead(sampleImagePath);
            if (img.Empty())
                throw new Exception("Could not decode sample image");

            var boxes = FindArrowRowBoxes(img);
            Directory.CreateDirectory(TemplateDir);

            var saved = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            for (int i = 0; i < Math.Min(boxes.Count, knownLabels.Length); i++)
            {
                string label = knownLabels[i].ToUpper();
                if (!saved.Contains(label))
                {
                    string outPath = Path.Combine(TemplateDir, $"arrow_{label.ToLower()}.png");
                    Cv2.ImWrite(outPath, boxes[i]);
                    saved.Add(label);
                }
                boxes[i].Dispose();
            }

            LoadTemplates();
        }

        public void Dispose()
        {
            foreach (var kvp in Templates)
            {
                kvp.Value.Dispose();
            }
            Templates.Clear();
        }
    }
}
