import os
import sys
import json
import threading
import webbrowser
import tkinter as tk
import urllib.request
from data import (
    DEBUG,
    CURRENT_VERSION,
    RELEASE_API_ENDPOINT,
    DOCUMENTATION_URL,
    CHUNK_SIZES,
)
from icons.data import (
    SMALL_ICON_DATA,
    LARGE_ICON_DATA,
)
from PIL import Image, ImageTk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from generators import (
    generate_object_main,
    validate_og_input_folder,
    generate_frames_main,
    validate_fg_input_folder,
)


def validate_integer_input(new_value):
    if new_value == "" or new_value == "-":
        return True
    try:
        value = int(new_value)
        return -999999 <= value <= 999999
    except ValueError:
        return False


class InfoDialog:
    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("About")
        self.dialog.geometry("400x330")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.focus_set()
        self._build_ui()

    def _build_ui(self):
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True)

        header_frame = tk.Frame(main_frame, bg="#2c3e50", height=80)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        tk.Label(
            header_frame,
            text="Object Studio",
            font=("Arial", 16, "bold"),
            bg="#2c3e50",
            fg="white",
        ).pack(pady=(20, 5))

        tk.Label(
            header_frame,
            text=f"Version {CURRENT_VERSION}",
            font=("Arial", 9),
            bg="#2c3e50",
            fg="#ecf0f1",
        ).pack()

        content_frame = ttk.Frame(main_frame, padding=30)
        content_frame.pack(fill=tk.BOTH, expand=True)

        desc_label = tk.Label(
            content_frame,
            text="A tool for Explorers of Sky that converts\nframes into objects and objects back to frames",
            font=("Arial", 10),
            justify=tk.CENTER,
            wraplength=340,
        )
        desc_label.pack(pady=(0, 15))

        separator = ttk.Separator(content_frame, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, pady=10)

        ttk.Label(
            content_frame,
            text="Built by WraithFire",
            font=("Arial", 9, "italic"),
            justify=tk.CENTER,
        ).pack(pady=(0, 20))

        button_frame = ttk.Frame(content_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        style = ttk.Style()
        style.configure("Accent.TButton", font=("Arial", 10))

        ttk.Button(
            button_frame,
            text="View Docs",
            command=lambda: webbrowser.open(DOCUMENTATION_URL),
            style="Accent.TButton",
        ).pack(fill=tk.X, pady=(0, 10))

        ttk.Button(button_frame, text="Close", command=self.dialog.destroy).pack(
            fill=tk.X
        )


class AnimationSequenceDialog:
    def __init__(self, parent, title, initial_data=None, available_frames=None):
        self.result = None
        self.available_frames = available_frames or ()
        self.frame_entries = []
        self.base_title = title
        self.made_changes = False

        self._build_window(parent, title)
        self._build_ui()
        self.validate_integer_input = (
            self.dialog.register(validate_integer_input),
            "%P",
        )
        self._load_initial_data(initial_data)
        self.dialog.wait_window()

    def _build_window(self, parent, title):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("650x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.focus_set()
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close_attempt)

    def _build_ui(self):
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        self._create_header(main_frame)
        self._create_content_area(main_frame)

    def _create_header(self, parent):
        ttk.Label(
            parent,
            text="Available frames:",
            font=("Arial", 10, "bold"),
        ).pack(pady=5)

        frames_text = ", ".join(str(f) for f in self.available_frames)
        tk.Label(
            parent,
            text=f"{frames_text}",
            font=("Arial", 9),
            fg="blue",
            wraplength=460,
            justify="center",
        ).pack(pady=(0, 10))

    def _create_content_area(self, parent):
        content_frame = ttk.Frame(parent)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self._create_frames_list(content_frame)

        ttk.Button(
            content_frame, text="Save Animation", command=self._save_and_close, width=15
        ).pack(anchor=tk.CENTER, pady=(20, 0))

    def _create_frames_list(self, parent):
        list_frame = ttk.LabelFrame(parent, text="Animation Frames", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(list_frame, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def on_mousewheel_linux(event):
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

        canvas.bind("<MouseWheel>", on_mousewheel)
        canvas.bind("<Button-4>", on_mousewheel_linux)
        canvas.bind("<Button-5>", on_mousewheel_linux)

        self.scrollable_frame.bind("<MouseWheel>", on_mousewheel)
        self.scrollable_frame.bind("<Button-4>", on_mousewheel_linux)
        self.scrollable_frame.bind("<Button-5>", on_mousewheel_linux)

        def update_scroll_region(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            if self.scrollable_frame.winfo_reqheight() > canvas.winfo_height():
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            else:
                scrollbar.pack_forget()

        self.scrollable_frame.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", update_scroll_region)

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _load_initial_data(self, initial_data):
        if initial_data:
            for frame_data in initial_data:
                self._add_frame_row(
                    frame_no=frame_data["frame"],
                    duration=frame_data["duration"],
                    is_initial_load=True,
                )
        else:
            self._add_frame_row(is_initial_load=True)

    def _add_frame_row(
        self, frame_no=None, duration=30, insert_after=None, is_initial_load=False
    ):
        if frame_no is None:
            frame_no = self.available_frames[0]

        row_frame = ttk.Frame(self.scrollable_frame)

        # If insert_after is specified, insert the new row below it
        if insert_after is not None:
            insert_index = None
            for idx, (_, _, existing_row) in enumerate(self.frame_entries):
                if existing_row == insert_after:
                    insert_index = idx + 1
                    break

            if insert_index is not None and insert_index < len(self.frame_entries):
                row_frame.pack(
                    fill=tk.X, pady=3, before=self.frame_entries[insert_index][2]
                )
            else:
                row_frame.pack(fill=tk.X, pady=3)
        else:
            row_frame.pack(fill=tk.X, pady=3)

        frame_var = self._create_frame_input(row_frame, frame_no)
        duration_var = self._create_duration_input(row_frame, duration)

        ttk.Button(
            row_frame,
            text="Remove",
            command=lambda: self._remove_frame_row(row_frame),
            width=10,
        ).pack(side=tk.LEFT, padx=(10, 5))

        ttk.Button(
            row_frame,
            text="Add Frame",
            command=lambda: self._add_frame_row(insert_after=row_frame),
            width=12,
        ).pack(side=tk.LEFT)

        # Insert into the list at the correct position
        if insert_after is not None and insert_index is not None:
            self.frame_entries.insert(
                insert_index, (frame_var, duration_var, row_frame)
            )
        else:
            self.frame_entries.append((frame_var, duration_var, row_frame))

        if not is_initial_load:
            self._mark_as_changed()

        # Add traces to detect value changes
        frame_var.trace_add("write", lambda *args: self._mark_as_changed())
        duration_var.trace_add("write", lambda *args: self._mark_as_changed())

    def _create_frame_input(self, parent, initial_value):
        ttk.Label(parent, text="Frame:", font=("Arial", 9)).pack(
            side=tk.LEFT, padx=(0, 3)
        )

        frame_var = tk.IntVar(value=initial_value)
        max_frame = max(self.available_frames) if self.available_frames else 100

        ttk.Spinbox(
            parent,
            from_=1,
            to=max_frame,
            textvariable=frame_var,
            width=15,
            validate="key",
            validatecommand=self.validate_integer_input,
        ).pack(side=tk.LEFT, padx=0)

        return frame_var

    def _create_duration_input(self, parent, initial_value):
        ttk.Label(parent, text="Duration:", font=("Arial", 9)).pack(
            side=tk.LEFT, padx=(10, 3)
        )

        duration_var = tk.IntVar(value=initial_value)

        ttk.Spinbox(
            parent,
            from_=1,
            to=1000,
            textvariable=duration_var,
            width=15,
            validate="key",
            validatecommand=self.validate_integer_input,
        ).pack(side=tk.LEFT, padx=0)

        return duration_var

    def _remove_frame_row(self, row_frame):
        # Check if this is the last frame
        if len(self.frame_entries) <= 1:
            messagebox.showwarning(
                "Cannot Delete",
                "At least one frame must exist in each animation.",
                parent=self.dialog,
            )
            return

        self.frame_entries = [
            entry for entry in self.frame_entries if entry[2] != row_frame
        ]
        row_frame.destroy()
        self._mark_as_changed()

    def _mark_as_changed(self):
        if not self.made_changes:
            self.made_changes = True
            self.dialog.title(f"{self.base_title} (Unsaved Changes)")

    def _on_close_attempt(self):
        if self.made_changes:
            response = messagebox.askyesnocancel(
                "Unsaved Changes",
                "Do you want to save before closing?",
                parent=self.dialog,
            )

            if response is True:
                self._save_and_close()
            elif response is False:
                self.dialog.destroy()
        else:
            self.dialog.destroy()

    def _save_and_close(self):
        # Check for empty fields first
        empty_fields = self._check_empty_fields()
        if empty_fields:
            self._show_invalid_error(error_type="empty_fields", empty_rows=empty_fields)
            return

        frame_data = [
            {"frame": frame_var.get(), "duration": duration_var.get()}
            for frame_var, duration_var, _ in self.frame_entries
        ]

        invalid_frames = self._validate_frames(frame_data)
        if invalid_frames:
            self._show_invalid_error(
                error_type="invalid_frames", invalid_frames=invalid_frames
            )
            return

        self.result = frame_data
        self.made_changes = False
        self.dialog.destroy()

    def _check_empty_fields(self):
        empty_rows = []
        for idx, (frame_var, duration_var, _) in enumerate(self.frame_entries, 1):
            try:
                frame_val = frame_var.get()
                duration_val = duration_var.get()

                if frame_val < 0 or duration_val <= 0:
                    empty_rows.append(idx)
            except tk.TclError:
                empty_rows.append(idx)

        return empty_rows

    def _validate_frames(self, frame_data):
        if not self.available_frames:
            return []

        return [
            item["frame"]
            for item in frame_data
            if item["frame"] not in self.available_frames
        ]

    def _show_invalid_error(self, error_type, **kwargs):
        error_messages = {
            "empty_fields": {
                "title": "Empty Fields",
                "message": lambda: (
                    "Please fill in frame number and duration correctly.\n\n"
                    f"Empty fields found in row(s): {', '.join(map(str, kwargs['empty_rows']))}"
                ),
            },
            "invalid_frames": {
                "title": "Invalid Frames",
                "message": lambda: (
                    f"The following frames are not available: {', '.join(str(f) for f in kwargs['invalid_frames'])}\n\n"
                    f"Available frames: {', '.join(str(f) for f in sorted(self.available_frames))}"
                ),
            },
        }

        error_config = error_messages.get(error_type)
        if error_config:
            title = error_config["title"]
            message = error_config["message"]()
            messagebox.showerror(title, message, parent=self.dialog)


class AnimationViewer:

    def __init__(self, parent, title, frame_number_to_image, animation_group):
        self.frame_number_to_image = frame_number_to_image
        self.animation_group = animation_group

        self._init_state()
        self._create_window(parent, title)
        self._create_ui()
        self._on_animation_changed()
        self.window.wait_window()

    def _init_state(self):
        self.window = None
        self.image_label = None
        self.play_button = None
        self.frame_spinbox = None

        self.current_anim_index = tk.IntVar(value=1)
        self.current_sequence = []
        self.current_frame_index = 0
        self.is_playing = False
        self.playback_after_id = None

        self.frame_spinbox_var = tk.StringVar(value="0")
        self.is_dark_background = True
        self.should_loop = tk.BooleanVar(value=True)

        self._frame_num_to_index = {}

    def _create_window(self, parent, title):
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.geometry("500x500")
        self.window.transient(parent)
        self.window.grab_set()
        self.window.focus_set()

    def _create_ui(self):
        control_frame = ttk.Frame(self.window, padding=8)
        control_frame.pack(side=tk.TOP, fill=tk.X)

        self._create_animation_selector(control_frame)
        self._create_playback_controls(control_frame)
        self._create_frame_selector(control_frame)

        self.image_label = tk.Label(self.window, bg="black")
        self.image_label.pack(expand=True, fill=tk.BOTH)

    def _create_animation_selector(self, parent):
        ttk.Label(parent, text="Animation:").pack(side=tk.LEFT)

        max_animations = max(1, len(self.animation_group))
        ttk.Spinbox(
            parent,
            from_=1,
            to=max_animations,
            textvariable=self.current_anim_index,
            width=6,
            state="readonly",
            command=self._on_animation_changed,
        ).pack(side=tk.LEFT, padx=(6, 12))

    def _create_playback_controls(self, parent):
        ttk.Checkbutton(parent, text="Loop", variable=self.should_loop).pack(
            side=tk.LEFT, padx=4
        )

        self.play_button = ttk.Button(
            parent, text="Play", command=self._toggle_playback
        )
        self.play_button.pack(side=tk.LEFT, padx=4)

        ttk.Button(parent, text="Toggle BG", command=self._toggle_background).pack(
            side=tk.LEFT, padx=4
        )

    def _create_frame_selector(self, parent):
        self.frame_spinbox = ttk.Spinbox(
            parent,
            textvariable=self.frame_spinbox_var,
            width=8,
            state="readonly",
            command=self._on_frame_selected,
        )
        self.frame_spinbox.pack(side=tk.RIGHT)

        ttk.Label(parent, text="Frame:").pack(side=tk.RIGHT, padx=(12, 4))

    # === Animation Loading ===

    def _on_animation_changed(self):
        anim_index = int(self.current_anim_index.get()) - 1

        if not (0 <= anim_index < len(self.animation_group)):
            self.current_sequence = []
            self._frame_num_to_index = {}
            self._reset_playback()
            return

        self._load_animation(anim_index)
        self._reset_playback()
        self._update_frame_selector()

    def _load_animation(self, anim_index):

        MS_PER_TICK = 1000 / 60

        animation = self.animation_group[anim_index]
        self.current_sequence = []
        self._frame_num_to_index = {}

        for frame_data in animation:
            frame_num = frame_data["frame"]

            image = self.frame_number_to_image.get(frame_num)
            if image is not None:
                duration_ticks = frame_data.get("duration")
                duration_ms = int(duration_ticks * MS_PER_TICK)

                idx = len(self.current_sequence)
                self.current_sequence.append((frame_num, duration_ms, image))
                self._frame_num_to_index[frame_num] = idx

    def _update_frame_selector(self):
        if self.current_sequence:
            frame_numbers = [
                str(frame_num) for frame_num, _, _ in self.current_sequence
            ]
            self.frame_spinbox.config(values=frame_numbers)
            self.frame_spinbox_var.set(frame_numbers[0])
            _, _, image = self.current_sequence[0]
            self.image_label.config(image=image)
        else:
            self.frame_spinbox.config(values=[])
            self.frame_spinbox_var.set("0")
            self.image_label.config(image="")

    # === Frame Display ===

    def _on_frame_selected(self):
        if self.is_playing:
            self._stop_playback()

        if not self.current_sequence:
            return

        try:
            selected_frame_num = int(self.frame_spinbox_var.get())
        except ValueError:
            return

        idx = self._frame_num_to_index.get(selected_frame_num)
        if idx is not None:
            self.current_frame_index = idx
            _, _, image = self.current_sequence[idx]
            self.image_label.config(image=image)

    # === Playback Control ===

    def _toggle_playback(self):
        if self.is_playing:
            self._stop_playback()
        else:
            self._start_playback()

    def _start_playback(self):
        if self.is_playing or not self.current_sequence:
            return

        # If loop is disabled and we're on the last frame, restart from beginning
        if (
            not self.should_loop.get()
            and self.current_frame_index == len(self.current_sequence) - 1
        ):
            self.current_frame_index = 0

        self.is_playing = True
        self.play_button.config(text="Stop")
        self._advance_frame()

    def _stop_playback(self):
        if self.playback_after_id is not None:
            try:
                self.window.after_cancel(self.playback_after_id)
            except Exception:
                pass
            self.playback_after_id = None

        self.is_playing = False

        if self.play_button:
            self.play_button.config(text="Play")

    def _reset_playback(self):
        self._stop_playback()
        self.current_frame_index = 0

    def _advance_frame(self):
        if not self.is_playing:
            return

        frame_num, duration_ms, image = self.current_sequence[self.current_frame_index]

        self.image_label.config(image=image)
        self.frame_spinbox_var.set(str(frame_num))

        seq_len = len(self.current_sequence)
        next_index = self.current_frame_index + 1

        # Check if we've reached the end of the sequence
        if next_index >= seq_len:
            if self.should_loop.get():
                # Loop back to the beginning
                self.current_frame_index = 0
                self.playback_after_id = self.window.after(
                    duration_ms, self._advance_frame
                )
            else:
                # Stop at the last frame
                self._stop_playback()
        else:
            # Continue to next frame
            self.current_frame_index = next_index
            self.playback_after_id = self.window.after(duration_ms, self._advance_frame)

    # === UI Actions ===

    def _toggle_background(self):
        self.is_dark_background = not self.is_dark_background
        bg_color = "black" if self.is_dark_background else "white"
        self.image_label.config(bg=bg_color)


class ObjectStudioGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Object Studio")
        self.root.geometry("1100x680")

        small_icon = tk.PhotoImage(data=SMALL_ICON_DATA)
        large_icon = tk.PhotoImage(data=LARGE_ICON_DATA)
        self.root.iconphoto(True, small_icon, large_icon)

        # Custom style
        style = ttk.Style()
        style.configure("Large.TButton", font=("Arial", 12, "bold"), padding=10)
        style.configure("Bold.TLabelframe.Label", font=("Arial", 10, "bold"))

        # Configuration variables
        self.input_folder = tk.StringVar(value="")
        self.min_density = tk.IntVar(value=50)
        self.displace_x = tk.IntVar(value=0)
        self.displace_y = tk.IntVar(value=0)
        self.animation_group = []

        # Frame images for viewer
        self.frame_number_to_image = {}

        # Object Generator folder data
        self.og_images_dict = {}
        self.og_shared_palette = None
        self.og_max_colors_used = None
        self.og_image_height = None
        self.og_image_width = None
        self.og_available_frames = []

        # Frames Generator folder data
        self.fg_normal_mode = False
        self.fg_special_cases_info = None
        self.fg_images_dict = {}
        self.fg_riff_palette_data = None
        self.fg_frames_xml_root = None
        self.fg_animations_xml_root = None

        self.validate_integer_input = (self.root.register(validate_integer_input), "%P")

        self.create_widgets()
        self.redirect_stdout_to_console()
        self.root.after(100, self.check_for_update)

    def create_widgets(self):
        paned_window = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=10)
        paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # LEFT COLUMN
        left_frame = ttk.Frame(paned_window)
        paned_window.add(left_frame, minsize=500)

        self.notebook = ttk.Notebook(left_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", self.clear_console)

        # Tab 1
        object_generator_tab = ttk.Frame(self.notebook, padding=(10, 0))
        self.notebook.add(object_generator_tab, text="Object Generator")
        object_generator_tab.columnconfigure(0, weight=1)
        object_generator_tab.rowconfigure(1, weight=1)
        self.create_object_generator_tab(object_generator_tab)

        # Tab 2
        frames_generator_tab = ttk.Frame(self.notebook, padding=(10, 0))
        self.notebook.add(frames_generator_tab, text="Frames Generator")
        self.create_frames_generator_tab(frames_generator_tab)

        # RIGHT COLUMN
        right_frame = ttk.Frame(paned_window)
        paned_window.add(right_frame, minsize=500)

        info_btn = ttk.Button(
            right_frame, text="About", command=lambda: InfoDialog(self.root)
        )
        info_btn.pack(anchor=tk.E, padx=(0, 17), pady=(0, 17))

        console_container = ttk.Frame(right_frame)
        console_container.pack(fill=tk.BOTH, expand=True)
        self.create_console(console_container)

    def create_object_generator_tab(self, parent):
        # Basic Settings
        basic_frame = ttk.LabelFrame(
            parent, text="Basic Settings", style="Bold.TLabelframe", padding=(10, 5)
        )
        basic_frame.grid(row=0, column=0, sticky="ew", pady=10)
        basic_frame.columnconfigure(1, weight=1)
        self.create_basic_settings(basic_frame)

        # Animation Settings
        anim_frame = ttk.LabelFrame(
            parent, text="Animation Settings", style="Bold.TLabelframe", padding=(10, 0)
        )
        anim_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        anim_frame.rowconfigure(0, weight=1)
        anim_frame.columnconfigure(0, weight=1)
        self.create_animation_settings(anim_frame)

        # Config buttons
        config_frame = ttk.Frame(parent)
        config_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10), padx=10)
        config_frame.columnconfigure(0, weight=1)
        config_frame.columnconfigure(1, weight=1)

        self.load_config_btn = ttk.Button(
            config_frame, text="Load Config", command=self.load_config
        )
        self.load_config_btn.grid(row=0, column=0, sticky="ew", padx=(0, 2))

        ttk.Button(config_frame, text="Save Config", command=self.save_config).grid(
            row=0, column=1, sticky="ew", padx=(2, 0)
        )

        # Process button
        self.generate_object_btn = ttk.Button(
            parent,
            text="Generate Object",
            command=self.generate_object,
            style="Large.TButton",
            state="disabled",
        )
        self.generate_object_btn.grid(
            row=3, column=0, sticky="ew", padx=10, pady=(0, 10)
        )

    def create_frames_generator_tab(self, parent):
        self.recon_folder = tk.StringVar(value="")

        ttk.Label(
            parent, text="Select a folder containing:", font=("Arial", 12, "bold")
        ).pack(anchor=tk.W, pady=10)

        file_structure_listbox = tk.Listbox(
            parent,
            height=4,
            borderwidth=10,
            relief="flat",
        )
        file_structure_listbox.pack(fill=tk.X, pady=(0, 10), padx=10)

        # Add file structure items
        file_structure_listbox.insert(tk.END, "├── imgs")
        file_structure_listbox.insert(tk.END, "├── palette.pal")
        file_structure_listbox.insert(tk.END, "├── frames.xml")
        file_structure_listbox.insert(tk.END, "└── animations.xml")

        file_structure_listbox.config(state=tk.DISABLED)

        # Folder selection frame
        folder_frame = ttk.Frame(parent, padding=(10, 0))
        folder_frame.pack(fill=tk.X, pady=10)

        ttk.Entry(
            folder_frame, textvariable=self.recon_folder, width=35, state="readonly"
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.recon_browse_btn = ttk.Button(
            folder_frame, text="Browse", command=self.browse_recon_folder, width=10
        )
        self.recon_browse_btn.pack(side=tk.LEFT)

        # Avoid Overlap Settings
        overlap_frame = ttk.LabelFrame(
            parent, text="Avoid Overlap", style="Bold.TLabelframe", padding=10
        )
        overlap_frame.pack(fill=tk.X, pady=10, padx=10)

        self.avoid_overlap = tk.StringVar(value="pixel")

        ttk.Radiobutton(
            overlap_frame,
            text="Pixel + Palette",
            variable=self.avoid_overlap,
            value="pixel",
        ).pack(anchor=tk.W, pady=2)

        ttk.Radiobutton(
            overlap_frame,
            text="Chunk + Palette",
            variable=self.avoid_overlap,
            value="chunk",
        ).pack(anchor=tk.W, pady=2)

        ttk.Radiobutton(
            overlap_frame, text="Palette", variable=self.avoid_overlap, value="palette"
        ).pack(anchor=tk.W, pady=2)

        ttk.Radiobutton(
            overlap_frame,
            text="None",
            variable=self.avoid_overlap,
            value="none",
        ).pack(anchor=tk.W, pady=2)

        self.generate_frames_btn = ttk.Button(
            parent,
            text="Generate Frames",
            command=self.generate_frames,
            style="Large.TButton",
            state="disabled",
        )
        self.generate_frames_btn.pack(fill=tk.X, pady=(10, 0), padx=10)

    def create_basic_settings(self, parent):
        row = 0

        # Input Folder
        ttk.Label(parent, text="Frames Dir:", font=("Arial", 9, "bold")).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        folder_frame = ttk.Frame(parent)
        folder_frame.grid(row=row, column=1, sticky=tk.EW)

        ttk.Entry(
            folder_frame, textvariable=self.input_folder, width=25, state="readonly"
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.browse_btn = ttk.Button(
            folder_frame, text="Browse", command=self.browse_folder, width=8
        )
        self.browse_btn.pack(side=tk.LEFT, padx=(5, 0))

        row += 1

        # Min Row Column Density
        ttk.Label(parent, text="Min Density:", font=("Arial", 9, "bold")).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        density_frame = ttk.Frame(parent)
        density_frame.grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        density_frame.columnconfigure(0, weight=1)

        def update_density_label(v):
            self.density_label.config(text=f"{self.min_density.get()}%")

        ttk.Scale(
            density_frame,
            from_=0,
            to=100,
            variable=self.min_density,
            orient=tk.HORIZONTAL,
            length=230,
            command=update_density_label,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 5))

        self.density_label = tk.Label(density_frame, text=f"50%", width=5)
        self.density_label.grid(row=0, column=1)

        # Displace Object X and Y in one row
        row += 1
        ttk.Label(parent, text="Displace Object:", font=("Arial", 9, "bold")).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )

        displace_frame = ttk.Frame(parent)
        displace_frame.grid(row=row, column=1, sticky=tk.EW, pady=5, padx=5)
        displace_frame.columnconfigure(1, weight=1)
        displace_frame.columnconfigure(3, weight=1)

        ttk.Label(displace_frame, text="X:").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(
            displace_frame,
            from_=-999999,
            to=999999,
            textvariable=self.displace_x,
            validate="key",
            validatecommand=self.validate_integer_input,
        ).grid(row=0, column=1, sticky="ew", padx=(2, 10))

        ttk.Label(displace_frame, text="Y:").grid(row=0, column=2, sticky="w")
        ttk.Spinbox(
            displace_frame,
            from_=-999999,
            to=999999,
            textvariable=self.displace_y,
            validate="key",
            validatecommand=self.validate_integer_input,
        ).grid(row=0, column=3, sticky="ew", padx=(2, 0))

        # Quick select buttons for Displacement
        row += 1
        quick_select_frame = ttk.Frame(parent)
        quick_select_frame.grid(row=row, column=0, columnspan=2, sticky=tk.EW, pady=5)

        def set_displacement(position):
            w = 0 if self.og_image_width is None else self.og_image_width // 2
            h = 0 if self.og_image_height is None else self.og_image_height // 2

            if position == "TopL":
                x, y = w, h
            elif position == "TopR":
                x, y = -w, h
            elif position == "BottomL":
                x, y = w, -h
            elif position == "BottomR":
                x, y = -w, -h
            else:
                x, y = 0, 0

            self.displace_x.set(x)
            self.displace_y.set(y)

        buttons = [
            ("TopL", lambda: set_displacement("TopL")),
            ("TopR", lambda: set_displacement("TopR")),
            ("Center", lambda: set_displacement("Center")),
            ("BottomL", lambda: set_displacement("BottomL")),
            ("BottomR", lambda: set_displacement("BottomR")),
        ]

        for i, (label, cmd) in enumerate(buttons):
            ttk.Button(quick_select_frame, text=label, command=cmd).grid(
                row=0, column=i, sticky="nsew", padx=2
            )

        for i in range(len(buttons)):
            quick_select_frame.columnconfigure(i, weight=1)

        row += 1

        # Scan Options Section
        ttk.Label(parent, text="Scan Options:", font=("Arial", 9, "bold")).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )

        scan_frame = ttk.Frame(parent)
        scan_frame.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)

        self.intrascan_var = tk.BooleanVar(value=True)
        self.interscan_var = tk.BooleanVar(value=True)

        ttk.Checkbutton(
            scan_frame, text="Intra Frame", variable=self.intrascan_var
        ).pack(side=tk.LEFT, padx=(0, 15))

        ttk.Checkbutton(
            scan_frame, text="Inter Frame", variable=self.interscan_var
        ).pack(side=tk.LEFT)

        row += 1

        # Checkbox Grid Section
        ttk.Label(parent, text="Chunk Sizes:", font=("Arial", 9, "bold")).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )

        row += 1

        checkbox_container = ttk.Frame(parent)
        checkbox_container.grid(row=row, column=0, columnspan=2, sticky=tk.EW, pady=5)

        self.scan_chunk_sizes = {}
        labels = [f"{w}x{h}" for w, h in CHUNK_SIZES]

        for i, label in enumerate(labels):
            cb_row = i // 6
            cb_col = i % 6

            is_enabled = i < len(labels) - 3
            var = tk.BooleanVar(value=is_enabled)
            self.scan_chunk_sizes[label] = var

            cb = ttk.Checkbutton(checkbox_container, text=label, variable=var)
            cb.grid(row=cb_row, column=cb_col, sticky=tk.W, padx=5, pady=5)

            checkbox_container.columnconfigure(cb_col, weight=1)

    def create_animation_settings(self, parent):
        # Animation group list
        list_frame = ttk.Frame(parent)
        list_frame.grid(row=0, column=0, sticky="nsew", pady=(10, 0), padx=10)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.anim_group_listbox = tk.Listbox(
            list_frame, yscrollcommand=scrollbar.set, height=8
        )
        self.anim_group_listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar.config(command=self.anim_group_listbox.yview)

        # Animation Buttons
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=1, column=0, sticky="ew", pady=(10, 18), padx=10)

        for i in range(4):
            btn_frame.columnconfigure(i, weight=1)

        ttk.Button(
            btn_frame,
            text="Add Animation",
            command=self.add_animation_sequence,
            width=14,
        ).grid(row=0, column=0, sticky="ew", padx=2)
        ttk.Button(
            btn_frame,
            text="Edit Animation",
            command=self.edit_animation_sequence,
            width=14,
        ).grid(row=0, column=1, sticky="ew", padx=2)
        ttk.Button(
            btn_frame, text="Delete", command=self.delete_frame_or_sequence, width=8
        ).grid(row=0, column=2, sticky="ew", padx=2)
        ttk.Button(
            btn_frame,
            text="View Animations",
            command=self.view_animation_sequences,
            width=16,
        ).grid(row=0, column=3, sticky="ew", padx=2)

        self.animation_group = []
        self.update_animation_group_listbox()

    def create_console(self, parent):
        self.console_text = scrolledtext.ScrolledText(
            parent,
            wrap=tk.WORD,
            bg="#1e1e1e",
            fg="#00ff00",
            font=("Consolas", 9),
            state="disabled",
        )
        self.console_text.pack(fill=tk.BOTH, expand=True)

        self.clear_console_btn = ttk.Button(
            parent, text="Clear", command=self.clear_console, width=8
        )
        self.clear_console_btn.place(relx=1.0, rely=1.0, anchor=tk.SE, x=-30, y=-10)

    def check_for_update(self):
        try:
            with urllib.request.urlopen(RELEASE_API_ENDPOINT, timeout=5) as response:
                if response.status != 200:
                    raise Exception(f"HTTP Error {response.status}: {response.reason}")

                data = response.read()
                latest_version = (
                    json.loads(data).get("name", "").replace("Version ", "")
                )

                if latest_version and CURRENT_VERSION != latest_version:
                    messagebox.showinfo(
                        "Update Available",
                        f"Version {latest_version} is now available. Please update.",
                    )
                elif DEBUG:
                    print("[OK] Up to date.")
        except Exception as e:
            if DEBUG:
                print(f"[WARNING] Could not check for updates. \n{e}")

    def browse_folder(self):
        folder = filedialog.askdirectory(
            initialdir=self.input_folder.get() if self.input_folder.get() else "."
        )

        if not folder:
            return

        prev_animation_group = None

        if folder != self.input_folder.get():
            self.displace_x.set(0)
            self.displace_y.set(0)
            self.input_folder.set(folder)
        else:
            prev_animation_group = self.animation_group

        self.prepare_object_generator_data()

        if prev_animation_group:
            result = self.validate_config_values(
                animation_group=prev_animation_group,
            )

            valid_values = result["valid_values"]

            if "animation_group" in valid_values:
                self.animation_group = valid_values["animation_group"]
            else:
                self.animation_group = []
        else:
            self.animation_group = []

        if not self.animation_group and self.og_available_frames:
            min_frame = self.og_available_frames[0]
            self.animation_group = [[{"frame": min_frame, "duration": 30}]]

        self.update_animation_group_listbox()

    def browse_recon_folder(self):
        folder = filedialog.askdirectory(
            initialdir=self.recon_folder.get() if self.recon_folder.get() else "."
        )

        if not folder:
            return

        self.recon_folder.set(folder)
        self.prepare_frames_generator_data()

    def add_animation_sequence(self):
        if not self.og_available_frames:
            messagebox.showwarning(
                "No Folder Selected", "Please select a folder with valid images first"
            )
            return

        dialog = AnimationSequenceDialog(
            self.root,
            "Add Animation Sequence",
            available_frames=self.og_available_frames,
        )

        if dialog.result:
            self.animation_group.append(dialog.result)
            self.update_animation_group_listbox()

    def edit_animation_sequence(self):
        selection = self.anim_group_listbox.curselection()
        if not selection:
            messagebox.showwarning(
                "No Selection", "Please select a animation sequence to edit"
            )
            return

        # Find which group the selected item belongs to
        selected_line = selection[0]
        group_idx = self.get_group_index_from_line(selected_line)

        dialog = AnimationSequenceDialog(
            self.root,
            "Edit Animation Sequence",
            self.animation_group[group_idx],
            self.og_available_frames,
        )
        if dialog.result:
            self.animation_group[group_idx] = dialog.result
            self.update_animation_group_listbox()

    def delete_frame_or_sequence(self):
        # Get the selected item
        selection = self.anim_group_listbox.curselection()
        if not selection:
            messagebox.showwarning(
                "No Selection", "Please select an animation or frame to delete"
            )
            return

        selected_line = selection[0]
        selected_text = self.anim_group_listbox.get(selected_line)

        # Check if a frame is selected (starts with tree characters)
        is_frame = selected_text.startswith("├──") or selected_text.startswith("└──")

        if is_frame:
            # === DELETING A FRAME ===
            group_idx, frame_idx, frame_no = self.get_frame_indices_from_line(
                selected_line
            )

            if group_idx is None or frame_idx is None:
                return

            # Check if this would delete the last frame of the last sequence
            is_last_sequence = len(self.animation_group) == 1
            is_last_frame_in_sequence = len(self.animation_group[group_idx]) == 1

            if is_last_sequence and is_last_frame_in_sequence:
                messagebox.showwarning(
                    "Cannot Delete", "At least one animation with one frame must exist."
                )
                return

            # Confirm and delete
            if messagebox.askyesno(
                "Confirm Delete",
                f"Delete frame {frame_no} from animation {group_idx + 1}?",
            ):
                del self.animation_group[group_idx][frame_idx]

                # If group becomes empty after deleting frame, remove the group too
                if not self.animation_group[group_idx]:
                    del self.animation_group[group_idx]

                self.update_animation_group_listbox()

        else:
            # === DELETING AN ENTIRE SEQUENCE ===
            group_idx = self.get_group_index_from_line(selected_line)

            if group_idx is None:
                return

            # Check if this is the last sequence
            is_last_sequence = len(self.animation_group) == 1

            if is_last_sequence:
                messagebox.showwarning(
                    "Cannot Delete", "At least one animation sequence must exist."
                )
                return

            # Confirm and delete
            if messagebox.askyesno(
                "Confirm Delete", f"Delete animation sequence {group_idx + 1}?"
            ):
                del self.animation_group[group_idx]
                self.update_animation_group_listbox()

    def view_animation_sequences(self):
        if not self.animation_group:
            messagebox.showwarning("No Animations", "No animation sequences to view.")
            return

        # Create the viewer window
        AnimationViewer(
            self.root,
            "Animation Viewer",
            self.frame_number_to_image,
            self.animation_group,
        )

    def get_group_index_from_line(self, line_idx):
        current_line = 0

        for group_idx, group in enumerate(self.animation_group):
            # Group header line
            if current_line == line_idx:
                return group_idx
            current_line += 1

            # Frame lines
            frame_count = len(group)
            if current_line <= line_idx < current_line + frame_count:
                return group_idx
            current_line += frame_count

        return None

    def get_frame_indices_from_line(self, line_idx):
        current_line = 0

        for group_idx, group in enumerate(self.animation_group):
            # Group header line
            current_line += 1

            # Frame lines
            for frame_idx, frame_data in enumerate(group):
                if current_line == line_idx:
                    return (group_idx, frame_idx, frame_data["frame"])
                current_line += 1

        return (None, None, None)

    def update_animation_group_listbox(self):
        self.anim_group_listbox.delete(0, tk.END)
        for i, group in enumerate(self.animation_group):
            # Add group header
            self.anim_group_listbox.insert(tk.END, f"Animation {i+1}")

            # Add frames with tree structure
            for idx, frame_data in enumerate(group):
                is_last = idx == len(group) - 1
                prefix = "└── " if is_last else "├── "
                frame_num = frame_data["frame"]
                duration = frame_data["duration"]
                self.anim_group_listbox.insert(
                    tk.END, f"{prefix}Frame {frame_num}: {duration}"
                )

    def clear_console(self, event=None):
        self.console_text.config(state="normal")
        self.console_text.delete(1.0, tk.END)
        self.console_text.config(state="disabled")

    def save_config(self):

        # Convert BooleanVar checkboxes to a simple dict
        chunk_sizes_config = {
            label: var.get() for label, var in self.scan_chunk_sizes.items()
        }

        config = {
            "frames_folder": self.input_folder.get(),
            "min_density": self.min_density.get(),
            "displace_x": self.displace_x.get(),
            "displace_y": self.displace_y.get(),
            "intrascan": self.intrascan_var.get(),
            "interscan": self.interscan_var.get(),
            "scan_chunk_sizes": chunk_sizes_config,
            "animation_group": self.animation_group,
        }

        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )

        if file_path:
            with open(file_path, "w") as f:
                json.dump(config, f, indent=4)
            messagebox.showinfo("Success", "Configuration saved successfully")

    def load_config(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not file_path:
            return

        try:
            with open(file_path, "r") as f:
                config = json.load(f)

            loaded_folder = config.get("frames_folder")
            if not os.path.exists(loaded_folder):
                messagebox.showerror(
                    "Folder Not Found", f"Folder does not exist:\n{loaded_folder}"
                )
                return

            self.input_folder.set(loaded_folder)
            self.prepare_object_generator_data()

            # ---- Validate config values ----
            result = self.validate_config_values(
                animation_group=config.get("animation_group"),
                min_density=config.get("min_density"),
                displace_x=config.get("displace_x"),
                displace_y=config.get("displace_y"),
                intrascan=config.get("intrascan"),
                interscan=config.get("interscan"),
                scan_chunk_sizes=config.get("scan_chunk_sizes"),
            )

            valid = result["valid_values"]
            invalid_values = result["invalid_values"]

            # ---- Apply valid values ----
            if "min_density" in valid:
                self.min_density.set(valid["min_density"])
                self.density_label.config(text=f"{self.min_density.get()}%")
            else:
                self.min_density.set(50)
                self.density_label.config(text="50%")

            if "displace_x" in valid:
                self.displace_x.set(valid["displace_x"])
            else:
                self.displace_x.set(0)

            if "displace_y" in valid:
                self.displace_y.set(valid["displace_y"])
            else:
                self.displace_y.set(0)

            if "intrascan" in valid:
                self.intrascan_var.set(valid["intrascan"])
            else:
                self.intrascan_var.set(True)

            if "interscan" in valid:
                self.interscan_var.set(valid["interscan"])
            else:
                self.interscan_var.set(True)

            if "scan_chunk_sizes" in valid:
                for label in self.scan_chunk_sizes.keys():
                    if label in valid["scan_chunk_sizes"]:
                        self.scan_chunk_sizes[label].set(
                            valid["scan_chunk_sizes"][label]
                        )
                    else:
                        labels_list = [f"{w}x{h}" for w, h in CHUNK_SIZES]
                        label_index = (
                            labels_list.index(label) if label in labels_list else -1
                        )
                        is_enabled = label_index < len(labels_list) - 3
                        self.scan_chunk_sizes[label].set(is_enabled)
            else:
                labels_list = [f"{w}x{h}" for w, h in CHUNK_SIZES]
                for label in self.scan_chunk_sizes.keys():
                    label_index = (
                        labels_list.index(label) if label in labels_list else -1
                    )
                    is_enabled = label_index < len(labels_list) - 3
                    self.scan_chunk_sizes[label].set(is_enabled)

            if "animation_group" in valid:
                self.animation_group = valid["animation_group"]
            elif self.og_available_frames:
                min_frame = self.og_available_frames[0]
                self.animation_group = [[{"frame": min_frame, "duration": 30}]]

            self.update_animation_group_listbox()

            # ---- Show warning if there are invalid values ----
            if invalid_values:
                error_lines = []
                for k, v in invalid_values.items():
                    if "\n" in v:
                        error_lines.append(f"Errors in {k}:")
                        for line in v.split("\n"):
                            error_lines.append(f"  • {line}")
                    else:
                        error_lines.append(f"Error in {k}:")
                        error_lines.append(f"  • {v}")

                invalid_str = "\n".join(error_lines)
                messagebox.showwarning(
                    "Invalid Config Values",
                    f"The following values were ignored:\n\n{invalid_str}",
                )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config: {str(e)}")

    def validate_config_values(
        self,
        animation_group=None,
        min_density=None,
        displace_x=None,
        displace_y=None,
        intrascan=None,
        interscan=None,
        scan_chunk_sizes=None,
    ):
        invalid_values = {}
        valid_values = {}

        # ---- Validate min_density ----
        if min_density is not None:
            if not isinstance(min_density, int):
                invalid_values["min_density"] = (
                    f"Must be a whole number. Received: {type(min_density).__name__}."
                )
            elif not (0 <= min_density <= 100):
                invalid_values["min_density"] = (
                    f"Must be between 0 and 100. Received: {min_density}."
                )
            else:
                valid_values["min_density"] = min_density

        # ---- Validate displace_x / displace_y ----
        for key, val in {"displace_x": displace_x, "displace_y": displace_y}.items():
            if val is None:
                continue
            if not isinstance(val, int):
                invalid_values[key] = (
                    f"Must be a whole number. Received: {type(val).__name__}."
                )
            elif not (-999999 <= val <= 999999):
                invalid_values[key] = (
                    f"Must be between -999999 and 999999. Received: {val}."
                )
            else:
                valid_values[key] = val

        # ---- Validate intrascan / interscan ----
        for key, val in {"intrascan": intrascan, "interscan": interscan}.items():
            if val is None:
                continue
            if not isinstance(val, bool):
                invalid_values[key] = (
                    f"Must be true or false. Received: {type(val).__name__}."
                )
            else:
                valid_values[key] = val

        # ---- Validate scan_chunk_sizes ----
        if scan_chunk_sizes is not None:
            if not isinstance(scan_chunk_sizes, dict):
                invalid_values["scan_chunk_sizes"] = (
                    f"Must be a dictionary of chunk sizes (e.g., {{'32x32': true, '16x16': false}}). Received: {type(scan_chunk_sizes).__name__}."
                )
            else:
                valid_chunk_sizes = {}
                invalid_chunk_errors = []
                valid_labels = {f"{w}x{h}" for w, h in CHUNK_SIZES}

                for label, value in scan_chunk_sizes.items():
                    if label not in valid_labels:
                        invalid_chunk_errors.append(f"'{label}': Invalid chunk size.")
                    elif not isinstance(value, bool):
                        invalid_chunk_errors.append(
                            f"'{label}': Must be true or false. Received: {type(value).__name__}."
                        )
                    else:
                        valid_chunk_sizes[label] = value

                if invalid_chunk_errors:
                    invalid_values["scan_chunk_sizes"] = "\n".join(invalid_chunk_errors)

                if valid_chunk_sizes:
                    valid_values["scan_chunk_sizes"] = valid_chunk_sizes

        # ---- Validate animation_group ----
        if animation_group is not None:
            if not isinstance(animation_group, list):
                invalid_values["animation_group"] = (
                    f"Must be a list of animations. Received: {type(animation_group).__name__}."
                )
            elif not self.og_available_frames:
                invalid_values["animation_group"] = (
                    "Cannot validate animations: No available frames found in selected folder."
                )
            else:
                cleaned_animation_group = []
                invalid_anim_errors = []

                for group_idx, group in enumerate(animation_group):
                    if not isinstance(group, list):
                        invalid_anim_errors.append(
                            f"Animation {group_idx + 1}: Must be a list of frame entries. Received: {type(group).__name__}."
                        )
                        continue

                    cleaned_group = []
                    for frame_idx, frame_data in enumerate(group):
                        if not isinstance(frame_data, dict):
                            invalid_anim_errors.append(
                                f"Animation {group_idx + 1}, Entry {frame_idx + 1}: Must be a dictionary with 'frame' and 'duration' fields. Received: {type(frame_data).__name__}."
                            )
                            continue

                        frame_num = frame_data.get("frame")
                        duration = frame_data.get("duration")

                        # Check frame number
                        if frame_num is None:
                            invalid_anim_errors.append(
                                f"Animation {group_idx + 1}, Entry {frame_idx + 1}: Missing 'frame' field."
                            )
                            continue
                        elif not isinstance(frame_num, int):
                            invalid_anim_errors.append(
                                f"Animation {group_idx + 1}, Entry {frame_idx + 1}: 'frame' must be a whole number. Received: {type(frame_num).__name__}."
                            )
                            continue
                        elif frame_num not in self.og_available_frames:
                            invalid_anim_errors.append(
                                f"Animation {group_idx + 1}, Entry {frame_idx + 1}: Frame {frame_num} not found."
                            )
                            continue

                        # Check duration
                        if duration is None:
                            invalid_anim_errors.append(
                                f"Animation {group_idx + 1}, Entry {frame_idx + 1}: Missing 'duration' field."
                            )
                            continue
                        elif not isinstance(duration, int):
                            invalid_anim_errors.append(
                                f"Animation {group_idx + 1}, Entry {frame_idx + 1}: 'duration' must be a whole number. Received: {type(duration).__name__}."
                            )
                            continue
                        elif duration <= 0:
                            invalid_anim_errors.append(
                                f"Animation {group_idx + 1}, Entry {frame_idx + 1}: 'duration' must be greater than 0. Received: {duration}."
                            )
                            continue

                        cleaned_group.append({"frame": frame_num, "duration": duration})

                    if cleaned_group:
                        cleaned_animation_group.append(cleaned_group)

                if invalid_anim_errors:
                    invalid_values["animation_group"] = "\n".join(invalid_anim_errors)

                if cleaned_animation_group:
                    valid_values["animation_group"] = cleaned_animation_group

        return {
            "invalid_values": invalid_values,
            "valid_values": valid_values,
        }

    def prepare_object_generator_data(self):
        self.generate_object_btn.config(state="disabled")

        # Reset Frame Images for Viewer
        self.frame_number_to_image = {}

        # Reset validation data
        self.og_images_dict = {}
        self.og_shared_palette = None
        self.og_max_colors_used = None
        self.og_image_height = None
        self.og_image_width = None
        self.og_available_frames = []

        folder = self.input_folder.get()

        if not folder or not os.path.exists(folder):
            return

        self.clear_console()

        (
            images_dict,
            common_image_size,
            original_shared_palette,
            max_colors_used,
            available_frames,
        ) = validate_og_input_folder(folder)

        if (
            images_dict
            and common_image_size
            and original_shared_palette
            and available_frames
        ):
            self.og_images_dict = images_dict
            self.og_image_width = common_image_size[0]
            self.og_image_height = common_image_size[1]
            self.og_shared_palette = original_shared_palette
            self.og_max_colors_used = max_colors_used
            self.og_available_frames = available_frames

            local_frame_number_to_image = {}
            frames_found = {}

            for data in self.og_images_dict.values():
                frame_num, layer_num, _ = data["frame_layer_palette_tuple"]
                frames_found.setdefault(frame_num, []).append(
                    (layer_num, data["image_data"])
                )

            # Composite each frame for viewer
            frame_numbers = sorted(frames_found.keys())
            for frame_no in frame_numbers:
                layers = sorted(frames_found[frame_no], key=lambda x: x[0])
                base = None
                for _, img in layers:
                    base = img if base is None else Image.alpha_composite(base, img)

                local_frame_number_to_image[frame_no] = ImageTk.PhotoImage(base)

            self.frame_number_to_image = local_frame_number_to_image

            if DEBUG:
                print(
                    f"[OK] Composite images created for frames: {self.og_available_frames}\n"
                )

            print(f"[OK] Available Frames: {self.og_available_frames}")

            # Enable process button
            self.generate_object_btn.config(state="normal")
            print("\n[OK] Validation Successful. Ready to generate.")

    def generate_object(self):
        self.clear_console()
        self.generate_object_btn.config(state="disabled")
        self.notebook.tab(1, state="disabled")
        self.browse_btn.config(state="disabled")
        self.load_config_btn.config(state="disabled")
        self.clear_console_btn.config(state="disabled")
        thread = threading.Thread(target=self.generate_object_thread)
        thread.daemon = True
        thread.start()

    def generate_object_thread(self):
        try:
            try:
                displace_x = self.displace_x.get()
                displace_y = self.displace_y.get()
            except tk.TclError:
                print(
                    f"\n[WARNING] Displace X and Y values cannot be empty — using 0 as default"
                )
                self.displace_x.set(0)
                self.displace_y.set(0)
                displace_x = 0
                displace_y = 0

            displace_object = [displace_x, displace_y]
            min_row_column_density = self.min_density.get() / 100
            animation_group = self.animation_group
            scan_chunk_sizes = [
                tuple(map(int, label.split("x")))
                for label, var in self.scan_chunk_sizes.items()
                if var.get()
            ]

            intra_scan = self.intrascan_var.get()
            inter_scan = self.interscan_var.get()
            input_folder = self.input_folder.get()

            print("\n[START] Starting Object Generation...")

            data_needed_for_processing = (
                input_folder,
                self.og_images_dict,
                self.og_shared_palette,
                self.og_max_colors_used,
                self.og_image_height,
                self.og_image_width,
                self.og_available_frames,
                min_row_column_density,
                displace_object,
                animation_group,
                scan_chunk_sizes,
                intra_scan,
                inter_scan,
            )

            generate_object_main(data_needed_for_processing)

            print(f"\n[OK] Object Generated Successfully")

        except Exception as e:
            print(f"\n[ERROR] Error during generation:\n{str(e)}")

        finally:
            self.root.after(0, lambda: self.browse_btn.config(state="normal"))
            self.root.after(0, lambda: self.load_config_btn.config(state="normal"))
            self.root.after(0, lambda: self.notebook.tab(1, state="normal"))
            self.root.after(0, lambda: self.clear_console_btn.config(state="normal"))
            self.root.after(0, lambda: self.generate_object_btn.config(state="normal"))

    def prepare_frames_generator_data(self):
        self.generate_frames_btn.config(state="disabled")

        folder = self.recon_folder.get()

        if not folder or not os.path.exists(folder):
            return

        self.clear_console()

        (
            riff_palette_data,
            images_dict,
            frames_xml_root,
            animations_xml_root,
            normal_mode,
            special_cases_info,
        ) = validate_fg_input_folder(folder)

        if (
            riff_palette_data
            and images_dict
            and frames_xml_root is not None
            and animations_xml_root is not None
        ):
            self.fg_normal_mode = normal_mode
            self.fg_special_cases_info = special_cases_info
            self.fg_riff_palette_data = riff_palette_data
            self.fg_images_dict = images_dict
            self.fg_frames_xml_root = frames_xml_root
            self.fg_animations_xml_root = animations_xml_root

            self.generate_frames_btn.config(state="normal")
            print("[OK] Validation Successful. Ready to generate.")

    def generate_frames(self):
        self.clear_console()
        self.generate_frames_btn.config(state="disabled")
        self.recon_browse_btn.config(state="disabled")
        self.notebook.tab(0, state="disabled")
        self.clear_console_btn.config(state="disabled")
        thread = threading.Thread(target=self.generate_frames_thread)
        thread.daemon = True
        thread.start()

    def generate_frames_thread(self):
        try:
            input_folder = self.recon_folder.get()
            avoid_overlap = self.avoid_overlap.get()

            print("\n[START] Starting Frames Generation...")

            data_needed_for_processing = (
                self.fg_normal_mode,
                self.fg_special_cases_info,
                input_folder,
                self.fg_riff_palette_data,
                self.fg_images_dict,
                self.fg_frames_xml_root,
                self.fg_animations_xml_root,
                avoid_overlap,
            )

            generate_frames_main(data_needed_for_processing)

            print(f"\n[OK] Frames Generated Successfully")

        except Exception as e:
            print(f"\n[ERROR] Error during generation:\n{str(e)}")

        finally:
            self.root.after(0, lambda: self.recon_browse_btn.config(state="normal"))
            self.root.after(0, lambda: self.notebook.tab(0, state="normal"))
            self.root.after(0, lambda: self.clear_console_btn.config(state="normal"))
            self.root.after(0, lambda: self.generate_frames_btn.config(state="normal"))

    def redirect_stdout_to_console(self):
        console_widget = self.console_text

        stdout_writer = type(
            "StdoutWriter",
            (object,),
            {
                "write": lambda self, text: (
                    console_widget.config(state="normal"),
                    console_widget.insert(tk.END, text),
                    console_widget.see(tk.END),
                    console_widget.config(state="disabled"),
                    console_widget.update_idletasks(),
                ),
                "flush": lambda self: None,
            },
        )()

        sys.stdout = stdout_writer


# ----------------Entry Point----------------

if __name__ == "__main__":
    root = tk.Tk()
    ObjectStudioGUI(root)
    root.mainloop()
