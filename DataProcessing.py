import re
import socket
import time
import numpy as np
import zmq
import queue
from msgpack import loads
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl
from collections import deque

# ---------------------------------------------------------
# DATA PROCESSING LOGIC
# ---------------------------------------------------------
class AreaFilter:
    """Class for filtering pupil area data."""
    def __init__(self, fps=60, thresh=0.85, device_type="gazepoint"):
        
        self.max_array_len = 1000
        if device_type == "gazepoint":
            #print("Using Gazepoint min and max area values")
            self.amin, self.amax = 50.0, 1000.0 # area is measured in mm^2
            self.ebf_thresh = 100.0
        else:
            #print("Using Pupil Core min and max area values")
            self.amin, self.amax = 1500.0, 10000.0 # area is measured in pixel units
            self.ebf_thresh = 500.0
        self.fps = fps
        #filter initializations
        self.pupil_areas_raw = deque(maxlen=self.max_array_len)
        self.pupil_areas = deque(maxlen=self.max_array_len)
        self.pupil_areas_diffs = deque(maxlen=self.max_array_len)
        self.pupil_areas_ebf = deque(maxlen=self.max_array_len)
        self.pupil_areas_fin = deque(maxlen=self.max_array_len)

        self.reject_count = 0

    def area_filtering(self, new_area):
        self.pupil_areas_raw.append(new_area)
        # Control on the pupil area with respect to physiological dimensions
        if self.amin <= new_area <= self.amax:
            self.pupil_areas.append(new_area)
        elif len(self.pupil_areas) > 0:
            self.pupil_areas.append(self.pupil_areas[-1])
        else:
            return new_area # no valid data yet

        if len(self.pupil_areas) > 0:
            
            # event-based filter
            self.pupil_areas_ebf.append(self.pupil_areas[-1])
            if len(self.pupil_areas_ebf) > 1:
                diff = abs(self.pupil_areas_ebf[-1] - self.pupil_areas_ebf[-2])
                self.pupil_areas_diffs.append(diff)
                
                win_len = int(self.fps / 4)
                if len(self.pupil_areas_diffs) > win_len+1:
                    recent_diffs = list(self.pupil_areas_diffs)[:-1][-win_len:]
                    baseline = np.mean(recent_diffs)
                    if diff > self.ebf_thresh + baseline:
                        self.reject_count += 1
                        
                        # Max allowed consecutive rejected frames (0.5 seconds)
                        max_rejects = int(self.fps / 2) 
                        
                        if self.reject_count < max_rejects:
                            # It's a short spike/blink. Reject it and hold the old value.
                            self.pupil_areas_ebf[-1] = self.pupil_areas_ebf[-2]
                            self.pupil_areas_diffs[-1] = baseline
                        else:
                            # Accept the new low value and reset the counter.
                            self.reject_count = 0
                    else:
                        # Normal physiological movement. Accept and reset counter.
                        self.reject_count = 0
                
            # moving average
            ma_win = int(self.fps / 2)

            if len(self.pupil_areas_ebf) >= ma_win:
                recent_ebf = list(self.pupil_areas_ebf)[-ma_win:]
                res = np.mean(recent_ebf)
            else:
                res = self.pupil_areas_ebf[-1]
                
            self.pupil_areas_fin.append(res)

            return res

        #return new_area
    
    def reset(self):
        self.pupil_areas_raw.clear()
        self.pupil_areas.clear()
        self.pupil_areas_ebf.clear()
        self.pupil_areas_fin.clear()

