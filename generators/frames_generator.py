import os
import json
import numpy as np
import xml.etree.ElementTree as ET
from data.config import DEBUG
from data.constants import TILE_SIZE, CHUNK_SIZES
from data.framegen import special_cases
from PIL import Image


def validate_fg_input_folder(folder):
    print("[VALIDATING] Validating files in folder...\n")

    images_dict = {}
    frames_xml_root = None
    animations_xml_root = None
    riff_palette_data = None
    special_cases_info = None
    normal_mode = False

    required_files = {
        "imgs": os.path.join(folder, "imgs"),
        "palette.pal": os.path.join(folder, "palette.pal"),
        "frames.xml": os.path.join(folder, "frames.xml"),
        "animations.xml": os.path.join(folder, "animations.xml"),
    }

    missing = [
        name for name, path in required_files.items() if not os.path.exists(path)
    ]

    if missing:
        print(
            f"The following required files/folders are missing:\n\n"
            + "\n".join(f"• {m}" for m in missing)
            + " \n\n[ERROR] Not a valid folder."
        )
        return (
            riff_palette_data,
            images_dict,
            frames_xml_root,
            animations_xml_root,
            normal_mode,
            special_cases_info,
        )

    with open(required_files["palette.pal"], "rb") as f:
        palette_data = f.read()

    if not palette_data.startswith(b"RIFF") or b"PAL " not in palette_data[:16]:
        print("[ERROR] Not a valid RIFF palette file")
    else:
        riff_palette_data = palette_data

    png_files = [
        f for f in os.listdir(required_files["imgs"]) if f.lower().endswith(".png")
    ]

    if not png_files:
        print("\n[ERROR] No png images found")
        return (
            riff_palette_data,
            images_dict,
            frames_xml_root,
            animations_xml_root,
            normal_mode,
            special_cases_info,
        )

    for file_name in png_files:
        name_without_ext = file_name[:-4]
        errors_for_file = []

        # Check if the name is exactly 4 digits
        if not (name_without_ext.isdigit() and len(name_without_ext) == 4):
            print(f"[WARNING] {file_name}:")
            print(f"    • Invalid name format, should be 4-digit number")
            continue

        image_path = os.path.join(required_files["imgs"], file_name)

        try:
            with Image.open(image_path) as img:
                if img.mode != "P":
                    errors_for_file.append("Not an indexed image")
                else:
                    numpy_array = np.asarray(img, dtype=np.uint8)

                width, height = img.size

                if (width, height) not in CHUNK_SIZES:
                    errors_for_file.append(
                        f"Image size {width}x{height} does not match allowed chunk sizes"
                    )

                # Print all errors for this file
                if errors_for_file:
                    print(f"[WARNING] {file_name}:")
                    for error in errors_for_file:
                        print(f"    • {error}")
                else:
                    chunk_id = int(file_name.replace(".png", ""))
                    images_dict[chunk_id] = {
                        "numpy_array": numpy_array,
                        "chunk_width": width,
                        "chunk_height": height,
                    }

        except Exception as e:
            print(f"[WARNING] {file_name}: Error reading file - {str(e)}")
            continue

    total_available_tiles = 0
    if not images_dict:
        print("\n[ERROR] No valid images found")
    else:
        input_folder_name = os.path.basename(folder).lower()
        special_cases_info = special_cases.get(input_folder_name, None)
        for chunk_idx, img_info in enumerate(images_dict.values()):
            chunk_width = img_info["chunk_width"]
            chunk_height = img_info["chunk_height"]

            tiles_x = chunk_width // TILE_SIZE
            tiles_y = chunk_height // TILE_SIZE
            tiles_in_chunk = tiles_x * tiles_y

            if special_cases_info and chunk_idx < len(special_cases_info):
                tiles_in_chunk = min(tiles_in_chunk, special_cases_info[chunk_idx])

            total_available_tiles += tiles_in_chunk

    max_tiles_required = 0
    try:
        frames_xml_tree = ET.parse(required_files["frames.xml"])
        frames_xml_root = frames_xml_tree.getroot()

        for frame_id, chunks_group in enumerate(frames_xml_root.findall("FrameGroup")):
            for chunk in chunks_group:
                chunk_id = int(chunk.find("ImageIndex").text)
                chunk_width = int(chunk.find("Resolution/Width").text)
                chunk_height = int(chunk.find("Resolution/Height").text)

                if chunk_id >= 0:
                    normal_mode = True
                    img_info = images_dict.get(chunk_id)
                    if not img_info or (chunk_width, chunk_height) != (
                        img_info["chunk_width"],
                        img_info["chunk_height"],
                    ):
                        print(
                            f"Can't generate frame {frame_id+1}, {chunk_id:04d} missing\n"
                        )
                        chunks_group.clear()
                        break
                elif not normal_mode:
                    chunk_memory_offset = int(chunk.find("Unk15").text, 16)
                    tiles_x = chunk_width // TILE_SIZE
                    tiles_y = chunk_height // TILE_SIZE
                    total_needed = tiles_x * tiles_y
                    start_tile_index = chunk_memory_offset * 4
                    tiles_required = start_tile_index + total_needed

                    if tiles_required > max_tiles_required:
                        max_tiles_required = tiles_required

        if not normal_mode:
            if DEBUG:
                print(f"Tile Mode Analysis:")
                print(f" • Total tiles available: {total_available_tiles}")
                print(f" • Maximum tiles required: {max_tiles_required}")
                print(
                    f" • Surplus/Deficit: {total_available_tiles - max_tiles_required:+d} tiles\n"
                )
            if total_available_tiles < max_tiles_required:
                print(
                    f"[ERROR] Can't generate frames: Required {max_tiles_required} tiles "
                    f"but only {total_available_tiles} available!\n"
                )
                frames_xml_root = None
    except Exception as e:
        print(f"[WARNING] Error in frames.xml: {str(e)}")

    try:
        animations_xml_tree = ET.parse(required_files["animations.xml"])
        animations_xml_root = animations_xml_tree.getroot()
    except Exception as e:
        print(f"[WARNING] Error in animations.xml: {str(e)}")

    return (
        riff_palette_data,
        images_dict,
        frames_xml_root,
        animations_xml_root,
        normal_mode,
        special_cases_info,
    )


