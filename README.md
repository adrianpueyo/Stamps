# Stamps

Stamps is a smart node connection system for Nuke.

It lets you create lightweight proxy nodes that point back to a single source node, so large scripts stay easier to read, navigate, and reconnect without filling the graph with long pipes and dots.

This repository currently ships the modernized `v1.2` codebase, including compatibility updates for newer Nuke / Qt environments, while also bundling the original user guide PDF for the established workflow.

<p align="center">
  <img src="./stamps/stamps.png" alt="Stamps icon" width="128" />
</p>

## At a Glance

- Built for Nuke artists who want cleaner node graphs without losing traceability.
- Uses **Anchors** as the source of truth and **Wired Stamps** as reusable references.
- Ships with menu integration, selector UI, reconnection tools, and optional W_hotbox support.
- Works with **2D, Deep, 3D, Camera, Axis, and Particle** workflows.

## What It Does

- Creates **Anchor Stamps** that act as the source reference for a node.
- Creates **Wired Stamps** that point back to an Anchor and can be placed anywhere in the script.
- Supports different node families including **2D, Deep, 3D, Camera, Axis, and Particle** nodes.
- Lets you find Anchors by **tag**, **backdrop**, **title**, **all**, or **most-used** entries through the selector UI.
- Includes several reconnection strategies: **by stored name**, **by title**, and **by explicit selected Anchor**.
- Can auto-reconnect pasted stamps **by title** when stored node names are no longer reliable.
- Carries tag and backdrop context from the Anchor into linked stamps.
- Adds bundled **W_hotbox** rules automatically when W_hotbox is available.

## Installation

### Fresh Install

1. Copy this repository to your Nuke plugin path, for example as:

   ```text
   ~/.nuke/Stamps
   ```

2. In your main Nuke `init.py`, add:

   ```python
   nuke.pluginAddPath("./Stamps")
   ```

3. Restart Nuke.

The repo's own `init.py` then adds the internal `stamps/` package to Nuke's plugin paths.

If you prefer, the same line can point to any other location where you keep Nuke tools:

```python
nuke.pluginAddPath("/path/to/Stamps")
```

### Updating

1. Replace the existing `Stamps` folder with the updated one.
2. Restart Nuke.
3. If needed, run `Edit -> Stamps -> Refresh all Stamps` in Nuke to rewrite callbacks and reconnect existing stamps.

## Usage

The main entry point is **`F8`** by default.

- With **regular nodes selected**, `F8` creates new Anchor + Wired Stamp pairs.
- With an **Anchor selected**, `F8` creates another Wired Stamp for that Anchor.
- With a **Wired Stamp selected**, `F8` duplicates it.
- With **nothing selected**, `F8` opens the Anchor selector if Anchors already exist, or starts a new empty Anchor if none do.

Stamps also adds menu entries under:

- `Edit -> Stamps`
- `Nodes -> Other -> Stamps`

## Typical Workflow

1. Select a node and press `F8`.
2. Confirm or adjust the proposed title and tags.
3. Stamps creates an **Anchor** near the source and a **Wired Stamp** linked to it.
4. Create more Wired Stamps for that Anchor anywhere else in the script.
5. If a script is duplicated, merged, or pasted into another setup, use the reconnect tools to restore links quickly.

## Core Concepts

### Anchor Stamp

An Anchor stores the canonical title, tags, and source identity for a stamped node. It also gives you quick actions to:

- create a new Wired Stamp
- select all linked stamps
- reconnect linked stamps
- jump through linked stamps in the node graph

### Wired Stamp

A Wired Stamp is the lightweight node you scatter through the script. It exposes quick actions to:

- show or zoom to its Anchor
- select similar stamps
- reconnect itself, similar stamps, or all stamps
- reconnect by title or by explicit selection
- enable auto-reconnect-by-title for copy/paste workflows

## Reconnection Tools

Stamps includes several recovery paths for broken or moved connections:

- **Reconnect by name** uses the stored Anchor node name.
- **Reconnect by title** finds an Anchor with the same visible title.
- **Reconnect by selection** forces one or more stamps onto a selected Anchor.
- **Auto-reconnect by title** helps when copying or pasting stamps between scripts where internal node names may change.

## Customization

You can override defaults by placing a `stamps_config.py` in your Python path, typically next to the package or in `.nuke`.

Supported customizations include:

- `STAMPS_SHORTCUT`
- `ANCHOR_STYLE`
- `STAMP_STYLE`
- `defaultTitle(node)`
- `defaultTags(node)`
- node-class mappings and exception lists

Example:

```python
STAMPS_SHORTCUT = "F8"

def defaultTags(node):
    if node.Class() == "Write":
        return ["File Out"]
    return []
```

For the full template, see [`stamps/stamps_config.py`](./stamps/stamps_config.py).

## Included Integrations

- **W_hotbox** rules are bundled in [`stamps/includes/W_hotbox`](./stamps/includes/W_hotbox) and registered automatically when W_hotbox is present.
- The package keeps compatibility wrappers such as `stamps.py`, `config.py`, and `qt_compat.py` so older imports continue to work.

## Documentation

- User guide PDF: [Stamps v1.1 User Guide.pdf](./Stamps%20v1.1%20User%20Guide.pdf)
- GitHub: [adrianpueyo/Stamps](https://github.com/adrianpueyo/Stamps)
- Nukepedia: [Stamps on Nukepedia](http://www.nukepedia.com/gizmos/other/stamps)
- Video tutorial: [Vimeo](https://vimeo.com/adrianpueyo/comma)

## Notes

- The bundled PDF is `v1.1`, while the code in this repo is `v1.2`. The core workflow is the same, but the repository includes more recent maintenance and compatibility work.
- The selector UI can group Anchors by tags, backdrop labels, title search, or popularity.
- Default shortcut and creation logic can be overridden without modifying the core package.

## License

This project is released under the terms in [LICENSE](./LICENSE).
