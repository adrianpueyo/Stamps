#------------------------------------------------------
# Stamps by Adrian Pueyo and Alexey Kuchinski
# Smart node connection system for Nuke
# adrianpueyo.com, 2018-2021
version= "v1.1"
date = "May 18 2021"
#-----------------------------------------------------

# Constants
STAMP_DEFAULTS = { "note_font_size":20, "hide_input":0 }
ANCHOR_DEFAULTS = { "tile_color" : int('%02x%02x%02x%02x' % (255,255,255,1),16),
        "autolabel": 'nuke.thisNode().knob("title").value()',
        "knobChanged":'stamps.anchorKnobChanged()',
        "onCreate":'if nuke.GUI:\n    try:\n        import stamps; stamps.anchorOnCreate()\n    except:\n        pass'}
WIRED_DEFAULTS = { "tile_color" : int('%02x%02x%02x%02x' % (1,0,0,1),16),
        "autolabel": 'nuke.thisNode().knob("title").value()',
        "knobChanged":'import stamps; stamps.wiredKnobChanged()'}
DeepExceptionClasses = ["DeepToImage","DeepHoldout","DeepHoldout2"] # Nodes with "Deep" in their class that don't classify as Deep.
NodeExceptionClasses = ["Viewer"] # Nodes that won't accept stamps
ParticleExceptionClasses = ["ParticleToImage"] # Nodes with "Particle" in class and an input called "particles" that don't classify as particles.
StampClasses = {"2D":"NoOp", "Deep":"DeepExpression"}
AnchorClassesAlt = {"2D":"NoOp", "Deep":"DeepExpression"}
StampClassesAlt = {"2D":"PostageStamp", "Deep":"DeepExpression", "3D":"LookupGeo", "Camera":"DummyCam", "Axis":"Axis", "Particle":"ParticleExpression"}
InputIgnoreClasses = ["NoOp", "Dot", "Reformat", "DeepReformat", "Crop"]
TitleIgnoreClasses = ["NoOp", "Dot", "Reformat", "DeepReformat", "Crop"]
TagsIgnoreClasses = ["NoOp", "Dot", "Reformat", "DeepReformat", "Crop"]

AnchorClassColors = {"Camera":int('%02x%02x%02x%02x' % (255,255,255,1),16),}
WiredClassColors = {"Camera":int('%02x%02x%02x%02x' % (51,0,0,1),16),}
STAMPS_HELP = "Stamps by Adrian Pueyo and Alexey Kuchinski.\nUpdated "+date
VERSION_TOOLTIP = "Stamps by Adrian Pueyo and Alexey Kuchinski.\nUpdated "+date+"."
STAMPS_SHORTCUT = "F8"
KEEP_ORIGINAL_TAGS = True

if 'Stamps_LastCreated' not in globals():
    Stamps_LastCreated = None

if 'Stamps_MenusLoaded' not in globals():
    Stamps_MenusLoaded = False

Stamps_LockCallbacks = False

import nuke
import nukescripts
import re
from functools import partial
import sys
import os

if sys.version_info[0] >= 3:
    unicode = str

# PySide import switch
try:
    if nuke.NUKE_VERSION_MAJOR < 11:
        from PySide import QtCore, QtGui, QtGui as QtWidgets
        from PySide.QtCore import Qt
    else:
        from PySide2 import QtWidgets, QtGui, QtCore
        from PySide2.QtCore import Qt
except ImportError:
    from Qt import QtCore, QtGui, QtWidgets

# Import stamps_config
# Optional: place the stamps_config.py file anywhere in your python path (i.e. in your /.nuke folder)
anchor_defaults = STAMP_DEFAULTS.copy()
anchor_defaults.update(ANCHOR_DEFAULTS)

wired_defaults = STAMP_DEFAULTS.copy()
wired_defaults.update(WIRED_DEFAULTS)
try:
    from stamps_config import *
    if ANCHOR_STYLE:
        anchor_defaults.update(ANCHOR_STYLE)
    if STAMP_STYLE:
        wired_defaults.update(STAMP_STYLE)
except:
    pass

#################################
### FUNCTIONS INSIDE OF BUTTONS
#################################
def wiredShowAnchor():
    n = nuke.thisNode()
    a_name = n.knob("anchor").value()
    if nuke.exists(a_name):
        nuke.show(nuke.toNode(a_name))
    elif n.inputs():
        nuke.show(n.input(0))

def wiredZoomAnchor():
    n = nuke.thisNode()
    a_name = n.knob("anchor").value()
    if nuke.exists(a_name):
        a = nuke.toNode(a_name)
        #nuke.show(a)
        nuke.zoom(nuke.zoom(),[a.xpos()+a.screenWidth()/2,a.ypos()+a.screenHeight()/2])
    elif n.inputs():
        ni = n.input(0)
        nuke.zoom(nuke.zoom(),[ni.xpos()+ni.screenWidth()/2,ni.ypos()+ni.screenHeight()/2])

def wiredZoomThis():
    n = nuke.thisNode()
    nuke.zoom(nuke.zoom(),[n.xpos(),n.ypos()])

def wiredStyle(n, style = 0):
    ''' Change the style of a wired stamp, based on some presets '''
    if "note_font_size" in wired_defaults.keys():
        size = wired_defaults["note_font_size"]
    else:
        size = 20
    nf = n["note_font"].value().split(" Bold")[0].split(" bold")[0]
    if style == 0: # DEFAULT
        n["note_font_size"].setValue(size)
        n["note_font_color"].setValue(0)
        n["note_font"].setValue(nf)
    elif style == 1: # BROKEN
        n["note_font_size"].setValue(size*2)
        n["note_font_color"].setValue(4278190335)
        n["note_font"].setValue(nf+" Bold")

def wiredGetStyle(n):
    ''' Check connection status of wired and set the style accordingly. '''
    if not isWired(n):
        return False
    if not n.inputs():
        wiredStyle(n,1)
    elif not isAnchor(n.input(0)):
        wiredStyle(n,1)
    elif n["anchor"].value() != n.input(0).name():
        wiredStyle(n,1)
    else:
        wiredStyle(n,0)

def wiredTagsAndBackdrops(n, updateSimilar=False):
    try:
        a = n.input(0)
        if not a:
            return
        a_tags = a["tags"].value().strip().strip(",")
        a_bd = backdropTags(a)
        an = n.knob("anchor").value()
        if updateSimilar:
            ns = [i for i in allWireds() if i.knob("anchor").value() == an]
        else:
            ns = [n]
        
        for n in ns:
            try:
                tags_knob = n.knob("tags")
                bd_knob = n.knob("backdrops")
                [i.setVisible(False) for i in [tags_knob, bd_knob]]
                if a_tags:
                    tags_knob.setValue("<i>{}</i>".format(a_tags))
                    tags_knob.setVisible(True)

                if len(a_bd) and a_bd != []:
                    bd_knob.setValue("<i>{}</i>".format(",".join(a_bd)))
                    bd_knob.setVisible(True)
            except:
                pass
    except:
        try:
            [i.setVisible(False) for i in [tags_knob, bd_knob]]
        except:
            pass

def wiredKnobChanged():
    global Stamps_LockCallbacks
    k = nuke.thisKnob()
    kn = k.name()
    if kn in ["xpos","ypos","reconnect_by_selection_this","reconnect_by_selection_similar"]:
        return
    n = nuke.thisNode()
    if Stamps_LockCallbacks == True:
        return
    ni = n.inputs()
    if n.knob("toReconnect") and n.knob("toReconnect").value() and nuke.GUI:
        if not ni:
            if n.knob("auto_reconnect_by_title") and n.knob("auto_reconnect_by_title").value() and n.knob("title"):
                n.knob("auto_reconnect_by_title").setValue(0)
                for a in allAnchors():
                    if a.knob("title") and a["title"].value() == n["title"].value():
                        n.knob("auto_reconnect_by_title").setValue(False)
                        nuke.thisNode().setInput(0,a)
                        n["anchor"].setValue(a.name())
                        wiredStyle(n)
                        return
            try:
                inp = n.knob("anchor").value()
                a = nuke.toNode(inp)
                if a.knob("title") and n.knob("title") and a["title"].value() == n["title"].value():
                    nuke.thisNode().setInput(0,a)
                    wiredStyle(n)
                else:
                    wiredStyle(n,1)
            except:
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
                        nuke.thisNode().setInput(0,a)
                    else:
                        wiredStyle(n,1)
                        n.setInput(0,None)
            except:
                pass
        n.knob("toReconnect").setValue(False)
    elif not ni:
        if nodeType(n)=="Particle" and not nuke.env["nukex"]:
            return
        wiredStyle(n,1)
        return
    elif kn == "selected": #First time it's this knob, it will activate the first if, then, ignore.
        return
    elif kn == "inputChange":
        wiredGetStyle(n)
    elif kn == "postage_stamp":
        n["postageStamp_show"].setVisible(True)
        n["postageStamp_show"].setValue(k.value())
    elif kn == "postageStamp_show":
        try:
            n["postage_stamp"].setValue(k.value())
        except:
            n["postageStamp_show"].setVisible(False)
    elif kn == "title":
        kv = k.value()
        if titleIsLegal(kv):
            if nuke.ask("Do you want to update the linked stamps' title?"):
                a = retitleAnchor(n) # Retitle anchor
                retitleWired(a) # Retitle wired stamps of anchor a
                return
        else:
            nuke.message("Please set a valid title.")
        try:
            n["title"].setValue(n["prev_title"].value())
        except:
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
                        n.knob("title").setValue(n.input(0).knob("title").value())
                        n.knob("prev_title").setValue(n.input(0).knob("title").value())
                    else:
                        n.setInput(0,None)
                        try:
                            n.setInput(0,nuke.toNode(n.knob("anchor").value()))
                        except:
                            pass
            wiredGetStyle(n)
        except:
            pass

    if kn == "showPanel":
        wiredTagsAndBackdrops(n)

def wiredOnCreate():
    n = nuke.thisNode()
    n.knob("toReconnect").setValue(1)
    for k in n.allKnobs():
        if k.name() not in ['wired_tab','identifier','lockCallbacks','toReconnect','title','prev_title','tags','backdrops','anchor','line1','anchor_label','show_anchor','zoom_anchor','stamps_label','zoomNext','selectSimilar','space_1','reconnect_label','reconnect_this','reconnect_similar','reconnect_all','space_2','advanced_reconnection','reconnect_by_title_label','reconnect_by_title_this','reconnect_by_title_similar', 'reconnect_by_title_selected', 'reconnect_by_selection_label','reconnect_by_selection_this','reconnect_by_selection_similar','reconnect_by_selection_selected','auto_reconnect_by_title','advanced_reconnection','line2','buttonHelp','version','postageStamp_show']:
            k.setFlag(0x0000000000000400)

