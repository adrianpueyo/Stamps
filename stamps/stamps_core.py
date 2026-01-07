"""
Stamps - Smart node connection system for Nuke
Version: v1.2
Date: May 18 2021

This script implements the Stamps tool (smart node connection system) for Nuke.
It maintains backward compatibility while adding support for Nuke 16's PySide6.
Authors: Adrian Pueyo and Alexey Kuchinski
"""

#------------------------------------------------------
version = "v1.2"
date = "March 3 2025"
#------------------------------------------------------


STAMPS_HELP = "Stamps by Adrian Pueyo and Alexey Kuchinski.\nUpdated " + date
VERSION_TOOLTIP = "Stamps by Adrian Pueyo and Alexey Kuchinski.\nUpdated " + date + "."

import nuke
import nukescripts
import re

from config import load_config
from context import StampsContext
from qt_compat import get_qt_modules

QtCore, QtGui, QtWidgets, Qt = get_qt_modules()

CONFIG = load_config()
context = StampsContext()

STAMP_DEFAULTS = CONFIG.stamp_defaults
anchor_defaults = CONFIG.anchor_defaults
wired_defaults = CONFIG.wired_defaults

DeepExceptionClasses = CONFIG.deep_exception_classes
NodeExceptionClasses = CONFIG.node_exception_classes
ParticleExceptionClasses = CONFIG.particle_exception_classes

StampClasses = CONFIG.stamp_classes
AnchorClassesAlt = CONFIG.anchor_classes_alt
StampClassesAlt = CONFIG.stamp_classes_alt

InputIgnoreClasses = CONFIG.input_ignore_classes
TitleIgnoreClasses = CONFIG.title_ignore_classes
TagsIgnoreClasses = CONFIG.tags_ignore_classes

AnchorClassColors = CONFIG.anchor_class_colors
WiredClassColors = CONFIG.wired_class_colors

STAMPS_SHORTCUT = CONFIG.stamps_shortcut
KEEP_ORIGINAL_TAGS = CONFIG.keep_original_tags


def log_exception(message):
    try:
        nuke.tprint("Stamps: {}".format(message))
    except Exception:
        pass


#################################
### FUNCTIONS INSIDE OF BUTTONS
#################################

def wiredShowAnchor():
    """
    Show the anchor node linked to the current node.
    If the anchor node does not exist, show the first input node (if available).
    """
    n = nuke.thisNode()
    a_name = n.knob("anchor").value()
    if nuke.exists(a_name):
        nuke.show(nuke.toNode(a_name))
    elif n.inputs():
        nuke.show(n.input(0))


def wiredZoomAnchor():
    """
    Zoom the view to center on the anchor node of the current node.
    If the anchor does not exist, zoom to the first input node (if available).
    """
    n = nuke.thisNode()
    a_name = n.knob("anchor").value()
    if nuke.exists(a_name):
        a = nuke.toNode(a_name)
        # Optionally show the node (line commented out in original code)
        # nuke.show(a)
        center = [a.xpos() + a.screenWidth() / 2, a.ypos() + a.screenHeight() / 2]
        nuke.zoom(nuke.zoom(), center)
    elif n.inputs():
        ni = n.input(0)
        center = [ni.xpos() + ni.screenWidth() / 2, ni.ypos() + ni.screenHeight() / 2]
        nuke.zoom(nuke.zoom(), center)


def wiredZoomThis():
    """
    Zoom the view to center on the current node.
    """
    n = nuke.thisNode()
    nuke.zoom(nuke.zoom(), [n.xpos(), n.ypos()])


def wiredStyle(n, style=0):
    """
    Change the style of a wired stamp based on preset styles.

    Args:
        n: The node to style.
        style: The style preset to apply (0 for default, 1 for broken).
    """
    size = wired_defaults.get("note_font_size", 20)
    # Remove any 'Bold' specifier from the font name.
    nf = n["note_font"].value().split(" Bold")[0].split(" bold")[0]
    if style == 0:  # DEFAULT
        n["note_font_size"].setValue(size)
        n["note_font_color"].setValue(0)
        n["note_font"].setValue(nf)
    elif style == 1:  # BROKEN
        n["note_font_size"].setValue(size * 2)
        n["note_font_color"].setValue(4278190335)
        n["note_font"].setValue(nf + " Bold")


def wiredGetStyle(n):
    """
    Check the connection status of the wired stamp and update its style accordingly.

    Returns:
        False if the node is not wired; otherwise, updates the style.
    """
    if not isWired(n):
        return False
    if not n.inputs():
        wiredStyle(n, 1)
    elif not isAnchor(n.input(0)):
        wiredStyle(n, 1)
    elif n["anchor"].value() != n.input(0).name():
        wiredStyle(n, 1)
    else:
        wiredStyle(n, 0)


def wiredTagsAndBackdrops(n, updateSimilar=False):
    """
    Update the tags and backdrop information of wired stamps based on the anchor node.

    Args:
        n: The current node.
        updateSimilar: If True, update all wired nodes sharing the same anchor.
    """
    try:
        a = n.input(0)
        if not a:
            return
        a_tags = a["tags"].value().strip().strip(",")
        a_bd = backdropTags(a)
        an = n.knob("anchor").value()
        ns = [i for i in allWireds() if i.knob("anchor").value() == an] if updateSimilar else [n]

        for node in ns:
            try:
                tags_knob = node.knob("tags")
                bd_knob = node.knob("backdrops")
                # Initially hide the knobs.
                for knob in (tags_knob, bd_knob):
                    knob.setVisible(False)
                if a_tags:
                    tags_knob.setValue("<i>{}</i>".format(a_tags))
                    tags_knob.setVisible(True)
                if a_bd and len(a_bd):
                    bd_knob.setValue("<i>{}</i>".format(",".join(a_bd)))
                    bd_knob.setVisible(True)
            except Exception:
                pass
    except Exception:
        try:
            for knob in (tags_knob, bd_knob):
                knob.setVisible(False)
        except Exception:
            pass


def wiredKnobChanged():
    """
    Callback for when a knob value changes on a wired stamp node.

    Handles reconnection, style updates, and title changes.
    """
    k = nuke.thisKnob()
    kn = k.name()
    # Ignore position changes and specific selection reconnection knobs.
    if kn in ["xpos", "ypos", "reconnect_by_selection_this", "reconnect_by_selection_similar"]:
        return
    n = nuke.thisNode()
    if context.lock_callbacks:
        return
    ni = n.inputs()

    if n.knob("toReconnect") and n.knob("toReconnect").value() and nuke.GUI:
        if not ni:
            if n.knob("auto_reconnect_by_title") and n.knob("auto_reconnect_by_title").value() and n.knob("title"):
                n.knob("auto_reconnect_by_title").setValue(0)
                for a in allAnchors():
                    if a.knob("title") and a["title"].value() == n["title"].value():
                        n.knob("auto_reconnect_by_title").setValue(False)
                        nuke.thisNode().setInput(0, a)
                        n["anchor"].setValue(a.name())
                        wiredStyle(n)
                        return
            try:
                inp = n.knob("anchor").value()
                a = nuke.toNode(inp)
                if a.knob("title") and n.knob("title") and a["title"].value() == n["title"].value():
                    nuke.thisNode().setInput(0, a)
                    wiredStyle(n)
                else:
                    wiredStyle(n, 1)
            except Exception:
                wiredGetStyle(n)
        else:
            try:
                a = n.input(0)
                if isAnchor(a):
                    if a.knob("title") and n.knob("title") and a["title"].value() == n["title"].value():
                        n.knob("anchor").setValue(a.name())
                else:
                    inp = n.knob("anchor").value()
                    a = nuke.toNode(inp)
                    if a.knob("title") and n.knob("title") and a["title"].value() == n["title"].value():
                        nuke.thisNode().setInput(0, a)
                    else:
                        wiredStyle(n, 1)
                        n.setInput(0, None)
            except Exception:
                pass
        n.knob("toReconnect").setValue(False)
    elif not ni:
        if nodeType(n) == "Particle" and not nuke.env["nukex"]:
            return
        wiredStyle(n, 1)
        return
    elif kn == "selected":
        # First activation for the 'selected' knob; ignore subsequent changes.
        return
    elif kn == "inputChange":
        wiredGetStyle(n)
    elif kn == "postage_stamp":
        n["postageStamp_show"].setVisible(True)
        n["postageStamp_show"].setValue(k.value())
    elif kn == "postageStamp_show":
        try:
            n["postage_stamp"].setValue(k.value())
        except Exception:
            n["postageStamp_show"].setVisible(False)
    elif kn == "title":
        kv = k.value()
        if titleIsLegal(kv):
            if nuke.ask("Do you want to update the linked stamps' title?"):
                a = retitleAnchor(n)  # Retitle anchor.
                retitleWired(a)  # Retitle wired stamps linked to the anchor.
                return
        else:
            nuke.message("Please set a valid title.")
        try:
            n["title"].setValue(n["prev_title"].value())
        except Exception:
            pass
    else:
        try:
            n.knob("toReconnect").setValue(False)
            if ni:
                if isAnchor(n.input(0)):
                    if n.knob("title").value() == n.input(0).knob("title").value():
                        n.knob("anchor").setValue(n.input(0).name())
                    elif nuke.ask("Do you want to change the anchor for the current stamp?"):
                        n.knob("anchor").setValue(n.input(0).name())
                        new_title = n.input(0).knob("title").value()
                        n.knob("title").setValue(new_title)
                        n.knob("prev_title").setValue(new_title)
                    else:
                        n.setInput(0, None)
                        try:
                            n.setInput(0, nuke.toNode(n.knob("anchor").value()))
                        except Exception:
                            pass
            wiredGetStyle(n)
        except Exception:
            pass

    if kn == "showPanel":
        wiredTagsAndBackdrops(n)


