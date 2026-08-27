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
        
        if device_type == "gazepoint":
            self.amin, self.amax = 50.0, 1000.0 # area is measured in square pixels
            self.ebf_thresh = 100.0
            self.max_array_len = 1000
        else:
            self.amin, self.amax = 1500.0, 10000.0 # area is measured in square pixels
            self.ebf_thresh = 500.0
            self.max_array_len = 2000
        self.fps = fps
        self.area_not_valid = False
        self.area_not_valid_time = 0.0
        self.timeout_triggered = False

        # FILTER INITIALISATIONS
        self.pupil_areas_raw = deque(maxlen=self.max_array_len)
        self.pupil_areas = deque(maxlen=self.max_array_len)
        self.pupil_areas_diffs = deque(maxlen=self.max_array_len)
        self.pupil_areas_ebf = deque(maxlen=self.max_array_len)
        self.pupil_areas_fin = deque(maxlen=self.max_array_len)

        self.reject_count = 0

    def area_filtering(self, new_area):
        self.pupil_areas_raw.append(new_area)
        
        # PHYSIOLOGICAL DIMENSIONS CONTROL
        if self.amin <= new_area <= self.amax:
            self.pupil_areas.append(new_area)
            if self.area_not_valid: 
                self.area_not_valid = False
                self.area_not_valid_time = 0.0
                self.timeout_triggered = False 
        elif len(self.pupil_areas) > 0:
            self.pupil_areas.append(self.pupil_areas[-1]) # Temporarily store previous valid frame
            if not self.area_not_valid: 
                self.area_not_valid = True
                self.area_not_valid_time = time.time()
            else:
                elapsed = time.time() - self.area_not_valid_time
                if elapsed > 5 and not self.timeout_triggered:
                    self.timeout_triggered = True
        else:
            return new_area # No valid data yet, temporarily fill with raw data

        if len(self.pupil_areas) > 0:
            
            # EVENT-BASED FILTER (EBF)
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
                        
                        max_rejects = int(self.fps * 0.8) # Max allowed consecutive rejected frames
                        
                        if self.reject_count < max_rejects:
                            # Short spike/blink: Reject and hold old value
                            self.pupil_areas_ebf[-1] = self.pupil_areas_ebf[-2]
                            self.pupil_areas_diffs[-1] = baseline
                        else:
                            # Prolonged drop: Accept new low value and reset counter
                            self.reject_count = 0
                    else:
                        # Normal physiological movement: Accept and reset counter
                        self.reject_count = 0
                
            # MOVING AVERAGE FILTER
            ma_win = int(self.fps / 2)

            if len(self.pupil_areas_ebf) >= ma_win:
                recent_ebf = list(self.pupil_areas_ebf)[-ma_win:]
                res = np.mean(recent_ebf)
            else:
                res = self.pupil_areas_ebf[-1]
                
            self.pupil_areas_fin.append(res)

            return res
    
    def reset(self):
        """Clears all data buffers and resets timeout flags."""
        self.pupil_areas_raw.clear()
        self.pupil_areas.clear()
        self.pupil_areas_diffs.clear()
        self.pupil_areas_ebf.clear()
        self.pupil_areas_fin.clear()
        self.area_not_valid = False
        self.area_not_valid_time = 0.0
        self.timeout_triggered = False


