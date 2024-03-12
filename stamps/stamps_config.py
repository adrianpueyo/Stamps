# ------------------------------------------------------
# Stamps by Adrian Pueyo and Alexey Kuchinski
# Smart node connection system for Nuke
# adrianpueyo.com, 2018-2020
config_version = "v2.0"
date = "Nov 2023"
# -----------------------------------------------------
# import os
import re

import nuke

# ----------------------------------------------
# INSTRUCTIONS:
# Modify this file as needed. Do not rename it.
# Place it in your python path (i.e. next to stamps.py, or in your /.nuke folder).
# ----------------------------------------------

# ----------------------------------------------
# 1. MAIN DEFAULTS
# ----------------------------------------------

STAMPS_SHORTCUT = "F8"

USE_LABELCONNECTOR_UI = True # restart nuke to take effect. True uses LabelConnector UI, False uses the previous UI

ANCHOR_STYLE = {
    "tile_color": 4294967041,
    "note_font_size": 20,
}

STAMP_STYLE = {
    "tile_color": 16777217,
    "note_font_size": 20,
    "postage_stamp": 0,
}

# colors for the getColorFromTags to automatically color Anchors
# this is not used for the color quick menu
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
    "Default": 673720575,
    "Deep": int("%02x%02x%02x%02x" % (40, 40, 100, 1), 16),
}

# Override tile_color for specific node classes, to be fancy.
AnchorClassColors = {
    "Camera": int("%02x%02x%02x%02x" % (255, 255, 255, 1), 16),
}
WiredClassColors = {
    "Camera": int("%02x%02x%02x%02x" % (51, 0, 0, 1), 16),
    "Deep": int("%02x%02x%02x%02x" % (40, 40, 100, 1), 16),
}
# WiredClassColors = {"Deep":int('%02x%02x%02x%02x' % (40,40,100,1),16),}


# ----------------------------------------------
# 2. CUSTOM FUNCTIONS
# ----------------------------------------------


def getColorFromTags(tags=""):
    """return a color based on tags"""

    if isinstance(tags, list):
        tags = " ".join(tags)

    tags = tags.lower()

    if "roto" in tags or "rotogroup" in tags or "mask" in tags or "crypto" in tags:
        return COLOR_LIST["Green"]
    elif "plates" in tags:
        return COLOR_LIST["Yellow"]
    elif "deep" in tags:
        return COLOR_LIST["Deep"]
    elif "camera" in tags:
        return COLOR_LIST["Red"]

    return None


def setColorFromAnchor(Wired):
    """set the color of the wired node to the color of the anchor node"""

    n = Wired
    anchor = n.dependencies(nuke.HIDDEN_INPUTS)[0]
    anchor_color = anchor["tile_color"].getValue()

    if anchor_color == int("%02x%02x%02x%02x" % (255, 255, 255, 1), 16):
        n["tile_color"].setValue(16777217)

    n["tile_color"].setValue(int(anchor_color))


def defaultTitle(node):
    """
    defaultTitle(node) -> (str)title
    Returns a custom default Stamp title for a given node.
    Customize this function to return any string you want.
    If you return None, it will calculate the default title.
    """

    # name = node.name()

    # ALL THIS IS SAMPLE CODE, FEEL FREE TO REMOVE OR MODIFY IT
    # Example 1: Make "cam" the default Stamp title for the first Camera
    if "Camera" in node.Class() and not any([(i.knob("title") and i["title"].value() == "cam") for i in nuke.allNodes("NoOp")]):
        title = "cam"
        return title

    # Example 2: If the node has a file knob, take the part of the filename that goes before the frame numbers
    if node.knob("file"):  # If node has knob "file"
        filepath = node.knob("file").value()
        if filepath:  # If the value of the knob "file" is not empty
            filename = filepath.split("/")[-1]  # 1. Take the file name only
            title = filename.split(".")[0]  # 2. Take the part of the filename before any dots
            title = str(re.split("_v[0-9]*_", title)[-1])  # 3. Take the part that goes after the version
            title = title.replace("_render", "")  # 4. If the title includes "_render", remove it
            return title

    # If we don't return a string, stamps.py will calculate the default title by itself.
    return


def defaultTags(node):
    """
    defaultTags(node) -> (list of str)tags
    Returns a custom default list of Stamp tags for a given node.
    Customize this function to return any string you want.
    If you return None, it will calculate the default tags.
    """

    # 1. We start off with an empty list
    tags = []

    # 2. Now we can add any custom default tags (strings) to the list, by making any calculations on the node.

    # Here's an example:
    node_class = node.Class()
    if node_class == "Write":
        tags.append("File Out")

    # Now, the list of tags for whenever we create a Stamp on a Write node, will contain "File Out" by default.

    # However, the default default tags (default written twice on purpose) will also be preserved, and the list we return will be appended on top of them.
    # So for a Write node, it would look: "2D, File Out, "

    # If we only want our own tags, the constant KEEP_ORIGINAL_TAGS should be set to False, below, in the ADVANCED section.

    return tags


# ----------------------------------------------
# 3. ADVANCED. DO NOT CHANGE UNLESS NEEDED.
# ----------------------------------------------

KEEP_ORIGINAL_TAGS = False  # True: Keep the default tags for the nodes, plus your custom-defined ones. False: Only keep the custom ones you can define below
DeepExceptionClasses = ["DeepToImage", "DeepHoldout", "DeepHoldout2"]  # Nodes with "Deep" in their class that don't classify as Deep.
NodeExceptionClasses = ["Viewer"]  # Nodes that won't accept stamps
ParticleExceptionClasses = ["ParticleToImage"]  # Nodes with "Particle" in class and an input called "particles" that don't classify as particles.

# The next two constants define the node classes that will be ignored when looking for the title or tags of a node.
# This means, it will look for the node's first input instead, recursively, until it finds a node that doesn't belong to these classes.
TitleIgnoreClasses = ["NoOp", "Dot", "Reformat", "DeepReformat", "Crop"]
TagsIgnoreClasses = ["NoOp", "Dot", "Reformat", "DeepReformat", "Crop"]

AnchorClassesAlt = {"2D": "NoOp", "Deep": "DeepExpression", "3D": "EditGeo", "Particle": "ParticleExpression"}

# modified for NoOp instead of PostageStamp
StampClassesAlt = {"2D": "NoOp", "Deep": "DeepExpression", "3D": "LookupGeo", "Camera": "NoOp", "Axis": "Axis", "Particle": "ParticleExpression"}

# Use the dictionary above to define the base node classes you want for each type.
# For any type you don't define, it will use a NoOp. Available types: 2D, 3D, Deep, Particle, Camera, Axis
# You shouldn't modify this except if you don't want to use DeepExpression nodes for deep stamps...
# ...or you have special plugins installed, like DeepNoOp and GeoNoOp
# StampClassesAlt = {"2D":"NoOp", "Deep":"DeepNoOp", "3D":"GeoNoOp"}
