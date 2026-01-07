"""Qt UI panels for Stamps."""

import re
from functools import partial

import nuke

from qt_compat import get_qt_modules
import stamps_core as core

QtCore, QtGui, QtWidgets, Qt = get_qt_modules()

unicode = str


class AnchorSelector(QtWidgets.QDialog):
    """
    Panel to select one or more anchors, displaying dropdowns grouped by tags and backdrops.

    TODO:
      - Display three columns similar to an asset loader (with optional border colours).
      - Add the ability to show/hide backdrops (either by toggling their visibility or 'bookmarking').
    """

    def __init__(self):
        super(AnchorSelector, self).__init__()
        self.setWindowTitle("Stamps: Select an Anchor.")
        self.chosen_anchors = []
        self.initUI()
        # Set focus on the custom anchors line edit.
        self.custom_anchors_lineEdit.setFocus()

    def initUI(self):
        # Find all anchors and collect their tags/backdrops.
        self.findAnchorsAndTags()  # Generates: {"Camera1": ["Camera", "New", "Custom1"], "Read": ["2D", "New"]}
        self.custom_chosen = False  # Tracks whether the custom line edit OK was clicked.

        # Header setup.
        self.headerTitle = QtWidgets.QLabel("Anchor Stamp Selector")
        self.headerTitle.setStyleSheet("font-weight:bold;color:#CCCCCC;font-size:14px;")
        self.headerSubtitle = QtWidgets.QLabel(
            "Select an Anchor to make a Stamp for.<br/><b><small style='color:#CCC'>Right click on the OK buttons for multiple selection.</small></b>")
        self.headerSubtitle.setStyleSheet("color:#999")

        self.headerLine = QtWidgets.QFrame()
        self.headerLine.setFrameShape(QtWidgets.QFrame.HLine)
        self.headerLine.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.headerLine.setLineWidth(0)
        self.headerLine.setMidLineWidth(1)

        # Master layout.
        self.master_layout = QtWidgets.QVBoxLayout()
        self.master_layout.addWidget(self.headerTitle)
        self.master_layout.addWidget(self.headerSubtitle)

        # Scroll area for dynamic content.
        self.scroll_content = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QVBoxLayout()
        self.scroll_content.setLayout(self.scroll_layout)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.scroll_content)
        self.scroll.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Sunken)

        # Grid layouts for tag/dropdown items.
        self.grid = QtWidgets.QGridLayout()
        self.lower_grid = QtWidgets.QGridLayout()

        self.scroll_layout.addLayout(self.grid)
        self.scroll_layout.addStretch()
        self.scroll_layout.setContentsMargins(2, 2, 2, 2)
        self.grid.setContentsMargins(2, 2, 2, 2)
        self.grid.setSpacing(5)

        num_tags = len(self._all_tags)

        middleLine = QtWidgets.QFrame()
        middleLine.setStyleSheet("margin-top:20px")
        middleLine.setFrameShape(QtWidgets.QFrame.HLine)
        middleLine.setFrameShadow(QtWidgets.QFrame.Sunken)
        middleLine.setLineWidth(0)
        middleLine.setMidLineWidth(1)

        # If any tags exist, add a header label.
        if len(list(filter(None, self._all_tags))) > 0:
            tags_label = QtWidgets.QLabel("<i>Tags")
            tags_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
            tags_label.setStyleSheet("color:#666;margin:0px;padding:0px;padding-left:3px")
            self.grid.addWidget(tags_label, 0, 0, 1, 3)

        # Build dropdowns for each tag/backdrop.
        for tag_num, tag in enumerate(self._all_tags_and_backdrops):
            if tag == "":
                continue
            if tag_num < num_tags:
                tag_label = QtWidgets.QLabel("<b>{}</b>:".format(tag))
                mode = "tag"
            else:
                tag_label = QtWidgets.QLabel("{}:".format(tag))
                mode = "backdrop"
            if tag_num == num_tags:
                backdrops_label = QtWidgets.QLabel(" <i> Backdrops")
                backdrops_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
                backdrops_label.setStyleSheet("color:#666;margin:0px;padding:0px;padding-left:3px")
                self.grid.addWidget(backdrops_label, tag_num * 10 - 3, 0, 1, 1)

            tag_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

            anchors_dropdown = QtWidgets.QComboBox()
            anchors_dropdown.setMinimumWidth(200)
            for i, cur_name in enumerate(self._all_anchors_names):
                cur_title = self._all_anchors_titles[i]
                title_repeated = self.titleRepeatedForTag(cur_title, tag, mode)
                if mode == "tag":
                    tag_dict = self._anchors_and_tags_tags
                elif mode == "backdrop":
                    tag_dict = self._anchors_and_tags_backdrops
                else:
                    tag_dict = self._anchors_and_tags

                if cur_name not in tag_dict:
                    continue

                if tag in tag_dict[cur_name]:
                    if title_repeated:
                        anchors_dropdown.addItem("{0} ({1})".format(cur_title, cur_name), cur_name)
                    else:
                        anchors_dropdown.addItem(cur_title, cur_name)

            ok_btn = QtWidgets.QPushButton("OK")
            ok_btn.clicked.connect(partial(self.okPressed, dropdown=anchors_dropdown))
            ok_btn.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            ok_btn.setMaximumWidth(ok_btn.sizeHint().width() - 19)
            ok_btn.customContextMenuRequested.connect(partial(self.okRightClicked, anchors_dropdown))

            self.grid.addWidget(tag_label, tag_num * 10 + 1, 0)
            self.grid.addWidget(anchors_dropdown, tag_num * 10 + 1, 1)
            self.grid.addWidget(ok_btn, tag_num * 10 + 1, 2)

        # "All" dropdown.
        tag_num = len(self._all_tags_and_backdrops)
        all_tag_label = QtWidgets.QLabel("<b>all</b>: ")
        all_tag_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.all_anchors_dropdown = QtWidgets.QComboBox()

        all_tag_texts = []  # Display texts.
        all_tag_names = [i for i in self._all_anchors_names]  # Actual anchor names.
        for i, cur_name in enumerate(self._all_anchors_names):
            cur_title = self._all_anchors_titles[i]
            title_repeated = self._all_anchors_titles.count(cur_title)
            if title_repeated > 1:
                all_tag_texts.append("{0} ({1})".format(cur_title, cur_name))
            else:
                all_tag_texts.append(cur_title)
        self.all_tag_sorted = sorted(list(zip(all_tag_texts, all_tag_names)), key=lambda pair: pair[0].lower())

        for text, name in self.all_tag_sorted:
            self.all_anchors_dropdown.addItem(text, name)

        all_ok_btn = QtWidgets.QPushButton("OK")
        all_ok_btn.clicked.connect(partial(self.okPressed, dropdown=self.all_anchors_dropdown))
        all_ok_btn.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        all_ok_btn.customContextMenuRequested.connect(partial(self.okRightClicked, self.all_anchors_dropdown))

        self.lower_grid.addWidget(all_tag_label, tag_num, 0)
        self.lower_grid.addWidget(self.all_anchors_dropdown, tag_num, 1)
        self.lower_grid.addWidget(all_ok_btn, tag_num, 2)
        tag_num += 1

        # "Popular" dropdown.
        tag_num = len(self._all_tags_and_backdrops) + 10
        popular_tag_label = QtWidgets.QLabel("<b>popular</b>: ")
        popular_tag_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.popular_anchors_dropdown = QtWidgets.QComboBox()
        all_tag_texts = []
        all_tag_names = [i for i in self._all_anchors_names]
        all_tag_count = [core.stampCount(i) for i in self._all_anchors_names]

        popular_tag_texts = []
        sorted_names_and_titles = [(x, y) for (_, x, y) in
                                   sorted(list(zip(all_tag_count, self._all_anchors_names, self._all_anchors_titles)),
                                          reverse=True)]
        popular_anchors_names = [x for x, _ in sorted_names_and_titles]
        popular_anchors_titles = [x for _, x in sorted_names_and_titles]
        popular_anchors_count = sorted(all_tag_count, reverse=True)

        for i, cur_name in enumerate(popular_anchors_names):
            cur_title = popular_anchors_titles[i]
            title_repeated = popular_anchors_titles.count(cur_title)
            if title_repeated > 1:
                popular_tag_texts.append("{0} ({1}) (x{2})".format(cur_title, cur_name, str(popular_anchors_count[i])))
            else:
                popular_tag_texts.append("{0} (x{1})".format(cur_title, str(popular_anchors_count[i])))

        for i, text in enumerate(popular_tag_texts):
            self.popular_anchors_dropdown.addItem(text, popular_anchors_names[i])

        popular_ok_btn = QtWidgets.QPushButton("OK")
        popular_ok_btn.clicked.connect(partial(self.okPressed, dropdown=self.popular_anchors_dropdown))
        popular_ok_btn.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        popular_ok_btn.customContextMenuRequested.connect(partial(self.okRightClicked, self.popular_anchors_dropdown))

        self.lower_grid.addWidget(popular_tag_label, tag_num, 0)
        self.lower_grid.addWidget(self.popular_anchors_dropdown, tag_num, 1)
        self.lower_grid.addWidget(popular_ok_btn, tag_num, 2)
        tag_num += 1

        # Custom line edit with completer.
        custom_tag_label = QtWidgets.QLabel("<b>by title</b>: ")
        custom_tag_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.custom_anchors_lineEdit = QtWidgets.QLineEdit()
        self.custom_anchors_completer = QtWidgets.QCompleter([i for i, _ in self.all_tag_sorted], self)
        self.custom_anchors_completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.custom_anchors_completer.setCompletionMode(QtWidgets.QCompleter.InlineCompletion)
        self.custom_anchors_lineEdit.setCompleter(self.custom_anchors_completer)
        if core.context.last_created is not None:
            try:
                title = nuke.toNode(core.context.last_created)["title"].value()
                self.custom_anchors_lineEdit.setPlaceholderText(title)
            except Exception:
                pass

        custom_ok_btn = QtWidgets.QPushButton("OK")
        custom_ok_btn.clicked.connect(partial(self.okCustomPressed, dropdown=self.custom_anchors_lineEdit))
        custom_ok_btn.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        custom_ok_btn.customContextMenuRequested.connect(
            partial(self.okCustomRightClicked, self.custom_anchors_lineEdit))

        self.lower_grid.addWidget(custom_tag_label, tag_num, 0)
        self.lower_grid.addWidget(self.custom_anchors_lineEdit, tag_num, 1)
        self.lower_grid.addWidget(custom_ok_btn, tag_num, 2)

        for combo in [self.all_anchors_dropdown, self.popular_anchors_dropdown]:
            combo.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContentsOnFirstShow)
            combo.setMinimumWidth(200)
            combo.resize(500, combo.sizeHint().height())
            combo.setSizePolicy(QtWidgets.QSizePolicy.Ignored, combo.sizePolicy().verticalPolicy())

        # Finalize layouts.
        self.grid.setColumnStretch(1, 1)
        if len(list(filter(None, self._all_tags_and_backdrops))):
            self.master_layout.addWidget(self.scroll)
        else:
            self.master_layout.addWidget(self.headerLine)
        self.master_layout.addLayout(self.lower_grid)
        self.setLayout(self.master_layout)
        self.resize(self.sizeHint().width(), min(self.sizeHint().height() + 10, 700))

    def keyPressEvent(self, e):
        selectorType = type(self.focusWidget()).__name__  # QComboBox or QLineEdit
        if e.key() == QtCore.Qt.Key_Return:
            if selectorType == "QLineEdit":
                self.okCustomPressed(dropdown=self.focusWidget())
            else:
                self.okPressed(dropdown=self.focusWidget())
        else:
            super(AnchorSelector, self).keyPressEvent(e)

    def findAnchorsAndTags(self):
        """
        Find all Anchor nodes and extract their titles, names, tags, and backdrop tags.

        Populates:
            - self._all_anchors_titles, self._all_anchors_names
            - self._all_tags, self._all_backdrops, self._all_tags_and_backdrops
            - self._anchors_and_tags, self._anchors_and_tags_tags, self._anchors_and_tags_backdrops
        """
        self._all_anchors_titles = []
        self._all_anchors_names = []
        self._all_tags = set()
        self._all_backdrops = set()
        self._backdrop_item_count = {}  # Counts per backdrop.
        self._all_tags_and_backdrops = set()
        self._anchors_and_tags = {}  # {anchor name: set(tags + backdrop tags)}
        self._anchors_and_tags_tags = {}  # {anchor name: set(tags)}
        self._anchors_and_tags_backdrops = {}  # {anchor name: set(backdrop tags)}

        for ni in core.allAnchors():
            try:
                title_value = ni["title"].value().strip()
                name_value = ni.name()
                tags_value = ni["tags"].value()
                tags = re.split(" *, *", tags_value.strip())
                backdrop_tags = core.backdropTags(ni)
                for t in backdrop_tags:
                    self._backdrop_item_count[t] = self._backdrop_item_count.get(t, 0) + 1
                tags_and_backdrops = list(set(tags + backdrop_tags))
                self._all_anchors_titles.append(title_value)
                self._all_anchors_names.append(name_value)
                self._all_tags.update(tags)
                self._all_backdrops.update(backdrop_tags)
                self._all_tags_and_backdrops.update(tags_and_backdrops)
                self._anchors_and_tags[name_value] = set(tags_and_backdrops)
                self._anchors_and_tags_tags[name_value] = set(tags)
                self._anchors_and_tags_backdrops[name_value] = set(backdrop_tags)
            except Exception:
                core.log_exception("Failed to read anchor tags")

        self._all_backdrops = sorted(list(self._all_backdrops), key=lambda x: -self._backdrop_item_count.get(x, 0))
        self._all_tags = sorted(list(self._all_tags), key=str.lower)
        self._all_tags_and_backdrops = self._all_tags + self._all_backdrops

        titles_and_names = list(zip(self._all_anchors_titles, self._all_anchors_names))
        titles_and_names.sort(key=lambda tup: tup[0].upper())
        self._all_anchors_titles = [x for x, y in titles_and_names]
        self._all_anchors_names = [y for x, y in titles_and_names]
        return self._anchors_and_tags

    def titleRepeatedForTag(self, title, tag, mode=""):
        """
        Determine if a title is repeated among anchors for a given tag.

        Args:
            title (str): The anchor title.
            tag (str): The tag or backdrop.
            mode (str): "tag" or "backdrop" determines which subset to check.

        Returns:
            bool: True if the title appears more than once within anchors that have the tag; False otherwise.
        """
        if self._all_anchors_titles.count(title) <= 1:
            return False

        names_with_tag = []
        titles_with_tag = []
        for i, name in enumerate(self._all_anchors_names):
            if mode == "tag":
                if tag in self._anchors_and_tags_tags.get(name, set()):
                    names_with_tag.append(name)
                    titles_with_tag.append(self._all_anchors_titles[i])
            elif mode == "backdrop":
                if tag in self._anchors_and_tags_backdrops.get(name, set()):
                    names_with_tag.append(name)
                    titles_with_tag.append(self._all_anchors_titles[i])
            else:
                if tag in self._anchors_and_tags.get(name, set()):
                    names_with_tag.append(name)
                    titles_with_tag.append(self._all_anchors_titles[i])
        return titles_with_tag.count(title) > 1

    def okPressed(self, dropdown, close=True):
        """
        Called when an OK button is pressed on a dropdown.

        Args:
            dropdown (QComboBox): The dropdown widget.
            close (bool): Whether to close the dialog if selection is valid.
        """
        dropdown_value = dropdown.currentText()
        dropdown_index = dropdown.currentIndex()
        dropdown_data = dropdown.itemData(dropdown_index)

        try:
            match_anchor = nuke.toNode(dropdown_data)
        except Exception:
            match_anchor = None

        self.chosen_value = dropdown_value
        self.chosen_anchor_name = dropdown_data
        if match_anchor is not None:
            self.chosen_anchors.append(match_anchor)
            if close:
                self.accept()
        else:
            nuke.message("There was a problem selecting a valid anchor.")

    def okRightClicked(self, dropdown, position):
        self.okPressed(dropdown, close=False)

    def okCustomPressed(self, dropdown, close=True):
        """
        Called when the custom OK button is pressed from the line edit.

        Args:
            dropdown (QLineEdit): The line edit widget.
            close (bool): Whether to close the dialog if selection is valid.
        """
        written_value = dropdown.text()
        written_lower = written_value.lower().strip()

        found_data = None
        if written_value == "" and core.context.last_created:
            found_data = core.context.last_created
        else:
            for text, name in reversed(self.all_tag_sorted):
                if written_lower == text.lower():
                    found_data = name
                    break
                if written_lower in text.lower():
                    found_data = name
        try:
            match_anchor = nuke.toNode(found_data)
        except Exception:
            nuke.message("Please write a valid name.")
            return

        self.chosen_value = written_value
        self.chosen_anchor_name = found_data
        if match_anchor is not None:
            self.chosen_anchors.append(match_anchor)
            if close:
                self.accept()
        else:
            nuke.message("There was a problem selecting a valid anchor.")

    def okCustomRightClicked(self, dropdown, position):
        self.okCustomPressed(dropdown, close=False)