def load_riff_palette(data):
    data_offset = data.find(b"data")

    header_offset = data_offset + 8
    num_colors = int.from_bytes(data[header_offset + 2 : header_offset + 4], "little")
    entries = data[header_offset + 4 : header_offset + 4 + num_colors * 4]

    arr = np.frombuffer(entries, dtype=np.uint8).reshape(-1, 4)
    return arr[:, :3].flatten()


def save_tile_map(tile_map, global_palette, debug_output_folder):
    TILEMAP_WIDTH = 64
    TILEMAP_HEIGHT = 32
    TOTAL_TILES = TILEMAP_WIDTH * TILEMAP_HEIGHT

    # Create blank VRAM canvas (filled with 0)
    canvas = np.zeros(
        (TILEMAP_HEIGHT * TILE_SIZE, TILEMAP_WIDTH * TILE_SIZE), dtype=np.uint8
    )

    # Limit to 2048 tiles (ignore extras if any)
    for i, tile in enumerate(tile_map[:TOTAL_TILES]):
        row = i // TILEMAP_WIDTH
        col = i % TILEMAP_WIDTH
        y = row * TILE_SIZE
        x = col * TILE_SIZE
        canvas[y : y + TILE_SIZE, x : x + TILE_SIZE] = tile

    img = Image.fromarray(canvas)
    img.putpalette(global_palette)
    output_path = os.path.join(debug_output_folder, "tilemap.png")
    img.save(output_path)
    print(
        f"\n[OK] Saved tile map ({canvas.shape[1]}x{canvas.shape[0]}) "
        f"with {min(len(tile_map), TOTAL_TILES)} tiles."
    )


def build_tile_map(images_dict, special_cases_info):
    all_tiles = []

    for chunk_idx, chunk_data in enumerate(images_dict.values()):
        arr = chunk_data["numpy_array"]

        h, w = arr.shape
        tiles_y = h // TILE_SIZE
        tiles_x = w // TILE_SIZE

        tiles = arr.reshape(tiles_y, TILE_SIZE, tiles_x, TILE_SIZE).swapaxes(1, 2)
        tiles = tiles.reshape(-1, TILE_SIZE, TILE_SIZE)

        if special_cases_info and chunk_idx < len(special_cases_info):
            tiles = tiles[: special_cases_info[chunk_idx]]

        all_tiles.append(tiles)

    tile_map = np.concatenate(all_tiles, axis=0)

    return {
        "original": tile_map,
        "flip_h": np.flip(tile_map, axis=2),
        "flip_v": np.flip(tile_map, axis=1),
        "flip_both": np.flip(tile_map, (1, 2)),
    }


