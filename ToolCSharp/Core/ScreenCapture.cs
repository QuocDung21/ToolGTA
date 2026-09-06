using System;
using System.Runtime.InteropServices;
using OpenCvSharp;

namespace ToolCSharp.Core
{
    public class ScreenCapture : IDisposable
    {
        [DllImport("user32.dll")]
        private static extern bool SetProcessDPIAware();

        [DllImport("user32.dll")]
        private static extern IntPtr GetDesktopWindow();

        [DllImport("user32.dll")]
        private static extern IntPtr GetWindowDC(IntPtr hWnd);

        [DllImport("user32.dll")]
        private static extern int ReleaseDC(IntPtr hWnd, IntPtr hDC);

        [DllImport("user32.dll")]
        private static extern int GetSystemMetrics(int nIndex);

        [DllImport("gdi32.dll")]
        private static extern IntPtr CreateCompatibleDC(IntPtr hdc);

        [DllImport("gdi32.dll")]
        private static extern IntPtr CreateCompatibleBitmap(IntPtr hdc, int nWidth, int nHeight);

        [DllImport("gdi32.dll")]
        private static extern IntPtr SelectObject(IntPtr hdc, IntPtr hgdiobj);

        [DllImport("gdi32.dll")]
        private static extern bool BitBlt(IntPtr hdcDest, int nXDest, int nYDest, int nWidth, int nHeight, IntPtr hdcSrc, int nXSrc, int nYSrc, int dwRop);

        [DllImport("gdi32.dll")]
        private static extern bool DeleteDC(IntPtr hdc);

        [DllImport("gdi32.dll")]
        private static extern bool DeleteObject(IntPtr hObject);

        [DllImport("gdi32.dll")]
        private static extern int GetDIBits(IntPtr hdc, IntPtr hbmp, uint uStartScan, uint cScanLines, [Out] byte[] lpvBits, ref BITMAPINFO lpbi, uint uUsage);

        [StructLayout(LayoutKind.Sequential)]
        private struct BITMAPINFOHEADER
        {
            public uint biSize;
            public int biWidth;
            public int biHeight;
            public ushort biPlanes;
            public ushort biBitCount;
            public uint biCompression;
            public uint biSizeImage;
            public int biXPelsPerMeter;
            public int biYPelsPerMeter;
            public uint biClrUsed;
            public uint biClrImportant;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct BITMAPINFO
        {
            public BITMAPINFOHEADER bmiHeader;
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 256)]
            public uint[] bmiColors;
        }

        private const int SM_CXSCREEN = 0;
        private const int SM_CYSCREEN = 1;
        private const int SRCCOPY = 0x00CC0020;

        public int ScreenWidth { get; private set; }
        public int ScreenHeight { get; private set; }

        public ScreenCapture()
        {
            try { SetProcessDPIAware(); } catch { }
            ScreenWidth = GetSystemMetrics(SM_CXSCREEN);
            ScreenHeight = GetSystemMetrics(SM_CYSCREEN);
        }

        public Mat CaptureFull()
        {
            IntPtr hDesktopWnd = GetDesktopWindow();
            IntPtr hDesktopDC = GetWindowDC(hDesktopWnd);
            IntPtr hCaptureDC = CreateCompatibleDC(hDesktopDC);
            IntPtr hCaptureBitmap = CreateCompatibleBitmap(hDesktopDC, ScreenWidth, ScreenHeight);
            IntPtr hOldBitmap = SelectObject(hCaptureDC, hCaptureBitmap);

            BitBlt(hCaptureDC, 0, 0, ScreenWidth, ScreenHeight, hDesktopDC, 0, 0, SRCCOPY);

            BITMAPINFO bmi = new BITMAPINFO();
            bmi.bmiHeader.biSize = (uint)Marshal.SizeOf(typeof(BITMAPINFOHEADER));
            bmi.bmiHeader.biWidth = ScreenWidth;
            bmi.bmiHeader.biHeight = -ScreenHeight; // top-down
            bmi.bmiHeader.biPlanes = 1;
            bmi.bmiHeader.biBitCount = 32;
            bmi.bmiHeader.biCompression = 0; // BI_RGB

            byte[] pixelData = new byte[ScreenWidth * ScreenHeight * 4];
            GetDIBits(hCaptureDC, hCaptureBitmap, 0, (uint)ScreenHeight, pixelData, ref bmi, 0);

            SelectObject(hCaptureDC, hOldBitmap);
            DeleteObject(hCaptureBitmap);
            DeleteDC(hCaptureDC);
            ReleaseDC(hDesktopWnd, hDesktopDC);

            GCHandle handle = GCHandle.Alloc(pixelData, GCHandleType.Pinned);
            try
            {
                using Mat bgra = Mat.FromPixelData(ScreenHeight, ScreenWidth, MatType.CV_8UC4, handle.AddrOfPinnedObject());
                Mat bgr = new Mat();
                Cv2.CvtColor(bgra, bgr, ColorConversionCodes.BGRA2BGR);
                return bgr;
            }
            finally
            {
                handle.Free();
            }
        }

        public void Dispose()
        {
        }
    }
}