def wiredOnCreate():
    """
    Initialization function for a wired stamp node upon creation.

    Sets the 'toReconnect' knob and adjusts flags on non-essential knobs.
    """
    n = nuke.thisNode()
    n.knob("toReconnect").setValue(1)
    protected_knobs = [
        'wired_tab', 'identifier', 'lockCallbacks', 'toReconnect', 'title', 'prev_title',
        'tags', 'backdrops', 'anchor', 'line1', 'anchor_label', 'show_anchor', 'zoom_anchor',
        'stamps_label', 'zoomNext', 'selectSimilar', 'space_1', 'reconnect_label', 'reconnect_this',
        'reconnect_similar', 'reconnect_all', 'space_2', 'advanced_reconnection',
        'reconnect_by_title_label', 'reconnect_by_title_this', 'reconnect_by_title_similar',
        'reconnect_by_title_selected', 'reconnect_by_selection_label', 'reconnect_by_selection_this',
        'reconnect_by_selection_similar', 'reconnect_by_selection_selected', 'auto_reconnect_by_title',
        'advanced_reconnection', 'line2', 'buttonHelp', 'version', 'postageStamp_show'
    ]
    for k in n.allKnobs():
        if k.name() not in protected_knobs:
            k.setFlag(0x0000000000000400)


def anchorKnobChanged():
    """
    Callback for when a knob value changes on an anchor node.

    Handles title updates, name changes, and propagates tag changes to linked wired stamps.
    """
    k = nuke.thisKnob()
    kn = k.name()
    if kn in ["xpos", "ypos"]:
        return
    n = nuke.thisNode()
    if kn == "title":
        kv = k.value()
        if titleIsLegal(kv):
            if nuke.ask("Do you want to update the linked stamps' title?"):
                retitleWired(n)  # Retitle wired stamps linked to the anchor.
                return
        else:
            nuke.message("Please set a valid title.")
        try:
            n["title"].setValue(n["prev_title"].value())
        except Exception:
            pass
    elif kn == "name":
        try:
            nn = anchor["prev_name"].value()
        except Exception:
            nn = anchor.name()
        for child in anchorWireds(n):
            child.knob("anchor").setValue(nn)
        n["prev_name"].setValue(n.name())
    elif kn == "tags":
        for ni in allWireds():
            if ni.knob("anchor").value() == n.name():
                wiredTagsAndBackdrops(ni, updateSimilar=True)
                return


def anchorOnCreate():
    """
    Initialization function for an anchor node upon creation.

    Adjusts flags on non-essential knobs and propagates the anchor's name to linked wired stamps.

    Returns:
        None
    """
    n = nuke.thisNode()
    protected_knobs = [
        'anchor_tab', 'identifier', 'title', 'prev_title', 'prev_name', 'showing',
        'tags', 'stamps_label', 'selectStamps', 'reconnectStamps', 'zoomNext',
        'createStamp', 'buttonHelp', 'line1', 'line2', 'version'
    ]
    for k in n.allKnobs():
        if k.name() not in protected_knobs:
            k.setFlag(0x0000000000000400)
    try:
        nn = n["prev_name"].value()
    except Exception:
        nn = n.name()
    for child in anchorWireds(n):
        child.knob("anchor").setValue(nn)
    n["prev_name"].setValue(n.name())
    return

def retitleAnchor(ref=""):
    """
    Retitle the anchor of the current wired stamp to match its title.

    Args:
        ref (nuke.Node): The reference node. If not provided, defaults to nuke.thisNode().

    Returns:
        nuke.Node or None: The updated anchor node, or None if an error occurs.
    """
    if ref == "":
        ref = nuke.thisNode()
    try:
        ref_title = ref["title"].value().strip()
        if ref_title:
            ref_anchor = ref["anchor"].value()
            na = nuke.toNode(ref_anchor)
            for kn in ["title", "prev_title"]:
                na[kn].setValue(ref_title)
            ref["prev_title"].setValue(ref_title)
            return na
    except Exception:
        return None


def retitleWired(anchor=""):
    """
    Retitle all wired stamps connected to the supplied anchor node.

    Args:
        anchor (nuke.Node): The anchor node. If empty, nothing is done.

    Returns:
        bool: True if retitling succeeded, False otherwise.
    """
    if anchor == "":
        return False
    try:
        anchor_title = anchor["title"].value()
        anchor_name = anchor.name()
        for nw in allWireds():
            if nw["anchor"].value() == anchor_name:
                nw["title"].setValue(anchor_title)
                nw["prev_title"].setValue(anchor_title)
        return True
    except Exception:
        return False


def wiredSelectSimilar(anchor_name=""):
    """
    Select all wired stamps that share the same anchor name.

    Args:
        anchor_name (str): The anchor node name. Defaults to the current node's anchor value if not provided.
    """
    if anchor_name == "":
        anchor_name = nuke.thisNode().knob("anchor").value()
    for node in allWireds():
        if node.knob("anchor").value() == anchor_name:
            node.setSelected(True)


def wiredReconnect(n=""):
    """
    Reconnect the given node to its anchor and update its style.

    Args:
        n (nuke.Node): The node to reconnect. Defaults to nuke.thisNode() if not provided.

    Returns:
        bool: True if reconnection succeeded, False otherwise.
    """
    succeeded = True
    if n == "":
        n = nuke.thisNode()
    try:
        anchor = nuke.toNode(n.knob("anchor").value())
        if not anchor:
            succeeded = False
        n.setInput(0, anchor)
    except Exception:
        succeeded = False
    try:
        wiredGetStyle(n)
    except Exception:
        pass
    return succeeded


def wiredReconnectSimilar(anchor_name=""):
    """
    Reconnect similar wired nodes that share the same anchor.

    Args:
        anchor_name (str): The anchor node name. Defaults to the current node's anchor value if not provided.
    """
    if anchor_name == "":
        anchor_name = nuke.thisNode().knob("anchor").value()
    for node in nuke.allNodes():
        if isWired(node) and node.knob("anchor").value() == anchor_name:
            reconnectErrors = 0
            try:
                node.knob("reconnect_this").execute()
            except Exception:
                reconnectErrors += 1
            finally:
                if reconnectErrors > 0:
                    nuke.message("Couldn't reconnect {} nodes".format(str(reconnectErrors)))
            wiredGetStyle(node)


def wiredReconnectAll():
    """
    Reconnect all wired nodes in the script.
    """
    for node in nuke.allNodes():
        if isWired(node):
            reconnectErrors = 0
            try:
                node.knob("reconnect_this").execute()
            except Exception:
                reconnectErrors += 1
            finally:
                if reconnectErrors > 0:
                    nuke.message("Couldn't reconnect {} nodes".format(str(reconnectErrors)))


def wiredReconnectByTitle(title=""):
    """
    Reconnect the current node based on matching title with anchor nodes.

    If exactly one match is found, connect to that anchor.
    If multiple matches are found, require the user to select one.
    If no matches are found, display a message.

    Args:
        title (str): The title to match. Defaults to the current node's title if not provided.
    """
    n = nuke.thisNode()
    if title == "":
        title = n.knob("title").value()
    matches = []
    for node in nuke.allNodes():
        if isAnchor(node) and node.knob("title").value() == title:
            matches.append(node)

    num_matches = len(matches)
    if num_matches == 1:  # One match -> Connect
        anchor = matches[0]
        n["anchor"].setValue(anchor.name())
        n.setInput(0, anchor)
    elif num_matches > 1:
        ns = nuke.selectedNodes()
        if ns and len(ns) == 1 and isAnchor(ns[0]):
            if ns[0].knob("title").value() == title:
                n["anchor"].setValue(ns[0].name())
                n.setInput(0, ns[0])
                n.knob("reconnect_this").execute()
        else:
            nuke.message("More than one Anchor Stamp found with the same title. Please select the one you like in the Node Graph and click this button again.")
    elif num_matches == 0:
        nuke.message("No Anchor Stamps with title '{}' found in the script.".format(title))