def build_chunk_from_tilemap(tile_map, start_tile_index, chunk_width, chunk_height):
    tiles_x = chunk_width // TILE_SIZE
    tiles_y = chunk_height // TILE_SIZE
    total_needed = tiles_x * tiles_y

    tiles = tile_map[start_tile_index : start_tile_index + total_needed]

    tiles = tiles.reshape(tiles_y, tiles_x, TILE_SIZE, TILE_SIZE)

    img_array = tiles.transpose(0, 2, 1, 3).reshape(chunk_height, chunk_width)

    return img_array


def reconstruct_frames(
    frames_xml_root,
    images_dict,
    normal_mode,
    special_cases_info,
    output_folder,
    avoid_overlap,
    global_palette,
):
    root = frames_xml_root

    # Compute global bounds
    global_min_x, global_min_y = float("inf"), float("inf")
    global_max_x, global_max_y = float("-inf"), float("-inf")
    frames_dict = {}

    for frame_id, chunks_group in enumerate(root.findall("FrameGroup")):
        chunks_info = []
        chunks = reversed(chunks_group.findall("Frame"))
        for chunk in chunks:
            chunk_id = int(chunk.find("ImageIndex").text)
            chunk_x = int(chunk.find("Offset/X").text)
            chunk_y = int(chunk.find("Offset/Y").text)
            chunk_palette_offset = int(chunk.find("Unk1").text, 16)
            chunk_memory_offset = int(chunk.find("Unk15").text, 16)
            chunk_width = int(chunk.find("Resolution/Width").text)
            chunk_height = int(chunk.find("Resolution/Height").text)
            chunk_vflip = int(chunk.find("VFlip").text)
            chunk_hflip = int(chunk.find("HFlip").text)

            chunks_info.append(
                (
                    chunk_id,
                    chunk_x,
                    chunk_y,
                    chunk_memory_offset,
                    chunk_width,
                    chunk_height,
                    chunk_vflip,
                    chunk_hflip,
                    chunk_palette_offset,
                )
            )

            # Update global bounds
            global_min_x = min(global_min_x, chunk_x)
            global_min_y = min(global_min_y, chunk_y)
            global_max_x = max(global_max_x, chunk_x + chunk_width)
            global_max_y = max(global_max_y, chunk_y + chunk_height)

        frames_dict[frame_id] = chunks_info

    if global_min_x == float("inf") or global_min_y == float("inf"):
        global_min_x = global_min_y = 0
        global_max_x = global_max_y = TILE_SIZE

    layer_width = global_max_x - global_min_x
    layer_height = global_max_y - global_min_y

    if DEBUG:
        print(
            f"\n[INFO] Bounds:"
            f"  min=({global_min_x}, {global_min_y})"
            f"  max=({global_max_x}, {global_max_y})"
        )

        center_x = (global_min_x + global_max_x) / 2
        center_y = (global_min_y + global_max_y) / 2

        print(
            f"[INFO] Object Center: ({center_x:.2f}, {center_y:.2f})\n"
            "[INFO] The coordinate origin is at (256, 512)"
        )

        offcenter_x = center_x - 256
        offcenter_y = center_y - 512
        offcenter_distance = (offcenter_x**2 + offcenter_y**2) ** 0.5

        print(
            f"[INFO] Offset from Origin:"
            f"  Δx={offcenter_x:.2f}, Δy={offcenter_y:.2f}, "
            f"distance={offcenter_distance:.2f}"
        )

    chunk_orientation_dict = {}

    def get_oriented_chunk(chunk_id, hflip, vflip):
        key = (chunk_id, hflip, vflip)
        if key in chunk_orientation_dict:
            return chunk_orientation_dict[key]

        # Load base image if not already cached
        base_key = (chunk_id, 0, 0)
        if base_key not in chunk_orientation_dict:
            chunk_orientation_dict[base_key] = images_dict[chunk_id]["numpy_array"]

        arr = chunk_orientation_dict[base_key]

        # Compute the requested orientation
        if hflip and vflip:
            arr = np.flip(arr, axis=(0, 1))
        elif hflip:
            arr = np.flip(arr, axis=1)
        elif vflip:
            arr = np.flip(arr, axis=0)

        chunk_orientation_dict[key] = arr
        return arr

    tile_map_dict = None

    # Reconstruct frames
    for frame_id, chunks_info in frames_dict.items():
        print(f"\n[PROCESSING] Generating Frame {frame_id+1}...")
        layers_list = []

        if not chunks_info:
            blank_layer = np.zeros((layer_height, layer_width), dtype=np.uint8)
            blank_mask = np.zeros((layer_height, layer_width), dtype=bool)
            layers_list.append((blank_layer, blank_mask, 0))

        for chunk_info in chunks_info:
            (
                chunk_id,
                chunk_x,
                chunk_y,
                chunk_memory_offset,
                chunk_width,
                chunk_height,
                chunk_vflip,
                chunk_hflip,
                chunk_palette_offset,
            ) = chunk_info

            if normal_mode:
                chunk_id = (
                    next(
                        (
                            chunk_info[0]
                            for chunk_info in chunks_info
                            if chunk_info[3] == chunk_memory_offset
                            and not chunk_info[0] < 0
                        ),
                        None,
                    )
                    if chunk_id < 0
                    else chunk_id
                )

                piece = get_oriented_chunk(chunk_id, chunk_hflip, chunk_vflip)

                if piece is None:
                    continue

            elif chunk_id < 0:
                # Build chunk directly from tile_map
                if tile_map_dict is None:
                    tile_map_dict = build_tile_map(images_dict, special_cases_info)

                start_tile_index = chunk_memory_offset * 4

                if chunk_hflip and chunk_vflip:
                    tile_map = tile_map_dict["flip_both"]
                elif chunk_hflip:
                    tile_map = tile_map_dict["flip_h"]
                elif chunk_vflip:
                    tile_map = tile_map_dict["flip_v"]
                else:
                    tile_map = tile_map_dict["original"]

                piece = build_chunk_from_tilemap(
                    tile_map,
                    start_tile_index,
                    chunk_width,
                    chunk_height,
                )

            # Map to global palette
            palette_no = (chunk_palette_offset - 0xC) // 0x10
            start_index = palette_no * 16
            mapped_data = np.where(piece != 0, start_index + piece, 0)

            # pixels to paint (always non-transparent)
            paint_mask = mapped_data != 0

            # Update mask for overlaps
            if avoid_overlap == "chunk":
                overlap_check_mask = np.ones_like(mapped_data, dtype=bool)
            elif avoid_overlap == "palette":
                overlap_check_mask = np.zeros_like(mapped_data, dtype=bool)
            elif avoid_overlap == "none":
                overlap_check_mask = np.zeros_like(mapped_data, dtype=bool)
            else:
                overlap_check_mask = paint_mask

            # Chunk position in frame
            y_slice = slice(
                chunk_y - global_min_y, chunk_y - global_min_y + chunk_height
            )
            x_slice = slice(
                chunk_x - global_min_x, chunk_x - global_min_x + chunk_width
            )

            # Find first layer without overlap
            placed = False
            for layer_array, layer_mask, layer_palette_no in layers_list:
                palette_matches = (avoid_overlap == "none") or (
                    layer_palette_no == palette_no
                )
                if palette_matches and not np.any(
                    layer_mask[y_slice, x_slice] & overlap_check_mask
                ):
                    layer_array[y_slice, x_slice] = np.where(
                        paint_mask, mapped_data, layer_array[y_slice, x_slice]
                    )
                    layer_mask[y_slice, x_slice] |= paint_mask
                    placed = True
                    break

            if not placed:
                # Create new layer
                new_layer = np.zeros((layer_height, layer_width), dtype=np.uint8)
                new_mask = np.zeros((layer_height, layer_width), dtype=bool)
                new_layer[y_slice, x_slice] = np.where(paint_mask, mapped_data, 0)
                new_mask[y_slice, x_slice] = paint_mask
                layers_list.append((new_layer, new_mask, palette_no))

        # Save all layers
        for layer_id, (layer_array, _, layer_palette_no) in enumerate(layers_list):
            layer_img = Image.fromarray(layer_array)
            layer_img.putpalette(global_palette)
            out_path = os.path.join(
                output_folder, f"Frame-{frame_id + 1}-Layer-{layer_id + 1}.png"
            )
            layer_img.save(out_path, transparency=0)
            if DEBUG:
                print(
                    f"[OK] Saved: Frame-{frame_id + 1}-Layer-{layer_id + 1}.png",
                    f"Palette-{layer_palette_no}",
                )

    print(f"\n[OK] Frames saved to: {output_folder}")

    return tile_map_dict