def anchorKnobChanged():
    k = nuke.thisKnob()
    kn = k.name()
    if kn in ["xpos","ypos"]:
        return
    n = nuke.thisNode()
    if kn == "title":
        kv = k.value()
        if titleIsLegal(kv):
            if nuke.ask("Do you want to update the linked stamps' title?"):
                retitleWired(n) # Retitle wired stamps of anchor a
                return
        else:
            nuke.message("Please set a valid title.")
        try:
            n["title"].setValue(n["prev_title"].value())
        except:
            pass
    elif kn == "name":
        try:
            nn = anchor["prev_name"].value()
        except:
            nn = anchor.name()
        children = anchorWireds(n)
        for i in children:
            i.knob("anchor").setValue(nn)
        anchor["prev_name"].setValue(anchor.name())
    elif kn == "tags":
        for ni in allWireds():
            if ni.knob("anchor").value() == n.name():
                wiredTagsAndBackdrops(ni, updateSimilar=True)
                return

def anchorOnCreate():
    n = nuke.thisNode()
    for k in n.allKnobs():
        if k.name() not in ['anchor_tab','identifier','title','prev_title','prev_name','showing','tags','stamps_label','selectStamps','reconnectStamps','zoomNext','createStamp','buttonHelp','line1','line2','version']:
            k.setFlag(0x0000000000000400)
    try:
        nn = n["prev_name"].value()
    except:
        nn = n.name()
    children = anchorWireds(n)
    for i in children:
        i.knob("anchor").setValue(nn)
    n["prev_name"].setValue(n.name())
    return

def retitleAnchor(ref = ""):
    '''
    Retitle Anchor of current wired stamp to match its title.
    returns: anchor node
    ''' 
    if ref == "":
        ref = nuke.thisNode()
    try:
        ref_title = ref["title"].value()
        if ref_title.strip() != "":
            ref_title = ref_title.strip()
        ref_anchor = ref["anchor"].value()
        na = nuke.toNode(ref_anchor)
        for kn in ["title","prev_title"]:
            na[kn].setValue(ref_title)
        ref["prev_title"].setValue(ref_title)
        return na
    except:
        return None

def retitleWired(anchor = ""):
    '''
    Retitle wired stamps connected to supplied anchor
    '''
    if anchor == "":
        return
    try:
        anchor_title = anchor["title"].value()
        anchor_name = anchor.name()
        for nw in allWireds():
            if nw["anchor"].value() == anchor_name:
                nw["title"].setValue(anchor_title)
                nw["prev_title"].setValue(anchor_title)
        return True
    except:
        pass

def wiredSelectSimilar(anchor_name = ""):
    if anchor_name=="":
        anchor_name = nuke.thisNode().knob("anchor").value()
    for i in allWireds():
        if i.knob("anchor").value() == anchor_name:
            i.setSelected(True)

def wiredReconnect(n=""):
    succeeded=True
    if n=="":
        n = nuke.thisNode()
    try:
        anchor = nuke.toNode(n.knob("anchor").value())
        if not anchor:
            succeeded = False
        n.setInput(0,anchor)
    except:
        succeeded = False
    try:
        wiredGetStyle(n)
    except:
        pass
    return succeeded

def wiredReconnectSimilar(anchor_name = ""):
    if anchor_name=="":
        anchor_name = nuke.thisNode().knob("anchor").value()
    for i in nuke.allNodes():
        if isWired(i) and i.knob("anchor").value() == anchor_name:
            reconnectErrors = 0
            try:
                i.knob("reconnect_this").execute()
            except:
                reconnectErrors += 1
            finally:
                if reconnectErrors > 0:
                    nuke.message("Couldn't reconnect {} nodes".format(str(reconnectErrors)))
        wiredGetStyle(i)

def wiredReconnectAll():
    for i in nuke.allNodes():
        if isWired(i):
            reconnectErrors = 0
            try:
                i.knob("reconnect_this").execute()
            except:
                reconnectErrors += 1
            finally:
                if reconnectErrors > 0:
                    nuke.message("Couldn't reconnect {} nodes".format(str(reconnectErrors)))

def wiredReconnectByTitle(title=""):
    #1. Find matching nodes.
    n = nuke.thisNode()
    if title=="":
        title = n.knob("title").value()
    matches = []
    for i in nuke.allNodes():
        if isAnchor(i) and i.knob("title").value() == title:
            matches.append(i)

    #2. Do what's necessary
    num_matches = len(matches)
    if num_matches == 1: # One match -> Connect
        anchor = matches[0]
        n["anchor"].setValue(anchor.name())
        n.setInput(0,anchor)
    elif num_matches > 1:
        # More than one match...
        ns = nuke.selectedNodes()
        if ns and len(ns) == 1 and isAnchor(ns[0]):
            # Exactly one anchor selected and title matches -> connect
            if ns[0].knob("title").value() == title:
                n["anchor"].setValue(ns[0].name())
                n.setInput(0,ns[0])
                n.knob("reconnect_this").execute()
        else:
            # Selection not matching -> Message asking to select a specific anchor.
            nuke.message("More than one Anchor Stamp found with the same title. Please select the one you like in the Node Graph and click this button again.")
    elif num_matches == 0:
        nuke.message("No Anchor Stamps with title '{}' found in the script.".format(title))

def wiredReconnectByTitleSimilar(title=""):
    #1. Find matching anchors.
    n = nuke.thisNode()
    if title=="":
        title = n.knob("title").value()
    matches = []
    for i in allAnchors():
        if i.knob("title").value() == title:
            matches.append(i)

    #2. Do what's necessary
    num_matches = len(matches)
    if num_matches == 0:
        # No matches -> abort
        nuke.message("No Anchor Stamps with title '{}' found in the script.")
        return

    anchor_name = n.knob("anchor").value()
    siblings = [i for i in nuke.allNodes() if isWired(i) and i.knob("anchor").value() == anchor_name]

    if num_matches == 1: # One match -> Connect
        anchor = matches[0]
        for s in siblings:
            s["anchor"].setValue(anchor.name())
            s.setInput(0,anchor)
            wiredStyle(s,0)
            s.knob("reconnect_this").execute()
    elif num_matches > 1:
        # More than one match...
        ns = nuke.selectedNodes()
        if ns and len(ns) == 1 and isAnchor(ns[0]):
            # Exactly one anchor selected and title matches -> connect
            if ns[0].knob("title").value() == title:
                for s in siblings:
                    s["anchor"].setValue(ns[0].name())
                    s.setInput(0,ns[0])
                    wiredStyle(s,0)
                    s.knob("reconnect_this").execute()
        else:
            # Selection not matching -> Message asking to select a specific anchor.
            nuke.message("More than one Anchor Stamp found with the same title. Please select the one you like in the Node Graph and click this button again.")

def wiredReconnectByTitleSelected():
    #1. Find matching anchors.
    ns = nuke.selectedNodes()
    ns = [i for i in ns if isWired(i)]

    for n in ns:
        title = n.knob("title").value()
        matches = []
        for i in allAnchors():
            if i.knob("title").value() == title:
                matches.append(i)

        #2. Do what's necessary only for the one match cases
        anchor_name = n.knob("anchor").value()
        if len(matches) == 1: # One match -> Connect
            anchor = matches[0]
            n["anchor"].setValue(anchor.name())
            n.setInput(0,anchor)
            wiredStyle(n,0)
            n.knob("reconnect_this").execute()

def wiredReconnectBySelection():
    global Stamps_LockCallbacks
    n = nuke.thisNode()
    ns = nuke.selectedNodes()

    if not len(ns):
        nuke.message("Please select an Anchor Stamp first.")
    elif len(ns)>1:
        nuke.message("Multiple nodes selected, please select only one Anchor Stamp.")
    else:
        if not isAnchor(ns[0]):
            nuke.message("Please select an Anchor Stamp.")
        else:
            Stamps_LockCallbacks = True
            n["anchor"].setValue(ns[0].name())
            n["title"].setValue(ns[0]["title"].value())
            n.setInput(0,ns[0])
            wiredGetStyle(n)
            Stamps_LockCallbacks = False
            n.knob("reconnect_this").execute()

def wiredReconnectBySelectionSimilar():
    global Stamps_LockCallbacks
    n = nuke.thisNode()
    ns = nuke.selectedNodes()

    if not len(ns):
        nuke.message("Please select an Anchor Stamp first.")
    elif len(ns)>1:
        nuke.message("Multiple nodes selected, please select only one Anchor Stamp.")
    elif not isAnchor(ns[0]):
        nuke.message("Please select an Anchor Stamp.")
    else:
        anchor_name = n.knob("anchor").value()
        siblings = [i for i in nuke.allNodes() if isWired(i) and i.knob("anchor").value() == anchor_name]
        for s in siblings:
            Stamps_LockCallbacks = True
            s["anchor"].setValue(ns[0].name())
            s["title"].setValue(ns[0]["title"].value())
            s.setInput(0,ns[0])
            wiredStyle(s,0)
            Stamps_LockCallbacks = False
            s.knob("reconnect_this").execute()

def wiredReconnectBySelectionSelected():
    global Stamps_LockCallbacks
    n = nuke.thisNode()
    ns = nuke.selectedNodes()

    if not len(ns):
        nuke.message("Please select one Anchor plus one or more Stamps first.")
        return

    anchors = []
    stamps = []
    for i in ns:
        if isAnchor(i):
            anchors.append(i)
        if isWired(i):
            stamps.append(i)

    if len(anchors) != 1:
        nuke.message("Please select one Anchor, plus one or more Stamps.")
        return
    else:
        anchor = anchors[0]

    if not len(stamps):
        nuke.message("Please, also select one or more Stamps that you want to reconnect to the selected Anchor.")

    for s in stamps:
        Stamps_LockCallbacks = True
        s["anchor"].setValue(anchor.name())
        s["title"].setValue(anchor["title"].value())
        s.setInput(0,anchor)
        wiredStyle(s,0)
        Stamps_LockCallbacks = False
        s.knob("reconnect_this").execute()

def anchorReconnectWired(anchor = ""):
    if anchor=="":
        anchor = nuke.thisNode()
    anchor_name = anchor.name()
    for i in allWireds():
        if i.knob("anchor").value() == anchor_name:
            reconnectErrors = 0
            try:
                i.setInput(0,anchor)
            except:
                reconnectErrors += 1
            finally:
                if reconnectErrors > 0:
                    nuke.message("Couldn't reconnect {} nodes".format(str(reconnectErrors)))

def wiredZoomNext(anchor_name = ""):
    if anchor_name=="":
        anchor_name = nuke.thisNode().knob("anchor").value()
    anchor = nuke.toNode(anchor_name)
    showing_knob = anchor.knob("showing")
    showing_value = showing_knob.value()
    i = 0
    for ni in allWireds():
        if ni.knob("anchor").value() == anchor_name:
            if i == showing_value:
                nuke.zoom(1.5,[ni.xpos()+ni.screenWidth()/2,ni.ypos()+ni.screenHeight()/2])
                showing_knob.setValue(i+1)
                return
            i+=1
    showing_knob.setValue(0)
    nuke.message("Couldn't find any more similar wired stamps.")

