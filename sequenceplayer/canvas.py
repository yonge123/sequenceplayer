# -*- coding: utf-8 -*-

"""
Sequence player canvas
"""

import logging

from PySide2 import QtWidgets

logger = logging.getLogger(__name__)


class ImageCanvas(QtWidgets.QLabel):
    def __init__(self, parent=None):
        QtWidgets.QLabel.__init__(self, parent)
