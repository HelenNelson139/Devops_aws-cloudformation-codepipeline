"""
Creates a pkg_resources compatibility shim.
Taskcat imports pkg_resources (from setuptools) but in some Python 3.11
environments it is missing. This shim provides the subset taskcat needs.
"""
import pathlib
import sys

site_packages = pathlib.Path(next(p for p in sys.path if "site-packages" in p))
shim_dir = site_packages / "pkg_resources"
shim_dir.mkdir(exist_ok=True)

shim_code = '''\
import importlib.metadata as _m

class _Dist:
    def __init__(self, name):
        try:
            self.version = _m.version(name)
        except Exception:
            self.version = "0.0.0"
        self.project_name = name

def get_distribution(name):
    return _Dist(name)

def require(requirements):
    pass

class _WorkingSet:
    def require(self, requirements):
        pass

working_set = _WorkingSet()
'''

(shim_dir / "__init__.py").write_text(shim_code)
print(f"pkg_resources shim created at {shim_dir}")
