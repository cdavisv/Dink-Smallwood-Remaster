"""Blender CPU-only source repair/inspection. No Unreal imports, exports or activation.

blender -b -noaudio -t 2 --python repair_gable.py -- --project-root PROJECT --output DISPOSABLE/Candidate.blend
blender -b -noaudio -t 2 --python repair_gable.py -- --inspect CANDIDATE --report DISPOSABLE/report.json
"""
import argparse,hashlib,json,os,struct,sys,traceback
from pathlib import Path
import bpy
from mathutils import Vector
SOURCE_SHA='d7a42dd31f79a63953df9f2e2593c40f3db70a60e3682cd23fde43ff32a8c6d9'
SOURCE_REL='SourceAssets/Art/Stonebrook/Refinements/InteriorRoofSharedV1/InteriorRoof_Shared2mCandidate.blend'
GABLES=tuple('SM_IndoorRoof_Gable_'+side+'_01' for side in ('EN','ES','WN','WS'))

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def mesh_signature(obj):
    m=obj.data;h=hashlib.sha256();h.update(str(tuple(tuple(x)for x in obj.matrix_world)).encode());h.update(str([x.name for x in m.materials]).encode())
    for v in m.vertices:h.update(struct.pack('<3f',*v.co))
    for p in m.polygons:h.update(str((tuple(p.vertices),p.material_index)).encode())
    for uv in m.uv_layers:
        h.update(uv.name.encode())
        for v in uv.data:h.update(struct.pack('<2f',*v.uv))
    for n in m.corner_normals:h.update(struct.pack('<3f',*n.vector))
    return h.hexdigest()
def inspect():
    meshes={o.name:mesh_signature(o)for o in bpy.data.objects if o.type=='MESH'};dependencies=[]
    for image in bpy.data.images:
        if image.source in {'GENERATED','VIEWER'}:continue
        packed=list(image.packed_files);path=bpy.path.abspath(image.filepath)
        dependencies.append(dict(name=image.name,source=image.source,filepath=image.filepath,packed=bool(packed),packed_sha256=[hashlib.sha256(x.packed_file.data).hexdigest()for x in packed],size=list(image.size),colorspace=image.colorspace_settings.name,external_file_required=not bool(packed),external_exists=Path(path).is_file()))
    libraries=[lib.filepath for lib in bpy.data.libraries]
    return dict(mesh_signatures=meshes,mesh_count=len(meshes),UCX_count=sum(n.startswith('UCX_')for n in meshes),image_dependencies=dependencies,linked_libraries=libraries,scope='Source inspection; not native/import/collision acceptance')
def readonly_load(path):bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
def write_new(path,data):
    with path.open('x')as stream:json.dump(data,stream,indent=2);stream.write('\n')
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--project-root',type=Path);ap.add_argument('--output',type=Path);ap.add_argument('--inspect',type=Path);ap.add_argument('--report',type=Path)
    args=ap.parse_args(sys.argv[sys.argv.index('--')+1:]if '--'in sys.argv else [])
    if args.inspect:
        if not args.report or args.output or args.project_root:raise ValueError('Inspection requires only --inspect and new --report')
        path=args.inspect.resolve(strict=True);report=args.report.resolve();report.parent.mkdir(parents=True,exist_ok=True)
        if report.exists()or report==path:raise ValueError('Preserve existing inspection outputs')
        digest=sha(path);readonly_load(path);data=inspect();data.update(source_sha256=digest,source_bytes_unchanged=sha(path)==digest);write_new(report,data);return
    if not args.project_root or not args.output or args.report:raise ValueError('Repair requires --project-root and --output only')
    project=args.project_root.resolve(strict=True);source=project/SOURCE_REL;output=args.output.resolve();bundle=Path(__file__).resolve().parents[1]
    for protected in (project,bundle):
        if output.is_relative_to(protected)or protected.is_relative_to(output.parent):raise ValueError('Output must be disposable and separate from project/source bundle')
    if output.suffix!='.blend'or output.exists()or(output.parent.exists()and any(output.parent.iterdir())):raise ValueError('New blend and empty disposable output directory required')
    if sha(source)!=SOURCE_SHA:raise ValueError('Frozen original source payload differs; hydrate its LFS object explicitly')
    output.parent.mkdir(parents=True,exist_ok=True);readonly_load(source);before=inspect();changed=[]
    if before['mesh_count']!=328 or before['UCX_count']!=312:raise ValueError('Frozen source membership differs')
    for name in GABLES:
        obj=bpy.data.objects[name];m=obj.data;old=[v.co.copy()for v in m.vertices];normals=[n.vector.copy()for n in m.corner_normals];sign=1 if '_E'in name else -1;inner=7.3575;outer=7.5175;scale=(outer-inner-.02)/(outer-inner);count=0
        for v in m.vertices:
            world=obj.matrix_world@v.co;x=sign*world.x
            if x>=inner-1e-5:world.x=sign*(outer-(outer-x)*scale);v.co=obj.matrix_world.inverted()@world;count+=1
        restored=[]
        for loop,n in zip(m.loops,normals):
            if sign*(obj.matrix_world@old[loop.vertex_index]).x>=inner-1e-5:n=Vector((n.x/scale,n.y,n.z)).normalized()
            restored.append(n)
        m.normals_split_custom_set(restored);m.update()
        moved=sum(v.co!=p for v,p in zip(m.vertices,old))
        if count!=102 or moved!=93 or any(v.co.y!=p.y or v.co.z!=p.z for v,p in zip(m.vertices,old)):raise ValueError('Bounded cap repair differs')
        changed.append(dict(object=name,selected_cap_vertices=count,moved_vertices=moved,depth_m=.02,cap_x_scale=scale))
    after=inspect()
    if set(after['mesh_signatures'])!=set(before['mesh_signatures']):raise ValueError('Mesh membership changed')
    if any(after['mesh_signatures'][n]!=h for n,h in before['mesh_signatures'].items()if n not in GABLES):raise ValueError('Unrelated mesh or UCX changed')
    bpy.ops.wm.save_as_mainfile(filepath=str(output),check_existing=False,compress=True)
    if sha(source)!=SOURCE_SHA:raise ValueError('Original input changed')
    write_new(output.with_suffix('.json'),dict(source_relative=SOURCE_REL,source_sha256=SOURCE_SHA,generated_sha256=sha(output),changed=changed,scope='Regenerated geometry from frozen source; binary blend may differ from reviewed candidate due to saved scene/light metadata',saved_only_disposable=True,native=False,source_unchanged=True,mesh_signatures_before=before['mesh_signatures'],mesh_signatures_after=after['mesh_signatures']))
if __name__=='__main__':
    try:main();print('SOURCE_RECIPE_COMPLETE',flush=True);sys.stdout.flush();sys.stderr.flush();os._exit(0)
    except BaseException:traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
