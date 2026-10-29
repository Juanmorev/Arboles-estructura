"""Canvas that draws the organization chart as a tree diagram."""
import tkinter as tk

import customtkinter as ctk

from models.org_node import OrgNode

COLORS = {
    OrgNode.ROOT: "#FFC107",    # yellow  -> root
    OrgNode.BRANCH: "#BBD3F2",  # blue    -> branch
    OrgNode.LEAF: "#8BD04F",    # green   -> leaf
}
SELECTED_BORDER = "#E53935"


class OrgCanvas(ctk.CTkFrame):
    """Draws every node as a box, connected to its boss with a line."""

    BOX_W, BOX_H = 150, 52
    H_GAP, V_GAP = 22, 58
    MARGIN = 30

    def __init__(self, master, on_select):
        super().__init__(master, fg_color="transparent")
        self.on_select = on_select
        self._positions = {}
        self._next_x = 0

        self.canvas = tk.Canvas(self, bg="white", highlightthickness=0)
        h_scroll = tk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        v_scroll = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

    def draw(self, root, selected_id=None):
        self.canvas.delete("all")
        self._positions = {}
        if root is None:
            self.canvas.create_text(200, 80, text="El organigrama está vacío.",
                                    font=("Helvetica", 14), fill="gray40")
            self.canvas.configure(scrollregion=(0, 0, 400, 160))
            return
        self._next_x = self.MARGIN
        self._layout(root, 0)
        self._draw_lines(root)
        self._draw_nodes(root, selected_id)
        bbox = self.canvas.bbox("all")
        self.canvas.configure(scrollregion=(0, 0, bbox[2] + self.MARGIN, bbox[3] + self.MARGIN))

    # --------------------------------------------------------------- layout
    def _layout(self, node, depth):
        """Leaves take the next free column; a boss is centered over its children."""
        y = self.MARGIN + depth * (self.BOX_H + self.V_GAP)
        if node.is_leaf:
            x = self._next_x
            self._next_x += self.BOX_W + self.H_GAP
        else:
            for child in node.children:
                self._layout(child, depth + 1)
            first = self._positions[child_id(node.children[0])][0]
            last = self._positions[child_id(node.children[-1])][0]
            x = (first + last) / 2
        self._positions[child_id(node)] = (x, y)

    # -------------------------------------------------------------- drawing
    def _draw_lines(self, node):
        x, y = self._positions[child_id(node)]
        for child in node.children:
            cx, cy = self._positions[child_id(child)]
            mid_y = y + self.BOX_H + self.V_GAP / 2
            start_x = x + self.BOX_W / 2
            end_x = cx + self.BOX_W / 2
            self.canvas.create_line(start_x, y + self.BOX_H, start_x, mid_y,
                                    end_x, mid_y, end_x, cy, fill="#455A64", width=2)
            self._draw_lines(child)

    def _draw_nodes(self, node, selected_id):
        x, y = self._positions[child_id(node)]
        employee = node.employee
        tag = f"emp{employee.employee_id}"
        is_selected = employee.employee_id == selected_id
        self.canvas.create_rectangle(
            x, y, x + self.BOX_W, y + self.BOX_H,
            fill=COLORS[node.node_type],
            outline=SELECTED_BORDER if is_selected else "#37474F",
            width=4 if is_selected else 1.5, tags=(tag,))
        self.canvas.create_text(x + self.BOX_W / 2, y + 17, text=self._shorten(employee.name, 20),
                                font=("Helvetica", 10, "bold"), fill="#212121", tags=(tag,))
        self.canvas.create_text(x + self.BOX_W / 2, y + 36, text=self._shorten(employee.position, 24),
                                font=("Helvetica", 8), fill="#37474F", tags=(tag,))
        self.canvas.tag_bind(tag, "<Button-1>",
                             lambda _e, emp_id=employee.employee_id: self.on_select(emp_id))
        for child in node.children:
            self._draw_nodes(child, selected_id)

    @staticmethod
    def _shorten(text, limit):
        return text if len(text) <= limit else text[: limit - 1] + "…"


def child_id(node):
    return node.employee.employee_id
