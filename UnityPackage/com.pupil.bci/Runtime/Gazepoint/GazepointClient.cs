using System;
using System.Collections.Concurrent;
using System.Globalization;
using System.Net.Sockets;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using UnityEngine;

namespace Pupil.Bci
{
    /// <summary>
    /// Background TCP client for Gazepoint Control (default 127.0.0.1:4242).
    /// Port of Pupil-com GazepointReceiver — samples are queued for the main thread.
    /// </summary>
    public sealed class GazepointClient : IDisposable
    {
        public readonly struct Sample
        {
            public readonly float Area;
            public readonly float BpogX;
            public readonly float BpogY;
            public readonly bool Connected;
            /// <summary>True when Gazepoint reports a valid pupil diameter (LPV/RPV).</summary>
            public readonly bool PupilValid;

            public Sample(float area, float bpogX, float bpogY, bool connected, bool pupilValid = true)
            {
                Area = area;
                BpogX = bpogX;
                BpogY = bpogY;
                Connected = connected;
                PupilValid = pupilValid;
            }
        }

        readonly string _host;
        readonly int _port;
        readonly ConcurrentQueue<Sample> _queue = new ConcurrentQueue<Sample>();

        Thread _thread;
        volatile bool _running;
        volatile bool _connected;
        volatile int _connectAttempts;
        volatile string _lastError = "";

        static readonly Regex Lpd = new Regex(@"LPD=""([0-9.]+)""", RegexOptions.Compiled);
        static readonly Regex Rpd = new Regex(@"RPD=""([0-9.]+)""", RegexOptions.Compiled);
        static readonly Regex BpogXRe = new Regex(@"BPOGX=""([0-9.-]+)""", RegexOptions.Compiled);
        static readonly Regex BpogYRe = new Regex(@"BPOGY=""([0-9.-]+)""", RegexOptions.Compiled);

        public bool IsConnected => _connected;
        public bool IsRunning => _running;
        public int ConnectAttempts => _connectAttempts;
        public string LastError => _lastError ?? "";

        public GazepointClient(string host = "127.0.0.1", int port = 4242)
        {
            _host = host;
            _port = port;
        }

        /// <summary>True if a Gazepoint-related process is running (Windows).</summary>
        public static bool IsGazepointProcessRunning()
        {
            try
            {
                foreach (var p in System.Diagnostics.Process.GetProcesses())
                {
                    string name;
                    try { name = p.ProcessName; }
                    catch { continue; }
                    if (string.IsNullOrEmpty(name)) continue;
                    var n = name.ToLowerInvariant();
                    if (n.Contains("gazepoint"))
                        return true;
                }
            }
            catch
            {
                // ignore
            }
            return false;
        }

        /// <summary>
        /// Try to start Gazepoint. Uses <paramref name="exePath"/> if valid,
        /// otherwise searches common Windows install locations (incl. bin64\Gazepoint.exe).
        /// </summary>
        public static bool TryLaunchGazepoint(string exePath, out string error)
        {
            error = null;
            var path = ResolveGazepointExePath(exePath);
            if (string.IsNullOrEmpty(path))
            {
                error =
                    "Gazepoint.exe non trovato.\n" +
                    "Imposta PupilBciConfig.gazepointExePath, es.:\n" +
                    @"C:\Program Files (x86)\Gazepoint\Gazepoint\bin64\Gazepoint.exe";
                return false;
            }

            if (IsGazepointProcessRunning())
            {
                // Already running — caller can still RetryConnection
                return true;
            }

            try
            {
                var psi = new System.Diagnostics.ProcessStartInfo
                {
                    FileName = path,
                    UseShellExecute = true,
                    WorkingDirectory = System.IO.Path.GetDirectoryName(path) ?? ""
                };
                System.Diagnostics.Process.Start(psi);
                Debug.Log("[PupilBci] Launched Gazepoint: " + path);
                return true;
            }
            catch (Exception e)
            {
                error = e.Message + "\nPath: " + path;
                return false;
            }
        }

        /// <summary>Configured path, or first existing candidate on this machine.</summary>
        public static string ResolveGazepointExePath(string configuredPath = null)
        {
            if (!string.IsNullOrWhiteSpace(configuredPath) && System.IO.File.Exists(configuredPath))
                return configuredPath;

            var pf = System.Environment.GetFolderPath(System.Environment.SpecialFolder.ProgramFiles);
            var pf86 = System.Environment.GetFolderPath(System.Environment.SpecialFolder.ProgramFilesX86);

            string[] candidates =
            {
                // Typical GP3 / Gazepoint 7.x layout on this PC
                System.IO.Path.Combine(pf86, "Gazepoint", "Gazepoint", "bin64", "Gazepoint.exe"),
                System.IO.Path.Combine(pf, "Gazepoint", "Gazepoint", "bin64", "Gazepoint.exe"),
                System.IO.Path.Combine(pf86, "Gazepoint", "Gazepoint", "bin", "Gazepoint.exe"),
                System.IO.Path.Combine(pf, "Gazepoint", "Gazepoint", "bin", "Gazepoint.exe"),
                System.IO.Path.Combine(pf86, "Gazepoint", "Gazepoint", "GazepointControl.exe"),
                System.IO.Path.Combine(pf, "Gazepoint", "Gazepoint", "GazepointControl.exe"),
                System.IO.Path.Combine(pf86, "Gazepoint", "GazepointControl.exe"),
                System.IO.Path.Combine(pf, "Gazepoint", "GazepointControl.exe"),
                @"C:\Program Files (x86)\Gazepoint\Gazepoint\bin64\Gazepoint.exe",
                @"C:\Program Files\Gazepoint\Gazepoint\bin64\Gazepoint.exe",
            };

            foreach (var c in candidates)
            {
                if (!string.IsNullOrEmpty(c) && System.IO.File.Exists(c))
                    return c;
            }

            return null;
        }