def anchorSelectWireds(anchor = ""):
    if anchor == "":
        try:
            anchor = nuke.selectedNode()
        except:
            pass
    if isAnchor(anchor):
        anchor.setSelected(False)
        wiredSelectSimilar(anchor.name())

def anchorWireds(anchor = ""):
    ''' Returns a list of the children stamps to the anchor with the specified name '''
    if anchor == "":
        try:
            anchor = nuke.selectedNode()
        except:
            pass
    if isAnchor(anchor):
        try:
            nn = anchor["prev_name"].value()
        except:
            nn = anchor.name()
        children = [i for i in allWireds() if i.knob("anchor").value() == nn]
        return children

wiredOnCreate_code = """if nuke.GUI:
    try:
        import stamps; stamps.wiredOnCreate()
    except:
        pass
"""

wiredReconnectToTitle_code = """n = nuke.thisNode()
try:
    nt = n.knob("title").value()
    for a in nuke.allNodes():
        if a.knob("identifier").value() == "anchor" and a.knob("title").value() == nt:
            n.setInput(0,a)
            break
except:
    nuke.message("Unable to reconnect.")
"""

wiredReconnect_code = """n = nuke.thisNode()
try:
    n.setInput(0,nuke.toNode(n.knob("anchor").value()))
except:
    nuke.message("Unable to reconnect.")
try:
    import stamps
    stamps.wiredGetStyle(n)
except:
    pass
"""

#################################
### STAMP, ANCHOR, WIRED
#################################

def anchor(title = "", tags = "", input_node = "", node_type = "2D"):
    ''' Anchor Stamp '''
    try:
        n = nuke.createNode(AnchorClassesAlt[node_type])
    except:
        try:
            n = nuke.createNode(StampClasses[node_type])
        except:
            n = nuke.createNode("NoOp")
    name = getAvailableName("Anchor",rand=True)
    n["name"].setValue(name)
    # Set default knob values
    for i,j in anchor_defaults.items():
        try:
            n.knob(i).setValue(j)
        except:
            pass

    if node_type in AnchorClassColors:
        try:
            n["tile_color"].setValue(AnchorClassColors[node_type])
        except:
            pass

    for k in n.allKnobs():
        k.setFlag(0x0000000000000400)

    # Main knobs
    anchorTab_knob = nuke.Tab_Knob('anchor_tab','Anchor Stamp')
    identifier_knob = nuke.Text_Knob('identifier','identifier', 'anchor')
    identifier_knob.setVisible(False)
    title_knob = nuke.String_Knob('title','Title:', title)
    title_knob.setTooltip("Displayed name on the Node Graph for this Stamp and its Anchor.\nIMPORTANT: This is only for display purposes, and is different from the real/internal name of the Stamps.")
    prev_title_knob = nuke.Text_Knob('prev_title','', title)
    prev_title_knob.setVisible(False)
    prev_name_knob = nuke.Text_Knob('prev_name','', name)
    prev_name_knob.setVisible(False)
    showing_knob = nuke.Int_Knob('showing','', 0)
    showing_knob.setVisible(False)
    tags_knob = nuke.String_Knob('tags','Tags', tags)
    tags_knob.setTooltip("Comma-separated tags you can define for each Anchor, that will help you find it when invoking the Stamp Selector by pressing the Stamps shortkey with nothing selected.")
    for k in [anchorTab_knob, identifier_knob, title_knob, prev_title_knob, prev_name_knob, showing_knob, tags_knob]:
        n.addKnob(k)

    n.addKnob(nuke.Text_Knob("line1", "", "")) # Line

    stampsLabel_knob = nuke.Text_Knob('stamps_label','Stamps:', " ")
    stampsLabel_knob.setFlag(nuke.STARTLINE)

    # Buttons
    buttonSelectStamps = nuke.PyScript_Knob("selectStamps","select","stamps.wiredSelectSimilar(nuke.thisNode().name())")
    buttonSelectStamps.setTooltip("Select all of this Anchor's Stamps.")
    buttonReconnectStamps = nuke.PyScript_Knob("reconnectStamps","reconnect","stamps.anchorReconnectWired()")
    buttonSelectStamps.setTooltip("Reconnect all of this Anchor's Stamps.")
    buttonZoomNext = nuke.PyScript_Knob("zoomNext","zoom next","stamps.wiredZoomNext(nuke.thisNode().name())")
    buttonZoomNext.setTooltip("Navigate to this Anchor's next Stamp on the Node Graph.")
    buttonCreateStamp = nuke.PyScript_Knob("createStamp","new","stamps.stampCreateWired(nuke.thisNode())")
    buttonCreateStamp.setTooltip("Create a new Stamp for this Anchor.")

    for k in [stampsLabel_knob, buttonCreateStamp, buttonSelectStamps, buttonReconnectStamps, buttonZoomNext]:
        n.addKnob(k)

    # Version (for future update checks)
    n.addKnob(nuke.Text_Knob("line2", "", "")) # Line
    buttonHelp = nuke.PyScript_Knob("buttonHelp","Help","stamps.showHelp()")
    version_knob = nuke.Text_Knob('version',' ','<a href="http://www.nukepedia.com/gizmos/other/stamps" style="color:#666;text-decoration: none;"><span style="color:#666"> <big>Stamps {}</big></b></a>'.format(version))
    version_knob.setTooltip(VERSION_TOOLTIP)
    version_knob.clearFlag(nuke.STARTLINE)
    for k in [buttonHelp, version_knob]:
        n.addKnob(k)
    n["help"].setValue(STAMPS_HELP)

    return n

