"""Node of the n-ary tree used by the organization chart."""


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