        public void Start()
        {
            if (_running)
                return;
            _running = true;
            _thread = new Thread(RunLoop)
            {
                IsBackground = true,
                Name = "PupilBci.Gazepoint"
            };
            _thread.Start();
        }

        public void Stop()
        {
            _running = false;
            if (_thread != null && _thread.IsAlive)
            {
                if (!_thread.Join(1500))
                    Debug.LogWarning("[PupilBci] Gazepoint thread did not stop in time.");
            }
            _thread = null;
            _connected = false;
        }

        public int Drain(System.Collections.Generic.List<Sample> into, int max = 64)
        {
            var n = 0;
            while (n < max && _queue.TryDequeue(out var s))
            {
                into.Add(s);
                n++;
            }
            return n;
        }

        public bool TryDequeue(out Sample sample) => _queue.TryDequeue(out sample);

        void RunLoop()
        {
            var buffer = "";
            TcpClient client = null;
            NetworkStream stream = null;

            while (_running)
            {
                if (!_connected)
                {
                    try
                    {
                        _connectAttempts++;
                        client?.Close();
                        client = new TcpClient();
                        var ar = client.BeginConnect(_host, _port, null, null);
                        if (!ar.AsyncWaitHandle.WaitOne(TimeSpan.FromSeconds(1)) || !client.Connected)
                        {
                            client.Close();
                            _lastError = $"Nessuna risposta su {_host}:{_port}. Avvia Gazepoint Control.";
                            Thread.Sleep(1000);
                            continue;
                        }
                        client.EndConnect(ar);
                        stream = client.GetStream();
                        stream.ReadTimeout = 1000;

                        Send(stream, "<SET ID=\"ENABLE_SEND_PUPIL_LEFT\" STATE=\"1\" />\r\n");
                        Send(stream, "<SET ID=\"ENABLE_SEND_PUPIL_RIGHT\" STATE=\"1\" />\r\n");
                        Send(stream, "<SET ID=\"ENABLE_SEND_POG_BEST\" STATE=\"1\" />\r\n");
                        Send(stream, "<SET ID=\"ENABLE_SEND_DATA\" STATE=\"1\" />\r\n");

                        _connected = true;
                        _lastError = "";
                        _queue.Enqueue(new Sample(0f, 0f, 0f, true, pupilValid: false));
                    }
                    catch (Exception e)
                    {
                        _connected = false;
                        _lastError = e.Message;
                        Thread.Sleep(1000);
                        continue;
                    }
                }

                try
                {
                    var buf = new byte[2048];
                    var read = stream.Read(buf, 0, buf.Length);
                    if (read <= 0)
                    {
                        _connected = false;
                        continue;
                    }

                    buffer += Encoding.UTF8.GetString(buf, 0, read);
                    while (true)
                    {
                        var idx = buffer.IndexOf("\r\n", StringComparison.Ordinal);
                        if (idx < 0)
                            break;
                        var line = buffer.Substring(0, idx);
                        buffer = buffer.Substring(idx + 2);
                        ParseLine(line);
                    }
                }
                catch (Exception)
                {
                    if (_running)
                        _connected = false;
                }
            }

            try { stream?.Close(); } catch { /* ignore */ }
            try { client?.Close(); } catch { /* ignore */ }
            _connected = false;
        }

        void ParseLine(string line)
        {
            if (!line.StartsWith("<REC", StringComparison.Ordinal))
                return;

            var lpV = line.Contains("LPV=\"1\"");
            var rpV = line.Contains("RPV=\"1\"");
            var matchL = Lpd.Match(line);
            var matchR = Rpd.Match(line);

            float? diameter = null;
            if (lpV && rpV && matchL.Success && matchR.Success
                && TryParse(matchL.Groups[1].Value, out var leftD)
                && TryParse(matchR.Groups[1].Value, out var rightD))
                diameter = (leftD + rightD) * 0.5f;
            else if (lpV && matchL.Success && TryParse(matchL.Groups[1].Value, out var onlyL))
                diameter = onlyL;
            else if (rpV && matchR.Success && TryParse(matchR.Groups[1].Value, out var onlyR))
                diameter = onlyR;

            float area = 0f;
            bool pupilValid = diameter.HasValue;
            if (diameter.HasValue)
            {
                var r = diameter.Value * 0.5f;
                area = Mathf.PI * r * r;
            }

            float bx = 0f, by = 0f;
            var bpogV = line.Contains("BPOGV=\"1\"");
            var mx = BpogXRe.Match(line);
            var my = BpogYRe.Match(line);
            if (bpogV && mx.Success && my.Success
                && TryParse(mx.Groups[1].Value, out bx)
                && TryParse(my.Groups[1].Value, out by))
            {
                // bx, by set
            }
            else
            {
                bx = 0f;
                by = 0f;
            }

            _queue.Enqueue(new Sample(area, bx, by, true, pupilValid));
        }

        static bool TryParse(string s, out float v) =>
            float.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out v);

        static void Send(NetworkStream stream, string msg)
        {
            var bytes = Encoding.ASCII.GetBytes(msg);
            stream.Write(bytes, 0, bytes.Length);
        }

        public void Dispose() => Stop();
    }
}
