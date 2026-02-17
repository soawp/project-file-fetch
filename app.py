#!/usr/bin/env python3
"""
Desktop GUI for Rentman Project File Fetch.
Enter a project ID → see equipment & serial numbers in a table.
"""

import os
import logging
import re
import shutil
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import customtkinter as ctk
from dotenv import load_dotenv

from request_api import RentmanClient

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

RENTMAN_TOKEN = os.getenv("RENTMAN_TOKEN", "")

# ── Theme ────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ── Global Treeview style (applied once) ─────────────────────────────
_style_applied = False


def _apply_treeview_style():
    global _style_applied
    if _style_applied:
        return
    _style_applied = True
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "Dark.Treeview",
        background="#1a1d27",
        foreground="#e4e4e7",
        fieldbackground="#1a1d27",
        borderwidth=0,
        rowheight=30,
        font=("Helvetica", 12),
    )
    style.configure(
        "Dark.Treeview.Heading",
        background="#2a2d3a",
        foreground="#9ca3af",
        font=("Helvetica", 12, "bold"),
        borderwidth=0,
        padding=(8, 6),
    )
    style.map(
        "Dark.Treeview",
        background=[("selected", "#6c63ff")],
        foreground=[("selected", "#ffffff")],
    )
    style.layout("Dark.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])


class ScrollableTable(ctk.CTkFrame):
    """Searchable, scrollable data-table built on tkinter Treeview."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        _apply_treeview_style()

        # ── Search bar ───────────────────────────────────────────────
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self.search_var,
            placeholder_text="Search…",
            width=300,
            height=32,
        )
        self.search_entry.pack(side="left")
        self.search_var.trace_add("write", lambda *_: self._filter())

        self.count_label = ctk.CTkLabel(
            search_frame, text="", font=ctk.CTkFont(size=12), text_color="#6b7280"
        )
        self.count_label.pack(side="left", padx=(12, 0))

        # ── Treeview ─────────────────────────────────────────────────
        self.tree = ttk.Treeview(self, style="Dark.Treeview", show="headings")

        vsb = ctk.CTkScrollbar(self, orientation="vertical", command=self.tree.yview)
        hsb = ctk.CTkScrollbar(self, orientation="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")
        hsb.grid(row=2, column=0, sticky="ew")

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._columns: list[str] = []
        self._all_rows: list[list[str]] = []

    def load(self, rows: list[dict], columns: list[str] | None = None):
        """Populate the table. Optionally restrict to *columns*."""
        self.tree.delete(*self.tree.get_children())
        self._all_rows.clear()
        self.search_var.set("")

        if not rows:
            self.tree["columns"] = ()
            self._columns = []
            self.count_label.configure(text="")
            return

        # Decide which columns to show
        if columns:
            self._columns = [c for c in columns if c in rows[0]]
        else:
            self._columns = list(rows[0].keys())

        self.tree["columns"] = self._columns
        for col in self._columns:
            display = col.replace("_", " ").title()
            self.tree.heading(col, text=display, anchor="w")
            self.tree.column(col, anchor="w", width=200, minwidth=80, stretch=True)

        # Store rows for filtering
        for row in rows:
            values = [str(row.get(c, "")) for c in self._columns]
            self._all_rows.append(values)

        self._insert_rows(self._all_rows)

    def _insert_rows(self, rows: list[list[str]]):
        self.tree.delete(*self.tree.get_children())
        for i, values in enumerate(rows):
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert("", "end", values=values, tags=(tag,))
        self.tree.tag_configure("even", background="#1a1d27")
        self.tree.tag_configure("odd", background="#1f2231")
        self.count_label.configure(text=f"{len(rows)} rows")

    def _filter(self):
        query = self.search_var.get().strip().lower()
        if not query:
            self._insert_rows(self._all_rows)
            return
        filtered = [
            row for row in self._all_rows
            if any(query in cell.lower() for cell in row)
        ]
        self._insert_rows(filtered)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Project File Fetch")
        self.geometry("1100x700")
        self.minsize(700, 420)

        # ── Top bar ──────────────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(20, 8))

        ctk.CTkLabel(
            top, text="Project File Fetch", font=ctk.CTkFont(size=22, weight="bold")
        ).pack(side="left")

        # ── Input row ────────────────────────────────────────────────
        input_row = ctk.CTkFrame(self, fg_color="transparent")
        input_row.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(input_row, text="Project ID:", font=ctk.CTkFont(size=14)).pack(
            side="left", padx=(0, 8)
        )

        self.project_entry = ctk.CTkEntry(
            input_row, width=200, placeholder_text="e.g. 123"
        )
        self.project_entry.pack(side="left", padx=(0, 10))
        self.project_entry.bind("<Return>", lambda _: self._on_fetch())

        self.fetch_btn = ctk.CTkButton(
            input_row, text="Fetch", width=100, command=self._on_fetch
        )
        self.fetch_btn.pack(side="left")

        self.status_label = ctk.CTkLabel(
            input_row, text="", font=ctk.CTkFont(size=12), text_color="#9ca3af"
        )
        self.status_label.pack(side="left", padx=(16, 0))

        # ── Tabs ─────────────────────────────────────────────────────
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        tab_eq = self.tabview.add("Equipment")
        tab_sn = self.tabview.add("Serial Numbers")

        self.equipment_table = ScrollableTable(tab_eq)
        self.equipment_table.pack(fill="both", expand=True)

        self.serial_table = ScrollableTable(tab_sn)
        self.serial_table.pack(fill="both", expand=True)

        # ── Folder row ───────────────────────────────────────────────
        folder_row = ctk.CTkFrame(self, fg_color="transparent")
        folder_row.pack(fill="x", padx=20, pady=(0, 6))

        ctk.CTkLabel(folder_row, text="Source Folder:", font=ctk.CTkFont(size=14)).pack(
            side="left", padx=(0, 8)
        )

        self.folder_var = ctk.StringVar()
        self.folder_entry = ctk.CTkEntry(
            folder_row, textvariable=self.folder_var, width=400,
            placeholder_text="Select a folder with files to match…",
        )
        self.folder_entry.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            folder_row, text="Browse", width=80, command=self._browse_folder
        ).pack(side="left", padx=(0, 10))

        self.copy_btn = ctk.CTkButton(
            folder_row, text="Copy Matching Files", width=160,
            fg_color="#22c55e", hover_color="#16a34a",
            command=self._on_copy,
        )
        self.copy_btn.pack(side="left")

        self.copy_status = ctk.CTkLabel(
            folder_row, text="", font=ctk.CTkFont(size=12), text_color="#9ca3af"
        )
        self.copy_status.pack(side="left", padx=(12, 0))

        # Keep serial IDs around for the copy step
        self._serial_ids: list[str] = []
        self._current_project_id: str = ""

    # ── Actions ──────────────────────────────────────────────────────

    def _on_fetch(self):
        project_id = self.project_entry.get().strip()
        if not project_id:
            messagebox.showwarning("Missing input", "Enter a project ID first.")
            return

        if not RENTMAN_TOKEN:
            messagebox.showerror(
                "No API token",
                "RENTMAN_TOKEN is not set.\n\n"
                "Add it to a .env file next to app.py:\n"
                "RENTMAN_TOKEN=your-token-here",
            )
            return

        try:
            project_id_int = int(project_id)
        except ValueError:
            messagebox.showwarning(
                "Invalid ID", f"'{project_id}' is not a valid number."
            )
            return

        # Disable button, show spinner text
        self.fetch_btn.configure(state="disabled", text="Fetching…")
        self.status_label.configure(text="Connecting to Rentman API…")

        # Run the API calls in a background thread so the UI doesn't freeze
        thread = threading.Thread(
            target=self._fetch_data, args=(project_id_int,), daemon=True
        )
        thread.start()

    def _fetch_data(self, project_id: int):
        try:
            client = RentmanClient(token=RENTMAN_TOKEN, project=project_id)

            self._set_status("Fetching equipment…")
            equipment = client.get_project_equipment()

            serial_ids = client.extract_serial_ids(equipment)
            serial_numbers = []
            if serial_ids:
                self._set_status(f"Fetching {len(serial_ids)} serial numbers…")
                serial_numbers = client.get_serial_number_info(serial_ids)

            # Update UI on main thread
            self.after(0, self._display_results, equipment, serial_numbers)

        except Exception as exc:
            logger.exception("Error fetching project data")
            self.after(
                0,
                lambda: (
                    messagebox.showerror("API Error", str(exc)),
                    self._reset_button(),
                ),
            )

    # Columns to show in each tab
    _EQ_COLUMNS = ["displayname", "name", "serial_number_ids"]
    _SN_COLUMNS = ["displayname", "qrcodes", "id"]

    def _display_results(self, equipment: list[dict], serial_numbers: list[dict]):
        self.equipment_table.load(equipment, columns=self._EQ_COLUMNS)
        self.serial_table.load(serial_numbers, columns=self._SN_COLUMNS)

        # Store all matchable identifiers for the copy feature
        self._match_values: set[str] = set()
        for sn in serial_numbers:
            for key in ("id", "qrcodes", "serial", "displayname", "ref"):
                val = sn.get(key)
                if val is None:
                    continue
                # qrcodes can be comma-separated like "F105304,R20000009413"
                for part in str(val).split(","):
                    part = part.strip()
                    if part:
                        self._match_values.add(part)
        self._match_values.discard("")
        logger.info("Built match set with %d unique values", len(self._match_values))

        parts = []
        parts.append(f"{len(equipment)} equipment items")
        parts.append(f"{len(serial_numbers)} serial numbers")
        self.status_label.configure(text="  |  ".join(parts))

        self._reset_button()
        self.tabview.set("Equipment")

    def _set_status(self, text: str):
        self.after(0, lambda: self.status_label.configure(text=text))

    def _reset_button(self):
        self.fetch_btn.configure(state="normal", text="Fetch")

    # ── Folder / Copy ────────────────────────────────────────────────

    def _browse_folder(self):
        path = filedialog.askdirectory(title="Select folder with files to match")
        if path:
            self.folder_var.set(path)

    def _on_copy(self):
        folder = self.folder_var.get().strip()
        project_id = self.project_entry.get().strip()

        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("No folder", "Select a valid source folder first.")
            return
        if not self._match_values:
            messagebox.showwarning(
                "No serial numbers",
                "Fetch a project first so there are serial numbers to match against.",
            )
            return
        if not project_id:
            messagebox.showwarning("No project", "Enter a project ID first.")
            return

        self.copy_btn.configure(state="disabled", text="Copying…")
        self.copy_status.configure(text="")

        thread = threading.Thread(
            target=self._copy_files, args=(folder, project_id), daemon=True
        )
        thread.start()

    def _copy_files(self, source_folder: str, project_id: str):
        try:
            dest_folder = os.path.join(source_folder, project_id)
            if os.path.exists(dest_folder):
                shutil.rmtree(dest_folder)
            os.makedirs(dest_folder)

            match_set = self._match_values
            logger.info("Match set has %d values", len(match_set))
            copied = 0
            scanned = 0
            unmatched_samples: list[str] = []

            for filename in os.listdir(source_folder):
                filepath = os.path.join(source_folder, filename)
                if not os.path.isfile(filepath):
                    continue
                scanned += 1
                name_no_ext = os.path.splitext(filename)[0]
                # Split on any common separator: _ - . space
                parts = re.split(r'[_\-\.\s]+', name_no_ext)
                # Check if any part of the filename matches a known value
                if any(part in match_set for part in parts) or name_no_ext in match_set:
                    shutil.copy2(filepath, os.path.join(dest_folder, filename))
                    copied += 1
                    logger.info("Copied %s → %s/", filename, dest_folder)
                elif len(unmatched_samples) < 20:
                    unmatched_samples.append(f"  {filename}  →  parts: {parts}")

            if unmatched_samples:
                logger.info("Sample UNMATCHED files:\n%s", "\n".join(unmatched_samples))

            msg = f"Done — copied {copied}/{scanned} files to {dest_folder}"
            logger.info(msg)
            self.after(
                0,
                lambda: (
                    self.copy_status.configure(text=msg),
                    self.copy_btn.configure(state="normal", text="Copy Matching Files"),
                ),
            )
        except Exception as exc:
            logger.exception("Error copying files")
            self.after(
                0,
                lambda: (
                    messagebox.showerror("Copy Error", str(exc)),
                    self.copy_btn.configure(state="normal", text="Copy Matching Files"),
                ),
            )


if __name__ == "__main__":
    app = App()
    app.mainloop()
