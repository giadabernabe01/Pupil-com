import numpy as np
from PyQt5 import QtCore, QtWidgets, QtGui
from DataProcessing import AreaFilter

class DigitalEyeWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300,200)
        self.raw_x = 0.5 
        self.raw_y = 0.5
        self.raw_area = 0.0
        self.tracking_active = False

        self.area_to_pixel_scale = 0.4

    def update_eye(self, x, y, area):
        """Called every frame to pass the new coordinates and size"""
        self.raw_x = x
        self.raw_y = y
        self.raw_area = area

        self.tracking_active = (x!=0 and y!=0 and area > 0)
        self.update()

    def paintEvent(self, event):
        """This method mathematically redraws the eye every frame"""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        center_x = width/2.0
        center_y = height/2.0

        synthetic_iris_radius = min(width, height) / 3.0

        if not self.tracking_active:
            painter.setBrush(QtGui.QBrush(QtGui.QColor('#444444')))
            painter.drawEllipse(QtCore.QPointF(center_x,center_y), synthetic_iris_radius, synthetic_iris_radius)
            painter.setPen(QtGui.QPen(QtCore.Qt.red, 3))
            painter.drawLine(int(center_x - 20), int(center_y - 20), int(center_x + 20), int(center_y + 20))
            painter.drawLine(int(center_x + 20), int(center_y - 20), int(center_x - 20), int(center_y + 20))
            return
        
        # Draw a static iris background
        painter.setBrush(QtGui.QBrush(QtGui.QColor("#4a90e2")))
        painter.setPen(QtGui.QPen(QtCore.Qt.black, 2))
        painter.drawEllipse(QtCore.QPointF(center_x, center_y), synthetic_iris_radius, synthetic_iris_radius)

        # MAP GAZE TO PIXELS
        # raw_x goes from 0.0 to 1.0. 
        # (raw_x - 0.5) shifts the range from -0.5 to +0.5.
        # We multiply by the iris radius so looking at the edge of the screen 
        # moves the pupil to the edge of the synthetic iris.
        offset_x = (self.raw_x - 0.5) * synthetic_iris_radius
        offset_y = (self.raw_y - 0.5) * synthetic_iris_radius 
        
        pupil_center_x = center_x + offset_x
        pupil_center_y = center_y + offset_y

        # MAP AREA TO RADIUS
        # Area = pi * r^2 -> r = sqrt(Area/pi). We simplify to sqrt(Area) * scale.
        calculated_pupil_radius = np.sqrt(self.raw_area) * self.area_to_pixel_scale

        final_pupil_radius = max(5.0, min(calculated_pupil_radius, synthetic_iris_radius * 0.9))

        # DRAW THE REAL PUPIL DATA
        painter.setBrush(QtGui.QBrush(QtCore.Qt.black))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawEllipse(QtCore.QPointF(pupil_center_x, pupil_center_y), final_pupil_radius, final_pupil_radius)

        # (Optional) Draw a tiny white reflection dot so it looks like a 3D eye
        #painter.setBrush(QtGui.QBrush(QtCore.Qt.white))
        #painter.drawEllipse(QtCore.QPointF(pupil_center_x + final_pupil_radius*0.3, pupil_center_y - final_pupil_radius*0.3), final_pupil_radius*0.15, final_pupil_radius*0.15)