"""GUI application for AnimeUnityDownloader.

This module provides a graphical user interface using tkinter that allows users to:
- Input the anime URL
- Specify starting and ending episode numbers
- Choose the download directory
- Start the download process

Usage:
    Run this script directly: python gui.py
"""

from __future__ import annotations

import asyncio
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from anime_downloader import process_anime_download


class AnimeDownloaderGUI:
    """GUI application for downloading anime episodes."""

    def __init__(self, root: tk.Tk) -> None:
        """Initialize the GUI application."""
        self.root = root
        self.root.title("AnimeUnity Downloader")
        self.root.resizable(False, False)

        # Default download path
        self.download_path = str(Path.cwd() / "Downloads")

        self._create_widgets()
        self._layout_widgets()
        self._fit_window_to_content()

    def _create_widgets(self) -> None:
        """Create all GUI widgets."""
        # Title
        title_label = tk.Label(
            self.root,
            text="AnimeUnity Downloader",
            font=("Arial", 18, "bold"),
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=20)

        # URL input
        url_label = tk.Label(self.root, text="Anime URL:", font=("Arial", 11))
        url_label.grid(row=1, column=0, sticky="e", padx=10, pady=10)

        self.url_entry = tk.Entry(self.root, width=50, font=("Arial", 10))
        self.url_entry.grid(row=1, column=1, columnspan=2, padx=10, pady=10)

        # Start episode
        start_label = tk.Label(self.root, text="Start Episode:", font=("Arial", 11))
        start_label.grid(row=2, column=0, sticky="e", padx=10, pady=10)

        self.start_entry = tk.Entry(self.root, width=20, font=("Arial", 10))
        self.start_entry.grid(row=2, column=1, sticky="w", padx=10, pady=10)
        self.start_entry.insert(0, "1")

        # End episode
        end_label = tk.Label(self.root, text="End Episode:", font=("Arial", 11))
        end_label.grid(row=3, column=0, sticky="e", padx=10, pady=10)

        self.end_entry = tk.Entry(self.root, width=20, font=("Arial", 10))
        self.end_entry.grid(row=3, column=1, sticky="w", padx=10, pady=10)
        self.end_entry.insert(0, "")

        # Download path
        path_label = tk.Label(self.root, text="Download Path:", font=("Arial", 11))
        path_label.grid(row=4, column=0, sticky="e", padx=10, pady=10)

        self.path_entry = tk.Entry(self.root, width=35, font=("Arial", 10))
        self.path_entry.grid(row=4, column=1, padx=10, pady=10)
        self.path_entry.insert(0, self.download_path)

        self.browse_button = tk.Button(
            self.root,
            text="Browse",
            command=self._browse_directory,
            font=("Arial", 10),
        )
        self.browse_button.grid(row=4, column=2, padx=5, pady=10)

        # Download button
        self.download_button = tk.Button(
            self.root,
            text="Download",
            command=self._start_download,
            font=("Arial", 12, "bold"),
            bg="#4CAF50",
            fg="white",
            width=20,
            height=2,
        )
        self.download_button.grid(row=5, column=0, columnspan=3, pady=20)

        # Status label
        self.status_label = tk.Label(
            self.root,
            text="Ready to download",
            font=("Arial", 10),
            fg="gray",
        )
        self.status_label.grid(row=6, column=0, columnspan=3, pady=10)

        # Progress bar
        self.progress_bar = ttk.Progressbar(
            self.root,
            mode="indeterminate",
            length=400,
        )

    def _layout_widgets(self) -> None:
        """Configure grid weights for responsive layout."""
        self.root.grid_columnconfigure(1, weight=1)

    def _fit_window_to_content(self) -> None:
        """Size the window to the actual content so the layout does not look half empty."""
        self.root.update_idletasks()
        width = max(self.root.winfo_reqwidth() + 20, 600)
        height = self.root.winfo_reqheight() + 10
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(width, height)

    def _browse_directory(self) -> None:
        """Open a directory browser dialog."""
        directory = filedialog.askdirectory(initialdir=self.download_path)
        if directory:
            self.download_path = directory
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, directory)

    def _validate_inputs(self) -> tuple[str, int | None, int | None]:
        """Validate user inputs and return parsed values."""
        url = self.url_entry.get().strip()
        if not url:
            raise ValueError("Please enter an anime URL")

        # Parse start episode
        start_text = self.start_entry.get().strip()
        start_episode = int(start_text) if start_text else None

        # Parse end episode
        end_text = self.end_entry.get().strip()
        end_episode = int(end_text) if end_text else None

        # Validate episode range
        if start_episode and end_episode and start_episode > end_episode:
            raise ValueError("Start episode must be less than or equal to end episode")

        return url, start_episode, end_episode

    def _update_status(self, message: str, color: str = "gray") -> None:
        """Update the status label."""
        self.status_label.config(text=message, fg=color)

    def _enable_ui(self, enabled: bool = True) -> None:
        """Enable or disable UI elements during download."""
        state = "normal" if enabled else "disabled"
        self.url_entry.config(state=state)
        self.start_entry.config(state=state)
        self.end_entry.config(state=state)
        self.path_entry.config(state=state)
        self.browse_button.config(state=state)
        self.download_button.config(state=state)

        if not enabled:
            self.progress_bar.grid(row=7, column=0, columnspan=3, pady=10)
            self.progress_bar.start(10)
        else:
            self.progress_bar.stop()
            self.progress_bar.grid_remove()

    async def _download_async(
        self,
        url: str,
        start_episode: int | None,
        end_episode: int | None,
    ) -> None:
        """Perform the actual download asynchronously."""
        try:
            # Temporarily change working directory to download path
            import os
            original_dir = os.getcwd()
            os.chdir(self.download_path)

            await process_anime_download(url, start_episode, end_episode)

            # Restore original directory
            os.chdir(original_dir)

            self.root.after(
                0,
                lambda: self._update_status("Download completed!", "green"),
            )
            self.root.after(
                0,
                lambda: messagebox.showinfo("Success", "Download completed successfully!"),
            )

        except Exception as e:
            self.root.after(
                0,
                lambda: self._update_status(f"Error: {e}", "red"),
            )
            self.root.after(
                0,
                lambda: messagebox.showerror("Error", f"Download failed: {e}"),
            )

        finally:
            self.root.after(0, lambda: self._enable_ui(True))

    def _run_download_thread(
        self,
        url: str,
        start_episode: int | None,
        end_episode: int | None,
    ) -> None:
        """Run the download in a separate thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._download_async(url, start_episode, end_episode))
        loop.close()

    def _start_download(self) -> None:
        """Start the download process."""
        try:
            url, start_episode, end_episode = self._validate_inputs()

            # Update UI
            self._enable_ui(False)
            episode_range = f"{start_episode or 1} to {end_episode or 'end'}"
            self._update_status(f"Downloading episodes {episode_range}...", "blue")

            # Start download in a separate thread
            thread = threading.Thread(
                target=self._run_download_thread,
                args=(url, start_episode, end_episode),
                daemon=True,
            )
            thread.start()

        except ValueError as e:
            messagebox.showerror("Input Error", str(e))
            self._update_status("Ready to download", "gray")


def main() -> None:
    """Run the GUI application."""
    root = tk.Tk()
    AnimeDownloaderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
