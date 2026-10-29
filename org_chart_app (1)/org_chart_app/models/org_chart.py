"""Organization chart: an n-ary tree of employees."""
from collections import deque

from models.employee import Employee
from models.org_node import OrgNode


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