class AnchorTags_LineEdit(QtWidgets.QLineEdit):
    """
    QLineEdit subclass that emits a custom signal with the current list of tags and the current prefix.
    """
    new_text = QtCore.Signal(object, object)

    def __init__(self, *args):
        super(AnchorTags_LineEdit, self).__init__(*args)
        self.textChanged.connect(self.text_changed)
        self.completer = None

    def text_changed(self, text):
        all_text = unicode(text)
        text = all_text[:self.cursorPosition()]
        prefix = text.split(',')[-1].strip()
        text_tags = list(set([t.strip() for t in all_text.split(',') if t.strip() != '']))
        self.new_text.emit(text_tags, prefix)

    def mouseReleaseEvent(self, e):
        self.text_changed(self.text())

    def complete_text(self, text):
        cursor_pos = self.cursorPosition()
        before_text = unicode(self.text())[:cursor_pos]
        after_text = unicode(self.text())[cursor_pos:]
        prefix_len = len(before_text.split(',')[-1].strip())
        if after_text.strip() == '':
            self.setText('%s%s' % (before_text[:cursor_pos - prefix_len], text))
        else:
            self.setText('%s%s, %s' % (before_text[:cursor_pos - prefix_len], text, after_text))
        self.setCursorPosition(cursor_pos - prefix_len + len(text) + 2)


