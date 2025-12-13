#!/usr/bin/env python3
"""
Test script for object and frames generators.
Tests the full round-trip: frames -> objects -> frames
"""

import sys
import os
import json
import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from generators import og_process_multiple_folder, fg_process_multiple_folder


@dataclass
class TestResult:
    success: bool
    differences: int
    was_generated: bool
    differences_log: List[str]
    part_name: str


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

    base_path = Path(base_path) if base_path else directory
    for debug_folder in sorted(directory.rglob("DEBUG")):
        if debug_folder.is_dir():
            shutil.rmtree(debug_folder)
            print(f"  🗑️  Deleted folder: {debug_folder.relative_to(base_path)}")


def get_all_files(directory):
    directory = Path(directory)
    if not directory.exists():
        return {}

    files = {}
    for file_path in sorted(directory.rglob("*")):
        if file_path.is_file():
            rel_path = str(file_path.relative_to(directory))
            if not rel_path.endswith("config.json"):
                files[rel_path] = file_path
    return files


def compare_config_json(gen_path, ref_path):
    try:
        with open(gen_path, "r", encoding="utf-8") as f:
            gen_data = json.load(f)
        with open(ref_path, "r", encoding="utf-8") as f:
            ref_data = json.load(f)
        return gen_data.get("animation_group") == ref_data.get("animation_group")
    except (json.JSONDecodeError, KeyError, FileNotFoundError):
        return False


def compare_directories(generated_dir, reference_dir):
    gen_dir = Path(generated_dir)
    ref_dir = Path(reference_dir)

    differences = []
    file_difference_count = 0

    # Get all files (excluding config.json)
    gen_files = get_all_files(generated_dir)
    ref_files = get_all_files(reference_dir)
    all_files = set(gen_files.keys()) | set(ref_files.keys())

    # Compare regular files using checksums
    for file_path in sorted(all_files):
        gen_file = gen_files.get(file_path)
        ref_file = ref_files.get(file_path)

        if gen_file is None:
            differences.append(f"Missing in generated: {file_path}")
            file_difference_count += 1
        elif ref_file is None:
            differences.append(f"Extra in generated: {file_path}")
            file_difference_count += 1
        else:
            gen_checksum = calculate_file_checksum(gen_file)
            ref_checksum = calculate_file_checksum(ref_file)
            if gen_checksum != ref_checksum:
                differences.append(f"Checksum mismatch: {file_path}")
                differences.append(f"  Generated: {gen_checksum[:16]}...")
                differences.append(f"  Reference: {ref_checksum[:16]}...")
                file_difference_count += 1

    # Compare config.json files separately
    for config_file in sorted(gen_dir.rglob("config.json")):
        if config_file.is_file():
            rel_path = str(config_file.relative_to(gen_dir))
            ref_config = ref_dir / rel_path

            if not ref_config.exists():
                differences.append(f"Extra in generated: {rel_path}")
                file_difference_count += 1
            elif not compare_config_json(config_file, ref_config):
                differences.append(
                    f"Config mismatch: {rel_path} (animation_group differs)"
                )
                file_difference_count += 1

    # Check for config.json files in reference that don't exist in generated
    for config_file in sorted(ref_dir.rglob("config.json")):
        if config_file.is_file():
            rel_path = str(config_file.relative_to(ref_dir))
            gen_config = gen_dir / rel_path
            if not gen_config.exists():
                differences.append(f"Missing in generated: {rel_path}")
                file_difference_count += 1

    return len(differences) == 0, differences, file_difference_count


def compare_subfolders(input_folder, reference_folder, output_subdir_name, item_name):
    all_match = True
    total_differences = 0
    all_differences_log = []

    input_path = Path(input_folder)
    subfolders = (
        sorted(f.name for f in input_path.iterdir() if f.is_dir())
        if input_path.exists()
        else []
    )
    for subfolder_name in subfolders:
        generated_dir = Path(input_folder) / subfolder_name / output_subdir_name
        reference_dir = Path(reference_folder) / subfolder_name

        print(f"Comparing: {subfolder_name}")

        if not generated_dir.exists():
            error_msg = f"Generated {item_name} folder not found: {generated_dir}"
            print(f"  ❌ {error_msg}")
            all_match = False
            total_differences += 1
            all_differences_log.append(f"[{subfolder_name}] {error_msg}")
            continue

        if not reference_dir.exists():
            print(f"  ⚠️  Reference folder not found: {reference_dir}")
            continue

        match, differences, file_difference_count = compare_directories(
            generated_dir, reference_dir
        )

        if match:
            num_files = len(get_all_files(generated_dir))
            print(f"  ✅ Match! ({num_files} files)")
        else:
            file_text = f"{file_difference_count} file{'s' if file_difference_count != 1 else ''} differ"
            print(f"  ❌ Mismatch! ({file_text})")
            for diff in differences[:5]:
                print(f"    {diff}")
            if len(differences) > 5:
                print(f"    ... and {len(differences) - 5} more detail lines")
            all_match = False
            total_differences += file_difference_count
            all_differences_log.append(f"\n[{subfolder_name}]")
            all_differences_log.extend(f"  {diff}" for diff in differences)
        print()

    return all_match, total_differences, all_differences_log


