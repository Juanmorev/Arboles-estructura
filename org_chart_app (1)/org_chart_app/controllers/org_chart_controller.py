"""Controller: connects the views with the OrgChart model."""
import json
import os

from models.org_chart import OrgChart, OrgChartError
from models.org_node import OrgNode

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