class TagsCompleter(QtWidgets.QCompleter):
    """
    A completer for tag input that updates its model based on already entered tags.
    """
    insertText = QtCore.Signal(str)

    def __init__(self, all_tags):
        super(TagsCompleter, self).__init__(all_tags)
        self.all_tags = set(all_tags)
        self.activated.connect(self.activated_text)

    def update(self, text_tags, completion_prefix):
        tags = list(self.all_tags - set(text_tags))
        model = QtCore.QStringListModel(tags, self)
        self.setModel(model)
        self.setCompletionPrefix(completion_prefix)
        self.complete()

    def activated_text(self, completion):
        self.insertText.emit(completion)


class NewAnchorPanel(QtWidgets.QDialog):
    """
    Panel to create a new Anchor Stamp on a selected node.
    Allows setting the title (with autocompletion) and tags.
    """

    def __init__(self, windowTitle="New Stamp", default_title="", all_tags=[], default_tags="", parent=None):
        super(NewAnchorPanel, self).__init__(parent)
        self.default_title = default_title
        self.all_tags = all_tags
        self.default_tags = default_tags
        self.setWindowTitle(windowTitle)
        self.initUI()
        self.setFixedSize(self.sizeHint())

    def initUI(self):
        self.createWidgets()
        self.createLayouts()

    def createWidgets(self):
        """Create UI widgets for the new anchor panel."""
        self.newAnchorTitle = QtWidgets.QLabel("New Anchor Stamp")
        self.newAnchorTitle.setStyleSheet("font-weight:bold;color:#CCCCCC;font-size:14px;")
        self.newAnchorSubtitle = QtWidgets.QLabel("Set Stamp title and tag/s (comma separated)")
        self.newAnchorSubtitle.setStyleSheet("color:#999")
        self.newAnchorLine = QtWidgets.QFrame()
        self.newAnchorLine.setFrameShape(QtWidgets.QFrame.HLine)
        self.newAnchorLine.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.newAnchorLine.setLineWidth(0)
        self.newAnchorLine.setMidLineWidth(1)
        self.anchorTitle_label = QtWidgets.QLabel("Title: ")
        self.anchorTitle_edit = QtWidgets.QLineEdit()
        self.anchorTitle_edit.setFocus()
        self.anchorTitle_edit.setText(self.default_title)
        self.anchorTitle_edit.selectAll()
        self.anchorTags_label = QtWidgets.QLabel("Tags: ")
        self.anchorTags_edit = AnchorTags_LineEdit()
        self.anchorTags_edit.setText(self.default_tags)
        self.anchorTags_completer = TagsCompleter(self.all_tags)
        self.anchorTags_completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.anchorTags_completer.insertText.connect(self.anchorTags_edit.complete_text)
        self.anchorTags_edit.new_text.connect(self.anchorTags_completer.update)
        self.anchorTags_completer.setWidget(self.anchorTags_edit)
        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.clickedOk)
        self.buttonBox.rejected.connect(self.clickedCancel)

    def createLayouts(self):
        """Arrange widgets into layouts."""
        self.titleAndTags_layout = QtWidgets.QGridLayout()
        self.titleAndTags_layout.addWidget(self.anchorTitle_label, 0, 0)
        self.titleAndTags_layout.addWidget(self.anchorTitle_edit, 0, 1)
        self.titleAndTags_layout.addWidget(self.anchorTags_label, 1, 0)
        self.titleAndTags_layout.addWidget(self.anchorTags_edit, 1, 1)
        self.master_layout = QtWidgets.QVBoxLayout()
        self.master_layout.addWidget(self.newAnchorTitle)
        self.master_layout.addWidget(self.newAnchorSubtitle)
        self.master_layout.addWidget(self.newAnchorLine)
        self.master_layout.addLayout(self.titleAndTags_layout)
        self.master_layout.addWidget(self.buttonBox)
        self.setLayout(self.master_layout)

    def clickedOk(self):
        """Handle OK button press."""
        self.anchorTitle = self.anchorTitle_edit.text().strip()
        if self.anchorTitle == "" and self.anchorTitle_edit.text() != "":
            self.anchorTitle = self.anchorTitle_edit.text()
        self.anchorTags = self.anchorTags_edit.text().strip()
        self.accept()
        return True

    def clickedCancel(self):
        """Abort new anchor creation."""
        self.reject()


