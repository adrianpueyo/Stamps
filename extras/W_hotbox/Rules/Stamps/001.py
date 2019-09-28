#----------------------------------------------------------------------------------------------------------
#
# AUTOMATICALLY GENERATED FILE TO BE USED BY W_HOTBOX
#
# NAME: Reconnect by Title
# COLOR: #6b4930
#
#----------------------------------------------------------------------------------------------------------

ns = [n for n in nuke.selectedNodes() if n.knob("identifier")]
for n in ns:
    try:
        n["reconnect_by_title_this"].execute()
    except:
        pass
