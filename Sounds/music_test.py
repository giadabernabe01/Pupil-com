import pygame
import time

pygame.mixer.init()


# pygame.mixer.music.play()
pygame.mixer.set_num_channels(1)  # default is 8

bt = pygame.mixer.Sound('/home/berry/Desktop/PyQtGUI/Sounds/MusicMachine/BackingTrack.mp3')

pygame.mixer.Channel(0).play(bt)

time.sleep(10)


notes = ['C2', 'D#2', 'F2', 'G2', 'A#2', 'C3']

# for note in notes:
#     pygame.mixer.Channel(1).play(pygame.mixer.Sound('/home/berry/Desktop/PyQtGUI/Sounds/MusicMachine/' + note + '.mp3'))
#     time.sleep(1)


# while pygame.mixer.music.get_busy():
#     time.sleep(1)


# import vlc

# player = vlc.MediaPlayer()
# player.set_media(vlc.Media('/home/berry/Desktop/PyQtGUI/Sounds/MusicMachine/BackingTrack.mp3'))
# player.play()

# time.sleep(10)

# import sys
# from PyQt5.QtWidgets import QApplication
# from PyQt5.QtCore import QUrl
# from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

# app = QApplication(sys.argv)

# backing_track = QMediaPlayer()
# backing_track.setMedia(QMediaContent(QUrl.fromLocalFile("/home/berry/Desktop/PyQtGUI/Sounds/MusicMachine/BackingTrack.mp3")))
# backing_track.setVolume(75)

# backing_track.play()

# sys.exit(app.exec_())