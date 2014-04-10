from django.utils.importlib import import_module

def get_module_attr(module, attr, fallback=None):
    m = import_module(module)
    return getattr(m, attr, fallback)