def create_json_from_animation_xml(animations_xml_root, output_folder):
    root = animations_xml_root

    animation_group = []

    for seq in root.findall(".//AnimSequence"):
        group = []
        for anim_frame in seq.findall("AnimFrame"):
            frame_no = int(anim_frame.find("MetaFrameGroupIndex").text) + 1
            duration = int(anim_frame.find("Duration").text)
            group.append({"frame": frame_no, "duration": duration})
        animation_group.append(group)

    json_output_path = os.path.join(output_folder, "config.json")

    data = {
        "frames_folder": os.path.abspath(output_folder),
        "animation_group": animation_group,
    }

    with open(json_output_path, "w") as f:
        json.dump(data, f, indent=4)

    print(f"\n[OK] Config JSON saved to: {json_output_path}")


def generate_frames_main(data):
    (
        normal_mode,
        special_cases_info,
        input_folder,
        riff_palette_data,
        images_dict,
        frames_xml_root,
        animations_xml_root,
        avoid_overlap,
    ) = data

    output_folder = os.path.join(input_folder, "frames")
    os.makedirs(output_folder, exist_ok=True)

    global_palette = load_riff_palette(riff_palette_data)

    # Reconstruct frames
    tile_map_dict = reconstruct_frames(
        frames_xml_root,
        images_dict,
        normal_mode,
        special_cases_info,
        output_folder,
        avoid_overlap,
        global_palette,
    )

    # Save Tilemap
    if DEBUG:
        debug_output_folder = os.path.join(input_folder, "DEBUG")
        os.makedirs(debug_output_folder, exist_ok=True)

        if not normal_mode:
            save_tile_map(
                tile_map_dict["original"], global_palette, debug_output_folder
            )

    # Generate animation.json
    create_json_from_animation_xml(animations_xml_root, output_folder)


