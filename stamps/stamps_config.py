#------------------------------------------------------
# Stamps by Adrian Pueyo and Alexey Kuchinski
# Smart node connection system for Nuke
# adrianpueyo.com, 2018-2020
config_version= "v1.1"
date = "May 16 2020"
#-----------------------------------------------------
import nuke
import os
import re
# ----------------------------------------------
# INSTRUCTIONS:
# Modify this file as needed. Do not rename it.
# Place it in your python path (i.e. next to stamps.py, or in your /.nuke folder).
# ----------------------------------------------

# ----------------------------------------------
# 1. MAIN DEFAULTS
# ----------------------------------------------

STAMPS_SHORTCUT = "F8"

ANCHOR_STYLE = {
    "tile_color": 4294967041,
    "note_font_size": 20,
    }

STAMP_STYLE = {
    "tile_color": 16777217,
    "note_font_size": 20,
    "postage_stamp": 0,
    }

# Override tile_color for specific node classes, to be fancy.
AnchorClassColors = {"Camera":int('%02x%02x%02x%02x' % (255,255,255,1),16),}
WiredClassColors = {"Camera":int('%02x%02x%02x%02x' % (51,0,0,1),16),}


# ----------------------------------------------
# 2. CUSTOM FUNCTIONS
# ----------------------------------------------

def defaultTitle(node):
    '''
    defaultTitle(node) -> (str)title
    Returns a custom default Stamp title for a given node.
    Customize this function to return any string you want.
    If you return None, it will calculate the default title.
    '''
    
    name = node.name()

    # ALL THIS IS SAMPLE CODE, FEEL FREE TO REMOVE OR MODIFY IT
    # Example 1: Make "cam" the default Stamp title for the first Camera
    if "Camera" in node.Class() and not any([(i.knob("title") and i["title"].value() == "cam") for i in nuke.allNodes("NoOp")]):
        title = "cam"
        return title

    # Example 2: If the node has a file knob, take the part of the filename that goes before the frame numbers
    if node.knob("file"): # If node has knob "file"
        filepath = node.knob("file").value()
        if filepath: # If the value of the knob "file" is not empty
            filename = filepath.split("/")[-1] # 1. Take the file name only
            title = filename.split(".")[0] # 2. Take the part of the filename before any dots
            title = str(re.split("_v[0-9]*_",title)[-1]) # 3. Take the part that goes after the version
            title = title.replace("_render","") # 4. If the title includes "_render", remove it
            return title


    # If we don't return a string, stamps.py will calculate the default title by itself.
    return

def defaultTags(node):
    '''
    defaultTags(node) -> (list of str)tags
    Returns a custom default list of Stamp tags for a given node.
    Customize this function to return any string you want.
    If you return None, it will calculate the default tags.
    '''

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

KEEP_ORIGINAL_TAGS = True # True: Keep the default tags for the nodes, plus your custom-defined ones. False: Only keep the custom ones you can define below
DeepExceptionClasses = ["DeepToImage","DeepHoldout","DeepHoldout2"] # Nodes with "Deep" in their class that don't classify as Deep.
NodeExceptionClasses = ["Viewer"] # Nodes that won't accept stamps
ParticleExceptionClasses = ["ParticleToImage"] # Nodes with "Particle" in class and an input called "particles" that don't classify as particles.

# The next two constants define the node classes that will be ignored when looking for the title or tags of a node.
# This means, it will look for the node's first input instead, recursively, until it finds a node that doesn't belong to these classes.
TitleIgnoreClasses = ["NoOp", "Dot", "Reformat", "DeepReformat", "Crop"]
TagsIgnoreClasses = ["NoOp", "Dot", "Reformat", "DeepReformat", "Crop"]

AnchorClassesAlt = {"2D":"NoOp", "Deep":"DeepExpression", "3D":"EditGeo", "Particle":"ParticleExpression"}
AnchorClassesAlt = {"2D":"NoOp"}
StampClassesAlt = {"2D":"PostageStamp", "Deep":"DeepExpression", "3D":"LookupGeo", "Camera":"DummyCam", "Axis":"Axis","Particle":"ParticleExpression"}

# Use the dictionary above to define the base node classes you want for each type.
# For any type you don't define, it will use a NoOp. Available types: 2D, 3D, Deep, Particle, Camera, Axis
# You shouldn't modify this except if you don't want to use DeepExpression nodes for deep stamps...
# ...or you have special plugins installed, like DeepNoOp and GeoNoOp
# StampClassesAlt = {"2D":"NoOp", "Deep":"DeepNoOp", "3D":"GeoNoOp"}
