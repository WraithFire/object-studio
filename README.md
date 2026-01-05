# 🧩 Object Studio

**Object Studio** is a set of two tools — **Object Generator** and **Frames Generator** — made for **Pokémon Mystery Dungeon: Explorers of Sky object modding**.

-   The **Object Generator** converts **frames into objects** that can be imported into **SkyTemple** or converted back into **.wan** format using **GFXCrunch** for in-game use.
-   The **Frames Generator** recreates **frames from existing object**, allowing them to be viewed and edited in external tools such as **Aseprite**.

## Why Use This?

**SkyTemple** is an amazing tool, but when it comes to objects, it has a few big limits:

-   You can only import **one-frame, one-layer** objects — meaning **no animations**.
-   Objects are limited to **16 colors**, even though the game actually supports **up to 192 colors** (12 palette groups).
-   It doesn’t **reuse chunks** — it stores duplicate chunks instead of referencing repeating ones, which wastes memory.

The **Object Generator** removes all of these limits, letting you create **animated, multi-layered, multi-palette objects** that are memory-efficient and fully compatible with the game.

## 🚀 Installation

You can download pre-built **executables** from the [Releases Page](https://github.com/WraithFire/object-studio/releases/latest).
These are ready-to-run builds for Windows and macOS.

If you prefer, you can also [run from source code](#linuxrun-from-source-code) — especially handy if your antivirus really hates unknown executables.

## Windows

1. Download **`object_studio_windows.zip`**
2. Extract the ZIP file and open the extracted folder
3. Double-click **`object_studio.exe`** to run.

> ⚠️ If Windows Defender warns you about an unrecognized app:
>
> -   Click **"More info"**
> -   Then click **"Run anyway"**

## macOS

**For Intel Macs:**

1. Download **`object_studio_mac_intel.dmg`**
2. Open the DMG file and drag **Object Studio** into **Applications**

**For Apple Silicon (M1/M2/M3):**

1. Download **`object_studio_mac_arm64.dmg`**
2. Open the DMG file and drag **Object Studio** into **Applications**

> ⚠️ If macOS blocks the app:
>
> -   Open **System Preferences → Security & Privacy**
> -   Click **“Open Anyway”** for _Object Studio_

## Linux/Run from source code

**Requirements:**

-   Python 3.9 or higher
-   pip (Python package manager)
-   tkinter (Python Tk GUI toolkit)

**Installation Steps:**

1. **Get the source code:**
   You can either **clone the repository** or **download the ZIP file** from this repository.

    - **Option 1: Clone the repository (recommended)**

        ```bash
        git clone https://github.com/WraithFire/object-studio
        ```

    - **Option 2: Download the ZIP file**

        - Direct link: [Download ZIP](https://github.com/WraithFire/object-studio/archive/refs/heads/master.zip)
        - After downloading, extract the ZIP file to your desired location.
        - Once extracted, **open terminal** in the extracted folder, **skip Step 2**, and continue from **Step 3** below.

2. **Navigate into the project directory:**

    ```bash
    cd object-studio
    ```

3. **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Run the application:**

    ```bash
    python object_studio.py
    ```

## 🤝 Contributing

Contributions are welcome!
If you have ideas, improvements, or bug fixes:

-   Open an **issue**
-   Or submit a **pull request**

## 🏆 Credits

Special thanks to the following community members:

-   **psy_commando** - for extensive documentation and the [GFX Crunch](https://github.com/PsyCommando/ppmdu_2) tool
-   **palika** - for the incredibly useful [Animated Object Guide](https://docs.google.com/document/d/1ckoH65jPlHYZAVn0PMxO3zsuhlzpR3pQ3fOjljqyqD0)

## 📜 License

This project is licensed under the **GNU General Public License v3.0**.
See the [LICENSE](LICENSE) file for full terms.

## 💬 Support

Need help?

1. Start by reading the [documentation](docs/README.md) — it explains how to use the tool and what each configuration means.
2. If the documentation doesn’t answer your question, feel free to message me on Discord: **@wraith_fire**
