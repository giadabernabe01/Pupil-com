using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using UnityEngine;
using Debug = UnityEngine.Debug;

namespace Pupil.Bci
{
    /// <summary>
    /// Bring Gazepoint.exe window to the foreground (windowed by default;
    /// optional maximize) so the user can reposition and re-acquire the eye.
    /// </summary>
    public static class GazepointWindowFocus
    {
        const int SwRestore = 9;
        const int SwShow = 5;
        const int SwMaximize = 3;

        [DllImport("user32.dll")]
        static extern bool SetForegroundWindow(IntPtr hWnd);

        [DllImport("user32.dll")]
        static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

        [DllImport("user32.dll")]
        static extern bool IsIconic(IntPtr hWnd);

        [DllImport("user32.dll")]
        static extern bool IsWindowVisible(IntPtr hWnd);

        [DllImport("user32.dll")]
        static extern IntPtr GetForegroundWindow();

        [DllImport("user32.dll")]
        static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);

        [DllImport("user32.dll")]
        static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);

        [DllImport("kernel32.dll")]
        static extern uint GetCurrentThreadId();

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

        /// <summary>Launch if needed, then focus Gazepoint (windowed unless maximize).</summary>
        public static bool BringToFront(string configuredExePath, bool maximize, out string error)
        {
            error = null;
            if (!GazepointClient.IsGazepointProcessRunning())
            {
                if (!GazepointClient.TryLaunchGazepoint(configuredExePath, out error))
                    return false;
            }

            if (!FocusExisting(maximize))
            {
                error = "Finestra Gazepoint non trovata ancora — riprova tra un attimo.";
                return false;
            }

            return true;
        }

        public static bool FocusExisting(bool maximize = false)
        {
            var hwnd = FindGazepointMainWindow();
            if (hwnd == IntPtr.Zero)
                return false;

            try
            {
                // Restore from minimized/maximized so it stays windowed when maximize=false.
                ShowWindow(hwnd, maximize ? SwMaximize : SwRestore);
                if (!maximize)
                    ShowWindow(hwnd, SwShow);
                ForceForeground(hwnd);
                return true;
            }
            catch (Exception e)
            {
                Debug.LogWarning("[PupilBci] FocusExisting: " + e.Message);
                return false;
            }
        }

        static void ForceForeground(IntPtr hwnd)
        {
            var fg = GetForegroundWindow();
            uint fgThread = fg != IntPtr.Zero ? GetWindowThreadProcessId(fg, out _) : 0;
            uint thisThread = GetCurrentThreadId();

            if (fgThread != 0 && fgThread != thisThread)
                AttachThreadInput(thisThread, fgThread, true);

            SetForegroundWindow(hwnd);

            if (fgThread != 0 && fgThread != thisThread)
                AttachThreadInput(thisThread, fgThread, false);
        }

        public static IntPtr FindGazepointMainWindow()
        {
            IntPtr best = IntPtr.Zero;

            try
            {
                foreach (var p in Process.GetProcesses())
                {
                    string name;
                    try { name = p.ProcessName; }
                    catch { continue; }

                    if (string.IsNullOrEmpty(name)
                        || name.IndexOf("gazepoint", StringComparison.OrdinalIgnoreCase) < 0)
                        continue;

                    try
                    {
                        p.Refresh();
                        var h = p.MainWindowHandle;
                        if (h == IntPtr.Zero || !IsWindowVisible(h))
                            continue;

                        var title = new StringBuilder(256);
                        GetWindowText(h, title, title.Capacity);
                        var t = title.ToString();
                        if (t.IndexOf("Analysis", StringComparison.OrdinalIgnoreCase) >= 0) continue;
                        if (t.IndexOf("Assistant", StringComparison.OrdinalIgnoreCase) >= 0) continue;
                        if (t.IndexOf("Driver", StringComparison.OrdinalIgnoreCase) >= 0) continue;
                        if (t.IndexOf("Utility", StringComparison.OrdinalIgnoreCase) >= 0) continue;

                        best = h;
                        // Prefer main product (often just "Gazepoint")
                        if (string.Equals(t.Trim(), "Gazepoint", StringComparison.OrdinalIgnoreCase)
                            || (t.IndexOf("Gazepoint", StringComparison.OrdinalIgnoreCase) >= 0
                                && t.Length < 24))
                            return h;
                    }
                    catch
                    {
                        // ignore single process failures
                    }
                }
            }
            catch (Exception e)
            {
                Debug.LogWarning("[PupilBci] FindGazepointMainWindow: " + e.Message);
            }

            return best;
        }
    }
}
