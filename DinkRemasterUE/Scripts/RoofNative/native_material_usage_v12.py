"""Explicit role-required usage; mutation only for caller-owned NEW materials."""


def require(ok,message):
    if not ok:raise ValueError(message)


def usages(U,recipe):
    names=recipe['required_usage'];require(isinstance(names,list) and len(names)==len(set(names)),'Usage requirements ambiguous')
    require(set(names)<={'MATUSAGE_NANITE'},'Unreviewed usage requirement')
    result={}
    for name in names:
        value=getattr(U.MaterialUsage,name,None);require(value is not None,'Required actual MaterialUsage enum unavailable: '+name);result[name]=value
    return result


def inspect_required_usage(U,material,recipe):
    getter=getattr(U.MaterialEditingLibrary,'has_material_usage',None);require(callable(getter),'Read-only usage getter unavailable')
    observed={name:bool(getter(material,value)) for name,value in usages(U,recipe).items()}
    require(all(observed.values()),'Saved material missing required usage: '+str(observed))
    return dict(required=observed,scope='Read-only HasMaterialUsage/GetUsageByFlag values; actual cooked shader permutations/rendering remain separate proof.')


def apply_required_usage(U,material,recipe,guard):
    require(callable(guard),'Mutation guard required');required=usages(U,recipe);E=U.MaterialEditingLibrary
    setter=getattr(E,'set_base_material_usage',None);require(callable(setter),'Explicit SetBaseMaterialUsage API unavailable')
    for value in required.values():
        guard();setter(material,value,True)
    if required:
        guard();E.recompile_material(material)
    return inspect_required_usage(U,material,recipe)
