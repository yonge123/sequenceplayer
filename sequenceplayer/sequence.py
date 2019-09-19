# -*- coding: utf-8 -*-

"""
Sequence player sequence classes
"""

import logging
import os

from PySide2 import QtCore, QtGui

logger = logging.getLogger(__name__)


def addImageFormatsSupport():
    import PySide2
    QtCore.QCoreApplication.addLibraryPath(os.path.join(os.path.dirname(PySide2.__file__), 'plugins'))


addImageFormatsSupport()


class SequenceFrame(QtCore.QObject):
    def __init__(self, image_path, parent=None):
        QtCore.QObject.__init__(self, parent)
        self.image_path = image_path
        self.image = None

    def clear(self):
        self.image = None

    def getImage(self):
        if not self.image:
            if os.path.exists(self.image_path):
                self.image = QtGui.QPixmap(self.image_path)
        return self.image

    def getImageScaled(self, factor):
        image = self.getImage()
        if image:
            return image.scaled(image.size() * factor, QtCore.Qt.KeepAspectRatio)


class Sequence(QtCore.QObject):
    cleared = QtCore.Signal()
    pathChanged = QtCore.Signal(str)

    def __init__(self, parent=None):
        QtCore.QObject.__init__(self, parent)
        self.path = None
        self.digits = 4
        self.frames = {}

    def clear(self):
        self.frames = {}
        self.cleared.emit()

    def setPath(self, path, digits):
        self.path = path
        self.digits = digits
        self.clear()
        self.pathChanged.emit(path)

    def getFrame(self, frame):
        if self.path:
            if frame not in self.frames:
                if frame < 0:
                    path = self.path.replace('#', '-%0' + str(self.digits) + 'd')
                else:
                    path = self.path.replace('#', '%0' + str(self.digits) + 'd')
                self.frames.update({frame: SequenceFrame(path % abs(frame))})
            return self.frames[frame]
        return None

