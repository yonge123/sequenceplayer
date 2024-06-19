# -*- coding: utf-8 -*-

"""
Sequence player main window
"""

import glob
import logging
import os
import re

from PySide2 import QtCore, QtWidgets
from PySide2.QtUiTools import QUiLoader


import sequenceplayer.canvas as canvas
import sequenceplayer.sequence as sequence

logger = logging.getLogger(__name__)

LIVE_UPDATE_INTERVAL_SECONDS = 1.0


class SequencePlayer(QtWidgets.QMainWindow):
    def __init__(self, file_path=None, fps=25.0, live_update=False, parent=None):
        super(SequencePlayer, self).__init__(parent)
        self._image_scale = 1
        self._list_update_latest = None
        self._live_update_timer = QtCore.QTimer()
        self._live_update_timer.setInterval(LIVE_UPDATE_INTERVAL_SECONDS * 1000)
        self._playback_timer = QtCore.QTimer()
        self._recent_browser_path = None
        self._sequence = sequence.Sequence(self)
        self.loadUi()
        self.loadSettings()
        self.populateMenu()
        self.wireSignals()
        self.ui.spinbox_fps.setValue(fps)
        self.setPlaybackSpeed()
        self.installEventFilter(self)
        if file_path:
            self.loadSequence(file_path)
            if live_update:
                self.ui.checkbox_live_update.setChecked(True)
            self.playbackStart()

    def loadUi(self):
        self.setWindowTitle('Sequence Player')
        ui_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mainwindow.ui')
        if os.path.isfile(ui_path):
            loader = QUiLoader()
            self.ui = loader.load(ui_path)
            self.ui.checkbox_live_update.setToolTip('Check for new sequence files every %.1f seconds' %
                                                    LIVE_UPDATE_INTERVAL_SECONDS +\
                                                    '(auto-disabled after 1 minute)')
            self.setCentralWidget(self.ui)
            self.image_canvas = canvas.ImageCanvas(self)
            self.image_canvas.setFocusPolicy(QtCore.Qt.StrongFocus)
            self.image_canvas.setAlignment(QtCore.Qt.AlignCenter)
            self.ui.frame_canvas.layout().insertWidget(0, self.image_canvas)
            self.statusBar().showMessage('No sequence loaded.', 0)
        else:
            logger.critical('UI file not found: %s' % ui_path)

    def wireSignals(self):
        self.ui.spinbox_now.valueChanged.connect(lambda: self.setTimelineFrame(self.ui.spinbox_now.value()))
        self.ui.timeline_slider.valueChanged.connect(lambda: self.ui.spinbox_now.setValue(self.timelineFrame()))
        self.ui.timeline_slider.valueChanged.connect(self.updateImage)
        self.ui.timeline_slider.actionTriggered.connect(self.playbackStop)
        self.ui.spinbox_start.editingFinished.connect(self.updateRanges)
        self.ui.spinbox_end.editingFinished.connect(self.updateRanges)
        self.ui.spinbox_fps.valueChanged.connect(self.setPlaybackSpeed)
        self.ui.loop_checkbox.toggled.connect(self.ui.spinbox_in.setVisible)
        self.ui.loop_checkbox.toggled.connect(self.ui.spinbox_out.setVisible)
        self.ui.button_tostart.clicked.connect(self.frameToStart)
        self.ui.button_annotations_previous.clicked.connect(self.annotationsPrevious)
        self.ui.button_decrement.clicked.connect(self.playbackStop)
        self.ui.button_decrement.clicked.connect(self.frameDecrement)
        self.ui.button_playpause.clicked.connect(self.togglePlayPause)
        self.ui.button_increment.clicked.connect(self.playbackStop)
        self.ui.button_increment.clicked.connect(self.frameIncrement)
        self.ui.button_annotations_next.clicked.connect(self.annotationsNext)
        self.ui.button_toend.clicked.connect(self.playbackStop)
        self.ui.button_toend.clicked.connect(self.frameToEnd)
        self._playback_timer.timeout.connect(self.frameIncrement)
        self._live_update_timer.timeout.connect(self.liveUpdate)
        self.ui.checkbox_live_update.toggled.connect(self.liveUpdateToggle)

    def liveUpdate(self):
        if self._sequence.path:
            for file_name in sorted(glob.glob(self._sequence.path.replace('#', '*')), key=lambda x: x.lower(), reverse=True):
                if file_name != self._list_update_latest:
                    self._list_update_latest = file_name
                    for match in re.findall('[0-9][0-9]+', file_name[::-1]):
                        frame = int(match[::-1])
                        start = self.ui.spinbox_in.value()
                        at_last_frame = self.timelineFrame() == self.ui.spinbox_out.value()
                        self.updateRanges(start, frame)
                        if at_last_frame and not self._playback_timer.isActive():
                            self.setTimelineFrame(frame)
                        break
                break

    def liveUpdateToggle(self, start):
        if start:
            self._live_update_timer.start()
            QtCore.QTimer.singleShot(1 * 60 * 1000, lambda: self.ui.checkbox_live_update.setChecked(False))
        else:
            self._live_update_timer.stop()

    def setImageScale(self, scale):
        self._image_scale = max(0.25, min(4, scale))
        if self.updateImage():
            QtCore.QTimer.singleShot(50, lambda: self.resize(10, 10))

    def updateImage(self, position=1):
        position += self.ui.spinbox_start.value()
        sequence_item = self._sequence.getFrame(position)
        if sequence_item:
            image = sequence_item.getImageScaled(self._image_scale)
            if image:
                self.image_canvas.setPixmap(image)
                self.statusBar().showMessage(sequence_item.image_path, 0)
                return image

    def updateRanges(self, start=None, end=None):
        start = start or self.ui.spinbox_start.value()
        end = end or self.ui.spinbox_end.value()
        length = end - start
        self.ui.timeline_slider.setMinimum(0)
        self.ui.timeline_slider.setMaximum(length)
        self.ui.spinbox_in.setMinimum(start)
        self.ui.spinbox_in.setMaximum(end)
        self.ui.spinbox_in.setValue(start)
        self.ui.spinbox_start.setValue(start)
        self.ui.spinbox_out.setMinimum(start)
        self.ui.spinbox_out.setMaximum(end)
        self.ui.spinbox_out.setValue(end)
        self.ui.spinbox_end.setValue(end)

    # def updateCurrent(self):
    #     self.ui.spinbox_now.setValue()

    def timelineFrame(self):
        return self.ui.timeline_slider.value() + self.ui.spinbox_start.value()

    def setTimelineFrame(self, frame):
        self.ui.timeline_slider.setValue(frame - self.ui.spinbox_start.value())

    def frameToStart(self):
        self.playbackStop()
        if self.ui.loop_checkbox.isChecked():
            self.setTimelineFrame(self.ui.spinbox_in.value())
        else:
            self.setTimelineFrame(self.ui.timeline_slider.minimum())

    def frameToEnd(self):
        self.playbackStop()
        if self.ui.loop_checkbox.isChecked():
            self.setTimelineFrame(self.ui.spinbox_out.value())
        else:
            self.setTimelineFrame(self.ui.timeline_slider.maximum())

    def frameIncrement(self):
        if self.ui.loop_checkbox.isChecked():
            if self.timelineFrame() < self.ui.spinbox_out.value():
                self.setTimelineFrame(self.timelineFrame() + 1)
            else:
                self.setTimelineFrame(self.ui.spinbox_in.value())
        else:
            if self.timelineFrame() < self.ui.spinbox_end.value():
                self.setTimelineFrame(self.timelineFrame() + 1)
            else:
                self.playbackStop()

    def frameDecrement(self):
        self.playbackStop()
        if self.ui.loop_checkbox.isChecked():
            if self.timelineFrame() > self.ui.spinbox_in.value():
                self.setTimelineFrame(self.timelineFrame() - 1)
            else:
                self.setTimelineFrame(self.ui.spinbox_out.value())
        else:
            if self.timelineFrame() > self.ui.spinbox_start.value():
                self.setTimelineFrame(self.timelineFrame() + 1)

    def setPlaybackSpeed(self):
        self._playback_timer.setInterval(1000.0 / self.ui.spinbox_fps.value())

    def playbackStart(self):
        self._playback_timer.start()
        self.ui.button_playpause.setText('Pause')

    def playbackStop(self):
        self._playback_timer.stop()
        self.ui.button_playpause.setText('Play')

    def togglePlayPause(self):
        if self._playback_timer.isActive():
            self.playbackStop()
        else:
            if self.ui.spinbox_end.value() > self.ui.spinbox_start.value():
                self.playbackStart()

    def setTimelineMin(self, value):
        self.ui.timeline_slider.setMinimum(value)
        self.ui.spinbox_in.setValue(value)
        self.ui.spinbox_start.setValue(value)

    def setTimelineMax(self, value):
        self.ui.timeline_slider.setMaximum(value)
        self.ui.spinbox_out.setValue(value)
        self.ui.spinbox_end.setValue(value)

    def timelineNow(self, value):
        self.ui.timeline_slider.setValue(value)

    def openFileBrowser(self):
        self.playbackStop()
        type_filter = "Images (*.exr *.gif *.jpg *.jpeg *.png *.svg *.tga);;All Files (*.*)"
        file_path = QtWidgets.QFileDialog.getOpenFileName(self, 'Open Sequence', self._recent_browser_path, type_filter)[0]
        if file_path:
            self.loadSequence(file_path)
        else:
            logger.info('User aborted.')

    def loadSequence(self, file_path, start=None, end=None):
        self._playback_timer.stop()
        file_dir = os.path.abspath(os.path.dirname(file_path))
        self._recent_browser_path = file_dir
        file_name = os.path.basename(file_path)
        if '$F' not in file_name and not re.findall('[0-9][0-9]+', file_name):
            # Single frame
            self._sequence.clear()
            self._sequence.addFrame(1, file_path)
            self.setTimelineMin(1)
            self.setTimelineMax(1)
            self.timelineNow(1)
        else:
            # Sequence
            if '$F4' in file_name:
                prefix, postfix = file_path.split('$F4')
                frame_digits = 4
            elif '$F' in file_name:
                prefix, postfix = file_path.split('$F')
                frame_digits = 1
            else:
                postfix, prefix = [x[::-1] for x in re.split('[0-9][0-9]+', file_name[::-1], 1)]
                frame_digits = len(file_name) - len(prefix) - len(postfix)
                if prefix[-1] == '-':
                    prefix = prefix[0:-1]
            sequence_path = os.path.join(file_dir, prefix + '#' + postfix)
            self._sequence.setPath(sequence_path, frame_digits)
            if not start or not end:
                frames = sorted(glob.glob(sequence_path.replace('#', '-' + '[0-9]' * frame_digits)), reverse=True)
                frames += sorted(glob.glob(sequence_path.replace('#', '[0-9]' * frame_digits)))
                if not start:
                    start = frames[0][-len(postfix) - frame_digits - 1:-len(postfix)]
                    if start[0] != '-':
                        start = start[1::]
                    start = int(start)
                if not end:
                    end = frames[-1][-len(postfix) - frame_digits - 1:-len(postfix)]
                    if end[0] != '-':
                        end = end[1::]
                    end = int(end)
            self.updateRanges(start, end)
            if '$F' not in file_name:
                self.timelineNow(int(file_name[len(prefix):-len(postfix)]))
        self.setImageScale(1.0)

    def refreshSequence(self):
        self._sequence.clear()

    def refreshFrame(self):
        frame = self._sequence.getFrame(self.timelineFrame())
        if frame:
            frame.clear()

    def setLoopIn(self, frame=None):
        self.ui.spinbox_in.setValue(frame or self.timelineFrame())

    def setLoopOut(self, frame=None):
        self.ui.spinbox_out.setValue(frame or self.timelineFrame())

    def annotationsToggle(self):
        logger.warning('TODO: annotations toggle')

    def annotationsPrevious(self):
        logger.warning('TODO: annotations previous')

    def annotationsNext(self):
        logger.warning('TODO: annotations next')

    def populateMenu(self):
        menu_file = self.menuBar().addMenu('&File')
        item = QtWidgets.QAction('&Open...\tCtrl+O', menu_file)
        item.triggered.connect(self.openFileBrowser)
        menu_file.addAction(item)
        item = QtWidgets.QAction('&Refresh Sequence\tCtrl+R', menu_file)
        item.triggered.connect(self.refreshSequence)
        menu_file.addAction(item)
        item = QtWidgets.QAction('&Refresh Frame\tShift+R', menu_file)
        item.triggered.connect(self.refreshFrame)
        menu_file.addAction(item)
        menu_file.addSeparator()
        item = QtWidgets.QAction('&Save Annotations', menu_file)
        item.setEnabled(False)
        menu_file.addAction(item)
        item = QtWidgets.QAction('Save && &Publish Annotations', menu_file)
        item.setEnabled(False)
        menu_file.addAction(item)
        menu_file.addSeparator()
        item = QtWidgets.QAction('&Quit\tCtrl+Q', menu_file)
        item.triggered.connect(self.close)
        menu_file.addAction(item)
        menu_playback = self.menuBar().addMenu('&Playback')
        item = QtWidgets.QAction('Toggle Loop\tCtrl+L', menu_playback)
        item.triggered.connect(self.ui.loop_checkbox.toggle)
        menu_playback.addAction(item)
        menu_playback.addSeparator()
        item = QtWidgets.QAction('Play/Pause\tUp/Space', menu_playback)
        item.triggered.connect(self.togglePlayPause)
        menu_playback.addAction(item)
        item = QtWidgets.QAction('Stop\tDown', menu_playback)
        item.triggered.connect(self.playbackStop)
        menu_playback.addAction(item)
        menu_playback.addSeparator()
        item = QtWidgets.QAction('First Frame\tHome', menu_playback)
        item.triggered.connect(self.frameToStart)
        menu_playback.addAction(item)
        item = QtWidgets.QAction('Last Frame\tEnd', menu_playback)
        item.triggered.connect(self.frameToEnd)
        menu_playback.addAction(item)
        menu_playback.addSeparator()
        item = QtWidgets.QAction('Previous Frame\tLeft', menu_playback)
        item.triggered.connect(self.frameDecrement)
        menu_playback.addAction(item)
        item = QtWidgets.QAction('Next Frame\tRight', menu_playback)
        item.triggered.connect(self.frameIncrement)
        menu_playback.addAction(item)
        menu_playback.addSeparator()
        menu_view = self.menuBar().addMenu('&View')
        # item = QtWidgets.QAction('Toggle &Fullscreen\tCtrl+F', menu_view)
        # menu_view.addAction(item)
        # menu_view.addSeparator()
        item = QtWidgets.QAction('25%\tCtrl+1', menu_view)
        item.triggered.connect(lambda: self.setImageScale(0.25))
        menu_view.addAction(item)
        item = QtWidgets.QAction('50%\tCtrl+2', menu_view)
        item.triggered.connect(lambda: self.setImageScale(0.5))
        menu_view.addAction(item)
        item = QtWidgets.QAction('100%\tCtrl+3', menu_view)
        item.triggered.connect(lambda: self.setImageScale(1.0))
        menu_view.addAction(item)
        item = QtWidgets.QAction('200%\tCtrl+4', menu_view)
        item.triggered.connect(lambda: self.setImageScale(2.0))
        menu_view.addAction(item)
        item = QtWidgets.QAction('400%\tCtrl+5', menu_view)
        item.triggered.connect(lambda: self.setImageScale(4.0))
        menu_view.addAction(item)
        menu_annotations = self.menuBar().addMenu('&Annotations')
        item = QtWidgets.QAction('Show\tCtrl+A', menu_annotations)
        item.setCheckable(True)
        item.setChecked(True)
        menu_annotations.addAction(item)
        menu_annotations.addSeparator()
        item = QtWidgets.QAction('Previous Annotation\tPage Up', menu_annotations)
        item.triggered.connect(self.annotationsPrevious)
        menu_annotations.addAction(item)
        item = QtWidgets.QAction('Next Annotation\tPage Down', menu_annotations)
        item.triggered.connect(self.annotationsNext)
        menu_annotations.addAction(item)
        menu_annotations.addSeparator()
        menu_annotations.addAction(QtWidgets.QAction('Paint\tCtrl+P', menu_annotations))
        menu_annotations.addAction(QtWidgets.QAction('Clear', menu_annotations))

    def eventFilter(self, widget, event):
        if event.type() == QtCore.QEvent.KeyPress:
            key = event.key()
            # if key == QtCore.Qt.Key_Escape:
            #     self.exitFullscreen()
            if key == QtCore.Qt.Key_1:
                self.setImageScale(0.25)
            if key == QtCore.Qt.Key_2:
                self.setImageScale(0.5)
            if key == QtCore.Qt.Key_3:
                self.setImageScale(1)
            if key == QtCore.Qt.Key_4:
                self.setImageScale(2)
            if key == QtCore.Qt.Key_5:
                self.setImageScale(4)
            if event.modifiers() & QtCore.Qt.ControlModifier:
                if key == QtCore.Qt.Key_O:
                    self.openFileBrowser()
                if key == QtCore.Qt.Key_R:
                    self.refreshSequence()
                if key == QtCore.Qt.Key_L:
                    self.ui.loop_checkbox.toggle()
                # if key == QtCore.Qt.Key_F:
                #     self.toggleFullscreen()
                if key == QtCore.Qt.Key_Q:
                    self.close()
                if key == QtCore.Qt.Key_W:
                    self.close()
                if key == QtCore.Qt.Key_A:
                    self.annotationsToggle()
                if key == QtCore.Qt.Key_Left:
                    self.frameToStart()
                if key == QtCore.Qt.Key_Right:
                    self.frameToEnd()
            elif event.modifiers() & QtCore.Qt.ShiftModifier:
                if key == QtCore.Qt.Key_R:
                    self.refreshFrame()
            else:
                if key == QtCore.Qt.Key_I:
                    self.setLoopIn()
                if key == QtCore.Qt.Key_O:
                    self.setLoopOut()
                if key == QtCore.Qt.Key_Space:
                    self.togglePlayPause()
                if key == QtCore.Qt.Key_Up:
                    self.togglePlayPause()
                if key == QtCore.Qt.Key_Left:
                    self.frameDecrement()
                if key == QtCore.Qt.Key_Right:
                    self.frameIncrement()
                if key == QtCore.Qt.Key_Down:
                    self.playbackStop()
                if key == QtCore.Qt.Key_Home:
                    self.frameToStart()
                if key == QtCore.Qt.Key_End:
                    self.frameToEnd()
                if key == QtCore.Qt.Key_PageUp:
                    self.annotationsPrevious()
                if key == QtCore.Qt.Key_PageDown:
                    self.annotationsNext()
            event.accept()
        if event.type() == QtCore.QEvent.Wheel:
            delta = None
            if 'delta' in dir(event):
                delta = event.delta()
            elif 'angleDelta' in dir(event):
                delta = event.angleDelta()
            if delta and delta > 0:
                self.playbackStop()
                self.frameDecrement()
            else:
                self.playbackStop()
                self.frameIncrement()
        return QtWidgets.QMainWindow.eventFilter(self, widget, event)

    def loadSettings(self):
        settings = QtCore.QSettings('Woodblock', 'Woodpipe')
        if settings.contains('SequencePlayer/recent_browser_path'):
            self._recent_browser_path = settings.value('SequencePlayer/recent_browser_path')
        if settings.contains('SequencePlayer/geometry'):
            self.restoreGeometry(settings.value('SequencePlayer/geometry'))

    def saveSettings(self):
        settings = QtCore.QSettings('Woodblock', 'Woodpipe')
        if self.geometry().top() < QtCore.QCoreApplication.instance().desktop().geometry().height():
            settings.setValue('SequencePlayer/geometry', self.saveGeometry())
        if self._recent_browser_path:
            settings.setValue('SequencePlayer/recent_browser_path', self._recent_browser_path)

    def closeEvent(self, event):
        self.saveSettings()
        return super(SequencePlayer, self).closeEvent(event)
