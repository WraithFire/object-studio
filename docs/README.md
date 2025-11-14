# Object Studio Documentation

## Table of Contents

-   [Object Generator](#object-generator)
    -   [What is a Cel?](#what-is-a-cel)
    -   [Sprite Format](#sprite-format)
        -   [Palette Info](#palette-info)
        -   [Creation Modes](#creation-modes)
    -   [Export Format](#export-format)
        -   [Filename Requirements](#filename-requirements)
        -   [Image Requirements](#image-requirements)
        -   [Exporting from Aseprite (or Other Tools)](#exporting-from-aseprite-or-other-tools)
    -   [Using the Object Generator](#using-the-object-generator)
    -   [Object Generator Configurations](#object-generator-configurations)
        -   [Min Density](#min-density)
        -   [Displace Object](#displace-object)
        -   [Scan Options](#scan-options)
        -   [Animation Settings](#animation-settings)
    -   [Object Generator Output](#object-generator-output)
        -   [How to Use with `SetAnimation()`](#how-to-use-with-setanimation)
-   [Frames Generator](#frames-generator)
    -   [Folder Requirements](#folder-requirements)
    -   [Using the Frames Generator](#using-the-frames-generator)
    -   [Frames Generator Configurations](#frames-generator-configurations)
        -   [Avoid Overlap](#avoid-overlap)
    -   [Frames Generator Output](#frames-generator-output)
-   [Bulk Conversion](#bulk-conversion)

# Object Generator

Objects in **Explorers of Sky** have a lot of potential — but **SkyTemple** currently only allows importing a single-frame, single-layer image.

This means we’re limited to a **static, 16-color image**, losing the ability to animate, use layers, or take advantage of multiple palette groups.

The **Object Generator** removes those limits.

With it, you can easily create **animated, multi-layered, multi-palette objects** that can be imported directly into **SkyTemple** or converted back into `.wan` format using **GFXCrunch** for in-game use.

Before continuing, it’s important to understand some basics about **cels**, since they’re referenced multiple times throughout this guide.

### What is a Cel?

<div align="center">
    <img src="images/cel.png" alt="Cel Example" />
</div>

A **cel** (short for _celluloid_) represents a single image used in a specific frame and layer.

As you can see in the image above, each frame in this sprite is made up of **three cels** stacked on top of each other to form the final frame.

## Sprite Format

### Palette Info

<div align="center">
    <img src="images/palette.png" alt="Palette Example" />
</div>

-   The game uses **12 palette slots** for objects. Each slot contains **16 colors**, with the **first color always transparent**.
-   This gives a total of **192 colors**, but since 12 are reserved for transparency, there are **180 unique usable colors**.
-   These **12 palette slots** are shared across all objects on screen — meaning the total combined palette groups of all visible objects **must not exceed 12**.

### Creation Modes

The tool supports **two modes** for sprite creation:

-   **Single-Cel Frame Mode**
-   **Multi-Cel Frame Mode**

Each mode has its own advantages and limitations.

**Single-Cel Frame Mode**

In Single-Cel Frame Mode, each frame is made up of **just one cel**.

-   **Advantages:**

    -   You can use all **180 available colors** freely anywhere in the cel.
    -   Fewer cels to manage and export — only one per frame.
    -   Great for **quick object creation** or when you don’t want to deal with multiple cels.

-   **Disadvantages:**

    -   Since all palette groups appear in a single cel, the tool has to **split it into layers** based on how many palette groups it detects.
    -   Once split, the layers can look **disjointed or deformed**, which makes repeated chunk detection more difficult.
    -   This leads to **higher memory usage** per frame and **less chunk reuse** overall.

**Multi-Cel Frame Mode**

In Multi-Cel Frame Mode, each frame is made up of **multiple cels**, with each cel limited to a **single palette group**.

-   **Advantages:**

    -   Allows for **efficient chunk reuse** — repeated chunks are easier to detect across frames.
    -   Helps **reduce memory usage per frame**, since shared chunks can be reused.
    -   Ideal for **objects that appear alongside others** in a scene, since it leaves more memory free for additional objects.

-   **Disadvantages:**

    -   Each cel can use **only one palette group** (out of the 12 available).
    -   Managing multiple cels can be tricky — it’s harder to keep track of which cel uses which palette group.
    -   More cels to export and organize overall.

**Mixed-Mode Warning**

Don’t mix **single-palette** and **multi-palette** cels within the same frame. Combining both will create **excessive layers** and **too many chunks per frame**, likely exceeding the game’s **108-chunk-per-frame limit**.

## Export Format

Once you’ve created your sprite, you’ll need to export your cel images from **Aseprite** or any other image editing tool.

These cel images must be formatted correctly — the tool is strict about this, but once you understand the requirements, it’s straightforward.

### Filename Requirements

Each cel image must follow this exact naming format so the **Object Generator** can correctly identify frame and layer order during processing.

```
Frame-[number]-Layer-[number].png

Examples:
Frame-0-Layer-0.png
Frame-0-Layer-1.png
Frame-1-Layer-0.png
Frame-1-Layer-2.png
```

**Layers are stacked in ascending order** — each higher layer is drawn **on top** of the one before it (Layer-1 covers Layer-0, Layer-2 covers Layer-1, and so on).

### Image Requirements

All cel images must meet the following requirements to be compatible with the **Object Generator**:

1. **Image Format**

    - Images must be **indexed PNGs** — not RGB or RGBA formats.
    - All cel images must share the **same global palette**, with a maximum of **192 colors** (12 palette groups).

2. **Image Dimensions**
    - All cel images must have the **same dimensions**.  
      If `Frame-0-Layer-0.png` is 160×160, then **every cel image** in the set must also be 160×160.  
      Mixing image sizes will cause validation errors.

### Exporting from Aseprite (or Other Tools)

If you’re using **Aseprite**, you can download the [Export Cels Script](https://github.com/WraithFire/aseprite-scripts/blob/master/export-cels.lua), which automatically exports all your cel images in the correct format.

If you’re using another image editor, you have **two options**:

-   **Multi-Cel Frame Mode:**  
    Toggle layer visibility on and off to export each cel image individually.
-   **Single-Cel Frame Mode:**  
    Export each frame as a single image.

Make sure to export each cel image using the **filename format** shown above.

## Using the Object Generator

<div align="center">
    <img src="images/object-generator.png" alt="Object Generator" />
</div>

**How to Use:**

1. **Select your folder**

    Choose the folder containing all cel images (`Frame-[number]-Layer-[number].png`).

    The tool automatically checks everything and lists any errors it finds, so you can correct them before generating.

2. **Adjust your configuration**

    Set your preferred **min density**, **displace object**, **chunk sizes**, and enable **Intra Frame** or **Inter Frame** scans if needed.

    You can also set up your Animation Settings — define how many animations your object has and how the frames are arranged.

3. **Hit “Generate Object”**

    The tool will automatically build your object and organize everything into the correct structure.

    After generation, the console will display a summary with useful stats such as:

    ```
    Object Info:
    ❔ Maximum Memory Used by Animation: 28
    ❔ Total Colors Used: 48
    ❔ Total Unique Chunks: 29

    Frames Info:
    Frame-1: Total Chunks = 15 and Memory = 27
    Frame-2: Total Chunks = 13 and Memory = 28
    Frame-3: Total Chunks = 13 and Memory = 28
    ```

    If your object exceeds the game’s limits, the tool will warn you in the console so you can tweak your settings or simplify your sprite.

Once complete, you’ll find the output in a new folder named **object** inside your selected directory.
This folder contains all necessary files — you can **import it directly into SkyTemple** or **convert it back to `.wan`** with **GFXCrunch** for in-game use.

## Object Generator Configurations

### Min Density

Each image can be divided into **chunks**, which are smaller portions of the image.

Chunks are made up of **tiles**, and the game requires chunk dimensions to be powers of 2 (8, 16, 32, 64). The smallest possible chunk is **8×8 pixels**, which equals one tile.

**Min Density** is the minimum percentage of tiles that need to be filled in each row and column for a chunk to be considered valid for object generation.

<div align="center">
    <img src="images/min_density.png" alt="Min Density Example" />
</div>

For example, in the image above, we have a **32×32px** chunk that can be imagined as an **8×8px** tile grid with **4 rows** and **4 columns**, 4 tiles in each.

If the **min_density** is set to **50%**, then at least **2 tiles** in every row and column must be filled for the chunk to be considered valid.

Since **row 3** has only **1 tile** filled, it’s considered an **invalid chunk**.

### Displace Object

<div align="center">
    <img src="images/displacement.png" alt="Displacement Example" />
</div>

Every object exists within its own local coordinate space, centered at **(256, 512)**.

Anything **above** this center point appears in **front of the actor**, while anything **below** it appears **behind the actor**.

By default, the object is positioned so that its own center lines up with this coordinate-space center.

You can shift the object’s position relative to that point by adjusting the **X** and **Y** values under **Displace Object**.

-   **X** increases to the right and decreases to the left.
-   **Y** increases downward and decreases upward.

For example, if you set **Displace Object** to:

-   **X = +object_width / 2**
-   **Y = +object_height / 2**

…the object’s **top-left corner** will align with the coordinate-space center, making it appear fully **below** the actor.

**Quick Select Buttons:**

-   **TopL:** Aligns the coordinate-space center with the object’s **top-left corner**.
-   **TopR:** Aligns the coordinate-space center with the object’s **top-right corner**.
-   **Center:** Aligns the coordinate-space center with the object’s **center**.
-   **BottomL:** Aligns the coordinate-space center with the object’s **bottom-left corner**.
-   **BottomR:** Aligns the coordinate-space center with the object’s **bottom-right corner**.

### Scan Options

> **Note:** Only enable these options if you’re running into **memory issues**, as they can increase the total number of chunks generated depending on your frame content.

**Intra Frame Scan:**

Intra Frame Scan searches for repeated chunks within the same frame.

If a frame contains repeated chunks, the tool can detect them and reduce memory usage by referencing the same chunk in memory instead of storing duplicates.

This optimization saves memory, allowing more objects to be displayed together in a scene without running into memory limits.

**Inter Frame Scan:**

Inter Frame Scan searches for repeated chunks across different frames.

If **Frame 1** and **Frame 2** share about 80% of their content, only the remaining 20% will generate new chunks.

The shared parts reuse the same chunk data, reducing the overall number of total chunks.

**Chunk Sizes:**

Chunk Sizes define which dimensions the Object Generator checks when detecting repeated chunks in both **Intra** and **Inter Frame Scans**.

The generator checks each enabled size from largest to smallest, prioritizing larger chunks first since they are more memory efficient.

**Which sizes should you enable?**

```
64x64  64x32  32x64
32x32  32x16  16x32
32x8   8x32   16x16
16x8   8x16   8x8
```

Avoid enabling **16×8**, **8×16**, and **8×8** whenever possible, as these smaller sizes tend to waste memory — each memory block can hold up to **4 tiles**, and these sizes leave the memory block partially unfilled.

Only enable these sizes if you want to **aggressively search for similar chunks** and don’t mind the increased total number of chunks.

### Animation Settings

An **animation** is made up of a series of frames, each shown for a set amount of time measured in **ticks** (**60 ticks = 1 second**).

Each object can have up to **8 different animations**. If you need more than 8 animations, you’ll have to create a **second object** using the same files.

To create a **static object**, set up **one animation containing a single frame**.
The duration value doesn’t matter — the frame remains visible indefinitely.

**Example structure:**

```
Animation 1:
  ├── Frame 2: 15 ticks
  ├── Frame 3: 15 ticks
  ├── Frame 4: 15 ticks
  └── Frame 5: 15 ticks

Animation 2:
  ├── Frame 1: 15 ticks
  └── Frame 2: 15 ticks
```

Click **View Animations** to preview how it looks in-game — test the timing and flow, and adjust it until it feels right.

### How to Use with `SetAnimation()`

`SetAnimation` is an **ExplorerScript** function used to change the current animation of an object.

```
SetAnimation<entity ENTITY>(x)
```

It takes an **integer argument (x)** that determines which animation to play.

Depending on the behavior you want, the argument differs as follows:

-   **1–8** → Plays the specified animation **in a loop**.  
    (1 = Animation 1, 2 = Animation 2, …, 8 = Animation 8)

-   **9–16** → Displays the **first frame** of the specified animation.  
    (9 = Animation 1, 10 = Animation 2, …, 16 = Animation 8)

-   **17–24** → Plays the specified animation **once (no loop)**.  
    (17 = Animation 1, 18 = Animation 2, …, 24 = Animation 8)

# Frames Generator

The **Frames Generator** performs the reverse process — it takes an existing game object (with all its XML files and chunks) and reconstructs the frame images. This is useful for extracting sprites from the game or modifying existing objects.

## Folder Requirements

The Frames Generator requires a specific folder structure with all the necessary files to reconstruct the frames.

```
your_folder/
├── imgs/
│   ├── 0000.png
│   ├── 0001.png
│   ├── 0002.png
│   └── ...
├── palette.pal
├── frames.xml
└── animations.xml
```

**Where to get these files:**

These files are typically:

-   Generated by the Object Generator
-   Extracted from the game using tools like GFXCrunch and SkyTemple

## Using the Frames Generator

<div align="center">
    <img src="images/frames-generator.png" alt="Frames Generator" />
</div>

**How to Use:**

1. **Select your folder**

    Choose the folder containing your **object data** (as described above).

    The tool will validate the folder structure and let you know if anything’s missing or formatted incorrectly before continuing.

2. **Adjust your configuration**

    Set your preferred **Avoid Overlap** mode to control how chunks are layered when reconstructing frames.

    You can choose between **Chunk + Palette**, **Pixel + Palette**, **Palette**, or **None**, depending on how strict you want overlap detection to be.

3. **Hit “Generate Frames”**

    The tool will rebuild each frame by assembling the chunks in order and applying the correct palettes.

    After generation, the console will display the total number of frames processed.
    A **`config.json`** file is also created — you can load this into the **Object Generator** later to rebuild the object using the same settings.

Once the process finishes, your **frame images** will appear in a new folder named **frames** inside your selected directory.
You can open these images in any image editor to modify them freely.
If you’re using **Aseprite**, the [Import Cels Script](https://github.com/WraithFire/aseprite-scripts/blob/master/import-cels.lua) can automatically import all your frame images for easy editing.

## Frames Generator Configurations

### Avoid Overlap

When reconstructing frames, chunks may overlap with each other. The **Avoid Overlap** setting determines what the Frames Generator considers an overlap.

If overlaps are detected, the Frames Generator will place the chunks on different layers to prevent them from overlapping.

**Chunk + Palette**

The strict mode. Two chunks are considered overlapping if:

-   Their areas intersect
-   They use different palette groups

**Pixel + Palette**

The balanced mode. Two chunks are considered overlapping if:

-   Two non-transparent pixels occupy the same pixel position
-   They use different palette groups

**Palette**

The lenient mode. Two chunks are considered overlapping if:

-   They use different palette groups

**None**

The unrestricted mode. No overlap detection is performed.

-   All chunks are placed on a single layer per frame, regardless of their positions or palette groups

## Bulk Conversion

If you’re running **Object Studio** from source, you can perform **bulk conversions** using the built-in helper functions from the `generators` modules.

Below is an example of how you might call them in your script:

```python
from generators.frames_generator import frames_generator_process_multiple_folder
from generators.object_generator import object_generator_process_multiple_folder

# Bulk convert all frames folders into objects

og_parent_folder = "C:\\Users\\Desktop\\gfx_crunch\\frame_folders"

scan_chunk_sizes = [
    (64, 64),
    (32, 32),
    (16, 16)
]

object_generator_process_multiple_folder(
    parent_folder=og_parent_folder,
    min_row_column_density=0.5,
    displace_object=(0, 0),
    intra_scan=True,
    inter_scan=True,
    scan_chunk_sizes=scan_chunk_sizes,
)

# Bulk convert all object folders to frames

fg_parent_folder = "C:\\Users\\Desktop\\gfx_crunch\\object_folders"

frames_generator_process_multiple_folder(
    parent_folder=fg_parent_folder,
    avoid_overlap="none",
)
```

When running **bulk object generation**, each folder can include a **`config.json`** file to define animation settings.

If a folder doesn’t include one, the tool will automatically use a **default animation** for that object.
