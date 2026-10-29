"""Modal dialogs used by the main window."""
import customtkinter as ctk


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
