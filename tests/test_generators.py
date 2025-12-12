#!/usr/bin/env python3
"""
Test script for object and frames generators.
Tests the full round-trip: frames -> objects -> frames
"""

import sys
import os
import hashlib
import shutil
from pathlib import Path
from typing import Callable

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from generators import og_process_multiple_folder, fg_process_multiple_folder


def calculate_file_checksum(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def delete_debug_folders(directory, base_path=None):
    directory = Path(directory)
    if not directory.exists():
        return

    if base_path is None:
        base_path = directory
    else:
        base_path = Path(base_path)

    debug_folders = []
    for path in directory.rglob("DEBUG"):
        if path.is_dir():
            debug_folders.append(path)

    for debug_folder in sorted(debug_folders):
        shutil.rmtree(debug_folder)
        relative_path = debug_folder.relative_to(base_path)
        print(f"  🗑️  Deleted folder: {relative_path}")


def get_directory_checksums(directory):
    checksums = {}
    directory = Path(directory)

    if not directory.exists():
        return checksums

    for file_path in sorted(directory.rglob("*")):
        if file_path.is_file():
            relative_path = file_path.relative_to(directory)
            checksums[str(relative_path)] = calculate_file_checksum(file_path)

    return checksums


def compare_directories(generated_dir, reference_dir):
    generated_checksums = get_directory_checksums(generated_dir)
    reference_checksums = get_directory_checksums(reference_dir)

    differences = []
    all_files = set(generated_checksums.keys()) | set(reference_checksums.keys())

    for file_path in sorted(all_files):
        gen_checksum = generated_checksums.get(file_path)
        ref_checksum = reference_checksums.get(file_path)

        if gen_checksum is None:
            differences.append(f"Missing in generated: {file_path}")
        elif ref_checksum is None:
            differences.append(f"Extra in generated: {file_path}")
        elif gen_checksum != ref_checksum:
            differences.append(f"Checksum mismatch: {file_path}")
            differences.append(f"  Generated: {gen_checksum[:16]}...")
            differences.append(f"  Reference: {ref_checksum[:16]}...")

    return len(differences) == 0, differences


def is_reference_empty(reference_folder):
    return (
        not os.path.exists(reference_folder)
        or len(
            [
                f
                for f in os.listdir(reference_folder)
                if os.path.isdir(os.path.join(reference_folder, f))
            ]
        )
        == 0
    )


def get_subfolders(folder):
    if not os.path.exists(folder):
        return []
    return [
        f for f in sorted(os.listdir(folder)) if os.path.isdir(os.path.join(folder, f))
    ]


def copy_generated_to_reference(input_folder, reference_folder, output_subdir_name):
    os.makedirs(reference_folder, exist_ok=True)

    for subfolder_name in get_subfolders(input_folder):
        subfolder_path = os.path.join(input_folder, subfolder_name)
        generated_dir = os.path.join(subfolder_path, output_subdir_name)
        reference_dir = os.path.join(reference_folder, subfolder_name)

        if os.path.exists(generated_dir):
            if os.path.exists(reference_dir):
                shutil.rmtree(reference_dir)
            shutil.copytree(generated_dir, reference_dir)
            print(f"  Copied: {subfolder_name}/")


def compare_subfolders(input_folder, reference_folder, output_subdir_name, item_name):
    all_match = True
    total_differences = 0

    for subfolder_name in get_subfolders(input_folder):
        subfolder_path = os.path.join(input_folder, subfolder_name)
        generated_dir = os.path.join(subfolder_path, output_subdir_name)
        reference_dir = os.path.join(reference_folder, subfolder_name)

        print(f"Comparing: {subfolder_name}")

        if not os.path.exists(generated_dir):
            print(f"  ❌ Generated {item_name} folder not found: {generated_dir}")
            all_match = False
            total_differences += 1
            continue

        if not os.path.exists(reference_dir):
            print(f"  ⚠️  Reference folder not found: {reference_dir}")
            continue

        match, differences = compare_directories(generated_dir, reference_dir)

        if match:
            num_files = len(get_directory_checksums(generated_dir))
            print(f"  ✅ Match! ({num_files} files)")
        else:
            print(f"  ❌ Mismatch! ({len(differences)} differences)")
            for diff in differences[:5]:  # Show first 5 differences
                print(f"    {diff}")
            if len(differences) > 5:
                print(f"    ... and {len(differences) - 5} more differences")
            all_match = False
            total_differences += len(differences)
        print()

    return all_match, total_differences


def test_generator(
    input_folder: str,
    reference_folder: str,
    generator_func: Callable,
    generator_args: dict,
    output_subdir_name: str,
    item_name: str,
    part_name: str,
    part_number: str,
):
    print("\n" + "=" * 70)
    print(f"{part_number}: {part_name}")
    print("=" * 70)
    print(f"Input folder: {input_folder}")
    print(f"Reference folder: {reference_folder}")
    print()

    # Check if reference folder is empty
    reference_is_empty = is_reference_empty(reference_folder)

    # Run the generator
    print(f"Running {item_name} generator...")
    generator_func(input_folder, **generator_args)
    print()

    # Delete DEBUG folders from processing folders
    print("Deleting Temporary folders from processing folders...")
    test_dir = os.path.dirname(input_folder)
    for subfolder_name in get_subfolders(input_folder):
        subfolder_path = os.path.join(input_folder, subfolder_name)
        delete_debug_folders(subfolder_path, base_path=test_dir)
    print()

    if reference_is_empty:
        print(f"⚠️  Reference folder '{reference_folder}' is empty or doesn't exist.")
        print(f"📋 Copying generated {item_name} to reference folder...")
        copy_generated_to_reference(input_folder, reference_folder, output_subdir_name)
        print("✅ Copy complete! Using generated files as new reference.\n")
        return True, 0, True  # (success, differences, was_generated)

    # Compare results
    all_match, total_differences = compare_subfolders(
        input_folder, reference_folder, output_subdir_name, item_name
    )

    return all_match, total_differences, False  # (success, differences, was_generated)


def cleanup_generated_folders(frames_folder, objects_folder):
    print("Cleaning up generated folders...")

    # Clean up object folders from frames_folder
    for subfolder_name in get_subfolders(frames_folder):
        subfolder_path = os.path.join(frames_folder, subfolder_name)
        generated_object_dir = os.path.join(subfolder_path, "object")
        if os.path.exists(generated_object_dir):
            shutil.rmtree(generated_object_dir)
            print(f"  Deleted: {generated_object_dir}")

    # Clean up frames folders from objects_folder
    for subfolder_name in get_subfolders(objects_folder):
        subfolder_path = os.path.join(objects_folder, subfolder_name)
        generated_frames_dir = os.path.join(subfolder_path, "frames")
        if os.path.exists(generated_frames_dir):
            shutil.rmtree(generated_frames_dir)
            print(f"  Deleted: {generated_frames_dir}")

    print()


def main():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    frames_folder = os.path.join(test_dir, "frames-files")
    objects_folder = os.path.join(test_dir, "objects-files")
    frames_reference_folder = frames_folder
    objects_reference_folder = objects_folder

    # Create frames-files directory if it doesn't exist
    if not os.path.exists(frames_folder):
        print(f"📁 Creating frames-files directory: {frames_folder}")
        os.makedirs(frames_folder, exist_ok=True)
        print()

    print("=" * 70)
    print("Generators Test")
    print("=" * 70)

    # Part 1: Test Object Generator (frames -> objects)
    og_success, og_differences, og_was_generated = test_generator(
        input_folder=frames_folder,
        reference_folder=objects_reference_folder,
        generator_func=og_process_multiple_folder,
        generator_args={
            "min_row_column_density": 0.5,
            "displace_object": [0, 0],
            "intra_scan": True,
            "inter_scan": True,
            "scan_chunk_sizes": None,
        },
        output_subdir_name="object",
        item_name="object",
        part_name="Object Generator Test (frames -> objects)",
        part_number="PART 1",
    )

    # Clean up object folders from frames-files before Part 2
    # (so they don't interfere with frames comparison)
    print("\nCleaning up object folders from frames-files before Part 2...")
    for subfolder_name in get_subfolders(frames_folder):
        object_dir = os.path.join(frames_folder, subfolder_name, "object")
        if os.path.exists(object_dir):
            shutil.rmtree(object_dir)
            print(f"  Deleted: {object_dir}")
    print()

    # Part 2: Test Frames Generator (objects -> frames)
    fg_success, fg_differences, fg_was_generated = test_generator(
        input_folder=objects_folder,
        reference_folder=frames_reference_folder,
        generator_func=fg_process_multiple_folder,
        generator_args={
            "avoid_overlap": "none",
        },
        output_subdir_name="frames",
        item_name="frames",
        part_name="Frames Generator Test (objects -> frames)",
        part_number="PART 2",
    )

    # Cleanup
    cleanup_generated_folders(frames_folder, objects_folder)

    # Print summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    og_status = "✅ PASSED" if og_success else "❌ FAILED"
    og_note = (
        " (files generated, not compared)"
        if og_was_generated
        else f" ({og_differences} differences)"
    )
    print(f"Object Generator:  {og_status}{og_note}")

    fg_status = "✅ PASSED" if fg_success else "❌ FAILED"
    fg_note = (
        " (files generated, not compared)"
        if fg_was_generated
        else f" ({fg_differences} differences)"
    )
    print(f"Frames Generator:  {fg_status}{fg_note}")
    print()

    overall_success = og_success and fg_success
    if overall_success:
        if og_was_generated or fg_was_generated:
            print("✅ All tests passed! Generated files were saved as new reference.")
        else:
            print("✅ All tests passed! Generated files match reference files.")
    else:
        print(
            f"❌ Some tests failed! Total differences: {og_differences + fg_differences}"
        )
    print("=" * 70)

    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