def wired(anchor):
    ''' Wired Stamp '''
    global Stamps_LastCreated
    Stamps_LastCreated = anchor.name()

    node_type = nodeType(realInput(anchor))
    try:
        n = nuke.createNode(StampClassesAlt[node_type])
    except:
        try:
            n = nuke.createNode(StampClasses[node_type])
        except:
            n = nuke.createNode("NoOp")
    n["name"].setValue(getAvailableName("Stamp"))
    # Set default knob values
    for i,j in wired_defaults.items():
        try:
            n[i].setValue(j)
        except:
            pass

    for k in n.allKnobs():
        k.setFlag(0x0000000000000400)

    if node_type in WiredClassColors:
        n["tile_color"].setValue(WiredClassColors[node_type])
    n["onCreate"].setValue(wiredOnCreate_code)

    # Inner functionality knobs
    wiredTab_knob = nuke.Tab_Knob('wired_tab','Wired Stamp')
    identifier_knob = nuke.Text_Knob('identifier','identifier', 'wired')
    identifier_knob.setVisible(False)
    lock_knob = nuke.Int_Knob('lockCallbacks','',0) #Lock callbacks...
    lock_knob.setVisible(False)
    toReconnect_knob = nuke.Boolean_Knob("toReconnect")
    toReconnect_knob.setVisible(False)
    title_knob = nuke.String_Knob('title','Title:', anchor["title"].value())
    title_knob.setTooltip("Displayed name on the Node Graph for this Stamp and its Anchor.\nIMPORTANT: This is only for display purposes, and is different from the real/internal name of the Stamps.")
    prev_title_knob = nuke.Text_Knob('prev_title','', anchor["title"].value())
    prev_title_knob.setVisible(False)
    tags_knob = nuke.Text_Knob('tags','Tags:', " ")
    tags_knob.setTooltip("Tags of this stamp's Anchor, for information purpose only.\nClick \"show anchor\" to change them.")
    backdrops_knob = nuke.Text_Knob('backdrops','Backdrops:', " ")
    backdrops_knob.setTooltip("Labels of backdrop nodes which contain this stamp's Anchor.")
    postageStamp_knob = nuke.Boolean_Knob("postageStamp_show","postage stamp")
    postageStamp_knob.setTooltip("Enable the postage stamp thumbnail in this node.\nYou're seeing this because the class of this node includes the postage_stamp knob.")
    postageStamp_knob.setFlag(nuke.STARTLINE)
    postageStamp_knob.setVisible("postage_stamp" in n.knobs() and nodeType(n) == "2D")

    anchor_knob = nuke.String_Knob('anchor','Anchor', anchor.name()) # This goes in the advanced part

    for k in [wiredTab_knob, identifier_knob, lock_knob, toReconnect_knob, title_knob, prev_title_knob, tags_knob, backdrops_knob]:
        n.addKnob(k)

    wiredTab_knob.setFlag(0) # Open the tab

    n.addKnob(nuke.Text_Knob("line1", "", "")) # Line
    n.addKnob(postageStamp_knob)

    ### Buttons

    # Anchor
    anchorLabel_knob = nuke.Text_Knob('anchor_label','Anchor:', " ")
    anchorLabel_knob.setFlag(nuke.STARTLINE)
    buttonShowAnchor = nuke.PyScript_Knob("show_anchor"," show anchor ","stamps.wiredShowAnchor()")
    buttonShowAnchor.setTooltip("Show the properties panel for this Stamp's Anchor.")
    buttonShowAnchor.clearFlag(nuke.STARTLINE)
    buttonZoomAnchor = nuke.PyScript_Knob("zoom_anchor","zoom anchor","stamps.wiredZoomAnchor()")
    buttonZoomAnchor.setTooltip("Navigate to this Stamp's Anchor on the Node Graph.")

    for k in [anchorLabel_knob, buttonShowAnchor, buttonZoomAnchor]:
        n.addKnob(k)

    # Stamps
    stampsLabel_knob = nuke.Text_Knob('stamps_label','Stamps:', " ")
    stampsLabel_knob.setFlag(nuke.STARTLINE)
    buttonZoomNext = nuke.PyScript_Knob("zoomNext"," zoom next ","stamps.wiredZoomNext()")
    buttonZoomNext.setTooltip("Navigate to this Stamp's next sibling on the Node Graph.")
    buttonZoomNext.clearFlag(nuke.STARTLINE)
    buttonSelectSimilar = nuke.PyScript_Knob("selectSimilar"," select similar ","stamps.wiredSelectSimilar()")
    buttonSelectSimilar.clearFlag(nuke.STARTLINE)
    buttonSelectSimilar.setTooltip("Select all similar Stamps to this one on the Node Graph.")

    space_1_knob = nuke.Text_Knob("space_1", "", " ")
    space_1_knob.setFlag(nuke.STARTLINE)

    for k in [stampsLabel_knob, buttonZoomNext, buttonSelectSimilar, space_1_knob]:
        n.addKnob(k)

    # Reconnect Simple
    reconnectLabel_knob = nuke.Text_Knob('reconnect_label','Reconnect:', " ")
    reconnectLabel_knob.setTooltip("Reconnect by the stored Anchor name.")
    reconnectLabel_knob.setFlag(nuke.STARTLINE)
    buttonReconnectThis = nuke.PyScript_Knob("reconnect_this","this",wiredReconnect_code)
    buttonReconnectThis.setTooltip("Reconnect this Stamp to its Anchor, by its stored Anchor name.")
    buttonReconnectSimilar = nuke.PyScript_Knob("reconnect_similar","similar","stamps.wiredReconnectSimilar()")
    buttonReconnectSimilar.setTooltip("Reconnect this Stamp and similar ones to their Anchor, by their stored anchor name.")
    buttonReconnectAll = nuke.PyScript_Knob("reconnect_all","all","stamps.wiredReconnectAll()")
    buttonReconnectAll.setTooltip("Reconnect all the Stamps to their Anchors, by their stored anchor names.")
    space_2_knob = nuke.Text_Knob("space_2", "", " ")
    space_2_knob.setFlag(nuke.STARTLINE)

    for k in [reconnectLabel_knob, buttonReconnectThis, buttonReconnectSimilar, buttonReconnectAll, space_2_knob]:
        n.addKnob(k)

    # Advanced Reconnection
    advancedReconnection_knob = nuke.Tab_Knob('advanced_reconnection', 'Advanced Reconnection', nuke.TABBEGINCLOSEDGROUP)
    n.addKnob(advancedReconnection_knob)

    reconnectByTitleLabel_knob = nuke.Text_Knob('reconnect_by_title_label','<font color=gold>By Title:', " ")
    reconnectByTitleLabel_knob.setFlag(nuke.STARTLINE)
    reconnectByTitleLabel_knob.setTooltip("Reconnect by searching for a matching title.")
    buttonReconnectByTitleThis = nuke.PyScript_Knob("reconnect_by_title_this","this","stamps.wiredReconnectByTitle()")
    buttonReconnectByTitleThis.setTooltip("Look for an Anchor that shares this Stamp's title, and connect this Stamp to it.\nIMPORTANT: Use this carefully, and only when the normal reconnection doesn't work.")
    buttonReconnectByTitleSimilar = nuke.PyScript_Knob("reconnect_by_title_similar","similar","stamps.wiredReconnectByTitleSimilar()")
    buttonReconnectByTitleSimilar.setTooltip("Look for an Anchor that shares this Stamp's title, and connect this Stamp and similar ones to it.\nIMPORTANT: Use this carefully, and only when the normal reconnection doesn't work.")
    buttonReconnectByTitleSelected = nuke.PyScript_Knob("reconnect_by_title_selected","selected","stamps.wiredReconnectByTitleSelected()")
    buttonReconnectByTitleSelected.setTooltip("For each Stamp selected, look for an Anchor that shares its title, and connect to it.\nIMPORTANT: Use this carefully, and only when the normal reconnection doesn't work.")
    reconnectBySelectionLabel_knob = nuke.Text_Knob('reconnect_by_selection_label','<font color=orangered>By Selection:', " ")
    reconnectBySelectionLabel_knob.setFlag(nuke.STARTLINE)
    reconnectBySelectionLabel_knob.setTooltip("Force reconnect to a selected Anchor.")
    buttonReconnectBySelectionThis = nuke.PyScript_Knob("reconnect_by_selection_this","this","stamps.wiredReconnectBySelection()")
    buttonReconnectBySelectionThis.setTooltip("Force reconnect this Stamp to a selected Anchor, whatever its name or title.\nIMPORTANT: Use this carefully, and only when the normal reconnection doesn't work.")
    buttonReconnectBySelectionSimilar = nuke.PyScript_Knob("reconnect_by_selection_similar","similar","stamps.wiredReconnectBySelectionSimilar()")
    buttonReconnectBySelectionSimilar.setTooltip("Force reconnect this Stamp and similar ones to a selected Anchor, whatever its name or title.\nIMPORTANT: Use this carefully, and only when the normal reconnection doesn't work.")
    buttonReconnectBySelectionSelected = nuke.PyScript_Knob("reconnect_by_selection_selected","selected","stamps.wiredReconnectBySelectionSelected()")
    buttonReconnectBySelectionSelected.setTooltip("Force reconnect all selected Stamps to an also selected Anchor, whatever its name or title.\nIMPORTANT: Use this carefully, and only when the normal reconnection doesn't work.")
    
    checkboxReconnectByTitleOnCreation = nuke.Boolean_Knob("auto_reconnect_by_title","<font color=#ED9977>&nbsp; auto-reconnect by title")
    checkboxReconnectByTitleOnCreation.setTooltip("When creating this stamp again (like on copy-paste), auto-reconnect it by title instead of doing it by the saved anchor's name, and auto-turn this off immediately.\nIMPORTANT: Should be off by default. Only use this for setting up templates.")
    checkboxReconnectByTitleOnCreation.setFlag(nuke.STARTLINE)

    advancedReconnection_knob = nuke.Tab_Knob('advanced_reconnection', 'Advanced Reconnection', -1)

    for k in [reconnectByTitleLabel_knob, buttonReconnectByTitleThis, buttonReconnectByTitleSimilar, buttonReconnectByTitleSelected,
              reconnectBySelectionLabel_knob, buttonReconnectBySelectionThis, buttonReconnectBySelectionSimilar, buttonReconnectBySelectionSelected,
              anchor_knob, checkboxReconnectByTitleOnCreation,advancedReconnection_knob]:
        n.addKnob(k)

    # Version (for future update checks)
    line_knob = nuke.Text_Knob("line2", "", "")
    buttonHelp = nuke.PyScript_Knob("buttonHelp","Help","stamps.showHelp()")
    version_knob = nuke.Text_Knob('version',' ','<a href="http://www.nukepedia.com/gizmos/other/stamps" style="color:#666;text-decoration: none;"><span style="color:#666"> <big>Stamps {}</big></b></a>'.format(version))
    version_knob.clearFlag(nuke.STARTLINE)
    version_knob.setTooltip(VERSION_TOOLTIP)
    for k in [line_knob, buttonHelp, version_knob]:
        n.addKnob(k)

    # Hide input while not messing position
    x,y = n.xpos(),n.ypos()
    nw = n.screenWidth()
    aw = anchor.screenWidth()
    n.setInput(0,anchor)
    n["hide_input"].setValue(True)
    n["xpos"].setValue(x-nw/2+aw/2)
    n["ypos"].setValue(y)

    n["help"].setValue(STAMPS_HELP)

    wiredTagsAndBackdrops(n)

    return n
    Stamps_LastCreated = anchor.name()

def getAvailableName(name = "Untitled", rand=False):
    ''' Returns a node name starting with @name followed by a number, that doesn't exist already '''
    import random
    i = 1
    while True:
        if not rand:
            available_name = name+str(i)
        else:
            available_name = name+str('_%09x' % random.randrange(9**12))
        if not nuke.exists(available_name):
            return available_name
        i += 1

#################################
### CLASSES
#################################

