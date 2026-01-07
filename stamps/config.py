"""Configuration loading for Stamps."""

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

STAMP_DEFAULTS: Dict[str, int] = {"note_font_size": 20, "hide_input": 0}

ANCHOR_DEFAULTS = {
    "tile_color": int('%02x%02x%02x%02x' % (255, 255, 255, 1), 16),
    "autolabel": 'nuke.thisNode().knob("title").value()',
    "knobChanged": 'stamps.anchorKnobChanged()',
    "onCreate": 'if nuke.GUI:\n    try:\n        import stamps; stamps.anchorOnCreate()\n    except:\n        pass',
}

WIRED_DEFAULTS = {
    "tile_color": int('%02x%02x%02x%02x' % (1, 0, 0, 1), 16),
    "autolabel": 'nuke.thisNode().knob("title").value()',
    "knobChanged": 'if nuke.GUI:\n    try:\n        import stamps; stamps.wiredKnobChanged()\n    except:\n        pass',
}

DeepExceptionClasses = ["DeepToImage", "DeepHoldout", "DeepHoldout2"]
NodeExceptionClasses = ["Viewer"]
ParticleExceptionClasses = ["ParticleToImage"]

StampClasses = {"2D": "NoOp", "Deep": "DeepExpression"}
AnchorClassesAlt = {"2D": "NoOp", "Deep": "DeepExpression"}
StampClassesAlt = {
    "2D": "PostageStamp",
    "Deep": "DeepExpression",
    "3D": "LookupGeo",
    "Camera": "DummyCam",
    "Axis": "Axis",
    "Particle": "ParticleExpression",
}

InputIgnoreClasses = ["NoOp", "Dot", "Reformat", "DeepReformat", "Crop"]
TitleIgnoreClasses = ["NoOp", "Dot", "Reformat", "DeepReformat", "Crop"]
TagsIgnoreClasses = ["NoOp", "Dot", "Reformat", "DeepReformat", "Crop"]

AnchorClassColors = {"Camera": int('%02x%02x%02x%02x' % (255, 255, 255, 1), 16)}
WiredClassColors = {"Camera": int('%02x%02x%02x%02x' % (51, 0, 0, 1), 16)}

STAMPS_SHORTCUT = "F8"
KEEP_ORIGINAL_TAGS = True


@dataclass
class StampsConfig:
    anchor_defaults: Dict[str, int]
    wired_defaults: Dict[str, int]
    stamp_defaults: Dict[str, int]
    deep_exception_classes: List[str]
    node_exception_classes: List[str]
    particle_exception_classes: List[str]
    stamp_classes: Dict[str, str]
    anchor_classes_alt: Dict[str, str]
    stamp_classes_alt: Dict[str, str]
    input_ignore_classes: List[str]
    title_ignore_classes: List[str]
    tags_ignore_classes: List[str]
    anchor_class_colors: Dict[str, int]
    wired_class_colors: Dict[str, int]
    stamps_shortcut: str
    keep_original_tags: bool
    default_title_fn: Optional[Callable]
    default_tags_fn: Optional[Callable]


def _load_user_module():
    try:
        import stamps_config as user_config
    except Exception:
        return None
    return user_config


def load_config() -> StampsConfig:
    anchor_defaults = STAMP_DEFAULTS.copy()
    anchor_defaults.update(ANCHOR_DEFAULTS)
    wired_defaults = STAMP_DEFAULTS.copy()
    wired_defaults.update(WIRED_DEFAULTS)

    stamp_classes = dict(StampClasses)
    anchor_classes_alt = dict(AnchorClassesAlt)
    stamp_classes_alt = dict(StampClassesAlt)

    input_ignore_classes = list(InputIgnoreClasses)
    title_ignore_classes = list(TitleIgnoreClasses)
    tags_ignore_classes = list(TagsIgnoreClasses)

    deep_exception_classes = list(DeepExceptionClasses)
    node_exception_classes = list(NodeExceptionClasses)
    particle_exception_classes = list(ParticleExceptionClasses)

    anchor_class_colors = dict(AnchorClassColors)
    wired_class_colors = dict(WiredClassColors)

    stamps_shortcut = STAMPS_SHORTCUT
    keep_original_tags = KEEP_ORIGINAL_TAGS

    default_title_fn = None
    default_tags_fn = None

    user_config = _load_user_module()
    if user_config:
        anchor_style = getattr(user_config, "ANCHOR_STYLE", None)
        if anchor_style:
            anchor_defaults.update(anchor_style)

        stamp_style = getattr(user_config, "STAMP_STYLE", None)
        if stamp_style:
            wired_defaults.update(stamp_style)

        stamps_shortcut = getattr(user_config, "STAMPS_SHORTCUT", stamps_shortcut)
        keep_original_tags = getattr(user_config, "KEEP_ORIGINAL_TAGS", keep_original_tags)

        deep_exception_classes = getattr(user_config, "DeepExceptionClasses", deep_exception_classes)
        node_exception_classes = getattr(user_config, "NodeExceptionClasses", node_exception_classes)
        particle_exception_classes = getattr(user_config, "ParticleExceptionClasses", particle_exception_classes)

        input_ignore_classes = getattr(user_config, "InputIgnoreClasses", input_ignore_classes)
        title_ignore_classes = getattr(user_config, "TitleIgnoreClasses", title_ignore_classes)
        tags_ignore_classes = getattr(user_config, "TagsIgnoreClasses", tags_ignore_classes)

        stamp_classes = getattr(user_config, "StampClasses", stamp_classes)
        anchor_classes_alt = getattr(user_config, "AnchorClassesAlt", anchor_classes_alt)
        stamp_classes_alt = getattr(user_config, "StampClassesAlt", stamp_classes_alt)

        anchor_class_colors = getattr(user_config, "AnchorClassColors", anchor_class_colors)
        wired_class_colors = getattr(user_config, "WiredClassColors", wired_class_colors)

        default_title_fn = getattr(user_config, "defaultTitle", None)
        default_tags_fn = getattr(user_config, "defaultTags", None)

    return StampsConfig(
        anchor_defaults=anchor_defaults,
        wired_defaults=wired_defaults,
        stamp_defaults=STAMP_DEFAULTS,
        deep_exception_classes=deep_exception_classes,
        node_exception_classes=node_exception_classes,
        particle_exception_classes=particle_exception_classes,
        stamp_classes=stamp_classes,
        anchor_classes_alt=anchor_classes_alt,
        stamp_classes_alt=stamp_classes_alt,
        input_ignore_classes=input_ignore_classes,
        title_ignore_classes=title_ignore_classes,
        tags_ignore_classes=tags_ignore_classes,
        anchor_class_colors=anchor_class_colors,
        wired_class_colors=wired_class_colors,
        stamps_shortcut=stamps_shortcut,
        keep_original_tags=keep_original_tags,
        default_title_fn=default_title_fn,
        default_tags_fn=default_tags_fn,
    )
