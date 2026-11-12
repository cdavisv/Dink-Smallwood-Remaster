"""New-material graph builder successor: explicit required usage before saving."""
from native_material_builder_v11 import build_graph as build_original_graph
from native_material_usage_v12 import apply_required_usage


def build_graph(U,material,recipe,textures,masked,guard):
    result=build_original_graph(U,material,recipe,textures,masked,guard)
    result['required_usage']=apply_required_usage(U,material,recipe,guard)
    return result
