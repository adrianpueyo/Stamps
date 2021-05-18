#----------------------------------------------------------------------------------------------------------
#
# AUTOMATICALLY GENERATED FILE TO BE USED BY W_HOTBOX
#
# NAME: Reconnect by Selection
# COLOR: #512a26
#
#----------------------------------------------------------------------------------------------------------

ns = [n for n in nuke.selectedNodes() if n.knob("reconnect_by_selection_selected")]
for n in ns:
    try:
        n.knob("reconnect_by_selection_selected").execute()
        break
    except:
        pass