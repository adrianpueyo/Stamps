"""
labelConnector v2.0 - 09/2023
Lukas Schwabe
Provides context-based UI helpers to setup and navigate Node Connections in Nuke.
Now merged with the base of Stamps, using the Label Connector UI.
"""

__version__ = 2.0

import fnmatch
import math
import re
import textwrap

import nuke
import PySide2.QtCore as QtCore
import PySide2.QtGui as QtGui
import PySide2.QtWidgets as QtGuiWidgets
import stamps

try:
    import stamps_config
except Exception:
    pass

BUTTON = "border-radius: 5px; font: 13px; padding: 4px 7px;"
BUTTON_SELECTED = "border-radius: 5px; font: 13px; font-weight: bold; padding: 4px 7px;"
BUTTON_BORDER_DEFAULT = "border: 1px solid #181818;"
BUTTON_BORDER_HIGHLIGHT = "border: 1px solid #AAAAAA;"
BUTTON_BORDER_SELECTED = "border: 1px solid #C6710C;"
BUTTON_REGULAR_COLOR = 673720575
BUTTON_REGULARDARK_COLOR = "#1c1f22"
BUTTON_REGULARMID_COLOR = "#212329"
BUTTON_HIGHLIGHT_COLOR = "#C6710C"

SEARCHFIELD = "border-radius: 5px; font: 13px; border: 1px solid #181818;"

MAX_COLUMNS_ALL_TAGS = 10
MAX_COLUMNS_ALL_ANCHORS = 12
MAX_CHARS_ANCHOR_BUTTONS = 16  # linebreak after this amount of characters
CONNECTORMINIMUMHEIGHT = 500  # UI minimun height in px

UNDO = nuke.Undo()

_labelConnectorUI = None
_last_used_tag = {"name": "", "is_backdrop_tag": False}

# List of UI colors for the color selection UI
COLOR_LIST = {
    "Red": 1277436927,
    "Orange": 2017657087,
    "Yellow": 2154504703,
    "Green": 793519103,
    "Dark Green": 304619007,
    "Cyan": 592071935,
    "Blue": 556482559,
    "Dark Blue": 320482047,
    "Purple": 975388415,
    "Default": BUTTON_REGULAR_COLOR,
}


class TagBackdropButton(QtGuiWidgets.QPushButton):
    """Class for the buttons on top of the UI that filter the Anchor Buttons by Tags/Backdrops."""

    def __init__(self, text, color="", is_backdrop_tag=False, parent=None):
        """Class for the buttons on top of the UI that filter the Anchor Buttons by Tags/Backdrops.

        Args:
            text (str): Button name
            is_backdrop_tag (bool): True if this is a backdrop tag, False if it's a regular tag.
            parent (QObject, optional): parent widget. Defaults to None.
        """

        super(TagBackdropButton, self).__init__(parent)

        self.color = color or BUTTON_REGULARDARK_COLOR
        self.highlight = BUTTON_HIGHLIGHT_COLOR
        self.selected = False

        self.is_backdrop_tag = is_backdrop_tag

        self.highlighted_style = (
            "QPushButton{background-color:"
            + self.color
            + ";"
            + BUTTON_SELECTED
            + BUTTON_BORDER_HIGHLIGHT
            + "} "
            + "QPushButton:hover{background-color:"
            + self.highlight
            + ";"
            + BUTTON_SELECTED
            + BUTTON_BORDER_HIGHLIGHT
            + "}"
        )

        self.default_style = (
            "QPushButton{background-color:"
            + self.color
            + ";"
            + BUTTON
            + BUTTON_BORDER_DEFAULT
            + "} "
            + "QPushButton:hover{background-color:"
            + self.highlight
            + ";"
            + BUTTON
            + BUTTON_BORDER_DEFAULT
            + "}"
        )

        self.setText(text)
        self.setFixedHeight(45)
        self.setMinimumWidth(145)
        self.setMaximumWidth(200)
        self.setSizePolicy(QtGuiWidgets.QSizePolicy.Expanding, QtGuiWidgets.QSizePolicy.Fixed)

        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setMouseTracking(True)

        self.setStyleDefault()

    def setStyleHighlighted(self):
        """Style used when this filter is active."""

        self.selected = True
        self.setStyleSheet(self.highlighted_style)

    def setStyleDefault(self):
        """default style."""

        self.selected = False
        self.setStyleSheet(self.default_style)


