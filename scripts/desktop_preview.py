"""Render the installed native workbench in its two primary UX modes for CI review."""

from __future__ import annotations

import tkinter as tk

from ac.gui.desktop import DesktopWorkbench


def main() -> None:
    root = tk.Tk()
    app = DesktopWorkbench(root)

    # Show a useful, reproducible conjecture and its computed result first.
    root.after(350, app.load_example)
    root.after(500, app.run)

    # Then capture the separate visual explanation of the prefix-lift example.
    def show_transform() -> None:
        app._show_view("transform")
        app.apply_transform()

    root.after(3800, show_transform)
    root.after(7500, root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