def wiredReconnectByTitleSimilar(title=""):
    """
    Reconnect similar wired nodes based on matching title with anchor nodes.

    Args:
        title (str): The title to match. Defaults to the current node's title if not provided.
    """
    n = nuke.thisNode()
    if title == "":
        title = n.knob("title").value()
    matches = []
    for node in allAnchors():
        if node.knob("title").value() == title:
            matches.append(node)

    num_matches = len(matches)
    if num_matches == 0:
        nuke.message("No Anchor Stamps with title '{}' found in the script.".format(title))
        return

    anchor_name = n.knob("anchor").value()
    siblings = [node for node in nuke.allNodes() if isWired(node) and node.knob("anchor").value() == anchor_name]

    if num_matches == 1:  # One match -> Connect
        anchor = matches[0]
        for s in siblings:
            s["anchor"].setValue(anchor.name())
            s.setInput(0, anchor)
            wiredStyle(s, 0)
            s.knob("reconnect_this").execute()
    elif num_matches > 1:
        ns = nuke.selectedNodes()
        if ns and len(ns) == 1 and isAnchor(ns[0]):
            if ns[0].knob("title").value() == title:
                for s in siblings:
                    s["anchor"].setValue(ns[0].name())
                    s.setInput(0, ns[0])
                    wiredStyle(s, 0)
                    s.knob("reconnect_this").execute()
        else:
            nuke.message("More than one Anchor Stamp found with the same title. Please select the one you like in the Node Graph and click this button again.")


def wiredReconnectByTitleSelected():
    """
    Reconnect selected wired nodes based on matching title with anchor nodes.
    Only processes wired nodes.
    """
    ns = nuke.selectedNodes()
    ns = [node for node in ns if isWired(node)]

    for n in ns:
        title = n.knob("title").value()
        matches = []
        for node in allAnchors():
            if node.knob("title").value() == title:
                matches.append(node)

        if len(matches) == 1:  # One match -> Connect
            anchor = matches[0]
            n["anchor"].setValue(anchor.name())
            n.setInput(0, anchor)
            wiredStyle(n, 0)
            n.knob("reconnect_this").execute()


def wiredReconnectBySelection():
    """
    Reconnect the current node using a selected Anchor Stamp.
    """
    n = nuke.thisNode()
    ns = nuke.selectedNodes()

    if not ns:
        nuke.message("Please select an Anchor Stamp first.")
    elif len(ns) > 1:
        nuke.message("Multiple nodes selected, please select only one Anchor Stamp.")
    else:
        if not isAnchor(ns[0]):
            nuke.message("Please select an Anchor Stamp.")
        else:
            context.lock_callbacks = True
            n["anchor"].setValue(ns[0].name())
            n["title"].setValue(ns[0]["title"].value())
            n.setInput(0, ns[0])
            wiredGetStyle(n)
            context.lock_callbacks = False
            n.knob("reconnect_this").execute()


def wiredReconnectBySelectionSimilar():
    """
    Reconnect similar wired nodes using a selected Anchor Stamp.
    """
    n = nuke.thisNode()
    ns = nuke.selectedNodes()

    if not ns:
        nuke.message("Please select an Anchor Stamp first.")
    elif len(ns) > 1:
        nuke.message("Multiple nodes selected, please select only one Anchor Stamp.")
    elif not isAnchor(ns[0]):
        nuke.message("Please select an Anchor Stamp.")
    else:
        anchor_name = n.knob("anchor").value()
        siblings = [node for node in nuke.allNodes() if isWired(node) and node.knob("anchor").value() == anchor_name]
        for s in siblings:
            context.lock_callbacks = True
            s["anchor"].setValue(ns[0].name())
            s["title"].setValue(ns[0]["title"].value())
            s.setInput(0, ns[0])
            wiredStyle(s, 0)
            context.lock_callbacks = False
            s.knob("reconnect_this").execute()


def wiredReconnectBySelectionSelected():
    """
    Reconnect multiple wired nodes to a selected Anchor Stamp.
    Requires one Anchor plus one or more Stamps to be selected.
    """
    n = nuke.thisNode()
    ns = nuke.selectedNodes()

    if not ns:
        nuke.message("Please select one Anchor plus one or more Stamps first.")
        return

    anchors = []
    stamps = []
    for node in ns:
        if isAnchor(node):
            anchors.append(node)
        if isWired(node):
            stamps.append(node)

    if len(anchors) != 1:
        nuke.message("Please select one Anchor, plus one or more Stamps.")
        return
    else:
        anchor = anchors[0]

    if not stamps:
        nuke.message("Please, also select one or more Stamps that you want to reconnect to the selected Anchor.")

    for s in stamps:
        context.lock_callbacks = True
        s["anchor"].setValue(anchor.name())
        s["title"].setValue(anchor["title"].value())
        s.setInput(0, anchor)
        wiredStyle(s, 0)
        context.lock_callbacks = False
        s.knob("reconnect_this").execute()


def anchorReconnectWired(anchor=""):
    """
    Reconnect all wired nodes associated with the given anchor node.

    Args:
        anchor (nuke.Node): The anchor node. Defaults to nuke.thisNode() if not provided.
    """
    if anchor == "":
        anchor = nuke.thisNode()
    anchor_name = anchor.name()
    for node in allWireds():
        if node.knob("anchor").value() == anchor_name:
            reconnectErrors = 0
            try:
                node.setInput(0, anchor)
            except Exception:
                reconnectErrors += 1
            finally:
                if reconnectErrors > 0:
                    nuke.message("Couldn't reconnect {} nodes".format(str(reconnectErrors)))


def wiredZoomNext(anchor_name=""):
    """
    Zoom to the next wired stamp associated with the given anchor.
    Cycles through wired stamps based on the 'showing' knob value.

    Args:
        anchor_name (str): The anchor node name. Defaults to the current node's anchor value if not provided.
    """
    if anchor_name == "":
        anchor_name = nuke.thisNode().knob("anchor").value()
    anchor = nuke.toNode(anchor_name)
    showing_knob = anchor.knob("showing")
    showing_value = showing_knob.value()
    i = 0
    for node in allWireds():
        if node.knob("anchor").value() == anchor_name:
            if i == showing_value:
                center = [node.xpos() + node.screenWidth() / 2, node.ypos() + node.screenHeight() / 2]
                nuke.zoom(1.5, center)
                showing_knob.setValue(i + 1)
                return
            i += 1
    showing_knob.setValue(0)
    nuke.message("Couldn't find any more similar wired stamps.")


def anchorSelectWireds(anchor=""):
    """
    Select all wired stamps associated with the given anchor.

    Args:
        anchor (nuke.Node or str): The anchor node. If empty, attempts to use the currently selected node.
    """
    if anchor == "":
        try:
            anchor = nuke.selectedNode()
        except Exception:
            return
    if isAnchor(anchor):
        anchor.setSelected(False)
        wiredSelectSimilar(anchor.name())


def anchorWireds(anchor=""):
    """
    Returns a list of wired stamps (children) connected to the specified anchor.

    Args:
        anchor (nuke.Node or str): The anchor node. If empty, attempts to use the currently selected node.

    Returns:
        list: A list of wired nodes connected to the anchor, or an empty list if none.
    """
    if anchor == "":
        try:
            anchor = nuke.selectedNode()
        except Exception:
            return []
    if isAnchor(anchor):
        try:
            nn = anchor["prev_name"].value()
        except Exception:
            nn = anchor.name()
        children = [node for node in allWireds() if node.knob("anchor").value() == nn]
        return children
    return []


# Code snippets used for onCreate and reconnection actions.
wiredOnCreate_code = """if nuke.GUI:
    try:
        import stamps; stamps.wiredOnCreate()
    except Exception:
        pass
"""

wiredReconnectToTitle_code = """n = nuke.thisNode()
try:
    nt = n.knob("title").value()
    for a in nuke.allNodes():
        if a.knob("identifier").value() == "anchor" and a.knob("title").value() == nt:
            n.setInput(0, a)
            break
except Exception:
    nuke.message("Unable to reconnect.")
"""

wiredReconnect_code = """n = nuke.thisNode()
try:
    n.setInput(0, nuke.toNode(n.knob("anchor").value()))
except Exception:
    nuke.message("Unable to reconnect.")
try:
    import stamps
    stamps.wiredGetStyle(n)
except Exception:
    pass
"""


#################################
### STAMP, ANCHOR, WIRED CREATION FUNCTIONS
#################################