class AnchorSelector(QtWidgets.QDialog):
    '''
    Panel to select one or more anchors, showing the different anchors on dropdowns based on their tags.
    '''

    # TODO LATER:
    # - Have three columns, distinguished, like an asset loader. Maybe even with border color?
    # - Ability to show and hide backdrops (would turn off their visibility or "bookmark"):
    #    - Checkbox named "show backdrops" maybe that gets saved in nuke root. If you want it permanent you can save it inside stamps_config.

    def __init__(self):
        super(AnchorSelector, self).__init__()
        self.setWindowTitle("Stamps: Select an Anchor.")
        self.chosen_anchors = []
        self.initUI()
        #self.setFixedSize(self.sizeHint())
        #self.setFixedWidth(self.sizeHint()[0])
        self.custom_anchors_lineEdit.setFocus()

    def initUI(self):
        # Find all anchors and get all tags
        self.findAnchorsAndTags() # Generate a dictionary: {"Camera1":["Camera","New","Custom1"],"Read":["2D","New"]}
        self.custom_chosen = False # If clicked OK on the custom lineedit

        # Header
        self.headerTitle = QtWidgets.QLabel("Anchor Stamp Selector")
        self.headerTitle.setStyleSheet("font-weight:bold;color:#CCCCCC;font-size:14px;")
        self.headerSubtitle = QtWidgets.QLabel("Select an Anchor to make a Stamp for.<br/><b><small style='color:#CCC'>Right click on the OK buttons for multiple selection.</small></b>")
        self.headerSubtitle.setStyleSheet("color:#999")

        self.headerLine = QtWidgets.QFrame()
        self.headerLine.setFrameShape(QtWidgets.QFrame.HLine)
        self.headerLine.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.headerLine.setLineWidth(0)
        self.headerLine.setMidLineWidth(1)
        self.headerLine.setFrameShadow(QtWidgets.QFrame.Sunken)


        # Layouts
        self.master_layout = QtWidgets.QVBoxLayout()
        self.master_layout.addWidget(self.headerTitle)
        self.master_layout.addWidget(self.headerSubtitle)
        #self.master_layout.addWidget(self.headerLine)

        # Main Scroll area
        self.scroll_content = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QVBoxLayout()

        self.scroll_content.setLayout(self.scroll_layout)

        # Scroll Area Properties
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.scroll_content)
        self.scroll.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Sunken)

        self.grid = QtWidgets.QGridLayout()
        #self.grid.setSpacing(0)
        self.lower_grid = QtWidgets.QGridLayout()

        self.scroll_layout.addLayout(self.grid)
        self.scroll_layout.addStretch()
        self.scroll_layout.setContentsMargins(2,2,2,2)
        self.grid.setContentsMargins(2,2,2,2)
        self.grid.setSpacing(5)

        num_tags = len(self._all_tags)

        middleLine = QtWidgets.QFrame()
        middleLine.setStyleSheet("margin-top:20px")
        middleLine.setFrameShape(QtWidgets.QFrame.HLine)
        middleLine.setFrameShadow(QtWidgets.QFrame.Sunken)
        middleLine.setLineWidth(0)
        middleLine.setMidLineWidth(1)
        middleLine.setFrameShadow(QtWidgets.QFrame.Sunken)

        if len(list(filter(None,self._all_tags)))>0:
            tags_label = QtWidgets.QLabel("<i>Tags")
            tags_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
            tags_label.setStyleSheet("color:#666;margin:0px;padding:0px;padding-left:3px")
            #self.grid.addWidget(middleLine,tag_num*10-6,1,2,3)
            self.grid.addWidget(tags_label,0,0,1,3)

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
                #self.grid.addWidget(middleLine,tag_num*10-5,0,1,3)
                self.grid.addWidget(backdrops_label,tag_num*10-3,0,1,1)

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

                if cur_name not in tag_dict.keys():
                    continue
                
                if tag in tag_dict[cur_name]:
                    if title_repeated:
                        anchors_dropdown.addItem("{0} ({1})".format(cur_title, cur_name), cur_name)
                    else:
                        anchors_dropdown.addItem(cur_title, cur_name)

            ok_btn = QtWidgets.QPushButton("OK")
            ok_btn.clicked.connect(partial(self.okPressed,dropdown=anchors_dropdown))

            ok_btn.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            ok_btn.setMaximumWidth(ok_btn.sizeHint().width()-19)
            ok_btn.customContextMenuRequested.connect(partial(self.okRightClicked,anchors_dropdown))


            self.grid.addWidget(tag_label,tag_num*10+1,0)
            self.grid.addWidget(anchors_dropdown,tag_num*10+1,1)
            self.grid.addWidget(ok_btn,tag_num*10+1,2)


        # ALL
        tag_num = len(self._all_tags_and_backdrops)
        all_tag_label = QtWidgets.QLabel("<b>all</b>: ")
        all_tag_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.all_anchors_dropdown = QtWidgets.QComboBox()

        all_tag_texts = [] # List of all texts of the items (usually equals the "title", or "title (name)")
        all_tag_names = [i for i in self._all_anchors_names] # List of all real anchor names of the items.
        for i, cur_name in enumerate(self._all_anchors_names):
            cur_title = self._all_anchors_titles[i]
            title_repeated = self._all_anchors_titles.count(cur_title)
            if title_repeated > 1:
                all_tag_texts.append("{0} ({1})".format(cur_title, cur_name))
            else:
                all_tag_texts.append(cur_title)
        self.all_tag_sorted = sorted(list(zip(all_tag_texts,all_tag_names)),  key=lambda pair: pair[0].lower())

        for [text, name] in self.all_tag_sorted:
            self.all_anchors_dropdown.addItem(text, name)

        all_ok_btn = QtWidgets.QPushButton("OK")
        all_ok_btn.clicked.connect(partial(self.okPressed,dropdown=self.all_anchors_dropdown))

        all_ok_btn.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        all_ok_btn.customContextMenuRequested.connect(partial(self.okRightClicked,self.all_anchors_dropdown))

        self.lower_grid.addWidget(all_tag_label,tag_num,0)
        self.lower_grid.addWidget(self.all_anchors_dropdown,tag_num,1)
        self.lower_grid.addWidget(all_ok_btn,tag_num,2)
        tag_num += 1

        # POPULAR
        tag_num = len(self._all_tags_and_backdrops)+10
        popular_tag_label = QtWidgets.QLabel("<b>popular</b>: ")
        popular_tag_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.popular_anchors_dropdown = QtWidgets.QComboBox()
        all_tag_texts = [] # List of all texts of the items (usually equals the "title", or "title (name)")
        all_tag_names = [i for i in self._all_anchors_names] # List of all real anchor names of the items.
        all_tag_count = [stampCount(i) for i in self._all_anchors_names] # Number of stamps for each anchor!

        popular_tag_texts = [] # List of popular texts of the items (usually equals the "title (x2)", or "title (name) (x2)")
        sorted_names_and_titles = [(x,y) for (_,x,y) in sorted(list(zip(all_tag_count,self._all_anchors_names,self._all_anchors_titles)),reverse=True)]
        popular_anchors_names = [x for x,_ in sorted_names_and_titles]
        popular_anchors_titles = [x for _,x in sorted_names_and_titles]
        #popular_anchors_titles = [x for _,x in sorted(zip(all_tag_count,self._all_anchors_titles),reverse=True)]
        popular_anchors_count = sorted(all_tag_count,reverse=True)

        for i, cur_name in enumerate(popular_anchors_names):
            cur_title = popular_anchors_titles[i]
            title_repeated = popular_anchors_titles.count(cur_title)
            if title_repeated > 1:
                popular_tag_texts.append("{0} ({1}) (x{2})".format(cur_title, cur_name,str(popular_anchors_count[i])))
            else:
                popular_tag_texts.append("{0} (x{1})".format(cur_title, str(popular_anchors_count[i])))

        for i, text in enumerate(popular_tag_texts):
            self.popular_anchors_dropdown.addItem(text, popular_anchors_names[i])

        popular_ok_btn = QtWidgets.QPushButton("OK")
        popular_ok_btn.clicked.connect(partial(self.okPressed,dropdown=self.popular_anchors_dropdown))

        popular_ok_btn.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        popular_ok_btn.customContextMenuRequested.connect(partial(self.okRightClicked,self.popular_anchors_dropdown))

        self.lower_grid.addWidget(popular_tag_label,tag_num,0)
        self.lower_grid.addWidget(self.popular_anchors_dropdown,tag_num,1)
        self.lower_grid.addWidget(popular_ok_btn,tag_num,2)
        tag_num += 1

        # LineEdit with completer
        custom_tag_label = QtWidgets.QLabel("<b>by title</b>: ")
        custom_tag_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.custom_anchors_lineEdit = QtWidgets.QLineEdit()
        self.custom_anchors_completer = QtWidgets.QCompleter([i for i,_ in self.all_tag_sorted], self)
        self.custom_anchors_completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.custom_anchors_completer.setCompletionMode(QtWidgets.QCompleter.InlineCompletion)
        self.custom_anchors_lineEdit.setCompleter(self.custom_anchors_completer)
        global Stamps_LastCreated
        if Stamps_LastCreated is not None:
            try:
                title = nuke.toNode(Stamps_LastCreated)["title"].value()
                self.custom_anchors_lineEdit.setPlaceholderText(title)
            except:
                pass

        custom_ok_btn = QtWidgets.QPushButton("OK")
        custom_ok_btn.clicked.connect(partial(self.okCustomPressed,dropdown=self.custom_anchors_lineEdit))

        custom_ok_btn.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        custom_ok_btn.customContextMenuRequested.connect(partial(self.okCustomRightClicked,self.custom_anchors_lineEdit))

        self.lower_grid.addWidget(custom_tag_label,tag_num,0)
        self.lower_grid.addWidget(self.custom_anchors_lineEdit,tag_num,1)
        self.lower_grid.addWidget(custom_ok_btn,tag_num,2)

        for i in [self.all_anchors_dropdown,self.popular_anchors_dropdown]:
            i.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContentsOnFirstShow)
            i.setMinimumWidth(200)
            i.resize(500,i.sizeHint().height())
            i.setSizePolicy(QtWidgets.QSizePolicy.Ignored,i.sizePolicy().verticalPolicy())

        # Layout shit
        self.grid.setColumnStretch(1,1)
        if len(list(filter(None,self._all_tags_and_backdrops))):
            self.master_layout.addWidget(self.scroll)
        else:
            self.master_layout.addWidget(self.headerLine)
        self.master_layout.addLayout(self.lower_grid)
        self.setLayout(self.master_layout)
        self.resize(self.sizeHint().width(),min(self.sizeHint().height()+10,700))
        #self.setFixedWidth(self.sizeHint().width()+40)

    def keyPressEvent(self, e):
        selectorType = type(self.focusWidget()).__name__ #QComboBox or QLineEdit
        if e.key() == 16777220:
            if selectorType == "QLineEdit":
                self.okCustomPressed(dropdown=self.focusWidget())
            else:
                self.okPressed(dropdown=self.focusWidget())
        else:
            return QtWidgets.QDialog.keyPressEvent(self, e)

    def findAnchorsAndTags(self):
        # Lets find anchors
        self._all_anchors_titles = []
        self._all_anchors_names = []

        self._all_tags = set()
        self._all_backdrops = set()
        self._backdrop_item_count = {} # Number of anchors per backdrop
        self._all_tags_and_backdrops = set()
        self._anchors_and_tags = {} # Name:tags. Not title.
        self._anchors_and_tags_tags = {} # Name:tags. Not title.
        self._anchors_and_tags_backdrops = {} # Name:tags. Not title.
        for ni in allAnchors():
            try:
                title_value = ni["title"].value()
                name_value = ni.name()
                tags_value = ni["tags"].value()
                tags = re.split(" *, *",tags_value.strip()) # Remove leading/trailing spaces and separate by commas (with or without spaces)
                #backdrop_tags = ["$b$"+x for x in backdropTags(ni)]
                backdrop_tags = backdropTags(ni)
                for t in backdrop_tags:
                    if t not in self._backdrop_item_count:
                        self._backdrop_item_count[t] = 0
                    self._backdrop_item_count[t] += 1
                tags_and_backdrops = list(set(tags + backdrop_tags))
                self._all_anchors_titles.append(title_value.strip())
                self._all_anchors_names.append(name_value)
                self._all_tags.update(tags)
                self._all_backdrops.update(backdrop_tags)
                self._all_tags_and_backdrops.update(tags_and_backdrops)
                self._anchors_and_tags[name_value] = set(tags_and_backdrops)
                self._anchors_and_tags_tags[name_value] = set(tags)
                self._anchors_and_tags_backdrops[name_value] = set(backdrop_tags)
            except:
                pass

        self._all_backdrops = sorted(list(self._all_backdrops), key = lambda x: -self._backdrop_item_count[x])
        self._all_tags = sorted(list(self._all_tags),key=str.lower)
        self._all_tags_and_backdrops = self._all_tags + self._all_backdrops

        #titles_upper = [x.upper() for x in self._all_anchors_titles]

        titles_and_names = list(zip(self._all_anchors_titles, self._all_anchors_names))
        titles_and_names.sort(key=lambda tup: tup[0].upper())
        self._all_anchors_titles = [x for x, y in titles_and_names]
        self._all_anchors_names = [y for x, y in titles_and_names]
        return self._anchors_and_tags

    def titleRepeatedForTag(self, title, tag, mode=""):
        if self._all_anchors_titles.count(title) <= 1:
            return False

        # Get list of all names that have that tag, and list of related titles
        names_with_tag = []
        titles_with_tag = []
        for i, name in enumerate(self._all_anchors_names):
            if mode == "tag":
                if tag in self._anchors_and_tags_tags[name]:
                    names_with_tag.append(name)
                    titles_with_tag.append(self._all_anchors_titles[i])
            elif mode == "backdrop":
                if tag in self._anchors_and_tags_backdrops[name]:
                    names_with_tag.append(name)
                    titles_with_tag.append(self._all_anchors_titles[i])
            else:
                if tag in self._anchors_and_tags[name]:
                    names_with_tag.append(name)
                    titles_with_tag.append(self._all_anchors_titles[i])

        # Count titles repetition
        title_repetitions = titles_with_tag.count(title)
        return (title_repetitions > 1)

    def okPressed(self, dropdown, close=True):
        ''' Runs after an ok button is pressed '''
        dropdown_value = dropdown.currentText()
        dropdown_index = dropdown.currentIndex()
        dropdown_data = dropdown.itemData(dropdown_index)

        try:
            match_anchor = nuke.toNode(dropdown_data)
        except:
            pass

        self.chosen_value = dropdown_value
        self.chosen_anchor_name = dropdown_data
        if match_anchor is not None:
            self.chosen_anchors.append(match_anchor)
            if close:
                self.accept()
        else:
            nuke.message("There was a problem selecting a valid anchor.")

    def okRightClicked(self, dropdown, position):
        self.okPressed(dropdown,close=False)

    def okCustomPressed(self, dropdown, close=True):
        ''' Runs after the custom ok button is pressed '''
        global Stamps_LastCreated
        written_value = dropdown.text() # This means it's been written down on the lineEdit
        written_lower = written_value.lower().strip()

        found_data = None

        if written_value == "" and 'Stamps_LastCreated' in globals():
            found_data = Stamps_LastCreated
        else:
            for [text, name] in reversed(self.all_tag_sorted):
                if written_lower == text.lower():
                    found_data = name
                    break
                elif written_lower in text.lower():
                    found_data = name
        try:
            match_anchor = nuke.toNode(found_data)
        except:
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
        self.okCustomPressed(dropdown,close=False)

