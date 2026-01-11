"""Qt binding selection for Nuke."""

import nuke


def get_qt_modules():
    if hasattr(nuke, 'NUKE_VERSION_MAJOR') and nuke.NUKE_VERSION_MAJOR >= 16:
        from PySide6 import QtCore, QtGui, QtWidgets
        from PySide6.QtCore import Qt
        return QtCore, QtGui, QtWidgets, Qt
    if nuke.NUKE_VERSION_MAJOR < 11:
        from PySide import QtCore, QtGui, QtGui as QtWidgets
        from PySide.QtCore import Qt
        return QtCore, QtGui, QtWidgets, Qt
    try:
        from PySide2 import QtWidgets, QtGui, QtCore
        from PySide2.QtCore import Qt
        return QtCore, QtGui, QtWidgets, Qt
    except ImportError:
        from Qt import QtCore, QtGui, QtWidgets
        from Qt.QtCore import Qt
        return QtCore, QtGui, QtWidgets, Qt
