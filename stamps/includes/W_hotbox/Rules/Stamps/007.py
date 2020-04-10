#----------------------------------------------------------------------------------------------------------
#
# AUTOMATICALLY GENERATED FILE TO BE USED BY W_HOTBOX
#
# NAME: auto-rec... by title toggle
# COLOR: #000000
#
#----------------------------------------------------------------------------------------------------------

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
    