class AnchorTags_LineEdit(QtWidgets.QLineEdit):
    new_text = QtCore.Signal(object, object)
    def __init__(self, *args):
        QtWidgets.QLineEdit.__init__(self, *args)
        self.textChanged.connect(self.text_changed)
        self.completer = None

    def text_changed(self, text):
        all_text = unicode(text)
        text = all_text[:self.cursorPosition()]
        prefix = text.split(',')[-1].strip()

        text_tags = []
        for t in all_text.split(','):
            t1 = unicode(t).strip()
            if t1 != '':
                text_tags.append(t.strip())
        text_tags = list(set(text_tags))
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
    insertText = QtCore.Signal(str)
    def __init__(self, all_tags):
        QtWidgets.QCompleter.__init__(self, all_tags)
        self.all_tags = set(all_tags)
        self.activated.connect(self.activated_text)

    def update(self, text_tags, completion_prefix):
        tags = list(self.all_tags-set(text_tags))
        model = QtCore.QStringListModel(tags, self)
        self.setModel(model)
        self.setCompletionPrefix(completion_prefix)
        self.complete()

    def activated_text(self,completion):
        self.insertText.emit(completion)

class NewAnchorPanel(QtWidgets.QDialog):
    '''
    Panel to create a new anchor on a selected node, where you can choose the name (autocompleted at first) and tags.
    '''
    def __init__(self, windowTitle = "New Stamp", default_title="", all_tags = [], default_tags = "", parent = None):
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
        """Create widgets..."""
        self.newAnchorTitle = QtWidgets.QLabel("New Anchor Stamp")
        self.newAnchorTitle.setStyleSheet("font-weight:bold;color:#CCCCCC;font-size:14px;")
        self.newAnchorSubtitle = QtWidgets.QLabel("Set Stamp title and tag/s (comma separated)")
        self.newAnchorSubtitle.setStyleSheet("color:#999")

        self.newAnchorLine = QtWidgets.QFrame()
        self.newAnchorLine.setFrameShape(QtWidgets.QFrame.HLine)
        self.newAnchorLine.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.newAnchorLine.setLineWidth(0)
        self.newAnchorLine.setMidLineWidth(1)
        self.newAnchorLine.setFrameShadow(QtWidgets.QFrame.Sunken)

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
        """Create layout..."""

        self.titleAndTags_layout = QtWidgets.QGridLayout()
        self.titleAndTags_layout.addWidget(self.anchorTitle_label,0,0)
        self.titleAndTags_layout.addWidget(self.anchorTitle_edit,0,1)
        self.titleAndTags_layout.addWidget(self.anchorTags_label,1,0)
        self.titleAndTags_layout.addWidget(self.anchorTags_edit,1,1)

        self.master_layout = QtWidgets.QVBoxLayout()
        self.master_layout.addWidget(self.newAnchorTitle)
        self.master_layout.addWidget(self.newAnchorSubtitle)
        self.master_layout.addWidget(self.newAnchorLine)
        self.master_layout.addLayout(self.titleAndTags_layout)
        self.master_layout.addWidget(self.buttonBox)
        self.setLayout(self.master_layout)

    def clickedOk(self):
        self.anchorTitle = self.anchorTitle_edit.text().strip()
        if self.anchorTitle == "" and self.anchorTitle_edit.text() != "":
            self.anchorTitle = self.anchorTitle_edit.text()
        self.anchorTags = self.anchorTags_edit.text().strip()
        self.accept()
        return True

    def clickedCancel(self):
        '''Abort mission'''
        self.reject()

class AddTagsPanel(QtWidgets.QDialog):
    '''
    Panel to add tags to the selected Stamps or nodes.
    '''
    def __init__(self, all_tags = [], default_tags = "", parent = None):
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
        self.addTagsLine.setFrameShadow(QtWidgets.QFrame.Sunken)

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
        self.addTo_btnA = QtWidgets.QRadioButton("All selected nodes")
        self.addTo_btnA.setChecked(True)
        self.addTo_btnB = QtWidgets.QRadioButton("Selected Stamps")
        addTo_ButtonGroup = QtWidgets.QButtonGroup(self)
        addTo_ButtonGroup.addButton(self.addTo_btnA)
        addTo_ButtonGroup.addButton(self.addTo_btnB)

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.clickedOk)
        self.buttonBox.rejected.connect(self.clickedCancel)

    def createLayouts(self):
        self.main_layout = QtWidgets.QGridLayout()
        self.main_layout.addWidget(self.tags_label,0,0)
        self.main_layout.addWidget(self.tags_edit,0,1)

        addTo_Buttons_layout = QtWidgets.QHBoxLayout()
        addTo_Buttons_layout.addWidget(self.addTo_btnA)
        addTo_Buttons_layout.addWidget(self.addTo_btnB)
        self.main_layout.addWidget(self.addTo_Label,1,0)
        self.main_layout.addLayout(addTo_Buttons_layout,1,1)

        self.master_layout = QtWidgets.QVBoxLayout()
        self.master_layout.addWidget(self.addTagsTitle)
        self.master_layout.addWidget(self.addTagsSubtitle)
        self.master_layout.addWidget(self.addTagsLine)
        self.master_layout.addLayout(self.main_layout)
        self.master_layout.addWidget(self.buttonBox)
        self.setLayout(self.master_layout)

    def clickedOk(self):
        '''Check if all is correct and submit'''
        self.tags = self.tags_edit.text().strip()
        self.allNodes = self.addTo_btnA.isChecked
        self.accept()
        return True

    def clickedCancel(self):
        '''Abort mission'''
        self.reject()

class RenameTagPanel(QtWidgets.QDialog):
    '''
    Panel to rename a tag on the selected (or all) nodes.
    '''
    def __init__(self, all_tags = [], default_tags = "", parent = None):
        super(RenameTagPanel, self).__init__(parent)

        self.all_tags = all_tags
        self.allNodes = True
        self.default_tags = default_tags
        self.setWindowTitle("Stamps: Rename tag")
        self.initUI()
        self.setFixedSize(self.sizeHint())

    def initUI(self):
        self.createWidgets()
        self.createLayouts()

    def createWidgets(self):
        self.headerTitle = QtWidgets.QLabel("Rename tag")
        self.headerTitle.setStyleSheet("font-weight:bold;color:#CCCCCC;font-size:14px;")
        self.headerSubtitle = QtWidgets.QLabel("Rename a tag on the selected (or all) nodes.")
        self.headerSubtitle.setStyleSheet("color:#999")

        self.headerLine = QtWidgets.QFrame()
        self.headerLine.setFrameShape(QtWidgets.QFrame.HLine)
        self.headerLine.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.headerLine.setLineWidth(0)
        self.headerLine.setMidLineWidth(1)
        self.headerLine.setFrameShadow(QtWidgets.QFrame.Sunken)

        self.tag_label = QtWidgets.QLabel("Rename: ")
        self.tag_edit = QtWidgets.QLineEdit()
        all_tags = allTags()
        self.tag_completer = QtWidgets.QCompleter(all_tags, self)
        self.tag_completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.tag_edit.setCompleter(self.tag_completer)

        self.tagReplace_label = QtWidgets.QLabel("To: ")
        self.tagReplace_edit = QtWidgets.QLineEdit()
        self.tagReplace_completer = QtWidgets.QCompleter(all_tags, self)
        self.tagReplace_completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.tagReplace_edit.setCompleter(self.tagReplace_completer)

        self.addTo_Label = QtWidgets.QLabel("Apply on: ")
        self.addTo_Label.setToolTip("Which nodes to rename the tag on.")
        self.addTo_btnA = QtWidgets.QRadioButton("Selected nodes")
        self.addTo_btnA.setChecked(True)
        self.addTo_btnB = QtWidgets.QRadioButton("All nodes")
        addTo_ButtonGroup = QtWidgets.QButtonGroup(self)
        addTo_ButtonGroup.addButton(self.addTo_btnA)
        addTo_ButtonGroup.addButton(self.addTo_btnB)

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.clickedOk)
        self.buttonBox.rejected.connect(self.clickedCancel)

    def createLayouts(self):
        self.main_layout = QtWidgets.QGridLayout()
        self.main_layout.addWidget(self.tag_label,0,0)
        self.main_layout.addWidget(self.tag_edit,0,1)
        self.main_layout.addWidget(self.tagReplace_label,1,0)
        self.main_layout.addWidget(self.tagReplace_edit,1,1)

        addTo_Buttons_layout = QtWidgets.QHBoxLayout()
        addTo_Buttons_layout.addWidget(self.addTo_btnA)
        addTo_Buttons_layout.addWidget(self.addTo_btnB)
        self.main_layout.addWidget(self.addTo_Label,2,0)
        self.main_layout.addLayout(addTo_Buttons_layout,2,1)

        self.master_layout = QtWidgets.QVBoxLayout()
        self.master_layout.addWidget(self.headerTitle)
        self.master_layout.addWidget(self.headerSubtitle)
        self.master_layout.addWidget(self.headerLine)
        self.master_layout.addLayout(self.main_layout)
        self.master_layout.addWidget(self.buttonBox)
        self.setLayout(self.master_layout)

    def clickedOk(self):
        '''Check if all is correct and submit'''
        self.tag = self.tag_edit.text().strip()
        self.tagReplace = self.tagReplace_edit.text().strip()
        self.allNodes = self.addTo_btnB.isChecked
        self.accept()
        return True

    def clickedCancel(self):
        '''Abort mission'''
        self.reject()

#################################
### FUNCTIONS
#################################

def getDefaultTitle(node = None):
    if node == None:
        return False
    title = str(node.name())

    # Default defaults here
     # cam
    if "Camera" in node.Class() and not any([(i.knob("title") and i["title"].value() == "cam") for i in nuke.allNodes("NoOp")]):
        title = "cam"
        return title

    if node.Class() in ["Dot","NoOp"] and node["label"].value().strip() != "":
        return node["label"].value().strip()

    # Filename
    try:
        file = node['file'].value()
        if not (node.knob("read_from_file") and not node["read_from_file"].value()):
            if file != "":
                rawname = file.rpartition('/')[2].rpartition('.')[0]
                if '.' in rawname:
                    rawname = rawname.rpartition('.')[0]
                # 1: beauty?
                m = re.match(r"([\w]+)_v[\d]+_beauty", rawname)
                if m:
                    pre_version = m.groups()[0]
                    title = "_".join(pre_version.split("_")[3:])
                    return title
                # 2: Other
                rawname = str(re.split("_v[0-9]*_",rawname)[-1]).replace("_render","")
                title = rawname
    except:
        pass

    return title