class AnchorButton(QtGuiWidgets.QPushButton):
    """Class for the buttons that represent the Anchors. Emitting a signal when right clicked."""

    rightClicked = QtCore.Signal()

    def __init__(self, anchor, parent=None):
        """Class for the buttons that represent the Anchors. Emitting a signal when right clicked.

        Args:
            anchor (node): Stores the Anchor node, retreiving button name from the title knob.
            parent (QObject, optional): parent widget. Defaults to None.
        """

        super(AnchorButton, self).__init__(parent)

        # self.label = anchor.knob('title').value()
        self.label = anchor.knob("title").value()
        self.wrapped_label = "\n".join(textwrap.wrap(anchor.knob("title").value(), width=MAX_CHARS_ANCHOR_BUTTONS))
        self.anchor = anchor
        self.tags = []
        self.backdrop_tags = dict()
        self.entered = False  # stores if mouse is hovering above button, to change name with keypresses
        self.color = rgb2hex(interface2rgb(getTileColor(anchor)))
        self.highlight = BUTTON_HIGHLIGHT_COLOR

        self.is_highlighted = False  # stores highlight state in case of being selected, to revert correctly

        self.highlighted_style = (
            "QPushButton{background-color:"
            + self.color
            + ";"
            + BUTTON
            + BUTTON_BORDER_HIGHLIGHT
            + "} "
            + "QPushButton:hover{background-color:"
            + self.highlight
            + ";"
            + BUTTON
            + BUTTON_BORDER_HIGHLIGHT
            + "}"
        )

        self.default_style = (
            "QPushButton{background-color:"
            + self.color
            + ";"
            + BUTTON
            + BUTTON_BORDER_DEFAULT
            + "} "
            + "QPushButton:hover{background-color:"
            + self.highlight
            + ";"
            + BUTTON
            + BUTTON_BORDER_DEFAULT
            + "}"
        )

        self.selected_style = (
            "QPushButton{background-color:"
            + self.color
            + ";"
            + BUTTON
            + BUTTON_BORDER_SELECTED
            + "} "
            + "QPushButton:hover{background-color:"
            + self.highlight
            + ";"
            + BUTTON
            + BUTTON_BORDER_SELECTED
            + "}"
        )

        self.setFixedHeight(65)
        self.setMinimumWidth(110)
        self.setMaximumWidth(160)
        self.setSizePolicy(QtGuiWidgets.QSizePolicy.MinimumExpanding, QtGuiWidgets.QSizePolicy.Fixed)

        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setMouseTracking(True)

        self.setTextDefault()
        self.setStyleDefault()

    def mousePressEvent(self, event):
        """Emits a signal when right clicked."""

        if event.button() == QtCore.Qt.RightButton:
            self.rightClicked.emit()
        super(AnchorButton, self).mousePressEvent(event)

    def setStyleHighlighted(self):
        """In case of a search pattern match."""

        self.setStyleSheet(self.highlighted_style)
        self.is_highlighted = True

    def setStyleDefault(self):
        """Default style."""

        self.setStyleSheet(self.default_style)
        self.is_highlighted = False

    def setStyleSelected(self):
        """In case of being selected to create multiple stamps."""

        self.setStyleSheet(self.selected_style)

    def enterEvent(self, event):
        """Change name with modifiers when mouse enters button."""

        keyModifier = QtGuiWidgets.QApplication.keyboardModifiers()

        if keyModifier == QtCore.Qt.ShiftModifier:
            self.setTextSelect()

        elif keyModifier == QtCore.Qt.AltModifier:
            self.setTextModify()

        elif keyModifier == QtCore.Qt.ControlModifier:
            self.setTextJumpAnchor()

        elif keyModifier == QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier:
            self.setTextJumpStamp()

        self.entered = True

    def leaveEvent(self, event):
        """Change reset name when mouse leaves button."""

        self.setTextDefault()
        self.entered = False

    def setTextJumpAnchor(self):
        self.setText("Jump to Anchor\n-\n" + self.wrapped_label)

    def setTextJumpStamp(self):
        self.setText("Jump to Stamp\n-\n" + self.wrapped_label)

    def setTextModify(self):
        self.setText("Colorize...\n-\n" + self.wrapped_label)

    def setTextSelect(self):
        self.setText("Create multiple\n-\n" + self.wrapped_label)

    def setTextDefault(self):
        self.setText(self.wrapped_label)


class ColorButton(QtGuiWidgets.QPushButton):
    """Custom QPushButton to build the UI for Color Picking."""

    def __init__(self, text, color=BUTTON_REGULAR_COLOR, parent=None):
        """Custom QPushButton to build the UI for Color Picking.

        Args:
            text (str): Name of the button.
            color (int, optional): Button color in Nukes int format used in the DAG. Defaults to BUTTON_REGULAR_COLOR.
            parent (QObject, optional): parent widget. Defaults to None.

        """
        super(ColorButton, self).__init__(parent)

        self.setText(text)

        self.setMinimumWidth(100)
        self.setMaximumWidth(150)
        self.setFixedHeight(65)
        self.setSizePolicy(QtGuiWidgets.QSizePolicy.Expanding, QtGuiWidgets.QSizePolicy.Fixed)

        self.interfaceColor = color

        self.color = rgb2hex(interface2rgb(color))  # converting color to hex
        self.highlight = BUTTON_HIGHLIGHT_COLOR  # highlight color for mouse hover
        self.setStyleSheet(
            "QPushButton{background-color:" + self.color + ";" + BUTTON + "} " + "QPushButton:hover{background-color:" + self.highlight + ";" + BUTTON + "}"
        )


class AnchorModel(QtCore.QStringListModel):
    """Class to extend the QAbstractListModel to store the Anchor full name in the model."""

    AnchorRole = QtCore.Qt.UserRole + 1

    def __init__(self, data, parent=None):
        """Class to extend the QAbstractListModel to store the Anchor node in the model.

        Args:
            data (dict): Dict containing {"name": "anchor_title", "anchor": "anchor_name"}
            parent (QObject, optional): parent widget. Defaults to None.
        """
        super(AnchorModel, self).__init__(parent)
        self.setStringList(data)

    def setStringList(self, data):
        """Update the model with the data.

        Args:
            data (dict): Dict containing {"name": "anchor_title", "anchor": "anchor_name"}
        """

        self._data = data

        anchor_names = [d["name"] for d in data]
        super(AnchorModel, self).setStringList(anchor_names)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """Extend the data method to return the Anchor node.

        Args:
            index (PySide2.QtCore.QModelIndex): Index of requested data.
            role (int, optional): Requested data role. Defaults to QtCore.Qt.DisplayRole.

        Returns:
            Any
        """

        if not self._data:
            return super(AnchorModel, self).data(index, role)

        if role == self.AnchorRole:
            return self._data[index.row()]["anchor"]

        return super(AnchorModel, self).data(index, role)

    def roleNames(self):
        roles = super(AnchorModel, self).roleNames()
        roles[self.AnchorRole] = b"anchor"
        return roles


