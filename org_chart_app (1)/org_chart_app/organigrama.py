"""Organigrama Empresarial - Taller de Arboles (Estructura de Datos).

Archivo unico: abrirlo en Visual Studio Code y presionar "Run" (el boton de play).
Si falta customtkinter, se instala solo la primera vez.
Codigo en ingles, interfaz en espanol. Arbol n-ario de empleados.
"""
import importlib.util
import json
import os
import subprocess
import sys

if importlib.util.find_spec("tkinter") is None:
    print("Error: Tkinter no esta instalado.\n"
          "  Windows/Mac: reinstale Python desde python.org.\n"
          "  Linux: sudo apt install python3-tk")
    sys.exit(1)
if importlib.util.find_spec("customtkinter") is None:
    print("Instalando customtkinter (solo la primera vez)...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "customtkinter"])

import tkinter as tk
from collections import deque
from tkinter import messagebox, ttk

import customtkinter as ctk


# ======================================================================
# models/employee.py
# ======================================================================
class Employee:
    """Holds the personal and job information of one employee."""

    def __init__(self, employee_id, name, position, department, salary):
        self.employee_id = employee_id
        self.name = name
        self.position = position
        self.department = department
        self.salary = salary

    def to_dict(self):
        return {
            "id": self.employee_id,
            "name": self.name,
            "position": self.position,
            "department": self.department,
            "salary": self.salary,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            data["id"],
            data["name"],
            data["position"],
            data["department"],
            data["salary"],
        )

    def __str__(self):
        return f"{self.name} ({self.position})"


# ======================================================================
# models/org_node.py
# ======================================================================
class OrgNode:
    """A node stores one employee, a link to its parent and a list of children."""

    ROOT = "root"
    BRANCH = "branch"
    LEAF = "leaf"

    def __init__(self, employee):
        self.employee = employee
        self.parent = None
        self.children = []

    # ---- structural properties (concepts seen in class) ----
    @property
    def degree(self):
        """Number of direct children."""
        return len(self.children)

    @property
    def level(self):
        """Distance from the root. The root is level 1."""
        level = 1
        current = self.parent
        while current is not None:
            level += 1
            current = current.parent
        return level

    @property
    def is_root(self):
        return self.parent is None

    @property
    def is_leaf(self):
        return not self.children

    @property
    def node_type(self):
        if self.is_root:
            return OrgNode.ROOT
        if self.is_leaf:
            return OrgNode.LEAF
        return OrgNode.BRANCH

    @property
    def siblings(self):
        if self.parent is None:
            return []
        return [child for child in self.parent.children if child is not self]

    # ---- child management ----
    def add_child(self, node):
        node.parent = self
        self.children.append(node)

    def remove_child(self, node):
        self.children.remove(node)
        node.parent = None


# ======================================================================
# models/org_chart.py
# ======================================================================
class OrgChartError(Exception):
    """Error whose message is meant to be shown to the user (in Spanish)."""


class OrgChart:
    """General (n-ary) tree. The root is the highest authority of the company."""

    def __init__(self):
        self.root = None
        self._index = {}
        self._next_id = 1

    # ------------------------------------------------------------ queries
    def is_empty(self):
        return self.root is None

    def find_by_id(self, employee_id):
        return self._index.get(employee_id)

    def search_by_name(self, text):
        text = text.strip().lower()
        if not text:
            return []
        return [
            node for node in self.preorder()
            if text in node.employee.name.lower()
            or text in node.employee.position.lower()
        ]

    # --------------------------------------------------------- statistics
    @property
    def weight(self):
        """Total number of nodes."""
        return len(self._index)

    @property
    def height(self):
        """Number of levels of the longest path from the root to a leaf."""
        return self._height(self.root)

    def _height(self, node):
        if node is None:
            return 0
        if node.is_leaf:
            return 1
        return 1 + max(self._height(child) for child in node.children)

    @property
    def order(self):
        """Maximum number of children found in any node."""
        return max((node.degree for node in self._index.values()), default=0)

    def leaves(self):
        return [node for node in self.preorder() if node.is_leaf]

    def count_descendants(self, node):
        return sum(1 + self.count_descendants(child) for child in node.children)

    def subtree_payroll(self, node):
        total = node.employee.salary
        for child in node.children:
            total += self.subtree_payroll(child)
        return total

    def path_to_root(self, node):
        path = []
        while node is not None:
            path.append(node)
            node = node.parent
        return path

    # --------------------------------------------------------- traversals
    def preorder(self, node=None, _first=True):
        """Boss first, then each subordinate branch."""
        if _first:
            node = self.root
        if node is None:
            return
        yield node
        for child in node.children:
            yield from self.preorder(child, False)

    def postorder(self, node=None, _first=True):
        """Subordinates first, boss last."""
        if _first:
            node = self.root
        if node is None:
            return
        for child in node.children:
            yield from self.postorder(child, False)
        yield node

    def level_order(self):
        """Breadth-first: level by level."""
        if self.root is None:
            return
        queue = deque([self.root])
        while queue:
            node = queue.popleft()
            yield node
            queue.extend(node.children)

    # ---------------------------------------------------------- mutations
    def add_employee(self, name, position, department, salary, boss_id=None):
        if self.root is None:
            node = self._register(name, position, department, salary)
            self.root = node
            return node
        if boss_id is None:
            raise OrgChartError("Debe seleccionar un jefe directo para el nuevo empleado.")
        boss = self.find_by_id(boss_id)
        if boss is None:
            raise OrgChartError("El jefe seleccionado no existe.")
        node = self._register(name, position, department, salary)
        boss.add_child(node)
        return node

    def update_employee(self, employee_id, name, position, department, salary):
        node = self._require(employee_id)
        node.employee.name = name
        node.employee.position = position
        node.employee.department = department
        node.employee.salary = salary
        return node

    def remove_employee(self, employee_id, reassign_children=True):
        """Remove an employee.

        reassign_children=True  -> subordinates move up to the removed boss's boss.
        reassign_children=False -> the whole branch is removed.
        """
        node = self._require(employee_id)
        if node.is_root:
            if node.children and reassign_children:
                raise OrgChartError(
                    "No se puede reasignar los subordinados del cargo más alto. "
                    "Elimine toda la estructura o mueva primero a los empleados."
                )
            self._unregister_branch(node)
            self.root = None
            return
        parent = node.parent
        parent.remove_child(node)
        if reassign_children:
            for child in list(node.children):
                node.remove_child(child)
                parent.add_child(child)
            self._index.pop(node.employee.employee_id)
        else:
            self._unregister_branch(node)

    def move_employee(self, employee_id, new_boss_id):
        """Move an employee (with his/her branch) under another boss."""
        node = self._require(employee_id)
        new_boss = self._require(new_boss_id)
        if node.is_root:
            raise OrgChartError("El cargo más alto no se puede mover.")
        if new_boss is node or new_boss in self._descendants(node):
            raise OrgChartError("Un empleado no puede reportar a sí mismo ni a uno de sus subordinados.")
        node.parent.remove_child(node)
        new_boss.add_child(node)

    def possible_bosses(self, employee_id):
        node = self._require(employee_id)
        forbidden = set(self._descendants(node)) | {node}
        return [n for n in self.preorder() if n not in forbidden]

    def clear(self):
        self.root = None
        self._index = {}
        self._next_id = 1

    # -------------------------------------------------------- persistence
    def to_dict(self):
        return {"next_id": self._next_id, "tree": self._node_to_dict(self.root)}

    def from_dict(self, data):
        self.clear()
        self._next_id = data.get("next_id", 1)
        if data.get("tree"):
            self.root = self._node_from_dict(data["tree"])

    def _node_to_dict(self, node):
        if node is None:
            return None
        return {
            "employee": node.employee.to_dict(),
            "children": [self._node_to_dict(child) for child in node.children],
        }

    def _node_from_dict(self, data):
        node = OrgNode(Employee.from_dict(data["employee"]))
        self._index[node.employee.employee_id] = node
        for child_data in data["children"]:
            node.add_child(self._node_from_dict(child_data))
        return node

    # ------------------------------------------------------------ helpers
    def _register(self, name, position, department, salary):
        employee = Employee(self._next_id, name, position, department, salary)
        self._next_id += 1
        node = OrgNode(employee)
        self._index[employee.employee_id] = node
        return node

    def _unregister_branch(self, node):
        for current in list(self.preorder(node, False)):
            self._index.pop(current.employee.employee_id, None)

    def _descendants(self, node):
        return list(self.preorder(node, False))[1:]

    def _require(self, employee_id):
        node = self.find_by_id(employee_id)
        if node is None:
            raise OrgChartError("El empleado seleccionado no existe.")
        return node


# ======================================================================
# controllers/org_chart_controller.py
# ======================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_PATH = os.path.join(BASE_DIR, "data", "organigrama.json")

NODE_TYPE_LABELS = {
    OrgNode.ROOT: "Raíz (máxima autoridad)",
    OrgNode.BRANCH: "Rama (jefe intermedio)",
    OrgNode.LEAF: "Hoja (sin subordinados)",
}


def format_money(value):
    """Format a number as Colombian pesos: $1.500.000"""
    return "$" + f"{value:,.0f}".replace(",", ".")


class OrgChartController:
    """Validates user input, calls the model and handles file persistence."""

    def __init__(self, data_path=DEFAULT_DATA_PATH):
        self.chart = OrgChart()
        self.data_path = data_path
        if os.path.exists(self.data_path):
            try:
                self.load()
            except (OSError, ValueError, KeyError):
                self.load_sample()
        else:
            self.load_sample()

    # ------------------------------------------------------------ actions
    def add_employee(self, name, position, department, salary_text, boss_id):
        name, position, department, salary = self._validate(name, position, department, salary_text)
        node = self.chart.add_employee(name, position, department, salary, boss_id)
        self.save()
        return node

    def update_employee(self, employee_id, name, position, department, salary_text):
        name, position, department, salary = self._validate(name, position, department, salary_text)
        node = self.chart.update_employee(employee_id, name, position, department, salary)
        self.save()
        return node

    def remove_employee(self, employee_id, reassign_children):
        self.chart.remove_employee(employee_id, reassign_children)
        self.save()

    def move_employee(self, employee_id, new_boss_id):
        self.chart.move_employee(employee_id, new_boss_id)
        self.save()

    def possible_bosses(self, employee_id):
        return self.chart.possible_bosses(employee_id)

    def search(self, text):
        return self.chart.search_by_name(text)

    def get_node(self, employee_id):
        return self.chart.find_by_id(employee_id)

    # ------------------------------------------------------------ reports
    def get_details(self, employee_id):
        node = self.chart.find_by_id(employee_id)
        if node is None:
            return None
        employee = node.employee
        return {
            "employee": employee,
            "type": NODE_TYPE_LABELS[node.node_type],
            "level": node.level,
            "degree": node.degree,
            "boss": node.parent.employee if node.parent else None,
            "siblings": [s.employee for s in node.siblings],
            "subordinates": [c.employee for c in node.children],
            "descendants": self.chart.count_descendants(node),
            "branch_payroll": self.chart.subtree_payroll(node),
            "path": [n.employee for n in reversed(self.chart.path_to_root(node))],
        }

    def get_statistics(self):
        chart = self.chart
        return {
            "weight": chart.weight,
            "height": chart.height,
            "order": chart.order,
            "leaves": len(chart.leaves()),
            "payroll": chart.subtree_payroll(chart.root) if chart.root else 0,
        }

    def get_traversal(self, kind):
        generators = {
            "preorder": self.chart.preorder,
            "postorder": self.chart.postorder,
            "level": self.chart.level_order,
        }
        return [node.employee for node in generators[kind]()]

    # -------------------------------------------------------- persistence
    def save(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, "w", encoding="utf-8") as file:
            json.dump(self.chart.to_dict(), file, ensure_ascii=False, indent=2)

    def load(self):
        with open(self.data_path, "r", encoding="utf-8") as file:
            self.chart.from_dict(json.load(file))

    def clear_all(self):
        self.chart.clear()
        self.save()

    def load_sample(self):
        """Load an example company so the app is not empty the first time."""
        chart = self.chart
        chart.clear()
        ceo = chart.add_employee("Carlos Ramírez", "Gerente General", "Dirección", 15000000)
        tech = chart.add_employee("Laura Gómez", "Directora de Tecnología", "Tecnología", 9000000, ceo.employee.employee_id)
        fin = chart.add_employee("Andrés Torres", "Director Financiero", "Finanzas", 8500000, ceo.employee.employee_id)
        hr = chart.add_employee("Marcela Díaz", "Directora de Talento Humano", "Recursos Humanos", 7500000, ceo.employee.employee_id)
        dev = chart.add_employee("Julián Pérez", "Líder de Desarrollo", "Tecnología", 6000000, tech.employee.employee_id)
        infra = chart.add_employee("Sofía Herrera", "Líder de Infraestructura", "Tecnología", 5800000, tech.employee.employee_id)
        chart.add_employee("Daniel Castro", "Desarrollador Backend", "Tecnología", 4200000, dev.employee.employee_id)
        chart.add_employee("Valentina Ruiz", "Desarrolladora Frontend", "Tecnología", 4000000, dev.employee.employee_id)
        chart.add_employee("Miguel Ángel Soto", "Administrador de Redes", "Tecnología", 3800000, infra.employee.employee_id)
        acc = chart.add_employee("Paula Moreno", "Contadora", "Finanzas", 5000000, fin.employee.employee_id)
        chart.add_employee("Esteban Vargas", "Auxiliar Contable", "Finanzas", 2500000, acc.employee.employee_id)
        chart.add_employee("Camila Rojas", "Analista de Selección", "Recursos Humanos", 3500000, hr.employee.employee_id)
        self.save()

    # ------------------------------------------------------------ helpers
    @staticmethod
    def _validate(name, position, department, salary_text):
        name, position, department = name.strip(), position.strip(), department.strip()
        if not name or not position or not department:
            raise OrgChartError("El nombre, el cargo y el departamento son obligatorios.")
        try:
            salary = float(salary_text.replace(".", "").replace(",", ".").replace("$", "").strip())
        except ValueError:
            raise OrgChartError("El salario debe ser un número válido (ejemplo: 3500000).")
        if salary < 0:
            raise OrgChartError("El salario no puede ser negativo.")
        return name, position, department, salary


# ======================================================================
# views/org_canvas.py
# ======================================================================
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


# ======================================================================
# views/dialogs.py
# ======================================================================
class EmployeeDialog(ctk.CTkToplevel):
    """Form to create or edit an employee. `result` is None if cancelled."""

    def __init__(self, master, title, employee=None, boss_text=None):
        super().__init__(master)
        self.title(title)
        self.geometry("420x440")
        self.resizable(False, False)
        self.result = None

        ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(18, 4))
        if boss_text:
            ctk.CTkLabel(self, text=boss_text, text_color="gray40").pack(pady=(0, 8))

        self.entries = {}
        fields = [
            ("name", "Nombre completo"),
            ("position", "Cargo"),
            ("department", "Departamento"),
            ("salary", "Salario mensual (COP)"),
        ]
        for key, label in fields:
            ctk.CTkLabel(self, text=label, anchor="w").pack(fill="x", padx=36, pady=(6, 0))
            entry = ctk.CTkEntry(self, height=34)
            entry.pack(fill="x", padx=36)
            self.entries[key] = entry

        if employee is not None:
            self.entries["name"].insert(0, employee.name)
            self.entries["position"].insert(0, employee.position)
            self.entries["department"].insert(0, employee.department)
            self.entries["salary"].insert(0, str(int(employee.salary)))

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(pady=22)
        ctk.CTkButton(buttons, text="Guardar", width=140, command=self._accept).pack(side="left", padx=8)
        ctk.CTkButton(buttons, text="Cancelar", width=140, fg_color="gray55",
                      hover_color="gray40", command=self.destroy).pack(side="left", padx=8)

        self.bind("<Return>", lambda _event: self._accept())
        self.bind("<Escape>", lambda _event: self.destroy())
        self.after(150, self._focus)

    def _focus(self):
        self.grab_set()
        self.entries["name"].focus()

    def _accept(self):
        self.result = {key: entry.get() for key, entry in self.entries.items()}
        self.destroy()