def backdropTags(node = None):
    ''' Returns the list of words belonging to the backdrop/s label/s'''
    backdrops = findBackdrops(node)
    tags = []
    for b in backdrops:
        if b.knob("visible_for_stamps"):
            if not b["visible_for_stamps"].value():
                continue
        elif not b["bookmark"].value():
            continue
        label = b["label"].value()
        if len(label) and len(label) < 50 and not label.startswith("\\"):
            label = label.split("\n")[0].strip()
            label = re.sub("<[^<>]>","",label)
            label = re.sub("[\s]+"," ",label)
            label = re.sub("\.$","",label)
            label = label.strip()
            tags.append(label)
    return tags

def stampCreateAnchor(node = None, extra_tags = [], no_default_tag = False):
    '''
    Create a stamp from any nuke node.
    Returns: extra_tags list is success, None if cancelled
    '''
    ns = nuke.selectedNodes()
    for n in ns:
        n.setSelected(False)

    if node is not None:
        node.setSelected(True)
        default_title = getDefaultTitle(realInput(node,stopOnLabel=True,mode="title"))
        default_tags = list(set([nodeType(realInput(node,mode="tags"))]))
        if node.Class() in ["ScanlineRender"]:
            default_tags += ["2D","Deep"]
        node_type = nodeType(realInput(node))
        window_title = "New Stamp: "+str(node.name())
    else:
        default_title = "Stamp"
        default_tags = ""
        node_type = ""
        window_title = "New Stamp"

    try:
        custom_default_title = defaultTitle(node)
        if custom_default_title:
            default_title = str(custom_default_title)
    except:
        pass

    try:
        custom_default_tags = defaultTags(node)
        if custom_default_tags:
            if KEEP_ORIGINAL_TAGS:
                default_tags += custom_default_tags
            else:
                default_tags = custom_default_tags

    except:
        pass

    default_default_tags = default_tags

    if no_default_tag:
        default_tags = ", ".join(extra_tags + [""])
    else:
        default_tags = list(filter(None,list(dict.fromkeys(default_tags + extra_tags))))
        default_tags = ", ".join(default_tags + [""])

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
                if not nuke.ask("There is already a Stamp titled "+anchor_title+".\nDo you still want to use this title?"):
                    continue
            na = anchor(title = anchor_title, tags = anchor_tags, input_node = node, node_type = node_type)
            na.setYpos(na.ypos()+20)
            stampCreateWired(na)
            for n in ns:
                n.setSelected(True)
                node.setSelected(False)
            extra_tags = anchor_tags.split(",")
            extra_tags = [t.strip() for t in extra_tags if t.strip() not in default_default_tags]
            break
        else:
            break
        
    return extra_tags

def stampSelectAnchors():
    '''
    Panel to select a stamp anchor (if there are any)
    Returns: selected anchor node, or None.
    '''
    # 1.Get position where to make the child...
    nodeForPos = nuke.createNode("NoOp")
    childNodePos = [nodeForPos.xpos(),nodeForPos.ypos()]
    nuke.delete(nodeForPos)
    # 2.Choose the anchor...
    anchorList = [n.name() for n in allAnchors()]
    if not len(anchorList):
        nuke.message("Please create some stamps first...")
        return None
    else:
        global select_anchors_panel
        select_anchors_panel = AnchorSelector()
        if select_anchors_panel.exec_(): # If user clicks OK
            chosen_anchors = select_anchors_panel.chosen_anchors
            if chosen_anchors:
                return chosen_anchors
        return None

def stampCreateWired(anchor = ""):
    ''' Create a wired stamp from an anchor node. '''
    global Stamps_LastCreated
    nw = ""
    nws = []
    if anchor == "":
        anchors = stampSelectAnchors()
        if anchorSelectWireds == None:
            return
        if anchors:
            for i, anchor in enumerate(anchors):
                nw = wired(anchor = anchor)
                nw.setInput(0,anchor)
                nws.append(nw)
                if i>0:
                    nws[i].setXYpos(nws[i-1].xpos()+100,nws[i-1].ypos())

    else:
        ns = nuke.selectedNodes()
        for n in ns:
            n.setSelected(False)
        dot = nuke.nodes.Dot()
        dot.setXYpos(anchor.xpos(),anchor.ypos())
        dot.setInput(0,anchor)
        nw = wired(anchor = anchor)
        code = "dummy = nuke.nodes.{}()".format(nw.Class())
        namespace = {}
        exec(code,globals(),namespace)
        dummy = namespace["dummy"]
        nww = dummy.screenWidth()
        nuke.delete(dummy)
        nuke.delete(dot)
        for n in ns:
            n.setSelected(True)
        nw.setXYpos(int(anchor.xpos()+anchor.screenWidth()/2-nww/2) ,anchor.ypos()+56)
        anchor.setSelected(False)
    return nw

def stampCreateByTitle(title = ""):
    ''' Create a wired stamp given a title. '''
    global Stamps_LastCreated

    anchor = None
    for a in allAnchors():
        if a.knob("title") and a["title"].value() == title:
            anchor = a
            break
    if anchor == None:
        return

    nw = wired(anchor = anchor)
    nw.setInput(0,anchor)
    return nw

def stampDuplicateWired(wired = ""):
    ''' Create a duplicate of a wired stamp '''
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
    new_wired.setXYpos(wired.xpos()-110,wired.ypos()+55)
    try:
        new_wired.setInput(0,wired.input(0))
    except:
        pass
    for n in ns:
        n.setSelected(True)
    wired.setSelected(False)

def stampType(n = ""):
    ''' Returns the identifier value if it exists, otherwise False. '''
    if isAnchor(n):
        return "anchor"
    elif isWired(n):
        return "wired"
    else:
        return False

def nodeType(n=""):
    '''Returns the node type: Camera, Deep, 3D, Particles, 2D or False'''
    try:
        nodeClass = n.Class()
    except:
        return False
    if nodeClass.startswith("Deep") and nodeClass not in DeepExceptionClasses:
        return "Deep"
    elif nodeClass.startswith("Particle") and nodeClass not in ParticleExceptionClasses:
        return "Particle"
    elif nodeClass.startswith("ScanlineRender"):
        return False
    elif nodeClass in ["Camera", "Camera2", "Camera3"]:
        return "Camera"
    elif nodeClass in ["Axis", "Axis2","Axis3"]:
        return "Axis"
    elif (n.knob("render_mode") and n.knob("display")) or nodeClass in ["GeoNoOp","EditGeo"]:
        return "3D"
    else:
        return "2D"

def allAnchors(selection=""):
    nodes = nuke.allNodes()
    if selection == "":
        anchors = [a for a in nodes if isAnchor(a)]
    else:
        anchors = [a for a in nodes if a in selection and isAnchor(a)]    
    return anchors

def allWireds(selection=""):
    nodes = nuke.allNodes()
    if selection == "":
        wireds = [a for a in nodes if isWired(a)]
    else:
        wireds = [a for a in nodes if a in selection and isWired(a)]   
    return wireds

def totalAnchors(selection=""):
    num_anchors = len(allAnchors(selection))
    return num_anchors

def allTags(selection=""):
    all_tags = set()
    for ni in allAnchors():
        try:
            tags_value = ni["tags"].value()
            tags = re.split(" *, *",tags_value.strip()) # Remove leading/trailing spaces and separate by commas (with or without spaces)
            all_tags.update(tags)
        except:
            pass

    all_tags = [i for i in list(all_tags) if i]
    all_tags.sort(key=str.lower)
    return all_tags

def findAnchorsByTitle(title = "", selection=""):
    ''' Returns list of nodes '''
    if title == "":
        return None
    if selection == "":
        found_anchors = [a for a in allAnchors() if a.knob("title") and a.knob("title").value() == title]
    else:
        found_anchors = [a for a in selection if a in allAnchors() and a.knob("title") and a.knob("title").value() == title]
    return found_anchors

def titleIsLegal(title=""):
    '''
    Convenience function to determine which stamp titles are legal.
    titleIsLegal(title) -> True or False
    '''
    if not title or title == "":
        return False
    return True

def isAnchor(node=""):
    ''' True or False '''
    return True if all(node.knob(i) for i in ["identifier","title"]) and node["identifier"].value() == "anchor" else False

def isWired(node=""):
    ''' True or False '''
    return True if all(node.knob(i) for i in ["identifier","title"]) and node["identifier"].value() == "wired" else False

def findBackdrops(node = ""):
    ''' Returns a list containing the backdrops that contain the given node.'''
    if node =="":
        return []
    x = node.xpos()
    y = node.ypos()
    w = node.screenWidth()
    h = node.screenHeight()

    backdrops = []
    for b in nuke.allNodes("BackdropNode"):
        bx = int(b['xpos'].value())
        by = int(b['ypos'].value())
        br = int(b['bdwidth'].value())+bx
        bt =int(b['bdheight'].value())+by
        if x >= bx and (x+w) <= br and y > by and (y+h) <= bt:
            backdrops.append(b)
    return backdrops

def realInput(node, stopOnLabel=False, mode=""):
    '''
    Returns the first input node that is not a Dot or a Stamp
    stopOnLabel=False. True: Stop when it's a dot or NoOp but it has a label.
    mode="title": ignores TitleIgnoreClasses
    mode="tags": ignores TagsIgnoreClasses
    '''
    try:
        n = node
        if stampType(n) or n.Class() in InputIgnoreClasses or (mode=="title" and n.Class() in TitleIgnoreClasses) or (mode=="tags" and n.Class() in TagsIgnoreClasses):
            if stopOnLabel and n.knob("label") and n["label"].value().strip()!="":
                return n
            if n.input(0):
                n = n.input(0)
                return realInput(n,stopOnLabel,mode)
            else:
                return n
        else:
            return n
    except:
        return node

def nodeToScript(node = ""):
    ''' Returns a node as a tcl string, similar as nodecopy without messing with the clipboard '''
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

def nodesFromScript(script = ""):
    ''' Returns string as a node, similar as nodepaste without messing with the clipboard '''
    if script == "":
        return
    clipboard = QtWidgets.QApplication.clipboard()
    ctext = clipboard.text()
    clipboard.setText(script)
    nuke.nodePaste("%clipboard%")
    clipboard.setText(ctext)
    return True

def stampCount(anchor_name=""):
    if anchor_name=="":
        return len(allWireds())
    stamps = [s for s in allWireds() if s["anchor"].value() == anchor_name]
    return len(stamps)