def anchor(title="", tags="", input_node="", node_type="2D"):
    """
    Create an Anchor Stamp node with default settings and UI knobs.

    Args:
        title (str): The display title for the anchor.
        tags (str): Comma-separated tags for filtering/search.
        input_node: Not used in this version.
        node_type (str): The type of node ("2D" is default).

    Returns:
        nuke.Node: The created anchor node.
    """
    try:
        n = nuke.createNode(AnchorClassesAlt[node_type])
    except Exception:
        try:
            n = nuke.createNode(StampClasses[node_type])
        except Exception:
            n = nuke.createNode("NoOp")
    name = getAvailableName("Anchor", rand=True)
    n["name"].setValue(name)

    # Set default knob values.
    for knob_name, value in anchor_defaults.items():
        try:
            n.knob(knob_name).setValue(value)
        except Exception:
            pass

    if node_type in AnchorClassColors:
        try:
            n["tile_color"].setValue(AnchorClassColors[node_type])
        except Exception:
            pass

    for k in n.allKnobs():
        k.setFlag(0x0000000000000400)

    # Create main UI knobs.
    anchorTab_knob = nuke.Tab_Knob('anchor_tab', 'Anchor Stamp')
    identifier_knob = nuke.Text_Knob('identifier', 'identifier', 'anchor')
    identifier_knob.setVisible(False)
    title_knob = nuke.String_Knob('title', 'Title:', title)
    title_knob.setTooltip("Displayed name on the Node Graph for this Stamp and its Anchor.\n"
                          "IMPORTANT: This is only for display purposes, and is different from the internal node name.")
    prev_title_knob = nuke.Text_Knob('prev_title', '', title)
    prev_title_knob.setVisible(False)
    prev_name_knob = nuke.Text_Knob('prev_name', '', name)
    prev_name_knob.setVisible(False)
    showing_knob = nuke.Int_Knob('showing', '', 0)
    showing_knob.setVisible(False)
    tags_knob = nuke.String_Knob('tags', 'Tags', tags)
    tags_knob.setTooltip("Comma-separated tags to help find this Anchor via the Stamp Selector.")

    for knob in [anchorTab_knob, identifier_knob, title_knob, prev_title_knob, prev_name_knob, showing_knob, tags_knob]:
        n.addKnob(knob)

    n.addKnob(nuke.Text_Knob("line1", "", ""))  # Separator line.

    stampsLabel_knob = nuke.Text_Knob('stamps_label', 'Stamps:', " ")
    stampsLabel_knob.setFlag(nuke.STARTLINE)

    # Create buttons.
    buttonSelectStamps = nuke.PyScript_Knob("selectStamps", "select",
                                            "stamps.wiredSelectSimilar(nuke.thisNode().name())")
    buttonSelectStamps.setTooltip("Select all of this Anchor's Stamps.")
    buttonReconnectStamps = nuke.PyScript_Knob("reconnectStamps", "reconnect", "stamps.anchorReconnectWired()")
    buttonReconnectStamps.setTooltip("Reconnect all of this Anchor's Stamps.")
    buttonZoomNext = nuke.PyScript_Knob("zoomNext", "zoom next", "stamps.wiredZoomNext(nuke.thisNode().name())")
    buttonZoomNext.setTooltip("Navigate to this Anchor's next Stamp on the Node Graph.")
    buttonCreateStamp = nuke.PyScript_Knob("createStamp", "new", "stamps.stampCreateWired(nuke.thisNode())")
    buttonCreateStamp.setTooltip("Create a new Stamp for this Anchor.")

    for knob in [stampsLabel_knob, buttonCreateStamp, buttonSelectStamps, buttonReconnectStamps, buttonZoomNext]:
        n.addKnob(knob)

    # Version information and help.
    n.addKnob(nuke.Text_Knob("line2", "", ""))
    buttonHelp = nuke.PyScript_Knob("buttonHelp", "Help", "stamps.showHelp()")
    version_knob = nuke.Text_Knob('version', ' ',
                                  '<a href="http://www.nukepedia.com/gizmos/other/stamps" '
                                  'style="color:#666;text-decoration: none;">'
                                  '<span style="color:#666"><big>Stamps {}</big></span></a>'.format(version))
    version_knob.setTooltip(VERSION_TOOLTIP)
    version_knob.clearFlag(nuke.STARTLINE)
    for knob in [buttonHelp, version_knob]:
        n.addKnob(knob)
    n["help"].setValue(STAMPS_HELP)

    return n


def wired(anchor):
    """
    Create a Wired Stamp node linked to the supplied Anchor.

    Args:
        anchor (nuke.Node): The anchor node to which this wired stamp is connected.

    Returns:
        nuke.Node: The created wired stamp node.
    """
    context.last_created = anchor.name()

    node_type = nodeType(realInput(anchor))
    try:
        n = nuke.createNode(StampClassesAlt[node_type])
    except Exception:
        try:
            n = nuke.createNode(StampClasses[node_type])
        except Exception:
            n = nuke.createNode("NoOp")
    n["name"].setValue(getAvailableName("Stamp"))

    # Set default knob values.
    for knob_name, value in wired_defaults.items():
        try:
            n[knob_name].setValue(value)
        except Exception:
            pass

    for k in n.allKnobs():
        k.setFlag(0x0000000000000400)

    if node_type in WiredClassColors:
        n["tile_color"].setValue(WiredClassColors[node_type])
    n["onCreate"].setValue(wiredOnCreate_code)

    # Create inner functionality knobs.
    wiredTab_knob = nuke.Tab_Knob('wired_tab', 'Wired Stamp')
    identifier_knob = nuke.Text_Knob('identifier', 'identifier', 'wired')
    identifier_knob.setVisible(False)
    lock_knob = nuke.Int_Knob('lockCallbacks', '', 0)
    lock_knob.setVisible(False)
    toReconnect_knob = nuke.Boolean_Knob("toReconnect")
    toReconnect_knob.setVisible(False)
    title_knob = nuke.String_Knob('title', 'Title:', anchor["title"].value())
    title_knob.setTooltip("Displayed name on the Node Graph for this Stamp and its Anchor.")
    prev_title_knob = nuke.Text_Knob('prev_title', '', anchor["title"].value())
    prev_title_knob.setVisible(False)
    tags_knob = nuke.Text_Knob('tags', 'Tags:', " ")
    tags_knob.setTooltip("Tags of this stamp's Anchor. Click 'show anchor' to change them.")
    backdrops_knob = nuke.Text_Knob('backdrops', 'Backdrops:', " ")
    backdrops_knob.setTooltip("Labels of backdrop nodes that contain this stamp's Anchor.")
    postageStamp_knob = nuke.Boolean_Knob("postageStamp_show", "postage stamp")
    postageStamp_knob.setTooltip("Enable the postage stamp thumbnail for this node.")
    postageStamp_knob.setFlag(nuke.STARTLINE)
    postageStamp_knob.setVisible("postage_stamp" in n.knobs() and nodeType(n) == "2D")

    anchor_knob = nuke.String_Knob('anchor', 'Anchor', anchor.name())

    for knob in [wiredTab_knob, identifier_knob, lock_knob, toReconnect_knob, title_knob, prev_title_knob, tags_knob,
                 backdrops_knob]:
        n.addKnob(knob)

    wiredTab_knob.setFlag(0)  # Open the tab.
    n.addKnob(nuke.Text_Knob("line1", "", ""))
    n.addKnob(postageStamp_knob)

    # Create buttons for Anchor functions.
    anchorLabel_knob = nuke.Text_Knob('anchor_label', 'Anchor:', " ")
    anchorLabel_knob.setFlag(nuke.STARTLINE)
    buttonShowAnchor = nuke.PyScript_Knob("show_anchor", " show anchor ", "stamps.wiredShowAnchor()")
    buttonShowAnchor.setTooltip("Show the properties panel for this Stamp's Anchor.")
    buttonShowAnchor.clearFlag(nuke.STARTLINE)
    buttonZoomAnchor = nuke.PyScript_Knob("zoom_anchor", "zoom anchor", "stamps.wiredZoomAnchor()")
    buttonZoomAnchor.setTooltip("Navigate to this Stamp's Anchor on the Node Graph.")

    for knob in [anchorLabel_knob, buttonShowAnchor, buttonZoomAnchor]:
        n.addKnob(knob)

    # Create buttons for Stamps functions.
    stampsLabel_knob = nuke.Text_Knob('stamps_label', 'Stamps:', " ")
    stampsLabel_knob.setFlag(nuke.STARTLINE)
    buttonZoomNext = nuke.PyScript_Knob("zoomNext", " zoom next ", "stamps.wiredZoomNext()")
    buttonZoomNext.setTooltip("Navigate to this Stamp's next sibling on the Node Graph.")
    buttonZoomNext.clearFlag(nuke.STARTLINE)
    buttonSelectSimilar = nuke.PyScript_Knob("selectSimilar", " select similar ", "stamps.wiredSelectSimilar()")
    buttonSelectSimilar.clearFlag(nuke.STARTLINE)
    buttonSelectSimilar.setTooltip("Select all similar Stamps to this one on the Node Graph.")

    space_1_knob = nuke.Text_Knob("space_1", "", " ")
    space_1_knob.setFlag(nuke.STARTLINE)

    for knob in [stampsLabel_knob, buttonZoomNext, buttonSelectSimilar, space_1_knob]:
        n.addKnob(knob)

    # Create Reconnect buttons.
    reconnectLabel_knob = nuke.Text_Knob('reconnect_label', 'Reconnect:', " ")
    reconnectLabel_knob.setTooltip("Reconnect by the stored Anchor name.")
    reconnectLabel_knob.setFlag(nuke.STARTLINE)
    buttonReconnectThis = nuke.PyScript_Knob("reconnect_this", "this", wiredReconnect_code)
    buttonReconnectThis.setTooltip("Reconnect this Stamp to its Anchor using the stored Anchor name.")
    buttonReconnectSimilar = nuke.PyScript_Knob("reconnect_similar", "similar", "stamps.wiredReconnectSimilar()")
    buttonReconnectSimilar.setTooltip("Reconnect this Stamp and similar ones using the stored anchor name.")
    buttonReconnectAll = nuke.PyScript_Knob("reconnect_all", "all", "stamps.wiredReconnectAll()")
    buttonReconnectAll.setTooltip("Reconnect all Stamps to their Anchors using the stored names.")
    space_2_knob = nuke.Text_Knob("space_2", "", " ")
    space_2_knob.setFlag(nuke.STARTLINE)

    for knob in [reconnectLabel_knob, buttonReconnectThis, buttonReconnectSimilar, buttonReconnectAll, space_2_knob]:
        n.addKnob(knob)

    # Advanced Reconnection tab.
    advancedReconnection_knob = nuke.Tab_Knob('advanced_reconnection', 'Advanced Reconnection',
                                              nuke.TABBEGINCLOSEDGROUP)
    n.addKnob(advancedReconnection_knob)

    reconnectByTitleLabel_knob = nuke.Text_Knob('reconnect_by_title_label', '<font color=gold>By Title:', " ")
    reconnectByTitleLabel_knob.setFlag(nuke.STARTLINE)
    reconnectByTitleLabel_knob.setTooltip("Reconnect by searching for a matching title.")
    buttonReconnectByTitleThis = nuke.PyScript_Knob("reconnect_by_title_this", "this", "stamps.wiredReconnectByTitle()")
    buttonReconnectByTitleThis.setTooltip("Find an Anchor that shares this Stamp's title and connect to it.")
    buttonReconnectByTitleSimilar = nuke.PyScript_Knob("reconnect_by_title_similar", "similar",
                                                       "stamps.wiredReconnectByTitleSimilar()")
    buttonReconnectByTitleSimilar.setTooltip("Find an Anchor by title and reconnect this Stamp and similar ones to it.")
    buttonReconnectByTitleSelected = nuke.PyScript_Knob("reconnect_by_title_selected", "selected",
                                                        "stamps.wiredReconnectByTitleSelected()")
    buttonReconnectByTitleSelected.setTooltip(
        "For each selected Stamp, reconnect using an Anchor that shares its title.")
    reconnectBySelectionLabel_knob = nuke.Text_Knob('reconnect_by_selection_label',
                                                    '<font color=orangered>By Selection:', " ")
    reconnectBySelectionLabel_knob.setFlag(nuke.STARTLINE)
    reconnectBySelectionLabel_knob.setTooltip("Force reconnect to a selected Anchor.")
    buttonReconnectBySelectionThis = nuke.PyScript_Knob("reconnect_by_selection_this", "this",
                                                        "stamps.wiredReconnectBySelection()")
    buttonReconnectBySelectionThis.setTooltip("Force reconnect this Stamp to a selected Anchor.")
    buttonReconnectBySelectionSimilar = nuke.PyScript_Knob("reconnect_by_selection_similar", "similar",
                                                           "stamps.wiredReconnectBySelectionSimilar()")
    buttonReconnectBySelectionSimilar.setTooltip("Force reconnect this Stamp and similar ones to a selected Anchor.")
    buttonReconnectBySelectionSelected = nuke.PyScript_Knob("reconnect_by_selection_selected", "selected",
                                                            "stamps.wiredReconnectBySelectionSelected()")
    buttonReconnectBySelectionSelected.setTooltip("Force reconnect all selected Stamps to the selected Anchor.")

    checkboxReconnectByTitleOnCreation = nuke.Boolean_Knob("auto_reconnect_by_title",
                                                           "<font color=#ED9977>&nbsp; auto-reconnect by title")
    checkboxReconnectByTitleOnCreation.setTooltip(
        "On copy-paste, auto-reconnect by title instead of stored Anchor name; turns off automatically.")
    checkboxReconnectByTitleOnCreation.setFlag(nuke.STARTLINE)

    # Add all advanced reconnection knobs.
    advancedReconnection_knob = nuke.Tab_Knob('advanced_reconnection', 'Advanced Reconnection', -1)
    for knob in [reconnectByTitleLabel_knob, buttonReconnectByTitleThis, buttonReconnectByTitleSimilar,
                 buttonReconnectByTitleSelected,
                 reconnectBySelectionLabel_knob, buttonReconnectBySelectionThis, buttonReconnectBySelectionSimilar,
                 buttonReconnectBySelectionSelected,
                 anchor_knob, checkboxReconnectByTitleOnCreation, advancedReconnection_knob]:
        n.addKnob(knob)

    # Version and help.
    line_knob = nuke.Text_Knob("line2", "", "")
    buttonHelp = nuke.PyScript_Knob("buttonHelp", "Help", "stamps.showHelp()")
    version_knob = nuke.Text_Knob('version', ' ',
                                  '<a href="http://www.nukepedia.com/gizmos/other/stamps" '
                                  'style="color:#666;text-decoration: none;">'
                                  '<span style="color:#666"><big>Stamps {}</big></span></a>'.format(version))
    version_knob.clearFlag(nuke.STARTLINE)
    version_knob.setTooltip(VERSION_TOOLTIP)
    for knob in [line_knob, buttonHelp, version_knob]:
        n.addKnob(knob)

    # Adjust input node position without affecting node layout.
    x, y = n.xpos(), n.ypos()
    nw = n.screenWidth()
    aw = anchor.screenWidth()
    n.setInput(0, anchor)
    n["hide_input"].setValue(True)
    n["xpos"].setValue(x - nw / 2 + aw / 2)
    n["ypos"].setValue(y)

    n["help"].setValue(STAMPS_HELP)
    wiredTagsAndBackdrops(n)

    context.last_created = anchor.name()
    return n


