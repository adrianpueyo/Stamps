# Stamps
Smart node connection system for Nuke by Adrian Pueyo and Alexey Kuchinski.

## Version
v1.2 (March 2025) - Updated for Nuke 16 compatibility

## Description
Stamps is a smart node connection system for Nuke that allows you to create linked instances of nodes. Stamps consists of Anchor stamps and Wired stamps. The Anchor is the source node and Wired stamps can be created to reference an Anchor from anywhere in the Node Graph.

## Compatibility
- Nuke 11.0 or later
- **Now supports Nuke 16 with Python 3.11 and PySide6**

## Installation

1. Copy the `stamps` folder to your `.nuke` folder or any other directory in your Nuke plugin path.
2. Add the following lines to your `menu.py` file:

```python
import nuke
nuke.pluginAddPath("stamps")
import stamps
```

If the plugin is stored in a subdirectory, adjust the path accordingly.

## Nuke 16 Compatibility Notes

The v1.2 update introduces compatibility with Nuke 16, which uses Python 3.11 and PySide6 (not PySide2 as in previous versions). The plugin has been updated to automatically use PySide6 when running in Nuke 16.

If you encounter any issues with Qt import errors, please verify that:

1. You're using the latest version of the plugin from the nuke16-compatibility branch
2. The installation paths are correct in your environment
3. Your Nuke 16 installation includes PySide6 (which should be included by default)

## Documentation
For detailed usage instructions, please refer to the included user guide: "Stamps v1.1 User Guide.pdf"

## License
See the LICENSE file for details.

## Credits
- Created by Adrian Pueyo and Alexey Kuchinski
- Website: http://www.adrianpueyo.com
- Nukepedia: http://www.nukepedia.com/gizmos/other/stamps
- GitHub: https://github.com/adrianpueyo/stamps 