def toNoOp(node=""):
    '''Turns a given node into a NoOp that shares everything else'''
    global Stamps_LockCallbacks
    Stamps_LockCallbacks = True
    if node == "":
        return
    if node.Class() == "NoOp":
        return
    nsn = nuke.selectedNodes()
    [i.setSelected(False) for i in nsn]
    scr = nodeToScript(node)
    scr = re.sub(r"\n[\s]*[\w]+[\s]*{\n","\nNoOp {\n",scr)
    scr = re.sub(r"^[\s]*[\w]+[\s]*{\n","NoOp {\n",scr)

    legal_starts = ["set","version","push","NoOp","help","onCreate","name","knobChanged","autolabel","tile_color","gl_color","note_font","selected","hide_input"]

    scr_split = scr.split("addUserKnob",1)
    scr_first = scr_split[0].split("\n")
    for i, line in enumerate(scr_first):
        if not any([line.startswith(x) or line.startswith(" "+x) for x in legal_starts]):
            scr_first[i] = ""
    scr_first = "\n".join([i for i in scr_first if i]+[""])
    scr_split[0] = scr_first

    scr = "addUserKnob".join(scr_split)

    node.setSelected(True)
    xp = node.xpos()
    yp = node.ypos()
    xw = node.screenWidth()/2
    d = nuke.createNode("Dot")
    d.setInput(0,node)
    inp = None
    [i.setSelected(True) for i in nsn]
    nuke.delete(node)
    d.setSelected(False)
    d.setSelected(True)
    d.setXYpos(int(xp+xw-d.screenWidth()/2),yp-18)
    nodesFromScript(scr)
    n = nuke.selectedNode()
    n.setXYpos(xp,yp)
    nuke.delete(d)
    for i in nsn:
        try:
            i.setSelected(True)
        except:
            pass
    Stamps_LockCallbacks = False

def allToNoOp():
    ''' Turns all the stamps into NoOps '''
    for n in nuke.allNodes():
        if stampType(n) and n.Class() != "NoOp":
            toNoOp(n)

def createWHotboxButtons():
    ''' If the folder is available inside the stamps package, it gets appended into the W_Hotbox packages. '''
    # DONE W_Hotbox buttons imported from stamps extras path
    w_hotbox_buttons_path = os.path.dirname(__file__).replace("\\","/")+"/includes/W_hotbox"
    if os.path.exists(w_hotbox_buttons_path):
        hotbox_paths = ""
        hotbox_names = ""
        if "W_HOTBOX_REPO_PATHS" in os.environ.keys() and "W_HOTBOX_REPO_NAMES" in os.environ.keys():
            hotbox_paths = os.environ["W_HOTBOX_REPO_PATHS"]
            hotbox_names = os.environ["W_HOTBOX_REPO_NAMES"]
        if hotbox_paths != "":
            hotbox_paths += os.pathsep
        if hotbox_names != "":
            hotbox_names += os.pathsep
        os.environ["W_HOTBOX_REPO_PATHS"] = hotbox_paths + os.path.dirname(__file__).replace("\\","/")+"/includes/W_hotbox"
        os.environ["W_HOTBOX_REPO_NAMES"] = hotbox_names + "Stamps"

#################################
### Menu functions
#################################

def refreshStamps(ns=""):
    '''Refresh all the wired Stamps in the script, to spot any wrong styles or connections.'''
    stamps = allWireds(ns)
    x = 0
    failed = []
    failed_names = []
    for s in stamps:
        if not wiredReconnect(s):
            x += 1 # Errors
            failed.append(s)
        else:
            try:
                s["reconnect_this"].execute()
            except:
                pass
    failed_names = ", ".join([i.name() for i in failed])
    if x==0:
        if ns == "":
            nuke.message("All Stamps refreshed! No errors detected.")
        else:
            nuke.message("Selected Stamps refreshed! No errors detected.")
    else:
        [i.setSelected(False) for i in nuke.selectedNodes()]
        [i.setSelected(True) for i in failed]
        if ns == "":
            nuke.message("All Stamps refreshed. Found {0} connection error/s:\n\n{1}".format(str(x), failed_names))
        else:
            nuke.message("Selected Stamps refreshed. Found {0} connection error/s:\n\n{1}".format(str(x), failed_names))

def addTags(ns=""):
    if ns=="":
        ns = nuke.selectedNodes()
    if not len(ns):
        if not nuke.ask("Nothing is selected. Do you wish to add tags to ALL nodes in the script?"):
            return
        ns = nuke.allNodes()
    
    global stamps_addTags_panel
    stamps_addTags_panel = AddTagsPanel(all_tags = allTags(), default_tags = "")
    if stamps_addTags_panel.exec_():
        all_nodes = stamps_addTags_panel.allNodes
        added_tags = stamps_addTags_panel.tags.strip()
        added_tags = re.split(r"[\s]*,[\s]*", added_tags)
        i = 0
        for n in ns:
            if isAnchor(n):
                tags_knob = n.knob("tags")
            elif isWired(n):
                a_name = n.knob("anchor").value()
                if nuke.exists(a_name):
                    a = nuke.toNode(a_name)
                    if a in ns or not isAnchor(a):
                        continue
                    tags_knob = a.knob("tags")
            elif all_nodes and n.Class() not in NodeExceptionClasses:
                tags_knob = n.knob("stamp_tags")
                if not tags_knob:
                    tags_knob = nuke.String_Knob('stamp_tags','Stamp Tags', "")
                    tags_knob.setTooltip("Stamps: Comma-separated tags you can define for each Anchor, that will help you find it when invoking the Stamp Selector by pressing the Stamps shortkey with nothing selected.")
                    n.addKnob(tags_knob)
            else:
                continue
            existing_tags = re.split(r"[\s]*,[\s]*", tags_knob.value().strip())
            merged_tags = list(filter(None,list(set(existing_tags + added_tags))))
            tags_knob.setValue(", ".join(merged_tags))
            i += 1
            continue
        if i>0:
            if all_nodes:
                nuke.message("Added the specified tag/s to {} nodes.".format(str(i)))
            else:
                nuke.message("Added the specified tag/s to {} Anchor Stamps.".format(str(i)))
    return

def renameTag(ns=""):
    if ns=="":
        ns = nuke.selectedNodes()
    if not len(ns):
        ns = nuke.allNodes()
    global stamps_renameTag_panel
    stamps_renameTag_panel = RenameTagPanel(all_tags = allTags())
    if stamps_renameTag_panel.exec_():
        all_nodes = stamps_renameTag_panel.allNodes
        if all_nodes:
            ns = nuke.allNodes()
        added_tag = str(stamps_renameTag_panel.tag.strip())
        added_tagReplace = str(stamps_renameTag_panel.tagReplace.strip())
        i = 0
        for n in ns:
            if isAnchor(n):
                tags_knob = n.knob("tags")
            elif isWired(n):
                a_name = n.knob("anchor").value()
                if nuke.exists(a_name):
                    a = nuke.toNode(a_name)
                    if a in ns or not isAnchor(a):
                        continue
                    tags_knob = a.knob("tags")
            elif n.Class() not in NodeExceptionClasses:
                tags_knob = n.knob("stamp_tags")
                if not tags_knob:
                    continue
            else:
                continue

            existing_tags = list(filter(None,re.split(r"[\s]*,[\s]*", tags_knob.value())))
            added_tag_list = re.split(r"[\s]*,[\s]*", added_tag.strip())
            added_tagReplace_list = re.split(r"[\s]*,[\s]*", added_tagReplace)

            merged_tags = existing_tags
            for atag in added_tag_list:
                for rtag in added_tagReplace_list:
                    merged_tags = [rtag if x == atag else x for x in merged_tags]

            merged_tags = [i for i in merged_tags if i]

            if merged_tags != existing_tags:
                tags_knob.setValue(", ".join(merged_tags))
                i += 1
            continue
        if i>0:
            nuke.message("Renamed the specified tag on {} nodes.".format(str(i)))
    return

def selectedReconnectByName():
    ns = [n for n in nuke.selectedNodes() if isWired(n)]
    for n in ns:
        try:
            n["reconnect_this"].execute()
        except:
            pass

def selectedReconnectByTitle():
    ns = [n for n in nuke.selectedNodes() if isWired(n)]
    for n in ns:
        try:
            n["reconnect_by_title_this"].execute()
        except:
            pass

def selectedReconnectBySelection():
    ns = [n for n in nuke.selectedNodes() if isWired(n)]
    for n in ns:
        try:
            n["reconnect_by_selection_this"].execute()
        except:
            pass

def selectedToggleAutorec():
    ns = [n for n in nuke.selectedNodes() if n.knob("auto_reconnect_by_title")]

    if any([not n.knob("auto_reconnect_by_title").value() for n in ns]):
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
    ns = [n for n in nuke.selectedNodes() if isWired(n) or isAnchor(n)]
    for n in ns:
        try:
            if n.knob("selectSimilar"):
                n["selectSimilar"].execute()
            if n.knob("selectStamps"):
                n["selectStamps"].execute()
        except:
            pass

def showInNukepedia():
    from webbrowser import open as openUrl
    openUrl("http://www.nukepedia.com/gizmos/other/stamps")

def showInGithub():
    from webbrowser import open as openUrl
    openUrl("https://github.com/adrianpueyo/stamps")


def showHelp():
     from webbrowser import open as openUrl
     openUrl("http://www.adrianpueyo.com/Stamps_v1.1.pdf")

def showVideo():        
     from webbrowser import open as openUrl     
     openUrl("https://vimeo.com/adrianpueyo/knobscripter2")

def stampBuildMenus():
    global Stamps_MenusLoaded
    if not Stamps_MenusLoaded:
        Stamps_MenusLoaded = True
        m = nuke.menu('Nuke')
        m.addCommand('Edit/Stamps/Make Stamp', 'stamps.goStamp()', STAMPS_SHORTCUT, icon="stamps.png")
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
        nuke.menu('Nodes').addCommand('Other/Stamps', 'stamps.goStamp()', STAMPS_SHORTCUT, icon="stamps.png")

        createWHotboxButtons()

def addIncludesPath():
    includes_dir = os.path.join(os.path.dirname(__file__),"includes")
    if os.path.isdir(includes_dir):
        nuke.pluginAddPath(includes_dir)


#################################
### MAIN IMPLEMENTATION
#################################

def goStamp(ns=""):
    ''' Main stamp function, the one that is called when pressing the main shortcut. '''
    if ns=="":
        ns = nuke.selectedNodes()
    if not len(ns):
        if not totalAnchors(): # If no anchors on the script, create an anchor with no input
            stampCreateAnchor(no_default_tag = True)
        else:
            stampCreateWired() # Selection panel in order to create a stamp
            return
    elif len(ns) == 1 and ns[0].Class() in NodeExceptionClasses:
        if not totalAnchors(): # If no anchors on the script, return
            return
        else:
            stampCreateWired() # Selection panel in order to create a stamp
            return
    else:
        # Warn if the selection is too big
        if len(ns) > 10 and not nuke.ask("You have "+str(len(ns))+" nodes selected.\nDo you want make stamps for all of them?"):
            return
        # Main loop
        extra_tags = []
        for n in ns:
            if n in NodeExceptionClasses:
                continue
            elif isAnchor(n):
                stampCreateWired(n) # Make a child to n
            elif isWired(n):
                stampDuplicateWired(n) # Make a copy of n next to it
            else:
                if n.knob("stamp_tags"):
                    stampCreateAnchor(n, extra_tags = n.knob("stamp_tags").value().split(","), no_default_tag = True)
                else:
                    extra_tags = stampCreateAnchor(n, extra_tags = extra_tags) # Create anchor via anchor creation panel
                if "Cryptomatte" in n.Class() and n.knob("matteOnly"):
                    n['matteOnly'].setValue(1)

stampBuildMenus()
addIncludesPath()