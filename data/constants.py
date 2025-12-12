TILE_SIZE = 8

CHUNK_SIZES = [
    (64, 64),
    (64, 32),
    (32, 64),
    (32, 32),
    (32, 16),
    (16, 32),
    (32, 8),
    (8, 32),
    (16, 16),
    (16, 8),
    (8, 16),
    (8, 8),
]

ORIENTATION_VALUES = {
    "original": (0, 0),
    "flip_h": (0, 1),
    "flip_v": (1, 0),
    "flip_both": (1, 1),
}