class ConstrictionMonitor:
    """Class for detecting pupil constriction and recovery events."""
    def __init__(self, fps=130, thresh=0.75, short_dur=0.5, long_dur=3.0, extra_dur=5.0, device_type="gazepoint"):
        self.fps = fps
        self.thresh = thresh
        self.short_dur = short_dur
        self.long_dur = long_dur
        self.extra_dur = extra_dur
        self.device_type = device_type
        self.baseline_buffer = deque(maxlen=round(self.fps*2)) 
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

    def baseline_collection(self, filt_area):
        """Collects initial data to calculate the first threshold baseline."""
        if filt_area is None or filt_area == 0:
            return False
        
        if len(self.baseline_buffer) < self.fps*2:
            self.baseline_buffer.append(filt_area)

    def constriction_detector(self, filt_area):
        """
        Returns:
        0 = No event
        1 = Short constriction 
        2 = Long constriction 
        3 = Extra-long constriction (Keyboard feature)
        """
        if filt_area is None or filt_area == 0:
            return 0

        # UPDATE THRESHOLD
        if len(self.baseline_buffer) > 0:
            current_mean = np.mean(self.baseline_buffer) 
            self.current_sma_thresh = current_mean * self.thresh 
        else:
            self.current_sma_thresh = 0.0

        # LOCK EXIT THRESHOLD IF EVENT IS ONGOING
        if self.short_trigger_handled and self.exit_thresh is not None:
            active_thresh = self.exit_thresh
        else:
            active_thresh = self.current_sma_thresh

        # CHECK FOR CONSTRICTION
        if filt_area < active_thresh:
            
            self.above_ma = (filt_area > self.current_sma_thresh)
            
            if self.drop_start_time is None:
                self.drop_start_time = time.time()
                self.exit_thresh = self.current_sma_thresh
                self.above_ma = False
                self.cross_count = 0
                
            elapsed = time.time() - self.drop_start_time
            
            # MA CROSSING TRACKER
            if self.above_ma and self.cross_count == 0:
                self.cross_count += 1 
            elif not self.above_ma and self.cross_count == 1:
                self.cross_count += 1
                
            # EVENT OVER - RESET
            if self.cross_count == 2:
                self.exit_thresh = None
                self.drop_start_time = None
                self.short_trigger_handled = False
                self.long_trigger_handled = False
                self.extra_trigger_handled = False
                self.baseline_buffer.append(filt_area)
                return 0

            # TRIGGER EVALUATION
            if elapsed >= self.extra_dur:
                if not self.extra_trigger_handled:
                    print(f"Extra constriction detected")
                    self.extra_trigger_handled = True
                    return 3
            elif elapsed >= self.long_dur:
                if not self.long_trigger_handled:
                    print(f"Long constriction detected")
                    self.long_trigger_handled = True
                    return 2
            elif elapsed >= self.short_dur:
                if not self.short_trigger_handled:
                    print("Short constriction detected.")
                    self.short_trigger_handled = True
                    return 1
                    
            self.baseline_buffer.append(filt_area)
            
        else:
            # NO EVENT - RESET FLAGS
            self.exit_thresh = None
            self.drop_start_time = None
            self.short_trigger_handled = False
            self.long_trigger_handled = False
            self.extra_trigger_handled = False
            self.baseline_buffer.append(filt_area)
            
        return 0 


# ---------------------------------------------------------
# RECEIVER: GAZEPOINT
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
        """Pulls all pending tuples from the queue."""
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
                continue 
            except Exception as e:
                if self.running:
                    self.connected = False
                    
        # CLEANUP
        if self.sock:
            self.sock.close()

    def stop(self):
        self.running = False
        self.wait(1500) 

# ---------------------------------------------------------
# RECEIVER: PUPIL LABS CORE
# ---------------------------------------------------------
class PupilLabsReceiver(QtCore.QThread):
    connected_signal = QtCore.pyqtSignal(bool) 

    def __init__(self):
        super().__init__()
        self.running = True
        self.connected = False
        self.data_queue = queue.Queue()

    def get_all_frames(self):
        """Pulls all pending tuples from the queue."""
        frames = []
        while not self.data_queue.empty():
            try:
                frames.append(self.data_queue.get_nowait())
            except queue.Empty:
                break
        return frames
    
    def run(self):
        # THREAD-SAFE ZMQ CONTEXT
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
                    # SAFELY CLOSE FAILED SOCKETS
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
                    else:
                        area = 0.0
                    norm_pos = latest_msg.get("norm_pos", [0.0, 0.0])
                    px = norm_pos[0]
                    py = norm_pos[1]
                    
                    self.data_queue.put((area, px, py))
            except zmq.Again:
                pass 
            except Exception as e:
                if self.running:
                    print(f"Receiver Warning: {e}")
        
        # MEMORY CLEANUP
        if req: req.close()
        if sub: sub.close()
        context.term()

    def stop(self):
        self.running = False
        self.wait(1500)