class AddTagsPanel(QtWidgets.QDialog):
    """
    Panel to add tags to the selected stamps or nodes.
    """

    def __init__(self, all_tags=[], default_tags="", parent=None):
        super(AddTagsPanel, self).__init__(parent)
        self.all_tags = all_tags
        self.allNodes = True
        self.default_tags = default_tags
        self.setWindowTitle("Stamps: Add Tags")
        self.initUI()
        self.setFixedSize(self.sizeHint())

    def initUI(self):
        self.createWidgets()
        self.createLayouts()

    def createWidgets(self):
        self.addTagsTitle = QtWidgets.QLabel("Add tag/s")
        self.addTagsTitle.setStyleSheet("font-weight:bold;color:#CCCCCC;font-size:14px;")
        self.addTagsSubtitle = QtWidgets.QLabel("Add tag/s to the selected nodes (comma separated).")
        self.addTagsSubtitle.setStyleSheet("color:#999")
        self.addTagsLine = QtWidgets.QFrame()
        self.addTagsLine.setFrameShape(QtWidgets.QFrame.HLine)
        self.addTagsLine.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.addTagsLine.setLineWidth(0)
        self.addTagsLine.setMidLineWidth(1)
        self.tags_label = QtWidgets.QLabel("Tags: ")
        self.tags_edit = AnchorTags_LineEdit()
        self.tags_edit.setText(self.default_tags)
        self.tags_completer = TagsCompleter(self.all_tags)
        self.tags_completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.tags_completer.insertText.connect(self.tags_edit.complete_text)
        self.tags_edit.new_text.connect(self.tags_completer.update)
        self.tags_completer.setWidget(self.tags_edit)
        self.addTo_Label = QtWidgets.QLabel("Add to: ")
        self.addTo_Label.setToolTip("Which nodes to add tag/s to.")
        self.addTo_All = QtWidgets.QCheckBox("All nodes")
        self.addTo_Stamps = QtWidgets.QCheckBox("Anchor Stamps only")
        self.addTo_All.setChecked(True)
        self.addTo_Stamps.setChecked(False)
        self.addTo_All.stateChanged.connect(self.addTo_Selection)
        self.addTo_Stamps.stateChanged.connect(self.addTo_Selection)
        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.clickedOk)
        self.buttonBox.rejected.connect(self.clickedCancel)

    def createLayouts(self):
        self.titleAndTags_layout = QtWidgets.QGridLayout()
        self.titleAndTags_layout.addWidget(self.tags_label, 0, 0)
        self.titleAndTags_layout.addWidget(self.tags_edit, 0, 1, 1, 2)
        self.titleAndTags_layout.addWidget(self.addTo_Label, 1, 0)
        self.titleAndTags_layout.addWidget(self.addTo_All, 1, 1)
        self.titleAndTags_layout.addWidget(self.addTo_Stamps, 1, 2)
        self.master_layout = QtWidgets.QVBoxLayout()
        self.master_layout.addWidget(self.addTagsTitle)
        self.master_layout.addWidget(self.addTagsSubtitle)
        self.master_layout.addWidget(self.addTagsLine)
        self.master_layout.addLayout(self.titleAndTags_layout)
        self.master_layout.addWidget(self.buttonBox)
        self.setLayout(self.master_layout)

    def addTo_Selection(self):
        if self.addTo_All.isChecked():
            self.addTo_Stamps.setChecked(False)
            self.allNodes = True
        else:
            self.addTo_Stamps.setChecked(True)
            self.allNodes = False

    def clickedOk(self):
        self.tags = self.tags_edit.text().strip()
        self.accept()
        return True

    def clickedCancel(self):
        self.reject()


