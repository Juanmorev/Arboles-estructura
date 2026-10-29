"""Employee data class."""


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