class MoveDialog(ctk.CTkToplevel):
    """Dialog to choose a new direct boss. `result` is the chosen employee id."""

    def __init__(self, master, employee_name, candidates):
        super().__init__(master)
        self.title("Cambiar de jefe")
        self.geometry("460x230")
        self.resizable(False, False)
        self.result = None
        self._options = {f"{n.employee.name}  —  {n.employee.position}": n.employee.employee_id
                         for n in candidates}

        ctk.CTkLabel(self, text=f"Nuevo jefe directo para {employee_name}",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(22, 10))
        self.combo = ctk.CTkComboBox(self, values=list(self._options), width=380, state="readonly")
        self.combo.pack(pady=8)
        if self._options:
            self.combo.set(next(iter(self._options)))

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(pady=22)
        ctk.CTkButton(buttons, text="Mover", width=140, command=self._accept).pack(side="left", padx=8)
        ctk.CTkButton(buttons, text="Cancelar", width=140, fg_color="gray55",
                      hover_color="gray40", command=self.destroy).pack(side="left", padx=8)
        self.after(150, self.grab_set)

    def _accept(self):
        self.result = self._options.get(self.combo.get())
        self.destroy()


# ======================================================================
# views/main_window.py
# ======================================================================
class MainWindow(ctk.CTk):
    """Left: actions. Center: tree views. Right: details and statistics."""

    def __init__(self, controller):
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.controller = controller
        self.selected_id = None

        self.title("Organigrama Empresarial — Estructura de Datos: Árboles")
        self.geometry("1280x760")
        self.minsize(1100, 640)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_center()
        self._build_right_panel()
        self._build_status_bar()
        self.refresh()

    # ============================================================ building
    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        ctk.CTkLabel(sidebar, text="🏢 Organigrama", font=ctk.CTkFont(size=22, weight="bold")
                     ).pack(pady=(24, 2), padx=16)
        ctk.CTkLabel(sidebar, text="Árbol n-ario de empleados", text_color="gray40"
                     ).pack(pady=(0, 18))

        actions = [
            ("➕  Agregar empleado", self.on_add, None),
            ("✏️  Editar seleccionado", self.on_edit, None),
            ("🔀  Cambiar de jefe", self.on_move, None),
            ("🗑️  Eliminar", self.on_delete, "#C62828"),
        ]
        for text, command, color in actions:
            kwargs = {"fg_color": color, "hover_color": "#8E0000"} if color else {}
            ctk.CTkButton(sidebar, text=text, height=38, anchor="w", command=command, **kwargs
                          ).pack(fill="x", padx=16, pady=5)

        ctk.CTkLabel(sidebar, text="Buscar", anchor="w").pack(fill="x", padx=16, pady=(20, 0))
        self.search_entry = ctk.CTkEntry(sidebar, placeholder_text="Nombre o cargo…")
        self.search_entry.pack(fill="x", padx=16, pady=4)
        self.search_entry.bind("<Return>", lambda _e: self.on_search())
        ctk.CTkButton(sidebar, text="🔍  Buscar", fg_color="gray45", hover_color="gray30",
                      command=self.on_search).pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(sidebar, text="Datos", anchor="w").pack(fill="x", padx=16, pady=(20, 0))
        ctk.CTkButton(sidebar, text="📂  Cargar ejemplo", fg_color="gray45", hover_color="gray30",
                      command=self.on_load_sample).pack(fill="x", padx=16, pady=4)
        ctk.CTkButton(sidebar, text="🧹  Vaciar todo", fg_color="gray45", hover_color="gray30",
                      command=self.on_clear).pack(fill="x", padx=16, pady=4)

    def _build_center(self):
        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        tab_list = self.tabs.add("Lista jerárquica")
        tab_graph = self.tabs.add("Diagrama del árbol")
        tab_walk = self.tabs.add("Recorridos")

        # --- hierarchical list (ttk.Treeview)
        style = ttk.Style()
        style.configure("Treeview", rowheight=30, font=("Helvetica", 11))
        style.configure("Treeview.Heading", font=("Helvetica", 11, "bold"))
        tab_list.grid_rowconfigure(0, weight=1)
        tab_list.grid_columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(tab_list, columns=("position", "department", "level"),
                                 selectmode="browse")
        self.tree.heading("#0", text="Empleado")
        self.tree.heading("position", text="Cargo")
        self.tree.heading("department", text="Departamento")
        self.tree.heading("level", text="Nivel")
        self.tree.column("#0", width=260)
        self.tree.column("position", width=220)
        self.tree.column("department", width=150)
        self.tree.column("level", width=60, anchor="center")
        scroll = ttk.Scrollbar(tab_list, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # --- diagram
        tab_graph.grid_rowconfigure(1, weight=1)
        tab_graph.grid_columnconfigure(0, weight=1)
        legend = ctk.CTkFrame(tab_graph, fg_color="transparent")
        legend.grid(row=0, column=0, sticky="w", pady=(0, 6))
        for node_type, label in [(OrgNode.ROOT, "Raíz"), (OrgNode.BRANCH, "Rama"), (OrgNode.LEAF, "Hoja")]:
            ctk.CTkLabel(legend, text="   ", fg_color=COLORS[node_type], corner_radius=4, width=22
                         ).pack(side="left", padx=(8, 4))
            ctk.CTkLabel(legend, text=label).pack(side="left")
        self.org_canvas = OrgCanvas(tab_graph, on_select=self.select_employee)
        self.org_canvas.grid(row=1, column=0, sticky="nsew")

        # --- traversals
        tab_walk.grid_rowconfigure(1, weight=1)
        tab_walk.grid_columnconfigure(0, weight=1)
        self.walk_choice = ctk.CTkSegmentedButton(
            tab_walk,
            values=["Preorden (jefe → equipo)", "Postorden (equipo → jefe)", "Por niveles"],
            command=self._on_walk_change)
        self.walk_choice.grid(row=0, column=0, pady=(0, 8))
        self.walk_choice.set("Preorden (jefe → equipo)")
        self.walk_box = ctk.CTkTextbox(tab_walk, font=ctk.CTkFont(size=14), state="disabled")
        self.walk_box.grid(row=1, column=0, sticky="nsew")

    def _build_right_panel(self):
        panel = ctk.CTkFrame(self, width=300, corner_radius=0)
        panel.grid(row=0, column=2, sticky="nsew")
        panel.grid_propagate(False)
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        self.stats_label = ctk.CTkLabel(panel, justify="left", anchor="w", text="",
                                        font=ctk.CTkFont(size=13))
        self.stats_label.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 6))

        self.details_box = ctk.CTkTextbox(panel, font=ctk.CTkFont(size=13), wrap="word",
                                          state="disabled")
        self.details_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 12))

    def _build_status_bar(self):
        self.status = ctk.CTkLabel(self, text="Listo.", anchor="w", text_color="gray30")
        self.status.grid(row=1, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 6))

    # ============================================================= refresh
    def refresh(self):
        """Redraw every view from the model."""
        chart = self.controller.chart
        if self.selected_id is not None and chart.find_by_id(self.selected_id) is None:
            self.selected_id = None

        self.tree.delete(*self.tree.get_children())
        if chart.root is not None:
            self._insert_tree_node("", chart.root)
            if self.selected_id is not None:
                self.tree.selection_set(str(self.selected_id))
                self.tree.see(str(self.selected_id))
        self.org_canvas.draw(chart.root, self.selected_id)
        self._update_stats()
        self._update_details()
        self._on_walk_change(self.walk_choice.get())

    def _insert_tree_node(self, parent_iid, node):
        employee = node.employee
        iid = str(employee.employee_id)
        self.tree.insert(parent_iid, "end", iid=iid, text=employee.name, open=True,
                         values=(employee.position, employee.department, node.level))
        for child in node.children:
            self._insert_tree_node(iid, child)

    def _update_stats(self):
        stats = self.controller.get_statistics()
        text = (
            "📊 Estadísticas del árbol\n"
            f"• Peso (empleados): {stats['weight']}\n"
            f"• Altura (niveles): {stats['height']}\n"
            f"• Orden (máx. subordinados): {stats['order']}\n"
            f"• Hojas: {stats['leaves']}\n"
            f"• Nómina total: {format_money(stats['payroll'])}"
        )
        self.stats_label.configure(text=text)

    def _update_details(self):
        details = self.controller.get_details(self.selected_id) if self.selected_id else None
        if details is None:
            text = "Seleccione un empleado en la lista o en el diagrama para ver sus detalles."
        else:
            e = details["employee"]
            names = lambda people: ", ".join(p.name for p in people) or "—"
            text = (
                f"👤 {e.name}\n"
                f"Cargo: {e.position}\n"
                f"Departamento: {e.department}\n"
                f"Salario: {format_money(e.salary)}\n\n"
                f"Tipo de nodo: {details['type']}\n"
                f"Nivel: {details['level']}\n"
                f"Grado (subordinados directos): {details['degree']}\n"
                f"Total de personas a cargo: {details['descendants']}\n"
                f"Nómina de su rama: {format_money(details['branch_payroll'])}\n\n"
                f"Jefe directo: {details['boss'].name if details['boss'] else '— (es la raíz)'}\n"
                f"Compañeros (hermanos): {names(details['siblings'])}\n"
                f"Subordinados: {names(details['subordinates'])}\n\n"
                f"Cadena de mando:\n" + "  →  ".join(p.name for p in details["path"])
            )
        self._set_text(self.details_box, text)

    def _on_walk_change(self, value):
        kinds = {"Preorden (jefe → equipo)": "preorder",
                 "Postorden (equipo → jefe)": "postorder",
                 "Por niveles": "level"}
        employees = self.controller.get_traversal(kinds[value])
        lines = [f"{i}. {e.name} — {e.position}" for i, e in enumerate(employees, 1)]
        self._set_text(self.walk_box, "\n".join(lines) or "El organigrama está vacío.")

    @staticmethod
    def _set_text(box, text):
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", text)
        box.configure(state="disabled")

    # ============================================================ selection
    def _on_tree_select(self, _event):
        selection = self.tree.selection()
        if selection:
            self.selected_id = int(selection[0])
            self.org_canvas.draw(self.controller.chart.root, self.selected_id)
            self._update_details()

    def select_employee(self, employee_id):
        """Called by the canvas when the user clicks a box."""
        self.selected_id = employee_id
        self.tree.selection_set(str(employee_id))
        self.tree.see(str(employee_id))

    def _require_selection(self):
        if self.selected_id is None:
            messagebox.showinfo("Seleccione un empleado",
                                "Primero seleccione un empleado en la lista o en el diagrama.")
            return False
        return True

    # ============================================================== actions
    def on_add(self):
        chart = self.controller.chart
        if chart.is_empty():
            boss_id, info = None, "Este empleado será la raíz (máxima autoridad)."
        else:
            if not self._require_selection():
                return
            boss = chart.find_by_id(self.selected_id).employee
            boss_id, info = boss.employee_id, f"Jefe directo: {boss.name}"
        dialog = EmployeeDialog(self, "Agregar empleado", boss_text=info)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        try:
            node = self.controller.add_employee(boss_id=boss_id, salary_text=dialog.result["salary"],
                                                name=dialog.result["name"],
                                                position=dialog.result["position"],
                                                department=dialog.result["department"])
        except OrgChartError as error:
            messagebox.showwarning("Datos no válidos", str(error))
            return
        self.selected_id = node.employee.employee_id
        self.refresh()
        self._say(f"Empleado «{node.employee.name}» agregado.")

    def on_edit(self):
        if not self._require_selection():
            return
        employee = self.controller.get_node(self.selected_id).employee
        dialog = EmployeeDialog(self, "Editar empleado", employee=employee)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        try:
            self.controller.update_employee(self.selected_id, dialog.result["name"],
                                            dialog.result["position"], dialog.result["department"],
                                            dialog.result["salary"])
        except OrgChartError as error:
            messagebox.showwarning("Datos no válidos", str(error))
            return
        self.refresh()
        self._say("Empleado actualizado.")

    def on_move(self):
        if not self._require_selection():
            return
        node = self.controller.get_node(self.selected_id)
        if node.is_root:
            messagebox.showinfo("No permitido", "El cargo más alto no tiene jefe y no se puede mover.")
            return
        dialog = MoveDialog(self, node.employee.name, self.controller.possible_bosses(self.selected_id))
        self.wait_window(dialog)
        if dialog.result is None:
            return
        try:
            self.controller.move_employee(self.selected_id, dialog.result)
        except OrgChartError as error:
            messagebox.showwarning("Movimiento no permitido", str(error))
            return
        self.refresh()
        self._say(f"{node.employee.name} ahora reporta a otro jefe.")

    def on_delete(self):
        if not self._require_selection():
            return
        node = self.controller.get_node(self.selected_id)
        name = node.employee.name
        reassign = True
        if node.children:
            total = self.controller.chart.count_descendants(node)
            if node.is_root:
                if not messagebox.askyesno(
                        "Eliminar toda la estructura",
                        f"«{name}» es la raíz y tiene {total} personas a cargo.\n"
                        "Se eliminará TODO el organigrama. ¿Continuar?"):
                    return
                reassign = False
            else:
                answer = messagebox.askyesnocancel(
                    "Eliminar empleado",
                    f"«{name}» tiene {node.degree} subordinado(s) directo(s).\n\n"
                    "SÍ  → Eliminarlo y pasar sus subordinados a su jefe directo.\n"
                    "NO  → Eliminarlo junto con toda su rama.\n"
                    "Cancelar → No hacer nada.")
                if answer is None:
                    return
                reassign = answer
        elif not messagebox.askyesno("Eliminar empleado", f"¿Eliminar a «{name}»?"):
            return
        try:
            self.controller.remove_employee(self.selected_id, reassign)
        except OrgChartError as error:
            messagebox.showwarning("No se pudo eliminar", str(error))
            return
        self.selected_id = None
        self.refresh()
        self._say(f"«{name}» eliminado.")

    def on_search(self):
        results = self.controller.search(self.search_entry.get())
        if not results:
            messagebox.showinfo("Búsqueda", "No se encontraron empleados con ese nombre o cargo.")
            return
        self.select_employee(results[0].employee.employee_id)
        self._say(f"{len(results)} resultado(s). Mostrando: {results[0].employee.name}.")

    def on_load_sample(self):
        if messagebox.askyesno("Cargar ejemplo", "Se reemplazará el organigrama actual. ¿Continuar?"):
            self.controller.load_sample()
            self.selected_id = None
            self.refresh()
            self._say("Organigrama de ejemplo cargado.")

    def on_clear(self):
        if messagebox.askyesno("Vaciar todo", "Se eliminarán todos los empleados. ¿Continuar?"):
            self.controller.clear_all()
            self.selected_id = None
            self.refresh()
            self._say("Organigrama vaciado.")

    def _say(self, message):
        self.status.configure(text=message)


# ======================================================================
# main
# ======================================================================
def main():
    controller = OrgChartController()
    app = MainWindow(controller)
    app.mainloop()


if __name__ == "__main__":
    main()
