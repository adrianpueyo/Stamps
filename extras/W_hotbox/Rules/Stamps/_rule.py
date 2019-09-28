#----------------------------------------------------------------------------------------------------------
#
# AUTOMATICALLY GENERATED FILE TO BE USED BY W_HOTBOX
#
# IGNORE CLASSES: 0
#
#----------------------------------------------------------------------------------------------------------

ns = nuke.selectedNodes()
if any([n.knob("identifier") and n["identifier"].value() in ["anchor", "wired"] and n.knob("title") for n in ns]):
    ret = True