class AnchorAbstractView(QtGuiWidgets.QListView):
    """Extend the QListView to emit a signal when the current index changes."""

    currentIndexChanged = QtCore.Signal()

    def currentChanged(self, current, previous):
        ret = super(AnchorAbstractView, self).currentChanged(current, previous)
        self.currentIndexChanged.emit()
        return ret


class LineEditConnectSelection(QtGuiWidgets.QLineEdit):
    """Custom QLineEdit with combined auto completion. Emitting a signal when the model changes."""

    modelChanged = QtCore.Signal()

    def __init__(self, parent=None):
        """Custom QLineEdit with combined auto completion. Emitting a signal when the model changes.

        Args:
            parent (QObject, optional): parent widget. Defaults to None.
        """

        super(LineEditConnectSelection, self).__init__(parent)

        self.filtered_anchor_name_list = []
        self.setStyleSheet(SEARCHFIELD)

        self.setFixedSize(150, 65)
        self.setSizePolicy(QtGuiWidgets.QSizePolicy.Fixed, QtGuiWidgets.QSizePolicy.Fixed)

        self.completer = QtGuiWidgets.QCompleter(self.filtered_anchor_name_list, self)
        self.completer.setCompletionMode(QtGuiWidgets.QCompleter.UnfilteredPopupCompletion)
        self.completer.setModel(AnchorModel(self.filtered_anchor_name_list))

        self.completer.setPopup(AnchorAbstractView())
        self.completer.popup().setMouseTracking(True)

        self.item_delegate = QtGuiWidgets.QStyledItemDelegate(self)  # this allows hover highlighting in the popup
        self.completer.popup().setItemDelegate(self.item_delegate)
        self.completer.popup().setStyleSheet("QAbstractItemView:item:hover{background-color:#484848;}")

        self.completer.popup().setMinimumHeight(70)
        self.completer.popup().setMinimumWidth(100)
        self.completer.popup().setMaximumWidth(150)
        self.completer.popup().setSizePolicy(
            QtGuiWidgets.QSizePolicy.MinimumExpanding,
            QtGuiWidgets.QSizePolicy.MinimumExpanding,
        )

        self.setCompleter(self.completer)

    def updateCompleterList(self):
        self.completer.model().setStringList(self.filtered_anchor_name_list)

        # the next line fixes a bug where the completer popup would not show up with just one character types
        self.completer.popup().show()

        # this next line fixes a bug where the popup won't show up a second time when no anchor buttons shown
        self.completer.popup().setStyleSheet("QAbstractItemView:item:hover{background-color:#484848;}")

        self.completer.popup().setCurrentIndex(self.completer.model().index(-1, -1))
        self.modelChanged.emit()

    def focusNextPrevChild(self, next):
        """overriding this, to be able to use TAB as ENTER, like the Nuke Node Menu"""

        return False


