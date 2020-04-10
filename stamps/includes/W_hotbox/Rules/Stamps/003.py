#----------------------------------------------------------------------------------------------------------
#
# AUTOMATICALLY GENERATED FILE TO BE USED BY W_HOTBOX
#
# NAME: Reconnect by Name
# COLOR: #445943
#
#----------------------------------------------------------------------------------------------------------

ns = [n for n in nuke.selectedNodes() if n.knob("identifier")]
for n in ns:
    try:
        n["reconnect_this"].execute()
    except:
        pass