def frames_generator_process_multiple_folder(parent_folder, avoid_overlap):
    if not os.path.exists(parent_folder):
        print(f"[ERROR] Parent folder does not exist: {parent_folder}")
        return

    if not os.path.isdir(parent_folder):
        print(f"[ERROR] Path is not a directory: {parent_folder}")
        return

    subfolders = [
        f
        for f in os.listdir(parent_folder)
        if os.path.isdir(os.path.join(parent_folder, f))
    ]

    if not subfolders:
        print(f"[ERROR] No subfolders found in: {parent_folder}")
        return

    print(f"[INFO] Found {len(subfolders)} folder(s) to process\n")
    print("=" * 60)

    success_count = 0
    failed_folders = []

    for idx, subfolder_name in enumerate(subfolders, 1):
        subfolder_path = os.path.join(parent_folder, subfolder_name)

        print(f"\n[{idx}/{len(subfolders)}] Processing: {subfolder_name}")
        print("=" * 60)

        (
            riff_palette_data,
            images_dict,
            frames_xml_root,
            animations_xml_root,
            normal_mode,
            special_cases_info,
        ) = validate_fg_input_folder(subfolder_path)

        if (
            riff_palette_data is None
            or not images_dict
            or frames_xml_root is None
            or animations_xml_root is None
        ):
            print(f"[ERROR] Skipping {subfolder_name} due to validation errors\n")
            failed_folders.append(subfolder_name)
            continue

        try:
            data = (
                normal_mode,
                special_cases_info,
                subfolder_path,
                riff_palette_data,
                images_dict,
                frames_xml_root,
                animations_xml_root,
                avoid_overlap,
            )

            generate_frames_main(data)
            print(f"[OK] Successfully processed: {subfolder_name}")
            success_count += 1

        except Exception as e:
            print(f"[ERROR] Error processing {subfolder_name}: {str(e)}")
            failed_folders.append(subfolder_name)

    print("\n" + "=" * 60)
    print("[SUMMARY] PROCESSING SUMMARY")
    print("=" * 60)
    print(f"[INFO] Total: {len(subfolders)}")
    print(f"[OK] Successful: {success_count}")
    print(f"[ERROR] Failed: {len(failed_folders)}")

    if failed_folders:
        print("\n[ERROR] Failed folders:")
        for folder in failed_folders:
            print(f"   • {folder}")

    print("=" * 60)