def getAvailableName(name="Untitled", rand=False):
    """
    Returns a unique node name starting with the given base name, followed by a sequential number or random hex.

    Args:
        name (str): The base name.
        rand (bool): If True, appends a random hexadecimal string; otherwise, a sequential number.

    Returns:
        str: An available node name that does not currently exist.
    """
    import random
    i = 1
    while True:
        if not rand:
            available_name = name + str(i)
        else:
            available_name = name + str('_%09x' % random.randrange(9 ** 12))
        if not nuke.exists(available_name):
            return available_name
        i += 1


#################################
### FUNCTIONS
#################################

def getDefaultTitle(node=None):
    """
    Determine the default title for a node based on its class and properties.

    For a Camera node, if no NoOp exists with title 'cam', returns 'cam'.
    For a Dot or NoOp node with a non-empty label, returns the label.
    For Read nodes, attempts to extract a filename-derived title.

    Args:
        node (nuke.Node): The node for which to generate a default title.

    Returns:
        str or bool: The default title as a string, or False if node is None.
    """
    if node is None:
        return False
    title = str(node.name())

    # Handle Camera nodes.
    if "Camera" in node.Class():
        try:
            if not any(i.knob("title") and i["title"].value() == "cam" for i in nuke.allNodes("NoOp")):
                return "cam"
        except Exception:
            pass

    # Handle Dot/NoOp nodes with a label.
    if node.Class() in ["Dot", "NoOp"]:
        try:
            label = node["label"].value().strip()
            if label != "":
                return label
        except Exception:
            pass

    # Handle Read nodes by extracting a filename-based title.
    try:
        file = node['file'].value()
        if not (node.knob("read_from_file") and not node["read_from_file"].value()):
            if file != "":
                rawname = file.rpartition('/')[2].rpartition('.')[0]
                if '.' in rawname:
                    rawname = rawname.rpartition('.')[0]
                # Option 1: Match a beauty pass pattern.
                m = re.match(r"([\w]+)_v[\d]+_beauty", rawname)
                if m:
                    pre_version = m.groups()[0]
                    title = "_".join(pre_version.split("_")[3:])
                    return title
                # Option 2: Generic extraction.
                rawname = str(re.split("_v[0-9]*_", rawname)[-1]).replace("_render", "")
                title = rawname
    except Exception:
        pass

    return title


def backdropTags(node=None):
    """
    Extract a list of cleaned label tags from the backdrop nodes that contain the given node.

    Args:
        node (nuke.Node): The node for which to find associated backdrops.

    Returns:
        list: A list of tag strings derived from the labels of matching BackdropNodes.
    """
    backdrops = findBackdrops(node)
    tags = []
    for b in backdrops:
        try:
            # Check custom visibility if available.
            if b.knob("visible_for_stamps"):
                if not b["visible_for_stamps"].value():
                    continue
            elif not b["bookmark"].value():
                continue
            label = b["label"].value()
            if label and len(label) < 50 and not label.startswith("\\"):
                # Process the label: remove newlines, HTML tags, extra spaces, and trailing periods.
                label = label.split("\n")[0].strip()
                label = re.sub("<[^<>]*>", "", label)
                label = re.sub("[\s]+", " ", label)
                label = re.sub("\.$", "", label)
                tags.append(label)
        except Exception:
            continue
    return tags


