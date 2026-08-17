"""Face detection, matching and image search.

Imports are deliberately *not* re-exported here: ``face_matching`` pulls in
DeepFace/TensorFlow and ``image_search`` needs Google credentials, so importing
``fraudguard.vision`` must stay free.  Import the submodule you need.
"""

__all__ = ["face_matching", "image_search"]
