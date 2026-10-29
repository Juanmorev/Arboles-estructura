"""Entry point of the Organization Chart application.

Run with:  python main.py
If CustomTkinter is missing, it is installed automatically.
"""
import importlib.util
import subprocess
import sys


def ensure_dependencies():
    """Install customtkinter automatically when it is not available."""
    if importlib.util.find_spec("tkinter") is None:
        print("Error: Tkinter no está instalado.\n"
              "  Windows/Mac: reinstale Python desde python.org marcando 'tcl/tk'.\n"
              "  Linux: sudo apt install python3-tk")
        sys.exit(1)
    if importlib.util.find_spec("customtkinter") is None:
        print("Instalando customtkinter (solo la primera vez)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "customtkinter"])


def main():
    ensure_dependencies()
    from controllers.org_chart_controller import OrgChartController
    from views.main_window import MainWindow

    controller = OrgChartController()
    app = MainWindow(controller)
    app.mainloop()


if __name__ == "__main__":
    main()