class LabelConnector(QtGuiWidgets.QWidget):
    """Core LabelConnector UI."""

    def __init__(self, all_anchors):
        """Main Connector UI.

        Args:
            all_anchors (list[node]): A list containing all anchor nodes in the DAG.
        """

        super(LabelConnector, self).__init__()

        self.all_anchors = all_anchors

        self.all_anchors.sort(key=lambda anchor: anchor.knob("title").value())  # sort by title

        self.anchorbuttons_by_tags = dict()
        self.anchor_dict_keys_sorted = list()
        self.anchorbuttons_by_backdrop_tags = dict()

        self.shiftPressed = False
        self.ctrlPressed = False
        self.altPressed = False

        # self.centered_ui = False
        self.changed_viewed_node = False

        global _last_used_tag
        self.current_view_filter = _last_used_tag

        self.tag_buttons = list()
        self.anchor_buttons = list()
        self.current_anchor_grid_buttons = list()
        self.current_anchor_grid_spacers = list()
        self.clicked_anchors_list = list()

        try:  # we have to try this in case no viewer exists or no active input is used
            self.current_viewed_node = nuke.activeViewer().node().input(nuke.activeViewer().activeInput())
        except Exception:
            self.current_viewed_node = None

        try:
            self.active_viewer_input = nuke.activeViewer().activeInput()  # returns None if nothing is connected
        except Exception:
            self.active_viewer_input = None

        if self.active_viewer_input is None:
            # if there was no input, we set it to 1 (which equals to Num2 in Nuke, to avoid the first input)
            self.active_viewer_input = 1

        # main layout
        self.main_widget = QtGuiWidgets.QWidget(self)
        self.main_layout = QtGuiWidgets.QVBoxLayout(self)
        self.quadrant_layout = QtGuiWidgets.QGridLayout(self)
        self.quadrant_layout.setColumnStretch(0, 1)
        self.quadrant_layout.setColumnStretch(1, 0)
        self.quadrant_layout.setRowStretch(0, 0)
        self.quadrant_layout.setRowStretch(1, 1)
        self.quadrant_layout.setRowStretch(2, 0)
        self.quadrant_layout.setSpacing(20)

        # grid for the Tag/Backdrop Buttons
        self.tags_grid = QtGuiWidgets.QGridLayout(self)
        self.tags_grid.setSpacing(5)

        # grid for the Anchor Buttons
        self.anchors_grid = QtGuiWidgets.QGridLayout(self)
        self.anchors_grid.setSpacing(5)

        # vertical layout for the search field and completer
        self.completer_vlayout = QtGuiWidgets.QVBoxLayout(self)
        self.completer_vlayout.setSpacing(5)
        self.completer_vlayout.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)

        self.prepare_all_anchors_and_tags()

        # populate the Tag/Backdrop Buttons grid
        self.populate_tag_grid()

        # search field and completer
        self.input = LineEditConnectSelection()
        self.input.textEdited.connect(self.updateSearchMatches)
        self.input.returnPressed.connect(self.lineEnter)
        self.input.modelChanged.connect(self.highlightButtonsMatchingResults)
        self.input.completer.popup().currentIndexChanged.connect(self.highlightButtonsMatchingResults)
        self.input.completer.popup().pressed.connect(self.lineEnter)

        self.completer_vlayout.addWidget(self.input, QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self.completer_vlayout.addWidget(self.input.completer.popup(), QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self.completer_vlayout.setStretch(0, 0)
        self.completer_vlayout.setStretch(1, 1)

        # populate the Anchor Buttons grid
        self.populate_anchors_grid()

        # explanation label at the bottom
        explanation_label = QtGuiWidgets.QLabel(self)
        explanation_label.setText("shift - multiple | alt - colorize | ctrl(+alt) - jump anchor(stamp) | right-click - preview")
        explanation_label.setStyleSheet("color: #AAAAAA; font: 10px;")
        explanation_label.setWordWrap(True)
        explanation_label.setAlignment(QtCore.Qt.AlignCenter)

        self.quadrant_layout.addLayout(self.tags_grid, 0, 0, QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self.quadrant_layout.addLayout(self.completer_vlayout, 1, 1, QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self.quadrant_layout.addLayout(self.anchors_grid, 1, 0, QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self.quadrant_layout.addWidget(explanation_label, 2, 0, QtCore.Qt.AlignTop)

        # add mainwidget to the layout
        self.main_widget.setLayout(self.quadrant_layout)
        self.main_widget.setSizePolicy(
            QtGuiWidgets.QSizePolicy.MinimumExpanding,
            QtGuiWidgets.QSizePolicy.MinimumExpanding,
        )
        self.main_widget.setObjectName("main_widget")
        self.main_widget.setStyleSheet("QWidget#main_widget{background-color: rgba(45, 45, 45, 0.9);}")
        self.main_layout.addWidget(self.main_widget)

        self.setLayout(self.main_layout)
        self.setSizePolicy(QtGuiWidgets.QSizePolicy.Preferred, QtGuiWidgets.QSizePolicy.Preferred)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        # self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.installEventFilter(self)

        self.input.setFocus()

    def populate_tag_grid(self):
        """Populate the Tag/Backdrop Buttons grid. It balances a split between the two."""

        total_amount_categories = len(self.anchorbuttons_by_tags) + len(self.anchorbuttons_by_backdrop_tags)
        self.anchors_grid_width = min(
            max(
                math.ceil(math.sqrt(float(len(self.all_anchors)))),
                total_amount_categories,
            ),
            MAX_COLUMNS_ALL_ANCHORS - 1,
        )

        column_counter, row_counter = 0, 0

        max_columns = MAX_COLUMNS_ALL_TAGS
        max_anchor_tag_columns = max(
            int((len(self.anchorbuttons_by_tags) / float(total_amount_categories)) * max_columns),
            1,
        )

        tag_button = TagBackdropButton("All Anchors", parent=self)
        tag_button.clicked.connect(self.tag_button_clicked)

        self.tags_grid.addWidget(tag_button, 0, column_counter)
        self.tag_buttons.append(tag_button)
        column_counter += 1

        for tag in sorted(self.anchorbuttons_by_tags.keys()):
            try:
                color_from_pipe = stamps_config.getColorFromTags(tag)
            except Exception:
                color_from_pipe = None

            if color_from_pipe:
                color_from_pipe = rgb2hex(interface2rgb(color_from_pipe))

            tag_button = TagBackdropButton(tag, color=color_from_pipe, parent=self)

            tag_button.clicked.connect(self.tag_button_clicked)
            self.tags_grid.addWidget(tag_button, row_counter, column_counter)
            self.tag_buttons.append(tag_button)
            column_counter += 1
            if column_counter > (max_anchor_tag_columns - 1):
                row_counter += 1
                column_counter = 0

        if self.anchorbuttons_by_backdrop_tags:
            column_counter, row_counter = max_anchor_tag_columns + 1, 0

            for tag in sorted(self.anchorbuttons_by_backdrop_tags.keys()):
                
                backdrop_node = self.anchorbuttons_by_backdrop_tags[tag][0].backdrop_tags[tag] # pick the backdrop node from first anchor
                color_from_backdrop = rgb2hex(interface2rgb(backdrop_node["tile_color"].value()))

                tag_button = TagBackdropButton(tag, color=color_from_backdrop, is_backdrop_tag=True, parent=self)
                tag_button.clicked.connect(self.tag_button_clicked)
                self.tags_grid.addWidget(tag_button, row_counter, column_counter)
                self.tag_buttons.append(tag_button)
                column_counter += 1
                if column_counter > (max_columns):
                    row_counter += 1
                    column_counter = max_anchor_tag_columns + 1

            column_counter, row_counter = max_anchor_tag_columns, 0

            # add a divider line between the two tag categories
            spacer = QtGuiWidgets.QLabel(self)
            spacer.setFixedWidth(1)
            spacer.setSizePolicy(QtGuiWidgets.QSizePolicy.Fixed, QtGuiWidgets.QSizePolicy.Expanding)
            spacer.setStyleSheet("background-color: black; border: 1px solid grey;")

            self.tags_grid.addWidget(spacer, row_counter, column_counter, self.tags_grid.rowCount(), 1)

    def prepare_all_anchors_and_tags(self):
        """create all anchor buttons and store them in a dict by tags."""

        for anchor in self.all_anchors:
            button = AnchorButton(anchor, self)
            button.clicked.connect(self.anchor_button_clicked)
            button.rightClicked.connect(self.anchor_button_right_clicked)

            tags_value = anchor["tags"].value().strip()
            # Remove leading/trailing spaces and separate by commas (with or without spaces)
            tags = [tag for tag in re.split(" *, *", tags_value.strip()) if tag]

            # make sure we don't loose nodes that don't have a Tag at all
            if not tags:
                tags = ["No Tag"]

            backdrop_tags = stamps.backdropTags(anchor)

            button.tags = tags  # store all tags in the button
            button.backdrop_tags = backdrop_tags

            # accumulate all tags in a dict containing all buttons with the same tag
            for tag in tags:
                self.anchorbuttons_by_tags.setdefault(tag, []).append(button)

            for tag in backdrop_tags:
                self.anchorbuttons_by_backdrop_tags.setdefault(tag, []).append(button)

            self.anchor_buttons.append(button)

        self.anchor_dict_keys_sorted = list(self.anchorbuttons_by_tags.keys())
        self.anchor_dict_keys_sorted.sort()

    def populate_anchors_grid(self):
        """Add the Anchor Buttons to the grid."""

        if self.current_anchor_grid_spacers:
            for spacer in self.current_anchor_grid_spacers:
                self.anchors_grid.removeWidget(spacer)
                spacer.setVisible(False)
                spacer.setParent(None)
                spacer.deleteLater()

        self.current_anchor_grid_spacers = []
        self.current_anchor_grid_buttons = []

        if self.current_view_filter["name"] == "":
            for anchor_button in self.anchor_buttons:
                anchor_button.setVisible(False)

        elif self.current_view_filter["name"] == "All Anchors":
            for anchor_button in self.anchor_buttons:
                anchor_button.setVisible(True)

            self.first_tag_to_add = True

            self.add_dict_with_spacer(self.anchorbuttons_by_tags)

        else:
            column_counter, row_counter = 0, 0

            is_backdrop_tag = self.current_view_filter["is_backdrop_tag"]
            query = self.current_view_filter["name"]

            for anchor_button in self.anchor_buttons:
                tags = list(anchor_button.backdrop_tags.keys()) if is_backdrop_tag else anchor_button.tags

                if query in tags:
                    self.anchors_grid.addWidget(anchor_button, row_counter, column_counter)
                    self.current_anchor_grid_buttons.append(anchor_button)
                    anchor_button.setVisible(True)
                    column_counter += 1
                    if column_counter > self.anchors_grid_width:
                        row_counter += 1
                        column_counter = 0

                else:
                    anchor_button.setVisible(False)

            row_counter += 1
            
        for tag_button in self.tag_buttons:
            if tag_button.is_backdrop_tag == self.current_view_filter["is_backdrop_tag"] and tag_button.text() == self.current_view_filter["name"]:
                tag_button.setStyleHighlighted()
            else:
                tag_button.setStyleDefault()

    def add_dict_with_spacer(self, anchor_dict):
        """
        Adds a dict of Anchor Buttons to the grid, adding a spacer line between different tags.
        Anchors are added only once, so if they are in multiple tags, they won't be added twice.
        This gives sort of a "tag" grouping in the UI, with out exploding the UI with too many tags.
        """

        column_counter, row_counter = 0, 0

        for tag in self.anchor_dict_keys_sorted:
            added_spacer = False
            added_tags = False

            # add the buttons
            for anchor_button in anchor_dict[tag]:
                if anchor_button not in self.current_anchor_grid_buttons:
                    if not added_spacer and not self.first_tag_to_add:
                        row_counter = self.add_dict_spacer(row_counter)
                        added_spacer = True

                    added_tags = True

                    self.anchors_grid.addWidget(anchor_button, row_counter, column_counter)
                    self.current_anchor_grid_buttons.append(anchor_button)
                    column_counter += 1
                    if column_counter > self.anchors_grid_width:
                        row_counter += 1
                        column_counter = 0

            if added_tags:
                self.first_tag_to_add = False
                row_counter = row_counter + 1
                column_counter = 0

    def add_dict_spacer(self, row_counter):
        """Adds the spacer line between different tags."""

        # add a vertical spacer before the line
        spacer_before = QtGuiWidgets.QLabel(self)
        spacer_before.setFixedHeight(1)
        spacer_before.setSizePolicy(QtGuiWidgets.QSizePolicy.Expanding, QtGuiWidgets.QSizePolicy.Fixed)
        self.current_anchor_grid_spacers.append(spacer_before)
        self.anchors_grid.addWidget(spacer_before, row_counter, 0, 1, self.anchors_grid_width + 1)
        row_counter += 1

        # add the line
        spacer = QtGuiWidgets.QLabel(self)
        spacer.setFixedHeight(1)
        spacer.setSizePolicy(QtGuiWidgets.QSizePolicy.Expanding, QtGuiWidgets.QSizePolicy.Fixed)
        spacer.setStyleSheet("background-color: black; border: 1px solid grey;")

        self.current_anchor_grid_spacers.append(spacer)
        self.anchors_grid.addWidget(spacer, row_counter, 0, 1, self.anchors_grid_width + 1)
        row_counter += 1

        # add a vertical spacer after the line
        spacer_after = QtGuiWidgets.QLabel(self)
        spacer_after.setFixedHeight(1)
        spacer_after.setSizePolicy(QtGuiWidgets.QSizePolicy.Expanding, QtGuiWidgets.QSizePolicy.Fixed)
        self.current_anchor_grid_spacers.append(spacer_after)
        self.anchors_grid.addWidget(spacer_after, row_counter, 0, 1, self.anchors_grid_width + 1)
        row_counter += 1

        return row_counter

    def resizeEvent(self, event):
        """This gets exectued by Qt when the GUI changed size."""

        # the setMinimumHeight method seems to do weird stuff, so lest just do it manually
        if event.size().height() < CONNECTORMINIMUMHEIGHT:
            self.resize(self.width(), CONNECTORMINIMUMHEIGHT)

        super(LabelConnector, self).resizeEvent(event)

        screen_center = QtGui.QGuiApplication.screenAt(QtGui.QCursor.pos()).geometry().center()

        geo = self.frameGeometry()

        geo.moveCenter(screen_center)
        self.move(geo.topLeft())

    def close(self):
        """Close the UI."""

        try:
            # if viewer input was changed, we set it back to the original input
            if self.changed_viewed_node:
                nuke.activeViewer().node().setInput(self.active_viewer_input, self.current_viewed_node)
        except Exception:
            pass

        super(LabelConnector, self).close()

    QtCore.Slot()

    def updateSearchMatches(self):
        """
        Searches for matches, filling the list for the completer as well as the highlighting.
        It matches patterns like the Nuke Node Menu does. Typing "cp" will match "Crypto People" for example.
        """

        inputText = self.input.text().lower().strip()

        self.input.filtered_anchor_name_list = []
        self.highlighted_buttons = []

        if inputText:
            query = "*" + "*".join(inputText) + "*"

            tempListUnsorted = []

            for button in self.anchor_buttons:
                if fnmatch.fnmatch(button.label.lower(), query):
                    self.highlighted_buttons.append(button)
                    tempListUnsorted.append({"name": button.label, "anchor": button.anchor.name()})

            for n in list(tempListUnsorted):
                if n["name"].startswith(inputText):
                    self.input.filtered_anchor_name_list.append(n)
                    tempListUnsorted.remove(n)

            for n in list(tempListUnsorted):
                if inputText in n["name"]:
                    self.input.filtered_anchor_name_list.append(n)
                    tempListUnsorted.remove(n)

            self.input.filtered_anchor_name_list.extend(tempListUnsorted)

        self.input.updateCompleterList()

        # global _last_used_tag

        # if self.current_view_filter["name"] == "":
        #     self.current_view_filter = {"name": "All Anchors", "is_backdrop_tag": False}
        #     _last_used_tag = self.current_view_filter
        #     self.populate_anchors_grid()

    QtCore.Slot()

    def highlightButtonsMatchingResults(self):
        """
        Highlights all Buttons matching the search result.
        Except there is an entry selected, then just this one.
        """

        inputText = self.input.text()

        for button in self.anchor_buttons:
            button.setStyleDefault()

        if inputText:
            selected_entry = self.input.completer.popup().currentIndex()

            if selected_entry.row() != -1:
                anchor_name = self.input.completer.model().data(selected_entry, QtCore.Qt.UserRole + 1)
            else:
                anchor_name = ""

            for button in self.highlighted_buttons:
                if anchor_name == button.anchor.name() and button.label == inputText:
                    button.setStyleHighlighted()
                    return

            for button in self.highlighted_buttons:
                button.setStyleHighlighted()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()
            return

        elif event.key() == QtCore.Qt.Key_Tab:
            self.lineEnter()
            return

        if event.key() == QtCore.Qt.Key_Control:
            self.ctrlPressed = True

        elif event.key() == QtCore.Qt.Key_Shift:
            self.shiftPressed = True

        elif event.key() == QtCore.Qt.Key_Alt:
            self.altPressed = True

        elif event.key() in [QtCore.Qt.Key_Up, QtCore.Qt.Key_Down]:
            self.input.completer.popup().keyPressEvent(event)

        if event.key() in [
            QtCore.Qt.Key_Alt,
            QtCore.Qt.Key_Shift,
            QtCore.Qt.Key_Control,
        ]:
            self.update_button_text()

    def keyReleaseEvent(self, event):
        if event.key() == QtCore.Qt.Key_Control:
            self.ctrlPressed = False

        elif event.key() == QtCore.Qt.Key_Shift:
            self.shiftPressed = False

            if self.clicked_anchors_list:
                self.create_multiple_wired()
                self.close()

        elif event.key() == QtCore.Qt.Key_Alt:
            self.altPressed = False

        # handle GUI changes for modifier keys
        if event.key() in [
            QtCore.Qt.Key_Alt,
            QtCore.Qt.Key_Shift,
            QtCore.Qt.Key_Control,
        ]:
            self.update_button_text()

    def update_button_text(self):
        """Set anchors button text based on pressed Modifier Keys."""

        if self.shiftPressed and not (self.altPressed or self.ctrlPressed):
            for button in self.anchor_buttons:
                if button.entered:
                    button.setTextSelect()
                    break

        elif self.altPressed and not (self.shiftPressed or self.ctrlPressed):
            for button in self.anchor_buttons:
                if button.entered:
                    button.setTextModify()
                    break

        elif self.ctrlPressed and not (self.shiftPressed or self.altPressed):
            for button in self.anchor_buttons:
                if button.entered:
                    button.setTextJumpAnchor()
                    break

        elif self.ctrlPressed and self.altPressed and not self.shiftPressed:
            for button in self.anchor_buttons:
                if button.entered:
                    button.setTextJumpStamp()
                    break

        else:
            for button in self.anchor_buttons:
                button.setTextDefault()

    QtCore.Slot()

    def anchor_button_clicked(self):
        """Clicking actions based on pressed Modifier Keys"""

        keyModifier = QtGuiWidgets.QApplication.keyboardModifiers()

        if keyModifier == QtCore.Qt.ControlModifier:
            self.jumpKeepingPreviousSelection([self.sender().anchor])

        elif keyModifier == QtCore.Qt.AltModifier:
            self.close()
            showColorSelectionUI([self.sender().anchor])

        elif keyModifier == QtCore.Qt.ShiftModifier:
            anchor_button = self.sender()
            if anchor_button not in self.clicked_anchors_list:
                self.clicked_anchors_list.append(anchor_button)
                anchor_button.setStyleSelected()
            else:
                self.clicked_anchors_list.remove(anchor_button)
                if anchor_button.is_highlighted:
                    anchor_button.setStyleHighlighted()
                else:
                    anchor_button.setStyleDefault()

        elif keyModifier == QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier:
            anchor_button = self.sender()
            stamps.wiredZoomNext(anchor_button.anchor.name(), no_error=True)

        else:
            UNDO.begin("Create Stamp")
            self.create_wired_node(self.sender().anchor)
            UNDO.end()

            self.close()

    QtCore.Slot()

    def anchor_button_right_clicked(self):
        """Set Viewer Input to the clicked Anchor."""

        try:
            if nuke.activeViewer().node().input(self.active_viewer_input) == self.sender().anchor:
                nuke.activeViewer().node().setInput(self.active_viewer_input, self.current_viewed_node)
            else:
                nuke.activeViewer().node().setInput(self.active_viewer_input, self.sender().anchor)
                nuke.activeViewer().activateInput(self.active_viewer_input)

            self.changed_viewed_node = True

        except Exception:
            pass

    def create_wired_node(self, anchor):
        """Create stamp."""

        return stamps.wired(anchor)

    def create_multiple_wired(self):
        """Create multiple stamps and place them in x direction."""

        if self.clicked_anchors_list:
            UNDO.begin("Create Stamps")
            created_nodes = []

            for anchor_button in self.clicked_anchors_list:
                n = self.create_wired_node(anchor_button.anchor)
                created_nodes.append(n)

            xPosFirst = created_nodes[0].xpos()
            yPosFirst = created_nodes[0].ypos()

            for i, node in enumerate(created_nodes):
                node.setXpos(xPosFirst + 120 * i)
                node.setYpos(yPosFirst)
                node.setSelected(True)

            self.clicked_anchors_list = []
            UNDO.end()

    QtCore.Slot()

    def tag_button_clicked(self):
        """Set the current view filter based on the clicked Tag Button."""

        keyModifier = QtGuiWidgets.QApplication.keyboardModifiers()

        if keyModifier == QtCore.Qt.ControlModifier:
            if self.sender().text() == "All Anchors":
                nodes = [button.anchor for button in self.anchor_buttons]
            elif self.sender().is_backdrop_tag:
                nodes = [button.anchor for button in self.anchorbuttons_by_backdrop_tags[self.sender().text()]]
            else:
                nodes = [button.anchor for button in self.anchorbuttons_by_tags[self.sender().text()]]

            self.jumpKeepingPreviousSelection(nodes)

        else:
            global _last_used_tag

            if self.sender().selected:
                self.current_view_filter = {"name": "", "is_backdrop_tag": False}

            else:
                self.current_view_filter = {
                    "name": self.sender().text(),
                    "is_backdrop_tag": self.sender().is_backdrop_tag,
                }

            _last_used_tag = self.current_view_filter

            self.populate_anchors_grid()

    QtCore.Slot()

    def lineEnter(self):
        """After pressing Enter or Tab"""

        if self.input.text() == "":
            # self.close()
            return

        selected_entry = self.input.completer.popup().currentIndex()
        connect_to = ""

        if selected_entry.row() != -1:
            anchor_name = self.input.completer.model().data(selected_entry, QtCore.Qt.UserRole + 1)
            for anchor in self.all_anchors:
                if anchor_name == anchor.name():
                    connect_to = anchor
                    break
        else:
            for anchor in self.all_anchors:
                if self.input.text().lower() == anchor.knob("title").getValue().lower():
                    connect_to = anchor
                    break

        if not connect_to and self.input.filtered_anchor_name_list:
            name_list = [d["name"] for d in self.input.filtered_anchor_name_list]
            for anchor in self.all_anchors:
                if name_list[0].lower() == anchor.knob("title").getValue().lower():
                    connect_to = anchor
                    break

        if connect_to:
            keyModifier = QtGuiWidgets.QApplication.keyboardModifiers()

            if keyModifier == QtCore.Qt.ControlModifier:
                self.jumpKeepingPreviousSelection([connect_to])

            else:
                self.create_wired_node(connect_to)

        self.close()

    def eventFilter(self, object, event):
        """Close the UI if it looses focus."""

        if object == self and event.type() in [
            QtCore.QEvent.WindowDeactivate,
            QtCore.QEvent.FocusOut,
        ]:
            self.create_multiple_wired()
            self.close()
            return True

        return False

    def mousePressEvent(self, event):
        """Close if there was a left click within the UIs geo, but no Button was triggered."""

        if event.button() == QtCore.Qt.LeftButton:
            self.create_multiple_wired()
            self.close()

    def jumpKeepingPreviousSelection(self, nodes):
        """
        Jump to node without destroyng previous selection of nodes

        Args:
            nodes (list): any amount of nuke nodes as list
        """

        if not nodes:
            return

        prevNodes = nuke.selectedNodes()

        for i in prevNodes:
            i.setSelected(False)

        for node in nodes:
            node.setSelected(True)

        nuke.zoomToFitSelected()

        for node in nodes:
            node.setSelected(False)

        for i in prevNodes:
            i.setSelected(True)


class LabelConnectorColorSelection(QtGuiWidgets.QWidget):
    """Color Selection UI."""

    def __init__(self, list_of_anchors):
        """Color Selection UI.

        Args:
            list_of_anchors (list[node]): List of nodes to colorize.
        """
        super(LabelConnectorColorSelection, self).__init__()

        self.list_of_anchors = list_of_anchors
        self.centered_ui = False

        grid = QtGuiWidgets.QGridLayout()
        self.setLayout(grid)
        self.setSizePolicy(QtGuiWidgets.QSizePolicy.Expanding, QtGuiWidgets.QSizePolicy.Expanding)

        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.installEventFilter(self)

        length = int(len(COLOR_LIST) / 2) - 1
        column_counter, row_counter = 0, 0

        for color in COLOR_LIST:
            button = ColorButton(color, COLOR_LIST[color], self)
            button.clicked.connect(self.setColor)
            grid.addWidget(button, row_counter, column_counter)

            column_counter += 1
            if column_counter > length:
                row_counter += 1
                column_counter = 0

    def eventFilter(self, object, event):
        """Close the UI if it looses focus."""

        if object == self and event.type() in [
            QtCore.QEvent.WindowDeactivate,
            QtCore.QEvent.FocusOut,
        ]:
            self.close()
            return True
        return False

    QtCore.Slot()

    def setColor(self):
        """Click on Color Button"""

        color = self.sender().interfaceColor

        if color == BUTTON_REGULAR_COLOR:
            color = int("%02x%02x%02x%02x" % (255, 255, 255, 1), 16)

        UNDO.begin("Set Anchor Color")

        for anchor in self.list_of_anchors:
            anchor.knob("tile_color").setValue(color)

        UNDO.end()

        self.close()

    def resizeEvent(self, event):
        """This gets exectued by Qt once the GUI is drawn. We know the Gui size now and can center it once around the mouse cursor."""

        super(LabelConnectorColorSelection, self).resizeEvent(event)

        if not self.centered_ui:  # set position only once in the beginning
            geo = self.frameGeometry()
            centerTo = QtGui.QCursor.pos()

            # slght offset feels better
            centerTo -= QtCore.QPoint(0, int(geo.height() * 0.1))

            geo.moveCenter(centerTo)
            self.move(geo.topLeft())

            self.centered_ui = True

            self.previous_mouse_pos = QtGui.QCursor.pos()
            self.previous_geo_top_left = geo.center()


def interface2rgb(hexValue):
    """
    Convert a color stored as a 32 bit value as used by nuke for interface colors to normalized rgb values.

    Special thanks to Falk Hofmann for these!
    """

    return [(0xFF & hexValue >> i) / 255.0 for i in [24, 16, 8]]


def rgb2interface(rgb):
    """
    Convert a color stored as rgb values to a 32 bit value as used by nuke for interface colors.
    """

    if len(rgb) == 3:
        rgb = rgb + (255,)

    return int("%02x%02x%02x%02x" % rgb, 16)


def getTileColor(node=None):
    """
    If a node has it's color set automatically, the 'tile_color' knob will return 0.
    If so, this function will scan through the preferences to find the correct color value.
    """

    node = node or nuke.selectedNode()
    interfaceColor = node.knob("tile_color").value()

    if (
        interfaceColor == 0
        or interfaceColor == nuke.defaultNodeColor(node.Class())
        or interfaceColor == 3435973632
        or interfaceColor == int("%02x%02x%02x%02x" % (255, 255, 255, 1), 16)
    ):
        interfaceColor = BUTTON_REGULAR_COLOR

    return interfaceColor


def rgb2hex(rgbaValues):
    """Convert a color stored as normalized rgb values to a hex."""

    if len(rgbaValues) < 3:
        return
    return "#%02x%02x%02x" % (
        int(rgbaValues[0] * 255),
        int(rgbaValues[1] * 255),
        int(rgbaValues[2] * 255),
    )


def hex2rgb(hexColor):
    """Convert a color stored as hex to rgb values."""

    hexColor = hexColor.lstrip("#")
    return tuple(int(hexColor[i : i + 2], 16) for i in (0, 2, 4))


def filter_out_disabled_anchors(all_anchors):
    """Filter out disabled anchors."""

    filtered_anchors = []

    for anchor in all_anchors:
        # if the disable knob doesn't exist, add the anchor as it's an old anchor
        if anchor.knob("disable"):
            if not anchor.knob("disable").value():
                filtered_anchors.append(anchor)
        else:
            filtered_anchors.append(anchor)

    return filtered_anchors


def showConnector(all_anchors):
    """Entry point for the LabelConnector UI."""

    global _labelConnectorUI

    all_anchors = filter_out_disabled_anchors(all_anchors)

    if not all_anchors:
        nuke.message("No Anchors to display.")
        return

    _labelConnectorUI = LabelConnector(all_anchors)
    _labelConnectorUI.show()


def showColorSelectionUI(list_of_anchors):
    """Entry point for the Color Selection UI."""

    global _labelConnectorUI

    _labelConnectorUI = LabelConnectorColorSelection(list_of_anchors)
    _labelConnectorUI.show()