class ConstrictionMonitor:
    """Class for detecting pupil constriction and recovery events."""
    def __init__(self, fps=130, thresh=0.75, short_dur=0.5, long_dur=3.0, extra_dur=5.0, device_type="gazepoint"):
        self.fps = fps
        self.thresh = thresh
        self.short_dur = short_dur
        self.long_dur = long_dur
        self.extra_dur = extra_dur
        self.device_type = device_type
        self.baseline_buffer = deque(maxlen=round(self.fps*2)) # last 1 seconds buffer
        self.filter = AreaFilter(fps=self.fps, device_type=self.device_type)
        self.drop_start_time = None
        self.short_trigger_handled = False
        self.long_trigger_handled = False
        self.extra_trigger_handled = False
        self.current_sma_thresh = 0.0
        self.exit_thresh = None

    def reset_monitor(self):
        """Resets internal timers and flags."""
        self.drop_start_time = None
        self.short_trigger_handled = False
        self.long_trigger_handled = False
        self.extra_trigger_handled = False
        #self.baseline_buffer.clear() # Critical: forces a fresh threshold calculation

    def baseline_collection(self, area):
        last_val = self.filter.area_filtering(area)

        # safety check for startup/empty data
        if last_val is None or last_val == 0:
            return False
        # collect baseline data for first 2 seconds
        if len(self.baseline_buffer) < self.fps*2:
            self.baseline_buffer.append(last_val)

    def constriction_detector(self, area):

        """Returns:
        0 = No event
        1 = Short constriction 
        2 = Long constriction 
        3 = Special feature for keyboard"""

        # get filtered data
        last_val = self.filter.area_filtering(area)

        # safety check for startup/empty data
        if last_val is None or last_val == 0:
            return 0

        if len(self.baseline_buffer) > 0:
            current_mean = np.mean(self.baseline_buffer) 
            self.current_sma_thresh = current_mean * self.thresh 
        else:
            self.current_sma_thresh = 0.0

        if self.drop_start_time is None:
            active_thresh = self.current_sma_thresh
        else:
            active_thresh = self.exit_thresh

        # check whether last value is below threshold
        if last_val < active_thresh:
            # check whether this is the first below threshold
            self.above_ma = (last_val > self.current_sma_thresh)
            if self.drop_start_time is None:
                self.drop_start_time = time.time()
                self.exit_thresh = self.current_sma_thresh
                self.above_ma = False
                self.cross_count = 0
            # check how long it has been below threshold
            elapsed = time.time() - self.drop_start_time
            #check if it's below moving average as well and count crossings
            if self.above_ma and self.cross_count == 0:
                self.cross_count += 1 
            elif not self.above_ma and self.cross_count == 1:
                self.cross_count += 1
            # set new threshold and mark a new constriction start if the signal hasn't gone above fixed threshold 
            # but has crossed ma threshold again
            if self.cross_count == 2:
                self.exit_thresh = None
                self.drop_start_time = None
                self.short_trigger_handled = False
                self.long_trigger_handled = False
                self.extra_trigger_handled = False
                self.baseline_buffer.append(last_val)
                return 0

            if elapsed >= self.extra_dur:
                # if below threshold for longer than extra_dur --> extra feature unlocked
                if not self.extra_trigger_handled:
                    print(f"Extra constriction detected")
                    self.extra_trigger_handled = True
                    return 3
            elif elapsed >= self.long_dur:
                # if below threshold for longer than long_dur --> it's a long trigger command!
                if not self.long_trigger_handled:
                    print(f"Long constriction detected")
                    self.long_trigger_handled = True
                    return 2
            # if below threshold for longer than short_dur --> it's a selection!
            elif elapsed >= self.short_dur:
                if not self.short_trigger_handled:
                    print("Short constriction detected.")
                    self.short_trigger_handled = True
                    return 1
            self.baseline_buffer.append(last_val) # add value to keep calculating moving average
        else:
            # reset timer
            self.exit_thresh = None
            self.drop_start_time = None
            self.short_trigger_handled = False
            self.long_trigger_handled = False
            self.extra_trigger_handled = False
            self.baseline_buffer.append(last_val)
        return 0 # no new event.

# ---------------------------------------------------------
# Gazepoint receiver
# ---------------------------------------------------------

