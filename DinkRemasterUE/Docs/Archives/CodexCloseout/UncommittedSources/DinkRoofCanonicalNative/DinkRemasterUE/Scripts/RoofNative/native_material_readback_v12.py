"""Read-only graph plus required-usage verification for imported/saved materials."""
from native_material_readback_v11 import inspect_graph as inspect_original_graph
from native_material_usage_v12 import inspect_required_usage


def inspect_graph(U,material,recipe,masked):
    result=inspect_original_graph(U,material,recipe,masked)
    result['required_usage']=inspect_required_usage(U,material,recipe)
    return result
