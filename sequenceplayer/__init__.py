# -*- coding: utf-8 -*-

"""
Sequence player
"""

import argparse
import logging

from PySide2 import QtCore, QtWidgets
import sequenceplayer.mainwindow as mainwindow

logger = logging.getLogger(__name__)


def show(file_path=None, fps=25.0, live_update=False, **kwargs):
    app = QtCore.QCoreApplication.instance() or QtWidgets.QApplication([])
    dlg = mainwindow.SequencePlayer(file_path=file_path, fps=fps, live_update=live_update, **kwargs)
    dlg.show()
    app.exec_()


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.WARNING)
    parser = argparse.ArgumentParser(description='WOODBLOCK SEQUENCE PLAYER')
    parser.add_argument('--input', type=str, default=None, help='file or sequence path')
    parser.add_argument('--fps', type=float, default=25.0, help='playback frames per second')
    parser.add_argument('--liveupdate', action='store_true', help='check for new sequence files every %.1f seconds' %
                                                                  mainwindow.LIVE_UPDATE_INTERVAL_SECONDS)
    parser.add_argument('--verbose', action='store_true', help='print debug messages')
    parser.print_help()
    args = parser.parse_args()
    show(file_path=args.input, fps=float(args.fps), live_update=args.liveupdate)