def test_generator(
    input_folder: str,
    reference_folder: str,
    generator_func: Callable,
    generator_args: dict,
    output_subdir_name: str,
    item_name: str,
    part_name: str,
    part_number: str,
) -> TestResult:
    print("\n" + "=" * 70)
    print(f"{part_number}: {part_name}")
    print("=" * 70)
    print(f"Input folder: {input_folder}")
    print(f"Reference folder: {reference_folder}")
    print()

    ref_path = Path(reference_folder)
    reference_is_empty = not ref_path.exists() or not any(ref_path.iterdir())

    print(f"Running {item_name} generator...")
    generator_func(input_folder, **generator_args)
    print()

    print("Deleting Temporary folders from processing folders...")
    test_dir = Path(input_folder).parent
    input_path = Path(input_folder)
    subfolders = (
        sorted(f.name for f in input_path.iterdir() if f.is_dir())
        if input_path.exists()
        else []
    )
    for subfolder_name in subfolders:
        delete_debug_folders(input_path / subfolder_name, base_path=test_dir)
    print()

    if reference_is_empty:
        print(f"⚠️  Reference folder '{reference_folder}' is empty or doesn't exist.")
        print(f"📋 Copying generated {item_name} to reference folder...")
        ref_path = Path(reference_folder)
        ref_path.mkdir(parents=True, exist_ok=True)

        input_path = Path(input_folder)
        subfolders = (
            sorted(f.name for f in input_path.iterdir() if f.is_dir())
            if input_path.exists()
            else []
        )
        for subfolder_name in subfolders:
            gen_dir = input_path / subfolder_name / output_subdir_name
            ref_dir = ref_path / subfolder_name
            if gen_dir.exists():
                if ref_dir.exists():
                    shutil.rmtree(ref_dir)
                shutil.copytree(gen_dir, ref_dir)
                print(f"  Copied: {subfolder_name}/")
        print("✅ Copy complete! Using generated files as new reference.\n")
        return TestResult(True, 0, True, [], part_name)

    all_match, total_differences, differences_log = compare_subfolders(
        input_folder, reference_folder, output_subdir_name, item_name
    )
    return TestResult(all_match, total_differences, False, differences_log, part_name)


def cleanup_generated_folders(frames_folder, objects_folder):
    print("Cleaning up generated folders...")

    for folder_name, subdir in [(frames_folder, "object"), (objects_folder, "frames")]:
        folder = Path(folder_name)
        if folder.exists():
            subfolders = sorted(f.name for f in folder.iterdir() if f.is_dir())
            for subfolder_name in subfolders:
                gen_dir = folder / subfolder_name / subdir
                if gen_dir.exists():
                    shutil.rmtree(gen_dir)
                    print(f"  Deleted: {gen_dir}")
    print()


def main():
    test_dir = Path(__file__).parent
    frames_folder = test_dir / "frames-files"
    objects_folder = test_dir / "objects-files"

    if not frames_folder.exists():
        print(f"📁 Creating frames-files directory: {frames_folder}")
        frames_folder.mkdir(parents=True, exist_ok=True)
        print()

    print("=" * 70)
    print("Generators Test")
    print("=" * 70)

    # Part 1: Test Object Generator (frames -> objects)
    og_result = test_generator(
        input_folder=str(frames_folder),
        reference_folder=str(objects_folder),
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
    print("\nCleaning up object folders from frames-files before Part 2...")
    subfolders = (
        sorted(f.name for f in frames_folder.iterdir() if f.is_dir())
        if frames_folder.exists()
        else []
    )
    for subfolder_name in subfolders:
        object_dir = frames_folder / subfolder_name / "object"
        if object_dir.exists():
            shutil.rmtree(object_dir)
            print(f"  Deleted: {object_dir}")
    print()

    # Part 2: Test Frames Generator (objects -> frames)
    fg_result = test_generator(
        input_folder=str(objects_folder),
        reference_folder=str(frames_folder),
        generator_func=fg_process_multiple_folder,
        generator_args={"avoid_overlap": "none"},
        output_subdir_name="frames",
        item_name="frames",
        part_name="Frames Generator Test (objects -> frames)",
        part_number="PART 2",
    )

    cleanup_generated_folders(str(frames_folder), str(objects_folder))

    # Print summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for result, name in [
        (og_result, "Object Generator"),
        (fg_result, "Frames Generator"),
    ]:
        status = "✅ PASSED" if result.success else "❌ FAILED"
        note = (
            " (files generated, not compared)"
            if result.was_generated
            else f" ({result.differences} differences)"
        )
        print(f"{name}:  {status}{note}")
    print()

    overall_success = og_result.success and fg_result.success

    # Write log file if tests failed
    if not overall_success:
        log_file_path = test_dir / "test_run_log.txt"
        with open(log_file_path, "w", encoding="utf-8") as log_file:
            log_file.write("=" * 70 + "\n")
            log_file.write("TEST RUN LOG - All File Mismatches\n")
            log_file.write("=" * 70 + "\n\n")

            for result in [og_result, fg_result]:
                if not result.success and result.differences_log:
                    log_file.write(f"{result.part_name}\n")
                    log_file.write("-" * 70 + "\n")
                    log_file.write("\n".join(result.differences_log))
                    log_file.write("\n\n")

            total_diff = og_result.differences + fg_result.differences
            log_file.write("=" * 70 + "\n")
            log_file.write(f"Total differences: {total_diff} files\n")
            log_file.write("=" * 70 + "\n")

        print(f"📝 Detailed log written to: {log_file_path}")
        print()

    if overall_success:
        if og_result.was_generated or fg_result.was_generated:
            print("✅ All tests passed! Generated files were saved as new reference.")
        else:
            print("✅ All tests passed! Generated files match reference files.")
    else:
        total_diff = og_result.differences + fg_result.differences
        print(f"❌ Some tests failed! Total differences: {total_diff}")
    print("=" * 70)

    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