def stampCreateAnchor(node=None, extra_tags=[], no_default_tag=False):
    """
    Create a new Anchor Stamp based on a given node, optionally appending extra tags.

    Args:
        node (nuke.Node): The node from which to derive the stamp.
        extra_tags (list): Additional tags to be merged with default tags.
        no_default_tag (bool): If True, override default tags completely.

    Returns:
        list or None: A list of extra tags (if creation succeeded) or None if cancelled.
    """
    ns = nuke.selectedNodes()
    for n in ns:
        n.setSelected(False)

    if node is not None:
        node.setSelected(True)
        default_title = getDefaultTitle(realInput(node, stopOnLabel=True, mode="title"))
        default_tags = list(set([nodeType(realInput(node, mode="tags"))]))
        if node.Class() in ["ScanlineRender"]:
            default_tags += ["2D", "Deep"]
        node_type = nodeType(realInput(node))
        window_title = "New Stamp: " + str(node.name())
    else:
        default_title = "Stamp"
        default_tags = ""
        node_type = ""
        window_title = "New Stamp"

    if CONFIG.default_title_fn:
        try:
            custom_default_title = CONFIG.default_title_fn(node)
            if custom_default_title:
                default_title = str(custom_default_title)
        except Exception:
            log_exception("Failed to apply defaultTitle override")

    if CONFIG.default_tags_fn:
        try:
            custom_default_tags = CONFIG.default_tags_fn(node)
            if custom_default_tags:
                if KEEP_ORIGINAL_TAGS:
                    default_tags += custom_default_tags
                else:
                    default_tags = custom_default_tags
        except Exception:
            log_exception("Failed to apply defaultTags override")

    default_default_tags = default_tags

    if no_default_tag:
        default_tags = ", ".join(extra_tags + [""])
    else:
        # Remove duplicates and join into a comma-separated string.
        default_tags = list(filter(None, list(dict.fromkeys(default_tags + extra_tags))))
        default_tags = ", ".join(default_tags + [""])

    from ui_panels import NewAnchorPanel
    global new_anchor_panel
    new_anchor_panel = NewAnchorPanel(window_title, default_title, allTags(), default_tags)

    while True:
        if new_anchor_panel.exec_():
            anchor_title = new_anchor_panel.anchorTitle
            anchor_tags = new_anchor_panel.anchorTags
            if not titleIsLegal(anchor_title):
                nuke.message("Please set a valid title.")
                continue
            elif len(findAnchorsByTitle(anchor_title)):
                if not nuke.ask(
                        "There is already a Stamp titled " + anchor_title + ".\nDo you still want to use this title?"):
                    continue
            na = anchor(title=anchor_title, tags=anchor_tags, input_node=node, node_type=node_type)
            na.setYpos(na.ypos() + 20)
            stampCreateWired(na)
            for n in ns:
                n.setSelected(True)
                node.setSelected(False)
            extra_tags = [t.strip() for t in anchor_tags.split(",") if t.strip() not in default_default_tags]
            break
        else:
            break

    return extra_tags


def stampSelectAnchors():
    """
    Display a panel to select an Anchor Stamp.

    Returns:
        list or None: A list of selected anchor nodes or None if cancelled.
    """
    # 1. Get a temporary node's position to use as reference.
    nodeForPos = nuke.createNode("NoOp")
    childNodePos = [nodeForPos.xpos(), nodeForPos.ypos()]
    nuke.delete(nodeForPos)
    # 2. Retrieve existing anchors.
    anchorList = [n.name() for n in allAnchors()]
    if not len(anchorList):
        nuke.message("Please create some stamps first...")
        return None
    else:
        global select_anchors_panel
        from ui_panels import AnchorSelector
        select_anchors_panel = AnchorSelector()
        if select_anchors_panel.exec_():
            chosen_anchors = select_anchors_panel.chosen_anchors
            if chosen_anchors:
                return chosen_anchors
        return None


def stampCreateWired(anchor=""):
    """
    Create a Wired Stamp linked to a specified Anchor.

    If no anchor is provided, prompts the user to select one.

    Args:
        anchor (nuke.Node or str): The anchor node to use.

    Returns:
        nuke.Node: The created wired stamp node.
    """
    nw = ""
    nws = []
    if anchor == "":
        anchors = stampSelectAnchors()
        if anchors is None:
            return
        if anchors:
            for i, anchor in enumerate(anchors):
                nw = wired(anchor=anchor)
                nw.setInput(0, anchor)
                nws.append(nw)
                if i > 0:
                    nws[i].setXYpos(nws[i - 1].xpos() + 100, nws[i - 1].ypos())
    else:
        ns = nuke.selectedNodes()
        for n in ns:
            n.setSelected(False)
        dot = nuke.nodes.Dot()
        dot.setXYpos(anchor.xpos(), anchor.ypos())
        dot.setInput(0, anchor)
        nw = wired(anchor=anchor)
        node_class = nw.Class()
        dummy = None
        node_factory = getattr(nuke.nodes, node_class, None)
        try:
            if callable(node_factory):
                dummy = node_factory()
            else:
                dummy = nuke.createNode(node_class, inpanel=False)
            nww = dummy.screenWidth()
        finally:
            if dummy is not None:
                nuke.delete(dummy)
        nuke.delete(dot)
        for n in ns:
            n.setSelected(True)
        nw.setXYpos(int(anchor.xpos() + anchor.screenWidth() / 2 - nww / 2), anchor.ypos() + 56)
        anchor.setSelected(False)
    return nw


def stampCreateByTitle(title=""):
    """
    Create a Wired Stamp by matching an Anchor's title.

    Args:
        title (str): The title to match.

    Returns:
        nuke.Node or None: The created wired stamp node, or None if no matching anchor is found.
    """
    anchor = None
    for a in allAnchors():
        if a.knob("title") and a["title"].value() == title:
            anchor = a
            break
    if anchor is None:
        return
    nw = wired(anchor=anchor)
    nw.setInput(0, anchor)
    return nw


def stampDuplicateWired(wired=""):
    """
    Duplicate a wired stamp node by copying and pasting it.

    Args:
        wired (nuke.Node): The wired stamp node to duplicate.
    """
    ns = nuke.selectedNodes()
    for n in ns:
        n.setSelected(False)
    wired.setSelected(True)

    clipboard = QtWidgets.QApplication.clipboard()
    ctext = clipboard.text()
    nuke.nodeCopy("%clipboard%")
    wired.setSelected(False)
    new_wired = nuke.nodePaste("%clipboard%")
    clipboard.setText(ctext)
    new_wired.setXYpos(wired.xpos() - 110, wired.ypos() + 55)
    try:
        new_wired.setInput(0, wired.input(0))
    except Exception:
        pass
    for n in ns:
        n.setSelected(True)
    wired.setSelected(False)


def stampType(n=""):
    """
    Identify the stamp type based on node properties.

    Args:
        n (nuke.Node): The node to inspect.

    Returns:
        str or bool: "anchor", "wired", or False if neither.
    """
    if isAnchor(n):
        return "anchor"
    elif isWired(n):
        return "wired"
    else:
        return False


def nodeType(n=""):
    """
    Determine the node type (e.g., Camera, Deep, 3D, Particle, or 2D).

    Args:
        n (nuke.Node): The node to check.

    Returns:
        str or bool: The node type or False if not determinable.
    """
    try:
        nodeClass = n.Class()
    except Exception:
        return False
    if nodeClass.startswith("Deep") and nodeClass not in DeepExceptionClasses:
        return "Deep"
    elif nodeClass.startswith("Particle") and nodeClass not in ParticleExceptionClasses:
        return "Particle"
    elif nodeClass.startswith("ScanlineRender"):
        return False
    elif nodeClass in ["Camera", "Camera2", "Camera3"]:
        return "Camera"
    elif nodeClass in ["Axis", "Axis2", "Axis3"]:
        return "Axis"
    elif (n.knob("render_mode") and n.knob("display")) or nodeClass in ["GeoNoOp", "EditGeo"]:
        return "3D"
    else:
        return "2D"


def allAnchors(selection=""):
    """
    Return a list of all Anchor nodes.

    Args:
        selection (list): Optional list of nodes to filter.

    Returns:
        list: Anchor nodes.
    """
    nodes = nuke.allNodes()
    if selection == "":
        anchors = [a for a in nodes if isAnchor(a)]
    else:
        anchors = [a for a in nodes if a in selection and isAnchor(a)]
    return anchors


def allWireds(selection=""):
    """
    Return a list of all Wired nodes.

    Args:
        selection (list): Optional list of nodes to filter.

    Returns:
        list: Wired nodes.
    """
    nodes = nuke.allNodes()
    if selection == "":
        wireds = [a for a in nodes if isWired(a)]
    else:
        wireds = [a for a in nodes if a in selection and isWired(a)]
    return wireds


def totalAnchors(selection=""):
    """
    Count the total number of Anchor nodes.

    Args:
        selection (list): Optional list of nodes to filter.

    Returns:
        int: Number of anchors.
    """
    return len(allAnchors(selection))


def allTags(selection=""):
    """
    Compile a sorted list of all unique tags from Anchor nodes.

    Args:
        selection: Not used.

    Returns:
        list: Sorted list of tags.
    """
    all_tags = set()
    for ni in allAnchors():
        try:
            tags_value = ni["tags"].value()
            tags = re.split(" *, *", tags_value.strip())
            all_tags.update(tags)
        except Exception:
            pass
    all_tags = [i for i in list(all_tags) if i]
    all_tags.sort(key=str.lower)
    return all_tags