class GazepointReceiver(QtCore.QThread):
    connected_signal = QtCore.pyqtSignal(bool)

    def __init__(self, ip='127.0.0.1', port=4242):
        super().__init__()
        self.running = True
        self.connected = False
        self.ip = ip
        self.port = port
        self.sock = None
        self.data_queue = queue.Queue()

    def get_all_frames(self):
        frames = []
        while not self.data_queue.empty():
            try:
                frames.append(self.data_queue.get_nowait())
            except queue.Empty:
                break
        return frames

    def run(self):
        buffer_str = ""
        while self.running:
            if not self.connected:
                try:
                    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.sock.settimeout(1.0) 
                    self.sock.connect((self.ip, self.port))
                    
                    self.sock.send(str.encode('<SET ID="ENABLE_SEND_PUPIL_LEFT" STATE="1" />\r\n'))
                    self.sock.send(str.encode('<SET ID="ENABLE_SEND_PUPIL_RIGHT" STATE="1" />\r\n'))
                    self.sock.send(str.encode('<SET ID="ENABLE_SEND_POG_BEST" STATE="1" />\r\n'))
                    self.sock.send(str.encode('<SET ID="ENABLE_SEND_DATA" STATE="1" />\r\n'))
                    
                    self.connected = True
                    self.connected_signal.emit(True)
                except Exception as e:
                    self.msleep(1000)
                    continue

            try:
                data = self.sock.recv(2048).decode('utf-8')
                if not data:
                    self.connected = False
                    continue
                    
                buffer_str += data
                while '\r\n' in buffer_str:
                    line, buffer_str = buffer_str.split('\r\n', 1)
                    if line.startswith('<REC'):
                        match_l = re.search(r'LPD="([0-9.]+)"', line)
                        match_r = re.search(r'RPD="([0-9.]+)"', line)
                        lp_v = 'LPV="1"' in line
                        rp_v = 'RPV="1"' in line
                        
                        d = None
                        if lp_v and rp_v and match_l and match_r:
                            d = (float(match_l.group(1)) + float(match_r.group(1))) / 2.0
                        elif lp_v and match_l: d = float(match_l.group(1))
                        elif rp_v and match_r: d = float(match_r.group(1))
                        
                        if d is not None:
                            area = np.pi * (d / 2.0) ** 2
                            #self.data_queue.put(area) 
                        else:
                            area = None

                        match_bx = re.search(r'BPOGX="([0-9.-]+)"', line)
                        match_by = re.search(r'BPOGY="([0-9.-]+)"', line)
                        bpog_v = 'BPOGV="1"' in line
                        
                        bpog_x = 0.0
                        bpog_y = 0.0
                        
                        if bpog_v and match_bx and match_by:
                            bpog_x = float(match_bx.group(1))
                            bpog_y = float(match_by.group(1))

                        self.data_queue.put((area, bpog_x, bpog_y)) if area is not None else self.data_queue.put((0.0, bpog_x, bpog_y))
            except socket.timeout:
                continue # Normal timeout, loop back to check if self.running is False
            except Exception as e:
                if self.running:
                    self.connected = False
                    
        # Cleanup
        if self.sock:
            self.sock.close()

    def stop(self):
        self.running = False
        self.wait(1500) # Give it 1.5 seconds max to clean up network ports safely

# ---------------------------------------------------------
# ZMQ Thread: receives pupil diameter from Pupil Labs
# ---------------------------------------------------------
class PupilLabsReceiver(QtCore.QThread):
    connected_signal = QtCore.pyqtSignal(bool) 

    def __init__(self):
        super().__init__()
        self.running = True
        self.connected = False
        self.data_queue = queue.Queue()

    def get_all_frames(self):
        frames = []
        while not self.data_queue.empty():
            try:
                frames.append(self.data_queue.get_nowait())
            except queue.Empty:
                break
        return frames
    
    def run(self):
        # 1. CREATE ZMQ CONTEXT INSIDE THE THREAD TO PREVENT DEADLOCKS
        context = zmq.Context()
        req = None
        sub = None
        
        while self.running:
            if not self.connected:
                try:
                    req = context.socket(zmq.REQ)
                    req.setsockopt(zmq.RCVTIMEO, 1000)
                    req.connect("tcp://127.0.0.1:50020")
                    req.send_string("SUB_PORT")
                    sub_port = req.recv_string()

                    sub = context.socket(zmq.SUB)
                    sub.setsockopt(zmq.RCVTIMEO, 100)
                    sub.connect(f"tcp://127.0.0.1:{sub_port}")
                    sub.setsockopt_string(zmq.SUBSCRIBE, "pupil.1.3d")
                    
                    self.connected = True
                    self.connected_signal.emit(True)
                except Exception as e:
                    print(f"Failed to connect to Pupil Labs: {e}")
                    # Safely close failed sockets before retrying
                    if req: req.close()
                    if sub: sub.close()
                    self.msleep(1000)
                    continue
                    
            try:
                msg_parts = sub.recv_multipart()
                if len(msg_parts) >= 2:
                    payload = msg_parts[1]
                    latest_msg = loads(payload, raw=False)
                    d = latest_msg.get("diameter", None)
                    if d is not None:
                        area = np.pi * (float(d)/2)**2
                        #self.data_queue.put(area)
                    else:
                        area = 0.0
                    norm_pos = latest_msg.get("norm_pos", [0.0, 0.0])
                    px = norm_pos[0]
                    py = norm_pos[1]
                    
                    self.data_queue.put((area, px, py))
            except zmq.Again:
                pass # Normal timeout
            except Exception as e:
                if self.running:
                    print(f"Receiver Warning: {e}")
        
        # 2. CLEANUP MEMORY ON EXIT
        if req: req.close()
        if sub: sub.close()
        context.term()

    def stop(self):
        self.running = False
        self.wait(1500) # Give the thread 1.5 seconds max to die, otherwise force continue!