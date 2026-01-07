"""Nuke integration hooks for Stamps."""

import os

import nuke

import stamps_core as core


def createWHotboxButtons():
    """
    If the 'W_hotbox' folder exists within the stamps package, add it to the W_HOTBOX repository.
    """
    w_hotbox_buttons_path = os.path.dirname(__file__).replace("\\", "/") + "/includes/W_hotbox"
    if os.path.exists(w_hotbox_buttons_path):
        hotbox_paths = ""
        hotbox_names = ""
        if "W_HOTBOX_REPO_PATHS" in os.environ and "W_HOTBOX_REPO_NAMES" in os.environ:
            hotbox_paths = os.environ["W_HOTBOX_REPO_PATHS"]
            hotbox_names = os.environ["W_HOTBOX_REPO_NAMES"]
        if hotbox_paths != "":
            hotbox_paths += os.pathsep
        if hotbox_names != "":
            hotbox_names += os.pathsep
        os.environ["W_HOTBOX_REPO_PATHS"] = hotbox_paths + w_hotbox_buttons_path
        os.environ["W_HOTBOX_REPO_NAMES"] = hotbox_names + "Stamps"


def stampBuildMenus():
    """
    Build and append Stamps-related menu commands to the Nuke menus and Nodes panel.
    """
    if not core.context.menus_loaded:
        core.context.menus_loaded = True
        m = nuke.menu('Nuke')
        m.addCommand('Edit/Stamps/Make Stamp', 'stamps.goStamp()', core.STAMPS_SHORTCUT, icon="stamps.png")
        m.addCommand('Edit/Stamps/Add tag\/s to selected nodes', 'stamps.addTags()')
        m.addCommand('Edit/Stamps/Rename Stamp tag', 'stamps.renameTag()')
        m.addCommand('Edit/Stamps/Refresh all Stamps', 'stamps.refreshStamps()')
        m.addCommand('Edit/Stamps/Selected/Reconnect by Name', 'stamps.selectedReconnectByName()')
        m.addCommand('Edit/Stamps/Selected/Reconnect by Title', 'stamps.selectedReconnectByTitle()')
        m.addCommand('Edit/Stamps/Selected/Reconnect by Selection', 'stamps.selectedReconnectBySelection()')
        m.menu('Edit').menu('Stamps').menu('Selected').addSeparator()
        m.addCommand('Edit/Stamps/Selected/Refresh', 'stamps.refreshStamps(nuke.selectedNodes())')
        m.addCommand('Edit/Stamps/Selected/Select Similar', 'stamps.selectedSelectSimilar()')
        m.addCommand('Edit/Stamps/Selected/Toggle auto-rec... by title ', 'stamps.selectedToggleAutorec()')

        m.addCommand('Edit/Stamps/Advanced/Convert all Stamps to NoOp', 'stamps.allToNoOp()')
        m.menu('Edit').menu('Stamps').addSeparator()
        m.addCommand('Edit/Stamps/GitHub', 'stamps.showInGithub()')
        m.addCommand('Edit/Stamps/Nukepedia', 'stamps.showInNukepedia()')
        m.menu('Edit').menu('Stamps').addSeparator()
        m.addCommand('Edit/Stamps/Video tutorials', 'stamps.showVideo()')
        m.addCommand('Edit/Stamps/Documentation (.pdf)', 'stamps.showHelp()')
        nuke.menu('Nodes').addCommand('Other/Stamps', 'stamps.goStamp()', core.STAMPS_SHORTCUT, icon="stamps.png")

        createWHotboxButtons()


def addIncludesPath():
    """
    Add the 'includes' directory within the stamps package to Nuke's plugin path.
    """
    includes_dir = os.path.join(os.path.dirname(__file__), "includes")
    if os.path.isdir(includes_dir):
        nuke.pluginAddPath(includes_dir)


def initialize():
    if nuke.GUI:
        stampBuildMenus()
    addIncludesPath()