def findAnchorsByTitle(title="", selection=""):
    """
    Find all Anchor nodes matching a given title.

    Args:
        title (str): The title to search for.
        selection (list): Optional list to filter.

    Returns:
        list or None: Matching anchors or None if title is empty.
    """
    if title == "":
        return None
    if selection == "":
        found_anchors = [a for a in allAnchors() if a.knob("title") and a.knob("title").value() == title]
    else:
        found_anchors = [a for a in selection if
                         a in allAnchors() and a.knob("title") and a.knob("title").value() == title]
    return found_anchors


def titleIsLegal(title=""):
    """
    Determine if a given stamp title is legal (non-empty).

    Args:
        title (str): The title to check.

    Returns:
        bool: True if legal, False otherwise.
    """
    if not title or title == "":
        return False
    return True


def isAnchor(node=""):
    """
    Check if a node is an Anchor.

    Args:
        node (nuke.Node): The node to check.

    Returns:
        bool: True if the node is an Anchor, otherwise False.
    """
    try:
        return all(node.knob(i) for i in ["identifier", "title"]) and node["identifier"].value() == "anchor"
    except Exception:
        return False


def isWired(node=""):
    """
    Check if a node is a Wired stamp.

    Args:
        node (nuke.Node): The node to check.

    Returns:
        bool: True if the node is Wired, otherwise False.
    """
    try:
        return all(node.knob(i) for i in ["identifier", "title"]) and node["identifier"].value() == "wired"
    except Exception:
        return False


def findBackdrops(node=""):
    """
    Find all BackdropNodes that fully contain the given node.

    Args:
        node (nuke.Node): The node to check.

    Returns:
        list: BackdropNodes containing the node.
    """
    if node == "":
        return []
    x = node.xpos()
    y = node.ypos()
    w = node.screenWidth()
    h = node.screenHeight()

    backdrops = []
    for b in nuke.allNodes("BackdropNode"):
        try:
            bx = int(b['xpos'].value())
            by = int(b['ypos'].value())
            br = int(b['bdwidth'].value()) + bx
            bt = int(b['bdheight'].value()) + by
            if x >= bx and (x + w) <= br and y > by and (y + h) <= bt:
                backdrops.append(b)
        except Exception:
            continue
    return backdrops


def realInput(node, stopOnLabel=False, mode=""):
    """
    Recursively find the first input node that is not a Dot or a Stamp.

    If stopOnLabel is True, stops if a Dot/NoOp with a non-empty label is encountered.
    Mode can be "title" or "tags" to ignore certain classes.

    Args:
        node (nuke.Node): The starting node.
        stopOnLabel (bool): Whether to stop if a node with a label is found.
        mode (str): Mode of operation ("title" or "tags").

    Returns:
        nuke.Node: The resulting node.
    """
    try:
        n = node
        if stampType(n) or n.Class() in InputIgnoreClasses or \
                (mode == "title" and n.Class() in TitleIgnoreClasses) or \
                (mode == "tags" and n.Class() in TagsIgnoreClasses):
            if stopOnLabel and n.knob("label") and n["label"].value().strip() != "":
                return n
            if n.input(0):
                return realInput(n.input(0), stopOnLabel, mode)
            else:
                return n
        else:
            return n
    except Exception:
        return node


def nodeToScript(node=""):
    """
    Export a node to a TCL script string, similar to nodeCopy, without altering the clipboard.

    Args:
        node (nuke.Node): The node to export.

    Returns:
        str: The node as a TCL script.
    """
    orig_sel_nodes = nuke.selectedNodes()
    if node == "":
        node = nuke.selectedNode()
    if not node:
        return ""
    for i in orig_sel_nodes:
        i.setSelected(False)
    node.setSelected(True)
    clipboard = QtWidgets.QApplication.clipboard()
    ctext = clipboard.text()
    nuke.nodeCopy("%clipboard%")
    node_as_script = clipboard.text()
    clipboard.setText(ctext)
    node.setSelected(False)
    for i in orig_sel_nodes:
        i.setSelected(True)
    return node_as_script


def nodesFromScript(script=""):
    """
    Paste nodes from a given TCL script string, similar to nodePaste, without affecting the clipboard.

    Args:
        script (str): The TCL script containing node data.

    Returns:
        bool: True on success.
    """
    if script == "":
        return
    clipboard = QtWidgets.QApplication.clipboard()
    ctext = clipboard.text()
    clipboard.setText(script)
    nuke.nodePaste("%clipboard%")
    clipboard.setText(ctext)
    return True


def stampCount(anchor_name=""):
    """
    Count the number of Wired stamps connected to a given anchor.

    Args:
        anchor_name (str): The name of the anchor.

    Returns:
        int: The count of wired stamps.
    """
    if anchor_name == "":
        return len(allWireds())
    stamps = [s for s in allWireds() if s["anchor"].value() == anchor_name]
    return len(stamps)


def toNoOp(node=""):
    """
    Convert a given node into a NoOp node while preserving its properties.

    This function exports the node to script, modifies the script to create a NoOp, and then pastes it.

    Args:
        node (nuke.Node): The node to convert.
    """
    context.lock_callbacks = True
    if node == "":
        return
    if node.Class() == "NoOp":
        return
    nsn = nuke.selectedNodes()
    for i in nsn:
        i.setSelected(False)
    scr = nodeToScript(node)
    scr = re.sub(r"\n[\s]*[\w]+[\s]*{\n", "\nNoOp {\n", scr)
    scr = re.sub(r"^[\s]*[\w]+[\s]*{\n", "NoOp {\n", scr)

    legal_starts = ["set", "version", "push", "NoOp", "help", "onCreate", "name", "knobChanged", "autolabel",
                    "tile_color", "gl_color", "note_font", "selected", "hide_input"]
    scr_split = scr.split("addUserKnob", 1)
    scr_first = scr_split[0].split("\n")
    for i, line in enumerate(scr_first):
        if not any(line.startswith(x) or line.startswith(" " + x) for x in legal_starts):
            scr_first[i] = ""
    scr_first = "\n".join([i for i in scr_first if i] + [""])
    scr_split[0] = scr_first
    scr = "addUserKnob".join(scr_split)

    node.setSelected(True)
    xp = node.xpos()
    yp = node.ypos()
    xw = node.screenWidth() / 2
    d = nuke.createNode("Dot")
    d.setInput(0, node)
    for i in nsn:
        i.setSelected(True)
    nuke.delete(node)
    d.setSelected(False)
    d.setSelected(True)
    d.setXYpos(int(xp + xw - d.screenWidth() / 2), yp - 18)
    nodesFromScript(scr)
    n = nuke.selectedNode()
    n.setXYpos(xp, yp)
    nuke.delete(d)
    for i in nsn:
        try:
            i.setSelected(True)
        except Exception:
            pass
    context.lock_callbacks = False


def allToNoOp():
    """
    Convert all stamp nodes (Anchors and Wired) into NoOp nodes.
    """
    for n in nuke.allNodes():
        if stampType(n) and n.Class() != "NoOp":
            toNoOp(n)


#################################
### Menu functions
#################################

def refreshStamps(ns=""):
    """
    Refresh all wired stamps in the script to update styles and reconnections.

    Args:
        ns (list, optional): A list of nodes to refresh. If empty, refreshes all wired stamps.
    """
    stamps = allWireds(ns)
    error_count = 0
    failed = []
    for s in stamps:
        if not wiredReconnect(s):
            error_count += 1
            failed.append(s)
        else:
            try:
                s["reconnect_this"].execute()
            except Exception:
                pass
    failed_names = ", ".join([i.name() for i in failed])
    if error_count == 0:
        if ns == "":
            nuke.message("All Stamps refreshed! No errors detected.")
        else:
            nuke.message("Selected Stamps refreshed! No errors detected.")
    else:
        # Deselect all, then select only the failed nodes.
        for i in nuke.selectedNodes():
            i.setSelected(False)
        for i in failed:
            i.setSelected(True)
        if ns == "":
            nuke.message(
                "All Stamps refreshed. Found {0} connection error/s:\n\n{1}".format(str(error_count), failed_names))
        else:
            nuke.message("Selected Stamps refreshed. Found {0} connection error/s:\n\n{1}".format(str(error_count),
                                                                                                  failed_names))


