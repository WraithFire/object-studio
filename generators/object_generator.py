import os
import json
import xxhash
import colorsys
import numpy as np
import xml.etree.ElementTree as ET
from xml.dom import minidom
from PIL import Image, ImageDraw
from data.config import DEBUG
from data.constants import TILE_SIZE, CHUNK_SIZES


def validate_og_input_folder(folder):
    print("🔍 Validating images in folder...\n")

    images_dict = {}
    common_image_size = None
    should_pad = False
    padding_height = 0
    padding_width = 0
    original_shared_palette = None
    max_colors_used = None
    available_frames = set()

    png_files = [f for f in os.listdir(folder) if f.lower().endswith(".png")]

    if not png_files:
        print("\n❌ No png images found")
        return (
            images_dict,
            common_image_size,
            original_shared_palette,
            max_colors_used,
            available_frames,
        )

    for file_name in png_files:
        name_without_ext = file_name[:-4]
        parts = name_without_ext.split("-")
        errors_for_file = []

        # Check name format
        if (
            len(parts) != 4
            or parts[0].lower() != "frame"
            or not parts[1].isdigit()
            or parts[2].lower() != "layer"
            or not parts[3].isdigit()
        ):
            print(f"⚠️  {file_name}:")
            print(f"    • Invalid name format")
            continue

        frame_num = int(parts[1])
        layer_num = int(parts[3])

        image_path = os.path.join(folder, file_name)

        try:
            with Image.open(image_path) as img:
                # Check if indexed
                if img.mode != "P":
                    errors_for_file.append("Not an indexed image")
                else:
                    if original_shared_palette is None:
                        original_shared_palette = img.getpalette()

                        max_colors_used = len(original_shared_palette) // 3

                        if max_colors_used > 192:
                            errors_for_file.append(
                                f"Uses {max_colors_used} colors (max allowed: 192)"
                            )

                    if img.getpalette() != original_shared_palette:
                        errors_for_file.append("Palette differs from other images.")

                # Check dimensions
                width, height = img.size
                if common_image_size is None:
                    common_image_size = (width, height)
                    padding_width = (width + 7) // 8 * 8 - width
                    padding_height = (height + 7) // 8 * 8 - height
                    should_pad = padding_width > 0 or padding_height > 0
                    if DEBUG and should_pad:
                        print(
                            f"Padding from {width}x{height} to "
                            f"{width+padding_width}x{height+padding_height}\n"
                        )
                elif (width, height) != common_image_size:
                    errors_for_file.append(
                        f"Size {width}x{height}. Expected: {common_image_size[0]}x{common_image_size[1]}"
                    )

                # Print all errors for this file
                if errors_for_file:
                    print(f"⚠️  {file_name}:")
                    for error in errors_for_file:
                        print(f"    • {error}")
                else:
                    numpy_array = np.asarray(img, dtype=np.uint8)

                    if should_pad:
                        numpy_array = np.pad(
                            numpy_array,
                            ((0, padding_height), (0, padding_width)),
                            mode="constant",
                            constant_values=0,
                        )

                        img = Image.fromarray(numpy_array, mode="P")
                        img.putpalette(original_shared_palette)
                        img.info["transparency"] = 0

                    reduced_numpy = numpy_array % 16
                    mask = reduced_numpy != 0
                    groups_used = np.unique(numpy_array[mask] // 16)

                    if groups_used.size > 1:
                        print(
                            f"💡 {file_name}: Splitting into palette layers {groups_used.tolist()}\n"
                        )

                        for palette_group in groups_used:
                            group_mask = (numpy_array // 16) == palette_group

                            split_array = np.where(group_mask, numpy_array, 0)
                            split_reduced = split_array % 16

                            sub_layer_name = f"frame-{frame_num}-layer-{layer_num}.{palette_group}.png"

                            split_img = Image.fromarray(split_array, mode="P")
                            split_img.putpalette(img.getpalette())

                            split_img.info["transparency"] = 0

                            images_dict[sub_layer_name] = {
                                "image_data": split_img.convert("RGBA"),
                                "tile_hash_dict": create_tile_hash_dict(
                                    split_reduced, False
                                ),
                                "frame_layer_palette_tuple": (
                                    frame_num,
                                    layer_num,
                                    int(palette_group),
                                ),
                                "is_transparent": False,
                            }
                    else:
                        is_transparent = False

                        if groups_used.size == 0:
                            groups_used = np.array([0], dtype=np.uint8)
                            is_transparent = True

                        images_dict[file_name] = {
                            "image_data": img.convert("RGBA"),
                            "tile_hash_dict": create_tile_hash_dict(
                                reduced_numpy, is_transparent
                            ),
                            "frame_layer_palette_tuple": (
                                frame_num,
                                layer_num,
                                int(groups_used[0]),
                            ),
                            "is_transparent": is_transparent,
                        }

                    available_frames.add(frame_num)

        except Exception as e:
            print(f"⚠️  {file_name}: Error reading file - {str(e)}")
            continue

    if not images_dict:
        print("\n❌ No valid images found")
    else:
        common_image_size = (
            common_image_size[0] + padding_width,
            common_image_size[1] + padding_height,
        )

    return (
        images_dict,
        common_image_size,
        original_shared_palette,
        max_colors_used,
        sorted(available_frames),
    )


def create_tile_hash_dict(image_array, is_transparent):
    tile_hash_dict = {}

    if is_transparent:
        return tile_hash_dict

    image_height, image_width = image_array.shape
    tiles_y = image_height // TILE_SIZE
    tiles_x = image_width // TILE_SIZE

    cropped = image_array[: tiles_y * TILE_SIZE, : tiles_x * TILE_SIZE]
    tiles = cropped.reshape(tiles_y, TILE_SIZE, tiles_x, TILE_SIZE)
    tiles = np.ascontiguousarray(tiles.transpose(0, 2, 1, 3))

    variants = {
        "original": tiles,
        "flip_h": np.flip(tiles, axis=3),
        "flip_v": np.flip(tiles, axis=2),
        "flip_both": np.flip(tiles, (2, 3)),
    }

    for orient_name, tile_array in variants.items():
        flat_tiles = tile_array.reshape(-1, TILE_SIZE * TILE_SIZE)
        flat_tiles = np.ascontiguousarray(flat_tiles)

        buf = flat_tiles.tobytes()
        tile_size_bytes = TILE_SIZE * TILE_SIZE * flat_tiles.itemsize

        orientation_hashes = np.fromiter(
            (
                xxhash.xxh3_64(buf[i : i + tile_size_bytes]).intdigest()
                for i in range(0, len(buf), tile_size_bytes)
            ),
            dtype=np.uint64,
            count=flat_tiles.shape[0],
        )

        orientation_hashes = orientation_hashes.reshape(tiles_y, tiles_x)

        orientation_numpy = tile_array.transpose(0, 2, 1, 3).reshape(
            tiles_y * TILE_SIZE, tiles_x * TILE_SIZE
        )

        tile_hash_dict[orient_name] = {
            "tile_hashes": orientation_hashes,
            "numpy_array": orientation_numpy,
        }

    return tile_hash_dict


def get_oriented_chunks_data(
    tile_hash_dict,
    chunk_x,
    chunk_y,
    chunk_width,
    chunk_height,
    min_density,
):
    unique_hashes = {}
    seen_hashes = set()

    tiles_height, tiles_width = chunk_height // TILE_SIZE, chunk_width // TILE_SIZE

    image_numpy = tile_hash_dict["original"]["numpy_array"]
    chunk_numpy = image_numpy[
        chunk_y : chunk_y + chunk_height, chunk_x : chunk_x + chunk_width
    ]

    # reshape to tile grid
    tiles = chunk_numpy[: tiles_height * TILE_SIZE, : tiles_width * TILE_SIZE]
    tiles = tiles.reshape(tiles_height, TILE_SIZE, tiles_width, TILE_SIZE).swapaxes(
        1, 2
    )

    filled_mask = (tiles != 0).any(axis=(2, 3))
    row_density = filled_mask.sum(axis=1) / tiles_width
    col_density = filled_mask.sum(axis=0) / tiles_height

    if not ((row_density >= min_density).all() and (col_density >= min_density).all()):
        return None

    # Compute chunk hashes for all orientations
    tiles_x, tiles_y = chunk_x // TILE_SIZE, chunk_y // TILE_SIZE

    for orient_name, orient_data in tile_hash_dict.items():
        numpy_array = orient_data["numpy_array"]
        tile_hashes = orient_data["tile_hashes"]

        sub_hashes = tile_hashes[
            tiles_y : tiles_y + tiles_height,
            tiles_x : tiles_x + tiles_width,
        ]

        hash_obj = xxhash.xxh3_64()
        hash_obj.update(np.asarray(sub_hashes.shape, dtype=np.int32).tobytes())
        hash_obj.update(sub_hashes.tobytes())
        chunk_hash = hash_obj.intdigest()

        if chunk_hash not in seen_hashes:
            chunk_numpy_orient = numpy_array[
                chunk_y : chunk_y + chunk_height,
                chunk_x : chunk_x + chunk_width,
            ]
            unique_hashes[orient_name] = (chunk_hash, chunk_numpy_orient.copy())
            seen_hashes.add(chunk_hash)

    return unique_hashes


def get_orientation_values(orientation):
    return {
        "original": (0, 0),
        "flip_h": (0, 1),
        "flip_v": (1, 0),
        "flip_both": (1, 1),
    }.get(orientation, (0, 0))


def get_inside_coordinates(x, y, chunk_width, chunk_height):
    used_coords = set()
    for cy in range(y, y + chunk_height, TILE_SIZE):
        for cx in range(x, x + chunk_width, TILE_SIZE):
            used_coords.add((cx, cy))
    return used_coords


def string_to_pretty_xml(text_string):
    reparsed = minidom.parseString(text_string)
    pretty_xml = reparsed.toprettyxml(indent="    ")

    lines = [line for line in pretty_xml.split("\n") if line.strip()]
    final_xml = "\n".join(lines)

    return final_xml


def format_chunk_track_dict(chunk_track_dict):
    grouped_chunks = {}

    for chunk_id, chunk_data in enumerate(chunk_track_dict.values()):
        # Parse main chunk info
        frame_num, layer_num, palette_num = chunk_data["frame_layer_palette_tuple"]
        coords = chunk_data["coordinates"]
        dim = chunk_data["dimension"]
        orientation_original = get_orientation_values("original")

        # Main chunk with precomputed sort key
        main_chunk = {
            "chunk_id": chunk_id,
            "coordinates": coords,
            "dimension": dim,
            "orientation": orientation_original,
            "layer": layer_num,
            "palette": palette_num,
            "_sort_key": (-layer_num, coords[0], coords[1]),
        }

        grouped_chunks.setdefault(frame_num, []).append(main_chunk)

        # Duplicates
        for dup in chunk_data.get("duplicates"):
            dup_frame, dup_layer, dup_palette = dup["frame_layer_palette_tuple"]
            dup_chunk = {
                "chunk_id": chunk_id,
                "coordinates": dup["coordinates"],
                "dimension": dim,
                "orientation": get_orientation_values(dup["orientation"]),
                "layer": dup_layer,
                "palette": dup_palette,
                "_sort_key": (-dup_layer, dup["coordinates"][0], dup["coordinates"][1]),
            }

            grouped_chunks.setdefault(dup_frame, []).append(dup_chunk)

    # Build final dict sorted by frame and chunk
    formatted_dict = {}
    for frame_num in sorted(grouped_chunks):
        chunks = grouped_chunks[frame_num]
        chunks.sort(key=lambda c: c["_sort_key"])
        formatted_dict[f"Frame-{frame_num}"] = chunks

    return formatted_dict


def save_riff_palette(palette, output_folder):

    # Get up to 256 (R, G, B) tuples
    colors = [tuple(palette[i : i + 3]) for i in range(0, min(len(palette), 768), 3)]
    num_colors = len(colors)

    # LOGPALETTE Header (palVersion: 0x300, palNumEntries: num_colors)
    header = (0x0300).to_bytes(2, "little") + num_colors.to_bytes(2, "little")

    # Each PALETTEENTRY = (R, G, B, Flags)
    entries = b"".join(bytes((r, g, b, 0)) for (r, g, b) in colors)

    # Chunk data
    chunk_data = header + entries
    chunk_size = len(chunk_data)

    # RIFF chunk
    riff_chunk = (
        b"RIFF"
        + (12 + chunk_size).to_bytes(4, "little")
        + b"PAL "
        + b"data"
        + chunk_size.to_bytes(4, "little")
        + chunk_data
    )

    PALETTE_OUT = os.path.join(output_folder, "palette.pal")

    with open(PALETTE_OUT, "wb") as f:
        f.write(riff_chunk)

    print(f"✅ palette.pal saved to: {PALETTE_OUT}")


def generate_frames_xml(formatted_chunk_track_dict, initial_coordinate, output_folder):
    root = ET.Element("FrameList")

    frame_memory_usage = []

    for chunks in formatted_chunk_track_dict.values():
        chunk_memory_map = {}
        # Create Image element
        image_elem = ET.SubElement(root, "FrameGroup")

        # Track memory offset for current image
        current_memory_offset = 0

        for chunk_data in chunks:
            chunk_elem = ET.SubElement(image_elem, "Frame")

            chunk_id = chunk_data["chunk_id"]
            coordinates = chunk_data["coordinates"]
            dimension = chunk_data["dimension"]
            orientation = chunk_data["orientation"]
            palette = chunk_data["palette"]

            chunk_id_elem = ET.SubElement(chunk_elem, "ImageIndex")

            # Handle chunk ID and memory offset
            if chunk_id in chunk_memory_map:
                # Duplicate chunk use -1 as chunk ID and reference existing memory offset
                chunk_id_elem.text = "-1"
                memory_offset = chunk_memory_map[chunk_id]
            else:
                # New chunk
                chunk_id_elem.text = str(chunk_id)
                memory_offset = current_memory_offset
                chunk_memory_map[chunk_id] = memory_offset

                # Calculate next memory offset
                width, height = dimension
                current_memory_offset += ((height * width) + 255) // 256

            # Unk0 Element has values ["0x0", "0x500", "0x7f00", "0xa00", "0xf600", "0xfb00"]
            unk0_elem = ET.SubElement(chunk_elem, "Unk0")
            unk0_elem.text = "0x0"

            # Add Offset
            offset_elem = ET.SubElement(chunk_elem, "Offset")
            x_elem = ET.SubElement(offset_elem, "X")
            x_elem.text = str(initial_coordinate[0] + coordinates[0])
            y_elem = ET.SubElement(offset_elem, "Y")
            y_elem.text = str(initial_coordinate[1] + coordinates[1])

            # Add palette (format: 0xc, 0x1c, 0x2c, etc.)
            palette_offset_elem = ET.SubElement(chunk_elem, "Unk1")
            palette_offset_elem.text = hex(0xC + palette * 0x10)

            # Add MemoryOffset
            memory_elem = ET.SubElement(chunk_elem, "Unk15")
            memory_elem.text = hex(memory_offset)

            # Add Resolution
            resolution_elem = ET.SubElement(chunk_elem, "Resolution")
            width_elem = ET.SubElement(resolution_elem, "Width")
            width_elem.text = str(dimension[0])
            height_elem = ET.SubElement(resolution_elem, "Height")
            height_elem.text = str(dimension[1])

            # Add VFlip and HFlip
            vflip_elem = ET.SubElement(chunk_elem, "VFlip")
            vflip_elem.text = str(orientation[0])
            hflip_elem = ET.SubElement(chunk_elem, "HFlip")
            hflip_elem.text = str(orientation[1])

            # Mosaic Element always 0
            mosaic = ET.SubElement(chunk_elem, "Mosaic")
            mosaic.text = "0"

            # XOffsetBit6 Element can be 0 or 1
            x_offsetbit_6 = ET.SubElement(chunk_elem, "XOffsetBit6")
            x_offsetbit_6.text = "0"

            # XOffsetBit7 Element always 0
            x_offsetbit_7 = ET.SubElement(chunk_elem, "XOffsetBit7")
            x_offsetbit_7.text = "0"

            # YOffsetBit3 Element always 0
            y_offsetbit_3 = ET.SubElement(chunk_elem, "YOffsetBit3")
            y_offsetbit_3.text = "0"

            # YOffsetBit5 Element always 0
            y_offsetbit_5 = ET.SubElement(chunk_elem, "YOffsetBit5")
            y_offsetbit_5.text = "0"

            # YOffsetBit6 Element always 0
            y_offsetbit_6 = ET.SubElement(chunk_elem, "YOffsetBit6")
            y_offsetbit_6.text = "0"

        frame_memory_usage.append(current_memory_offset)

    # Pretty print XML
    rough_string = ET.tostring(root, "unicode")
    pretty_xml = string_to_pretty_xml(rough_string)

    FRAMES_XML_OUT = os.path.join(output_folder, "frames.xml")

    with open(FRAMES_XML_OUT, "w", encoding="utf-8") as f:
        f.write(pretty_xml)

    print(f"✅ frames.xml saved to: {FRAMES_XML_OUT}")

    return frame_memory_usage


def generate_animations_xml(available_frames, animation_group, output_folder):
    root = ET.Element("AnimData")

    group_table = ET.SubElement(root, "AnimGroupTable")
    anim_group = ET.SubElement(group_table, "AnimGroup", name="")
    for i in range(len(animation_group)):
        # range 0-16
        ET.SubElement(anim_group, "AnimSequenceIndex").text = str(i)

    seq_table = ET.SubElement(root, "AnimSequenceTable")
    for anim in animation_group:
        anim_node = ET.SubElement(seq_table, "AnimSequence", name="")
        for frame_data in anim:
            image_no = frame_data["frame"]
            image_index = available_frames.index(image_no)
            duration = frame_data["duration"]
            frame_node = ET.SubElement(anim_node, "AnimFrame")
            # range 1-260
            ET.SubElement(frame_node, "Duration").text = str(duration)
            ET.SubElement(frame_node, "MetaFrameGroupIndex").text = str(image_index)

            # Sprite Element has range
            sprite_elem = ET.SubElement(frame_node, "Sprite")
            sprite_xoffset_elem = ET.SubElement(sprite_elem, "XOffset")
            sprite_xoffset_elem.text = "0"
            sprite_yoffset_elem = ET.SubElement(sprite_elem, "YOffset")
            sprite_yoffset_elem.text = "0"

            # Shadow Element has range
            shadow_elem = ET.SubElement(frame_node, "Shadow")
            shadow_xoffset_elem = ET.SubElement(shadow_elem, "XOffset")
            shadow_xoffset_elem.text = "0"
            shadow_yoffset_elem = ET.SubElement(shadow_elem, "YOffset")
            shadow_yoffset_elem.text = "0"

    # Pretty print XML
    rough_string = ET.tostring(root, "unicode")
    pretty_xml = string_to_pretty_xml(rough_string)

    ANIMATIONS_XML_OUT = os.path.join(output_folder, "animations.xml")

    with open(ANIMATIONS_XML_OUT, "w", encoding="utf-8") as f:
        f.write(pretty_xml)

    print(f"✅ animation.xml saved to: {ANIMATIONS_XML_OUT}")


def generate_sprite_info_xml(max_memory_used, max_colors_used, output_folder):
    root = ET.Element("SpriteProperties")
    # Always 0x0
    ET.SubElement(root, "Unk3").text = "0x0"
    # Total Color games use max 12 palette (192 color)
    ET.SubElement(root, "ColorsPerRow").text = str(max_colors_used)
    # Always 0x0
    ET.SubElement(root, "Unk4").text = "0x0"
    # Always 0xff
    ET.SubElement(root, "Unk5").text = "0xff"
    # Max Memory Taken by Animation 0x8a(138 dec)
    ET.SubElement(root, "Unk6").text = hex(max_memory_used)
    # Always 0x0
    ET.SubElement(root, "Unk7").text = "0x0"
    # Always 0x0
    ET.SubElement(root, "Unk8").text = "0x0"
    # Always 0x0
    ET.SubElement(root, "Unk9").text = "0x0"
    # Always 0x0
    ET.SubElement(root, "Unk10").text = "0x0"
    # Always 0x0
    ET.SubElement(root, "SpriteType").text = "0x0"
    # Always 0x0
    ET.SubElement(root, "Is256Colors").text = "0x0"
    # 0x0(chunk_mode) or 0x1(tile_mode) | (bugged in gfxcrunch so only chunk_mode for now)
    ET.SubElement(root, "Unk13").text = "0x0"
    # no of pallete slot used 0x1 - 0xc (max 12)
    palette_group = max_colors_used // 16
    ET.SubElement(root, "Unk11").text = hex(palette_group)
    # Always 0x0
    ET.SubElement(root, "Unk12").text = "0x0"

    # Pretty print XML
    rough_string = ET.tostring(root, "unicode")
    pretty_xml = string_to_pretty_xml(rough_string)

    SPRITE_INFO_XML_OUT = os.path.join(output_folder, "spriteinfo.xml")

    with open(SPRITE_INFO_XML_OUT, "w", encoding="utf-8") as f:
        f.write(pretty_xml)

    print(f"✅ spriteinfo.xml saved to: {SPRITE_INFO_XML_OUT}")


def generate_imgsinfo_and_offsets_xml(output_folder):
    # Generate imgsinfo.xml
    IMGS_INFO_XML_OUT = os.path.join(output_folder, "imgsinfo.xml")
    xml_text_string = '<?xml version="1.0"?><ImagesInfo />'
    pretty_xml = string_to_pretty_xml(xml_text_string)
    with open(IMGS_INFO_XML_OUT, "w", encoding="utf-8") as f:
        f.write(pretty_xml)
    print(f"✅ imgsinfo.xml saved to: {IMGS_INFO_XML_OUT}")

    # Generate offsets.xml
    OFFSETS_XML_OUT = os.path.join(output_folder, "offsets.xml")
    xml_text_string = '<?xml version="1.0"?><OffsetList />'
    pretty_xml = string_to_pretty_xml(xml_text_string)
    with open(OFFSETS_XML_OUT, "w", encoding="utf-8") as f:
        f.write(pretty_xml)
    print(f"✅ offsets.xml saved to: {OFFSETS_XML_OUT}")


def save_unique_chunk_in_dict(
    chunk_track_dict,
    hash_key,
    chunk_x,
    chunk_y,
    chunk_width,
    chunk_height,
    image_name,
    flp_tuple,
    numpy_array,
    coords_inside_chunk,
):

    chunk_track_dict[hash_key] = {
        "coordinates": (chunk_x, chunk_y),
        "dimension": (chunk_width, chunk_height),
        "source_image": image_name,
        "frame_layer_palette_tuple": flp_tuple,
        "duplicates": [],
        "chunk_numpy_array": numpy_array,
        "inside_coordinates": coords_inside_chunk,
    }

    if DEBUG:
        print(
            f"[SAVE] Unique Chunk {hash_key} from {image_name} at ({chunk_x}, {chunk_y})"
        )


def save_duplicate_chunk_in_dict(
    chunk_track_dict,
    hash_key,
    chunk_x,
    chunk_y,
    orient_name,
    image_name,
    flp_tuple,
):
    chunk_track_dict[hash_key]["duplicates"].append(
        {
            "coordinates": (chunk_x, chunk_y),
            "orientation": orient_name,
            "source_image": image_name,
            "frame_layer_palette_tuple": flp_tuple,
        }
    )

    if DEBUG:
        print(
            f"[APPEND] Duplicate Chunk of {hash_key} in {image_name} at "
            f"({chunk_x}, {chunk_y}) orientation={orient_name}"
        )


def save_transparent_frames_chunk(chunk_track_dict, frame_layes_name_dict):

    transparent_frames = [
        (frame, layers[0][0])
        for frame, layers in frame_layes_name_dict.items()
        if all(is_transparent for _, is_transparent in layers)
    ]

    numpy_array = np.zeros((TILE_SIZE, TILE_SIZE), dtype=np.uint8)
    for frame, layer_name in transparent_frames:
        if not chunk_track_dict.get("-9999"):
            save_unique_chunk_in_dict(
                chunk_track_dict,
                "-9999",
                0,
                0,
                TILE_SIZE,
                TILE_SIZE,
                layer_name,
                (frame, 0, 0),
                numpy_array,
                (0, 0),
            )
        else:
            save_duplicate_chunk_in_dict(
                chunk_track_dict,
                "-9999",
                0,
                0,
                "original",
                layer_name,
                (frame, 0, 0),
            )


def save_remaining_chunks(
    images_dict, chunk_track_dict, image_height, image_width, min_row_column_density
):
    unique_chunk_counter = 0
    for chunk_width, chunk_height in CHUNK_SIZES:
        if chunk_height > image_height or chunk_width > image_width:
            continue

        chunk_message = (
            f"\n🔍 Scanning for remaining chunks of size ({chunk_width}x{chunk_height})"
        )
        if DEBUG:
            chunk_message = f"\n{'-'*59}{chunk_message}\n{'-'*59}\n"

        print(chunk_message)

        for image_name, image_info in images_dict.items():
            current_image_tile_hash_dict = image_info["tile_hash_dict"]
            current_image_valid_coordinates = image_info["valid_coordinates"]
            current_image_flp_tuple = image_info["frame_layer_palette_tuple"]

            sorted_valid_coordinates = sorted(
                current_image_valid_coordinates, key=lambda coord: (coord[1], coord[0])
            )

            for x, y in sorted_valid_coordinates:
                if x + chunk_width > image_width or y + chunk_height > image_height:
                    continue

                # check for used area
                coordinates_inside_current_chunk = get_inside_coordinates(
                    x, y, chunk_width, chunk_height
                )

                if not coordinates_inside_current_chunk.issubset(
                    current_image_valid_coordinates
                ):
                    continue

                current_chunk_oriented_data = get_oriented_chunks_data(
                    current_image_tile_hash_dict,
                    x,
                    y,
                    chunk_width,
                    chunk_height,
                    min_row_column_density,
                )

                if not current_chunk_oriented_data:
                    continue

                coords_inside_chunk = get_inside_coordinates(
                    x, y, chunk_width, chunk_height
                )

                current_image_valid_coordinates.difference_update(coords_inside_chunk)

                matched = False

                original_hash = current_chunk_oriented_data["original"][0]
                original_numpy = current_chunk_oriented_data["original"][1]

                for orient_name, (
                    oriented_chunk_hash,
                    oriented_chunk_numpy,
                ) in current_chunk_oriented_data.items():

                    existing_entry = chunk_track_dict.get(oriented_chunk_hash)

                    if existing_entry is not None:
                        if np.array_equal(
                            existing_entry["chunk_numpy_array"], oriented_chunk_numpy
                        ):
                            save_duplicate_chunk_in_dict(
                                chunk_track_dict,
                                oriented_chunk_hash,
                                x,
                                y,
                                orient_name,
                                image_name,
                                current_image_flp_tuple,
                            )
                        else:
                            # Hash collison
                            save_unique_chunk_in_dict(
                                chunk_track_dict,
                                unique_chunk_counter,
                                x,
                                y,
                                chunk_width,
                                chunk_height,
                                image_name,
                                current_image_flp_tuple,
                                original_numpy,
                                coords_inside_chunk,
                            )
                            unique_chunk_counter += 1
                        matched = True
                        break

                if not matched:
                    save_unique_chunk_in_dict(
                        chunk_track_dict,
                        original_hash,
                        x,
                        y,
                        chunk_width,
                        chunk_height,
                        image_name,
                        current_image_flp_tuple,
                        original_numpy,
                        coords_inside_chunk,
                    )


def scan_for_repeated_chunks(
    images_dict,
    chunk_track_dict,
    image_height,
    image_width,
    min_row_column_density,
    current_image_name,
    chunk_width,
    chunk_height,
    tracking_hash_map,
    loop_no,
):
    current_image_info = images_dict[current_image_name]
    current_image_tile_hash_dict = current_image_info["tile_hash_dict"]
    current_image_flp_tuple = current_image_info["frame_layer_palette_tuple"]
    current_image_valid_coords = current_image_info["valid_coordinates"]

    sorted_valid_coordinates = sorted(
        current_image_valid_coords, key=lambda coord: (coord[1], coord[0])
    )

    for x, y in sorted_valid_coordinates:
        if x + chunk_width > image_width or y + chunk_height > image_height:
            continue

        coords_inside_current_chunk = get_inside_coordinates(
            x, y, chunk_width, chunk_height
        )

        if not coords_inside_current_chunk.issubset(current_image_valid_coords):
            continue

        current_chunk_oriented_data = get_oriented_chunks_data(
            current_image_tile_hash_dict,
            x,
            y,
            chunk_width,
            chunk_height,
            min_row_column_density,
        )

        if not current_chunk_oriented_data:
            continue

        matched = False

        for orient_name, (
            oriented_chunk_hash,
            oriented_chunk_numpy,
        ) in current_chunk_oriented_data.items():

            if loop_no == 1 and oriented_chunk_hash not in tracking_hash_map:
                continue

            if loop_no == 2 and (
                oriented_chunk_hash not in tracking_hash_map
                and oriented_chunk_hash not in chunk_track_dict
            ):
                continue

            # Retrieve the original chunk entry
            if oriented_chunk_hash in tracking_hash_map:
                original_chunk_entry = tracking_hash_map[oriented_chunk_hash]
            else:
                original_chunk_entry = chunk_track_dict[oriented_chunk_hash]
            original_chunk_numpy = original_chunk_entry["chunk_numpy_array"]
            original_chunk_image_name = original_chunk_entry["source_image"]
            ox, oy = original_chunk_entry["coordinates"]
            original_chunk_flp_tuple = original_chunk_entry["frame_layer_palette_tuple"]
            coords_inside_original_chunk = original_chunk_entry["inside_coordinates"]

            original_image_valid_coords = images_dict[original_chunk_image_name][
                "valid_coordinates"
            ]

            # Skip overlapping or invalid regions
            if (
                original_chunk_image_name == current_image_name
                and coords_inside_original_chunk & coords_inside_current_chunk
            ):
                continue

            if not np.array_equal(original_chunk_numpy, oriented_chunk_numpy):
                continue

            # ✅ Found a valid duplicate
            matched = True

            # Check if ANY orientation of this chunk is already in chunk_track_dict
            saved_orient_hash = None
            for o_chunk_hash, _ in current_chunk_oriented_data.values():
                if o_chunk_hash in chunk_track_dict:
                    saved_orient_hash = o_chunk_hash
                    break

            if saved_orient_hash is None:
                # No orientation saved yet - save the original chunk as unique
                original_image_valid_coords.difference_update(
                    coords_inside_original_chunk
                )
                save_unique_chunk_in_dict(
                    chunk_track_dict,
                    oriented_chunk_hash,
                    ox,
                    oy,
                    chunk_width,
                    chunk_height,
                    original_chunk_image_name,
                    original_chunk_flp_tuple,
                    original_chunk_numpy,
                    coords_inside_original_chunk,
                )
            else:
                # Some orientation already saved
                # Check if the original chunk is the saved entry itself
                saved_entry = chunk_track_dict[saved_orient_hash]
                is_original_the_saved_entry = saved_entry[
                    "source_image"
                ] == original_chunk_image_name and saved_entry["coordinates"] == (
                    ox,
                    oy,
                )

                if not is_original_the_saved_entry:
                    original_already_added = False
                    if "duplicates" in saved_entry:
                        for dup in saved_entry["duplicates"]:
                            if dup["source_image"] == original_chunk_image_name and dup[
                                "coordinates"
                            ] == (ox, oy):
                                original_already_added = True
                                break

                    if not original_already_added:
                        original_image_valid_coords.difference_update(
                            coords_inside_original_chunk
                        )
                        save_duplicate_chunk_in_dict(
                            chunk_track_dict,
                            saved_orient_hash,
                            ox,
                            oy,
                            orient_name,
                            original_chunk_image_name,
                            original_chunk_flp_tuple,
                        )

                # Update oriented_chunk_hash to use the saved orientation
                oriented_chunk_hash = saved_orient_hash

            # Record current as duplicate
            current_image_valid_coords.difference_update(coords_inside_current_chunk)

            save_duplicate_chunk_in_dict(
                chunk_track_dict,
                oriented_chunk_hash,
                x,
                y,
                orient_name,
                current_image_name,
                current_image_flp_tuple,
            )

            break  # Stop checking other orientations

        # If chunk wasn't found in hash map
        if not matched:
            # check if it's clashing duplicate
            orientation_hashes = {h for h, _ in current_chunk_oriented_data.values()}

            if tracking_hash_map.keys().isdisjoint(orientation_hashes):
                current_chunk_hash, current_chunk_numpy = current_chunk_oriented_data[
                    "original"
                ]
                tracking_hash_map[current_chunk_hash] = {
                    "source_image": current_image_name,
                    "coordinates": (x, y),
                    "frame_layer_palette_tuple": current_image_flp_tuple,
                    "inside_coordinates": coords_inside_current_chunk,
                    "chunk_numpy_array": current_chunk_numpy,
                }


def save_repeated_chunks(
    images_dict,
    frame_layes_name_dict,
    chunk_track_dict,
    image_height,
    image_width,
    intra_scan,
    inter_scan,
    scan_chunk_sizes,
    min_row_column_density,
):
    if intra_scan:

        for frame_no, frame_layers in frame_layes_name_dict.items():

            for chunk_width, chunk_height in scan_chunk_sizes:

                if chunk_height > image_height or chunk_width > image_width:
                    continue

                chunk_size_specific_dict = {}

                chunk_message = f"\n🔍 Scanning for repeated chunks of size ({chunk_width}x{chunk_height}) in Frame-{frame_no}"

                if DEBUG:
                    chunk_message = f"\n{'-'*59}{chunk_message}\n{'-'*59}\n"

                print(chunk_message)

                for layer_name, _ in frame_layers:

                    scan_for_repeated_chunks(
                        images_dict,
                        chunk_track_dict,
                        image_height,
                        image_width,
                        min_row_column_density,
                        layer_name,
                        chunk_width,
                        chunk_height,
                        chunk_size_specific_dict,
                        loop_no=1,
                    )

    if inter_scan:
        for chunk_width, chunk_height in scan_chunk_sizes:

            if chunk_height > image_height or chunk_width > image_width:
                continue

            chunk_size_specific_dict = {}

            chunk_message = f"\n🔍 Scanning across images for repeated chunks of size ({chunk_width}x{chunk_height})"

            if DEBUG:
                chunk_message = f"\n{'-'*59}{chunk_message}\n{'-'*59}\n"

            print(chunk_message)

            for current_image_name in images_dict:

                scan_for_repeated_chunks(
                    images_dict,
                    chunk_track_dict,
                    image_height,
                    image_width,
                    min_row_column_density,
                    current_image_name,
                    chunk_width,
                    chunk_height,
                    chunk_size_specific_dict,
                    loop_no=2,
                )


def annotate_chunks(
    images_dict, chunk_track_dict, total_unique_chunks, debug_output_dir
):

    # Generate distinct colors inside this function
    distinct_colors = []
    for i in range(total_unique_chunks):
        hue = i / total_unique_chunks
        lightness = 0.5
        saturation = 0.9
        rgb = colorsys.hls_to_rgb(hue, lightness, saturation)
        rgb = tuple(int(c * 255) for c in rgb)
        distinct_colors.append(rgb)

    for image_name, image_info in images_dict.items():
        image_data = image_info["image_data"].copy()
        draw = ImageDraw.Draw(image_data)

        # Iterate through chunk_track_dict
        for index, chunk_info in enumerate(chunk_track_dict.values()):
            color = distinct_colors[index]

            # Check if this chunk's original is from current image
            if chunk_info.get("source_image") == image_name:
                x, y = chunk_info["coordinates"]
                chunk_width, chunk_height = chunk_info["dimension"]
                draw.rectangle(
                    [x, y, x + chunk_width - 1, y + chunk_height - 1],
                    outline=color,
                    width=1,
                )

            # Draw rectangles for duplicates in this image
            for duplicate in chunk_info["duplicates"]:
                if duplicate.get("source_image") == image_name:
                    dup_x, dup_y = duplicate["coordinates"]
                    chunk_width, chunk_height = chunk_info["dimension"]
                    draw.rectangle(
                        [
                            dup_x,
                            dup_y,
                            dup_x + chunk_width - 1,
                            dup_y + chunk_height - 1,
                        ],
                        outline=color,
                        width=1,
                    )

        output_path = os.path.join(
            debug_output_dir,
            f"{image_name[:-4]}-Palette-{image_info['frame_layer_palette_tuple'][2]}-annotated.png",
        )
        image_data.save(output_path)

    print(f"\n✅Annotated images saved to: {debug_output_dir}\n")


def do_debug_exclusive_stuff(
    images_dict,
    chunk_track_dict,
    formatted_chunk_track_dict,
    total_unique_chunks,
    input_folder,
):
    debug_output_dir = os.path.join(input_folder, "DEBUG")
    if DEBUG:
        os.makedirs(debug_output_dir, exist_ok=True)

    # annotate chunks
    annotate_chunks(
        images_dict, chunk_track_dict, total_unique_chunks, debug_output_dir
    )

    for key in chunk_track_dict:
        chunk_track_dict[key].pop("chunk_numpy_array", None)
        chunk_track_dict[key].pop("inside_coordinates", None)

    for key in images_dict:
        images_dict[key].pop("image_data", None)
        images_dict[key].pop("tile_hash_dict", None)
        images_dict[key].pop("valid_coordinates", None)

    # save debug info
    DEBUG_LOG_OUTPUT = os.path.join(debug_output_dir, "log.py")
    with open(DEBUG_LOG_OUTPUT, "w", encoding="utf-8") as f:
        f.write("Chunk_Track_Dict = ")
        f.write(json.dumps(chunk_track_dict, indent=4, ensure_ascii=False))
        f.write("\n\nFormatted_Chunk_Track_Dict = ")
        f.write(json.dumps(formatted_chunk_track_dict, indent=4, ensure_ascii=False))
        f.write("\n\nImages_Dict = ")
        f.write(json.dumps(images_dict, indent=4, ensure_ascii=False))


def save_chunks_to_folder(chunk_track_dict, reduced_shared_palette, output_folder):
    chunk_output_dir = os.path.join(output_folder, "imgs")
    os.makedirs(chunk_output_dir, exist_ok=True)

    for index, chunk_info in enumerate(chunk_track_dict.values()):
        chunk_image = Image.fromarray(chunk_info["chunk_numpy_array"])
        chunk_image.putpalette(reduced_shared_palette)
        filename = os.path.join(chunk_output_dir, f"{index:04d}.png")
        chunk_image.save(filename)
    print(f"✅ chunks saved to: {chunk_output_dir}")


def give_object_overview(
    max_memory_used,
    frame_memory_usage,
    max_colors_used,
    total_unique_chunks,
    formatted_chunk_track_dict,
):
    print("\nObject Info:")
    print(f"❔ Maximum Memory Used by Animation: {max_memory_used}")

    if max_memory_used > 255:
        print(
            f"❌ Memory limit exceeded — this will cause in-game issues."
            f"\n💡 Allowed maximum memory offset: 0xFF (255)"
        )
    elif max_memory_used > 138:
        print(
            f"⚠️ High memory usage — may cause in-game issues."
            f"\n💡 Base-game objects only use up to 0x8A (138)"
        )

    print(f"❔ Total Colors Used: {max_colors_used}")

    print(f"❔ Total Unique Chunks: {total_unique_chunks}")
    if total_unique_chunks > 144:
        print(
            f"⚠️ High total chunk count — may cause in-game issues."
            f"\n💡 Base-game objects use up to 144 unique chunks"
        )

    print("\nFrames Info: ")
    for frame_no, (frame, chunks) in enumerate(formatted_chunk_track_dict.items()):
        total_chunks = len(chunks)
        print(
            f"{frame}: Total Chunks = {total_chunks} and Memory = {frame_memory_usage[frame_no]}"
        )
        if total_chunks > 108:
            print(
                f"❌ {frame} uses {total_chunks} chunks — exceeds in-game render limit."
                f"\n💡 Allowed maximum chunks per frame: 108"
            )
        elif total_chunks > 80:
            print(
                f"⚠️ {frame} uses {total_chunks} chunks — may cause in-game issues."
                f"\n💡 Base-game frames use up to 80 chunks"
            )


def generate_object_main(data):
    (
        input_folder,
        images_dict,
        original_shared_palette,
        max_colors_used,
        image_height,
        image_width,
        available_frames,
        min_row_column_density,
        displace_object,
        animation_group,
        scan_chunk_sizes,
        intra_scan,
        inter_scan,
    ) = data

    reduced_shared_palette = original_shared_palette[: 16 * 3]

    valid_coordinates = get_inside_coordinates(0, 0, image_width, image_height)

    for file_name in images_dict:
        if images_dict[file_name]["is_transparent"]:
            images_dict[file_name]["valid_coordinates"] = set()
            if DEBUG:
                print(f"\n⚠️ {file_name} is Transparent, No Valid Coordinate\n")
        else:
            images_dict[file_name]["valid_coordinates"] = valid_coordinates.copy()

    chunk_track_dict = {}

    frame_layes_name_dict = {}

    for image_name, image_info in images_dict.items():
        frame_num, _, _ = image_info["frame_layer_palette_tuple"]
        is_transparent = image_info["is_transparent"]
        frame_layes_name_dict.setdefault(frame_num, []).append(
            (image_name, is_transparent)
        )

    # Find repeated chunks across ALL images
    save_repeated_chunks(
        images_dict,
        frame_layes_name_dict,
        chunk_track_dict,
        image_height,
        image_width,
        intra_scan,
        inter_scan,
        scan_chunk_sizes,
        min_row_column_density,
    )

    # Save remaining chunks from each image
    save_remaining_chunks(
        images_dict, chunk_track_dict, image_height, image_width, min_row_column_density
    )

    # Save Chunks From Transparent Frames
    save_transparent_frames_chunk(chunk_track_dict, frame_layes_name_dict)

    output_folder = os.path.join(input_folder, "object")

    print("\nGenerated File Info:")
    # Chunk Saving
    save_chunks_to_folder(chunk_track_dict, reduced_shared_palette, output_folder)

    # Generate palette.pal
    save_riff_palette(original_shared_palette, output_folder)

    # calculate top left corner coordinates | (256, 512) is center
    top_left_x = round(256 + displace_object[0] - image_width / 2)
    top_left_y = round(512 + displace_object[1] - image_height / 2)
    initial_coordinate = [top_left_x, top_left_y]

    # Generate frames.xml
    formatted_chunk_track_dict = format_chunk_track_dict(chunk_track_dict)
    frame_memory_usage = generate_frames_xml(
        formatted_chunk_track_dict, initial_coordinate, output_folder
    )

    max_memory_used = max(frame_memory_usage)

    # Generate animations.xmls
    generate_animations_xml(available_frames, animation_group, output_folder)

    # Generate spriteinfo.xml
    generate_sprite_info_xml(max_memory_used, max_colors_used, output_folder)

    # Generate useless xml
    generate_imgsinfo_and_offsets_xml(output_folder)

    total_unique_chunks = len(chunk_track_dict)

    # Give Overview
    give_object_overview(
        max_memory_used,
        frame_memory_usage,
        max_colors_used,
        total_unique_chunks,
        formatted_chunk_track_dict,
    )

    # Debug Stuff
    if DEBUG:
        do_debug_exclusive_stuff(
            images_dict,
            chunk_track_dict,
            formatted_chunk_track_dict,
            total_unique_chunks,
            input_folder,
        )


def object_generator_process_multiple_folder(
    parent_folder,
    min_row_column_density,
    displace_object,
    intra_scan,
    inter_scan,
    scan_chunk_sizes,
):
    if not os.path.exists(parent_folder):
        print(f"❌ Parent folder does not exist: {parent_folder}")
        return

    if not os.path.isdir(parent_folder):
        print(f"❌ Path is not a directory: {parent_folder}")
        return

    subfolders = [
        f
        for f in os.listdir(parent_folder)
        if os.path.isdir(os.path.join(parent_folder, f))
    ]

    if not subfolders:
        print(f"❌ No subfolders found in: {parent_folder}")
        return

    print(f"📁 Found {len(subfolders)} folder(s) to process\n")
    print("=" * 60)

    success_count = 0
    failed_folders = []

    for idx, subfolder_name in enumerate(subfolders, 1):
        subfolder_path = os.path.join(parent_folder, subfolder_name)

        print(f"\n[{idx}/{len(subfolders)}] Processing: {subfolder_name}")
        print("=" * 60)

        (
            images_dict,
            common_image_size,
            original_shared_palette,
            max_colors_used,
            available_frames,
        ) = validate_og_input_folder(subfolder_path)

        if (
            not images_dict
            or common_image_size is None
            or original_shared_palette is None
            or not available_frames
        ):
            print(f"❌ Skipping {subfolder_name} due to validation errors\n")
            failed_folders.append(subfolder_name)
            continue

        config_path = os.path.join(subfolder_path, "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config_data = json.load(f)
                    current_animation_group = config_data.get("animation_group", [])
                    if not current_animation_group:
                        print(
                            f"⚠️ config.json found but animation_group is empty, using default"
                        )
                        current_animation_group = [
                            [
                                {"frame": frame_num, "duration": 10}
                                for frame_num in available_frames
                            ]
                        ]
            except Exception as e:
                print(f"⚠️ Error reading config.json: {str(e)}, using default")
                current_animation_group = [
                    [
                        {"frame": frame_num, "duration": 10}
                        for frame_num in available_frames
                    ]
                ]
        else:
            current_animation_group = [
                [{"frame": frame_num, "duration": 10} for frame_num in available_frames]
            ]

        try:
            image_width, image_height = common_image_size

            current_chunk_sizes = scan_chunk_sizes if scan_chunk_sizes else CHUNK_SIZES

            data = (
                subfolder_path,
                images_dict,
                original_shared_palette,
                max_colors_used,
                image_height,
                image_width,
                available_frames,
                min_row_column_density,
                displace_object,
                current_animation_group,
                current_chunk_sizes,
                intra_scan,
                inter_scan,
            )

            generate_object_main(data)
            print(f"✅ Successfully processed: {subfolder_name}")
            success_count += 1

        except Exception as e:
            print(f"❌ Error processing {subfolder_name}: {str(e)}")
            failed_folders.append(subfolder_name)

    print("\n" + "=" * 60)
    print("📊 PROCESSING SUMMARY")
    print("=" * 60)
    print(f"📁 Total: {len(subfolders)}")
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {len(failed_folders)}")

    if failed_folders:
        print("\n🚫 Failed folders:")
        for folder in failed_folders:
            print(f"   • {folder}")

    print("=" * 60)
