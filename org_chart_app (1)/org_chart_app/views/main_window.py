"""Main window of the application (UI text is in Spanish)."""
import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from controllers.org_chart_controller import format_money
from models.org_chart import OrgChartError
from views.dialogs import EmployeeDialog, MoveDialog
from views.org_canvas import COLORS, OrgCanvas
from models.org_node import OrgNode


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