def addTags(ns=""):
    """
    Add tags to nodes. If no nodes are selected, prompts the user whether to add tags to all nodes.

    Args:
        ns (list, optional): A list of nodes to add tags to. If empty, uses selected nodes or all nodes.
    """
    if ns == "":
        ns = nuke.selectedNodes()
    if not len(ns):
        if not nuke.ask("Nothing is selected. Do you wish to add tags to ALL nodes in the script?"):
            return
        ns = nuke.allNodes()

    from ui_panels import AddTagsPanel
    global stamps_addTags_panel
    stamps_addTags_panel = AddTagsPanel(all_tags=allTags(), default_tags="")
    if stamps_addTags_panel.exec_():
        all_nodes = stamps_addTags_panel.allNodes
        added_tags = stamps_addTags_panel.tags.strip()
        added_tags = re.split(r"[\s]*,[\s]*", added_tags)
        count = 0
        for n in ns:
            # Determine which knob holds the tags
            if isAnchor(n):
                tags_knob = n.knob("tags")
            elif isWired(n):
                a_name = n.knob("anchor").value()
                try:
                    if nuke.exists(a_name):
                        a = nuke.toNode(a_name)
                        # Skip if the anchor is already selected or not a valid Anchor.
                        if a in ns or not isAnchor(a):
                            continue
                        tags_knob = a.knob("tags")
                    else:
                        continue
                except Exception:
                    continue
            elif n.Class() not in NodeExceptionClasses:
                tags_knob = n.knob("stamp_tags")
                if not tags_knob:
                    tags_knob = nuke.String_Knob('stamp_tags', 'Stamp Tags', "")
                    tags_knob.setTooltip(
                        "Stamps: Comma-separated tags you can define for each Anchor, that will help you find it when invoking the Stamp Selector by pressing the Stamps shortkey with nothing selected.")
                    n.addKnob(tags_knob)
            else:
                continue
            try:
                existing_tags = re.split(r"[\s]*,[\s]*", tags_knob.value().strip())
            except Exception:
                existing_tags = []
            merged_tags = list(filter(None, list(set(existing_tags + added_tags))))
            tags_knob.setValue(", ".join(merged_tags))
            count += 1
        if count > 0:
            if all_nodes:
                nuke.message("Added the specified tag/s to {} nodes.".format(str(count)))
            else:
                nuke.message("Added the specified tag/s to {} Anchor Stamps.".format(str(count)))
    return


def renameTag(ns=""):
    """
    Rename a tag on nodes. If no nodes are selected, applies to all nodes.

    Args:
        ns (list, optional): A list of nodes to rename tags on. Defaults to selected nodes or all nodes.
    """
    if ns == "":
        ns = nuke.selectedNodes()
    if not len(ns):
        ns = nuke.allNodes()
    from ui_panels import RenameTagPanel
    global stamps_renameTag_panel
    stamps_renameTag_panel = RenameTagPanel(all_tags=allTags())
    if stamps_renameTag_panel.exec_():
        all_nodes = stamps_renameTag_panel.allNodes
        if all_nodes:
            ns = nuke.allNodes()
        tag_to_rename = str(stamps_renameTag_panel.tag.strip())
        tag_replace = str(stamps_renameTag_panel.tagReplace.strip())
        count = 0
        for n in ns:
            # Determine the knob that contains tags.
            if isAnchor(n):
                tags_knob = n.knob("tags")
            elif isWired(n):
                a_name = n.knob("anchor").value()
                try:
                    if nuke.exists(a_name):
                        a = nuke.toNode(a_name)
                        if a in ns or not isAnchor(a):
                            continue
                        tags_knob = a.knob("tags")
                    else:
                        continue
                except Exception:
                    continue
            elif n.Class() not in NodeExceptionClasses:
                tags_knob = n.knob("stamp_tags")
                if not tags_knob:
                    continue
            else:
                continue

            existing_tags = list(filter(None, re.split(r"[\s]*,[\s]*", tags_knob.value())))
            # Replace occurrences of the tag with the new tag.
            merged_tags = [tag_replace if x == tag_to_rename else x for x in existing_tags]
            merged_tags = [i for i in merged_tags if i]
            if merged_tags != existing_tags:
                tags_knob.setValue(", ".join(merged_tags))
                count += 1
        if count > 0:
            nuke.message("Renamed the specified tag on {} nodes.".format(str(count)))
    return


def selectedReconnectByName():
    """
    For each selected wired stamp, execute its 'reconnect_this' knob to reconnect by stored Anchor name.
    """
    ns = [n for n in nuke.selectedNodes() if isWired(n)]
    for n in ns:
        try:
            n["reconnect_this"].execute()
        except Exception:
            pass


def selectedReconnectByTitle():
    """
    For each selected wired stamp, execute its 'reconnect_by_title_this' knob to reconnect by title.
    """
    ns = [n for n in nuke.selectedNodes() if isWired(n)]
    for n in ns:
        try:
            n["reconnect_by_title_this"].execute()
        except Exception:
            pass


def selectedReconnectBySelection():
    """
    For each selected wired stamp, execute its 'reconnect_by_selection_this' knob to force reconnect by selection.
    """
    ns = [n for n in nuke.selectedNodes() if isWired(n)]
    for n in ns:
        try:
            n["reconnect_by_selection_this"].execute()
        except Exception:
            pass


def selectedToggleAutorec():
    """
    Toggle the 'auto_reconnect_by_title' knob for selected nodes that have it.
    If any are False, ask for confirmation to set all to True; otherwise, set all to False.
    """
    ns = [n for n in nuke.selectedNodes() if n.knob("auto_reconnect_by_title")]
    if any(not n.knob("auto_reconnect_by_title").value() for n in ns):
        if nuke.ask("Are you sure you want to set <b>auto-reconnect by title</b> True on all the selected stamps?"):
            count = 0
            for n in ns:
                n.knob("auto_reconnect_by_title").setValue(1)
                count += 1
            nuke.message("<b>auto-reconnect by title</b> is now True on {} selected stamps.".format(str(count)))
    else:
        count = 0
        for n in ns:
            n.knob("auto_reconnect_by_title").setValue(0)
            count += 1
        nuke.message("<b>auto-reconnect by title</b> is now <b>False</b> on {} selected stamps.".format(str(count)))


def selectedSelectSimilar():
    """
    For each selected node (Anchor or Wired), execute the 'selectSimilar' or 'selectStamps' knob to select similar stamps.
    """
    ns = [n for n in nuke.selectedNodes() if isWired(n) or isAnchor(n)]
    for n in ns:
        try:
            if n.knob("selectSimilar"):
                n["selectSimilar"].execute()
            if n.knob("selectStamps"):
                n["selectStamps"].execute()
        except Exception:
            pass


def showInNukepedia():
    """
    Open the Nukepedia page for Stamps in the default web browser.
    """
    from webbrowser import open as openUrl
    openUrl("http://www.nukepedia.com/gizmos/other/stamps")


def showInGithub():
    """
    Open the GitHub repository for Stamps in the default web browser.
    """
    from webbrowser import open as openUrl
    openUrl("https://github.com/adrianpueyo/stamps")


def showHelp():
    """
    Open the PDF documentation for Stamps in the default web browser.
    """
    from webbrowser import open as openUrl
    openUrl("http://www.adrianpueyo.com/Stamps_v1.1.pdf")


def showVideo():
    """
    Open the video tutorial for Stamps in the default web browser.
    """
    from webbrowser import open as openUrl
    openUrl("https://vimeo.com/adrianpueyo/knobscripter2")


#################################
### MAIN IMPLEMENTATION
#################################

def goStamp(ns=""):
    """
    Main stamp function, called when the main shortcut is pressed.

    Behavior:
      - If no nodes are selected:
          - If no anchors exist in the script, create a new anchor with no input.
          - Otherwise, invoke the selection panel to create a wired stamp.
      - If one node is selected and it belongs to NodeExceptionClasses:
          - If no anchors exist, do nothing.
          - Otherwise, invoke the selection panel to create a wired stamp.
      - If multiple nodes are selected:
          - Warn the user if more than 10 nodes are selected.
          - For each node:
              - If the node is an Anchor, create a wired stamp child.
              - If the node is a Wired stamp, duplicate it.
              - Otherwise, if the node has a "stamp_tags" knob, create an Anchor using its tags.
              - Additionally, if the node is of class containing "Cryptomatte" and has a "matteOnly" knob, set it to 1.

    Args:
        ns (list): List of nodes to process. If empty, defaults to nuke.selectedNodes().
    """
    if ns == "":
        ns = nuke.selectedNodes()
    if not ns:
        if not totalAnchors():  # No anchors exist in the script.
            stampCreateAnchor(no_default_tag=True)
        else:
            stampCreateWired()  # Show selection panel to create a stamp.
        return
    elif len(ns) == 1 and ns[0].Class() in NodeExceptionClasses:
        if not totalAnchors():
            return
        else:
            stampCreateWired()  # Show selection panel to create a stamp.
            return
    else:
        # Warn if the selection is too big.
        if len(ns) > 10 and not nuke.ask("You have {} nodes selected.\nDo you want to make stamps for all of them?".format(len(ns))):
            return
        extra_tags = []
        for n in ns:
            try:
                if n in NodeExceptionClasses:
                    continue
                elif isAnchor(n):
                    stampCreateWired(n)  # Create a child stamp for the anchor.
                elif isWired(n):
                    stampDuplicateWired(n)  # Duplicate the wired stamp.
                else:
                    if n.knob("stamp_tags"):
                        stampCreateAnchor(n, extra_tags=n.knob("stamp_tags").value().split(","), no_default_tag=True)
                    else:
                        extra_tags = stampCreateAnchor(n, extra_tags=extra_tags)
                    if "Cryptomatte" in n.Class() and n.knob("matteOnly"):
                        n['matteOnly'].setValue(1)
            except Exception:
                continue