class RenameTagPanel(QtWidgets.QDialog):
    """
    Panel to rename tags on selected nodes.
    """

    def __init__(self, all_tags=[], parent=None):
        super(RenameTagPanel, self).__init__(parent)
        self.all_tags = all_tags
        self.allNodes = True
        self.setWindowTitle("Stamps: Rename Tag")
        self.initUI()
        self.setFixedSize(self.sizeHint())

    def initUI(self):
        self.createWidgets()
        self.createLayouts()

    def createWidgets(self):
        self.renameTitle = QtWidgets.QLabel("Rename tag")
        self.renameTitle.setStyleSheet("font-weight:bold;color:#CCCCCC;font-size:14px;")
        self.renameSubtitle = QtWidgets.QLabel("Rename a tag on the selected nodes.")
        self.renameSubtitle.setStyleSheet("color:#999")
        self.renameLine = QtWidgets.QFrame()
        self.renameLine.setFrameShape(QtWidgets.QFrame.HLine)
        self.renameLine.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.renameLine.setLineWidth(0)
        self.renameLine.setMidLineWidth(1)
        self.tag_label = QtWidgets.QLabel("Tag: ")
        self.tag_edit = QtWidgets.QComboBox()
        self.tag_edit.addItems(self.all_tags)
        self.replace_label = QtWidgets.QLabel("Replace by: ")
        self.replace_edit = QtWidgets.QLineEdit()
        self.addTo_Label = QtWidgets.QLabel("Rename on: ")
        self.addTo_Label.setToolTip("Which nodes to rename tag/s to.")
        self.addTo_All = QtWidgets.QCheckBox("All nodes")
        self.addTo_Stamps = QtWidgets.QCheckBox("Anchor Stamps only")
        self.addTo_All.setChecked(True)
        self.addTo_Stamps.setChecked(False)
        self.addTo_All.stateChanged.connect(self.addTo_Selection)
        self.addTo_Stamps.stateChanged.connect(self.addTo_Selection)
        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.clickedOk)
        self.buttonBox.rejected.connect(self.clickedCancel)

    def createLayouts(self):
        self.titleAndTags_layout = QtWidgets.QGridLayout()
        self.titleAndTags_layout.addWidget(self.tag_label, 0, 0)
        self.titleAndTags_layout.addWidget(self.tag_edit, 0, 1, 1, 2)
        self.titleAndTags_layout.addWidget(self.replace_label, 1, 0)
        self.titleAndTags_layout.addWidget(self.replace_edit, 1, 1, 1, 2)
        self.titleAndTags_layout.addWidget(self.addTo_Label, 2, 0)
        self.titleAndTags_layout.addWidget(self.addTo_All, 2, 1)
        self.titleAndTags_layout.addWidget(self.addTo_Stamps, 2, 2)
        self.master_layout = QtWidgets.QVBoxLayout()
        self.master_layout.addWidget(self.renameTitle)
        self.master_layout.addWidget(self.renameSubtitle)
        self.master_layout.addWidget(self.renameLine)
        self.master_layout.addLayout(self.titleAndTags_layout)
        self.master_layout.addWidget(self.buttonBox)
        self.setLayout(self.master_layout)

    def addTo_Selection(self):
        if self.addTo_All.isChecked():
            self.addTo_Stamps.setChecked(False)
            self.allNodes = True
        else:
            self.addTo_Stamps.setChecked(True)
            self.allNodes = False

    def clickedOk(self):
        self.tag = self.tag_edit.currentText().strip()
        self.tagReplace = self.replace_edit.text().strip()
        self.accept()
        return True

    def clickedCancel(self):
        self.reject()
