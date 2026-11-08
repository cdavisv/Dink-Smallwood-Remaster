"""Pure portable contracts shared by the staged importer and guarded publisher."""
import collections, hashlib, json, math, struct, zlib
from pathlib import Path

SCHEMA = 'dink-photoreal-barrel/1'
HOUSE = 'Content/Dink/Data/Art/stonebrook.json'
COUNTS = {'SM_Barrel_Oak_01': (1, 16648)}
MESH_FOLDER = '/Game/Dink/Props/Stonebrook/PhotorealBarrelV1'
MAT_FOLDER = '/Game/Dink/Materials/Stonebrook/PhotorealBarrelV1'
TEX_FOLDER = '/Game/Dink/Textures/Stonebrook/PhotorealBarrelV1'
ROLES = ('BC', 'N', 'ORM')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def inside(root, relative):
    root = Path(root).resolve()
    require(not Path(relative).is_absolute(), 'Absolute dependency: ' + str(relative))
    path = (root / relative).resolve()
    require(path.is_relative_to(root), 'Escaping dependency: ' + str(relative))
    return path


def pins(root, directory):
    root = Path(root).resolve()
    return {str(p.relative_to(root)): sha(p) for p in sorted((root / directory).rglob('*')) if p.is_file()}


def object_path(package):
    return package + '.' + package.rsplit('/', 1)[1]


def package_file(package):
    require(package.startswith('/Game/Dink/'), 'Not a Dink package')
    return 'Content/' + package.removeprefix('/Game/') + '.uasset'


def packages(plan):
    return {package_file(p) for a in plan['assets'] for p in [a['mesh'], a['material']] + list(a['textures'].values())}


def tool_pins(folder):
    return {name: sha(Path(folder) / name) for name in ('barrel_contract.py', 'import_photoreal_barrel.py', 'publish_photoreal_barrel.py', 'barrel_fbxparse.py')}


def module_pins(root):
    """Bind the owned project's actual custom module bytes; never follow DLL links."""
    root=Path(root).resolve();files=[]
    for folder in [root/'Binaries/Linux',*sorted((root/'Plugins').glob('*/Binaries/Linux'))]:
        files.extend(p for p in folder.glob('*') if p.is_file() and p.suffix in {'.so','.modules','.target'})
    require(all(not p.is_symlink() and p.resolve().is_relative_to(root) for p in files),'Custom module outside owned project')
    return {str(p.relative_to(root)):sha(p)for p in sorted(files)}


def read_native_geometry(desc, vertex_id, triangle_id):
    """Guard validity/ranges before indexed native mesh-description getters."""
    points=[]
    for i in range(desc.get_vertex_count()):
        vid=vertex_id(id_value=i);require(desc.is_vertex_valid(vid),'Unexpected sparse vertex IDs')
        v=desc.get_vertex_position(vid);p=[float(v.x),float(v.y),float(v.z)]
        require(all(math.isfinite(x)for x in p),'Nonfinite native vertex');points.append(p)
    require(points,'Empty native mesh')
    triangles=[];groups=set()
    for i in range(desc.get_triangle_count()):
        tid=triangle_id(id_value=i);require(desc.is_triangle_valid(tid),'Unexpected sparse triangle IDs')
        instances=list(desc.get_triangle_vertex_instances(tid))
        require(len(instances)==3 and all(desc.is_vertex_instance_valid(vi)for vi in instances),'Invalid native corner instances')
        corners=[]
        for vi in instances:
            vertex=desc.get_vertex_instance_vertex(vi);index=int(vertex.get_editor_property('id_value'))
            require(desc.is_vertex_valid(vertex) and 0<=index<len(points),'Invalid native corner vertex')
            uv=desc.get_vertex_instance_uv(vi,0);values=[float(uv.x),float(uv.y)]
            require(all(math.isfinite(x)for x in values),'Nonfinite native UV')
            corners.append((points[index],values,[0,0,0]))
        groups.add(int(desc.get_triangle_polygon_group(tid).get_editor_property('id_value')));triangles.append(corners)
    return points,triangles,groups


def png_rgb(path):
    """Decode noninterlaced8-bit RGB PNG using stdlib, so no Pillow dependency in UE."""
    raw = Path(path).read_bytes()
    require(raw[:8] == b'\x89PNG\r\n\x1a\n', 'Not PNG')
    offset = 8; compressed = bytearray(); header = None
    while offset < len(raw):
        length = struct.unpack_from('>I', raw, offset)[0]; kind = raw[offset+4:offset+8]
        payload = raw[offset+8:offset+8+length]
        require(zlib.crc32(kind + payload) & 0xffffffff == struct.unpack_from('>I', raw, offset+8+length)[0], 'PNG CRC')
        if kind == b'IHDR': header = struct.unpack('>IIBBBBB', payload)
        if kind == b'IDAT': compressed.extend(payload)
        offset += length + 12
        if kind == b'IEND': break
    require(header is not None and header[2]==8 and header[3]in (2,6) and header[4:]==(0,0,0), 'Expected RGB8 noninterlaced PNG')
    width, height = header[:2]; bpp=3 if header[3]==2 else 4; stride = width * bpp; decoded = zlib.decompress(compressed)
    require(len(decoded) == height * (stride + 1), 'PNG payload length')
    output = bytearray(); previous = bytearray(stride)
    for y in range(height):
        start = y*(stride+1); kind = decoded[start]; row = bytearray(decoded[start+1:start+1+stride])
        require(kind <= 4, 'PNG filter')
        if kind:
            for i in range(stride):
                left = row[i-bpp] if i >= bpp else 0; up = previous[i]; upper_left = previous[i-bpp] if i >= bpp else 0
                if kind == 1: prediction = left
                elif kind == 2: prediction = up
                elif kind == 3: prediction = (left + up)//2
                else:
                    p = left+up-upper_left; distances = (abs(p-left), abs(p-up), abs(p-upper_left))
                    prediction = (left, up, upper_left)[distances.index(min(distances))]
                row[i] = (row[i] + prediction) & 255
        output.extend(row); previous = row
    if bpp==4:
        require(all(v==255 for v in output[3::4]),'Unexpected exported alpha')
        output=bytearray(v for i,v in enumerate(output)if i%4!=3)
    return width, height, output


def validate_orm_pixels(pixels):
    require(len(pixels)%3==0 and pixels, 'Invalid ORM RGB payload')
    require(all(v==255 for v in pixels[0::3]), 'Barrel AO must be neutral255')
    metal=pixels[2::3]
    require(min(metal)==0 and max(metal)==240 and any(v>100 for v in metal), 'Barrel metallic must retain wood0 and iron0..240')
    return {'AO_R_all255':True,'metallic_min':min(metal),'metallic_max':max(metal),'metallic_texels_over100':sum(v>100 for v in metal),'wood_zero_metal_texels':sum(v==0 for v in metal)}


def load_plan(source, check_pixels=True):
    source=Path(source).resolve();frozen=json.loads((source/'final_handoff.json').read_text())
    require(frozen['status'].startswith('source candidate frozen'), 'Source not frozen')
    require(frozen['native_imported']is False and frozen['runtime_published']is False, 'Source candidate state')
    require(frozen['source_sha256']==sha(source/'PhotorealBarrelV1_Source.blend'), 'Main source drift')
    require(frozen['export_source_sha256']==sha(source/'PhotorealBarrelV1_Export.blend'), 'Export source drift')
    pinned=frozen['frozen_files']
    require({'Export/manifest.json','PhotorealBarrelV1_Source.blend','PhotorealBarrelV1_Export.blend','texture_payload_validation.json'}.issubset(pinned), 'Source manifest/blends/pixel report not pinned')
    for relative,digest in pinned.items():require(sha(inside(source,relative))==digest, 'Frozen source drift: '+relative)
    manifest=json.loads((source/'Export/manifest.json').read_text());rows=manifest['assets']
    require(len(rows)==1 and rows[0]['name']=='SM_Barrel_Oak_01', 'Expected exactly one barrel')
    row=rows[0];name=row['name'];hulls,triangles=COUNTS[name]
    require(row['content_path']==MESH_FOLDER+'/'+name, 'Unexpected mesh destination')
    require(row['source']['sha256']==frozen['export_source_sha256'], 'Manifest source not bound')
    require(row['pivot_rule']=='base_center' and row['lod_count']==1 and row['nanite']is True, 'Mesh policy')
    require(row['collision']==['UCX_SM_Barrel_Oak_01_01'], 'Original hull identity')
    require(row['tris']=={'LOD0':triangles}, 'Triangle count')
    require(row['material_slots']==['MI_Barrel_Oak_01_PhotoBaked'] and row['validation']['errors']==0 and row['validation']['forced']is False, 'Source validation/material')
    bounds=row['bounds_cm'];expected=[83.94664525985718,84.45988893508911,100.75000524520874]
    require(all(abs(x-y)<.001 for x,y in zip(bounds['size_cm'],expected)), 'Original barrel bounds')
    require(all(abs(x-y)<.001 for x,y in zip(bounds['unreal_min_cm'],[-expected[0]/2,-expected[1]/2,0])) and all(abs(x-y)<.001 for x,y in zip(bounds['unreal_max_cm'],[expected[0]/2,expected[1]/2,expected[2]])), 'Original ground-center pivot')
    texrows={t['role']:t for t in row['textures']};require(set(texrows)==set(ROLES) and len(row['textures'])==3, 'Texture roles')
    texture_files={};textures={}
    for role,texture in texrows.items():
        relative='Export/'+texture['file'];path=inside(source,relative)
        require(relative in pinned, 'Consumed texture not pinned')
        require(texture['name']=='T_'+name[3:]+'_Photo_'+role and texture['srgb']==(role=='BC') and texture['normal_green_flip']==(role=='N'), 'Texture name/color contract')
        require(texture['size']==[2048,2048], 'Texture dimensions')
        if check_pixels:
            width,height,pixels=png_rgb(path);require((width,height)==(2048,2048), 'PNG dimensions')
            if role=='ORM':validate_orm_pixels(pixels)
        texture_files[role]=relative;textures[role]=TEX_FOLDER+'/'+texture['name']
    require(all('Export/'+row['files'][f]in pinned for f in ['fbx','glb']), 'Consumed geometry not pinned')
    asset={'name':name,'old':object_path('/Game/Dink/Kits/Stonebrook/'+name),'mesh':row['content_path'],'material':MAT_FOLDER+'/MI_'+name[3:]+'_PhotoBaked','textures':textures,'texture_files':texture_files,'fbx':'Export/'+row['files']['fbx'],'glb':'Export/'+row['files']['glb'],'bounds_cm':bounds,'hulls':hulls,'triangles':triangles}
    import barrel_fbxparse as fbx
    info=fbx.inspect(inside(source,asset['fbx']));require(set(info['models'])=={name,'UCX_SM_Barrel_Oak_01_01'} and info['coord_axis']==[0,1], 'Unexpected FBX models/coordinate axis')
    clouds=source_hulls(source,asset,include_points=True)
    expected_box=sorted((x,y,z)for x in [-37.5,37.5]for y in [-37.5,37.5]for z in [0.,100.])
    require(len(clouds)==1 and sorted(tuple(p)for p in clouds[0])==expected_box, 'Original UCX75x75x100 box geometry changed')
    return {'schema':SCHEMA,'frozen_handoff_sha256':sha(source/'final_handoff.json'),'source_sha256':dict(pinned,**{'final_handoff.json':sha(source/'final_handoff.json')}),'assets':[asset]}


def rewrite_house(document, plan, from_new=False):
    """Change only the barrel asset row and decorative Barrel1/Barrel2 meshes."""
    require(document.get('schema')=='dink-art/1' and document.get('screen')==1,'House schema')
    require(len(plan['assets'])==1 and plan['assets'][0]['name']=='SM_Barrel_Oak_01','One barrel plan required')
    result=json.loads(json.dumps(document));a=plan['assets'][0];old=a['old'];new=object_path(a['mesh']);before,after=(new,old)if from_new else(old,new)
    for section,count in {'assets':1,'replacements':0,'elements':2}.items():
        rows=result[section];found=[r for r in rows if r.get('mesh')==before]
        require(len(found)==count and not any(r.get('mesh')==after for r in rows),'Unexpected '+section+' barrel reference counts')
        if section=='elements':require({r.get('name')for r in found}=={'Barrel1','Barrel2'},'Decorative barrel identities')
        for row in found:row['mesh']=after
    return result


def source_triangles(source, asset, include_authored_normals=False):
    """Canonical frozen FBX triangle corners in native cm/handedness/DirectXUV0.

    UE5.8.4 ConvertPos/ConvertDir reflectY; FbxStaticMeshImport preserves
    PolygonVertex order when populating CornerInstanceIDs/CreateTriangle. Thus
    the existing order changes RHS counterclockwise into LHS clockwise without
    an extra corner swap. UV0 independently flipsV.
    Uses the same triangulated file as the importer, avoiding differences between
    glTF and FBX quad diagonals. Installed UE FbxStaticMeshImport.cpp:758 flipsV.
    Source normals are finite/unit checked; native normal preservation is checked
    by saved import/build flags (normal values have no reflected description getter).
    """
    import barrel_fbxparse as fbx
    path=inside(source,asset['fbx']);_,top=fbx.parse(path);by={n.name:n for n in top}
    models={n.props[0]:n.props[1].split('\x00')[0]for n in by['Objects'].children if n.name=='Model'}
    geometries={n.props[0]:n for n in by['Objects'].children if n.name=='Geometry'};geometry=None
    for connection in by['Connections'].children:
        if connection.name=='C' and connection.props[0]=='OO' and connection.props[1]in geometries and models.get(connection.props[2])==asset['name']:geometry=geometries[connection.props[1]]
    require(geometry is not None,'Missing FBX render geometry')
    raw=geometry.first('Vertices').props[0];points=[[raw[i]*100,-raw[i+1]*100,raw[i+2]*100]for i in range(0,len(raw),3)]
    indices=geometry.first('PolygonVertexIndex').props[0];uvlayer=geometry.first('LayerElementUV');normal=geometry.first('LayerElementNormal');material=geometry.first('LayerElementMaterial')
    require(uvlayer.first('MappingInformationType').props==['ByPolygonVertex'] and uvlayer.first('ReferenceInformationType').props==['IndexToDirect'],'Unsupported source UV mapping')
    require(set(material.first('Materials').props[0])=={0},'Source material indices')
    uvraw=uvlayer.first('UV').props[0];uvs=[[uvraw[i],1-uvraw[i+1]]for i in range(0,len(uvraw),2)];uvid=uvlayer.first('UVIndex').props[0]
    normals=normal.first('Normals').props[0];require(all(math.isfinite(v)for v in normals),'Nonfinite source normal')
    require(all(.9<sum(v*v for v in normals[i:i+3])<1.1 for i in range(0,len(normals),3)),'Source normal length')
    require(normal.first('MappingInformationType').props==['ByPolygonVertex'],'Source normal mapping')
    normal_reference=normal.first('ReferenceInformationType').props[0]
    require(normal_reference in ('Direct','IndexToDirect'),'Source normal reference')
    normal_indices=normal.first('NormalsIndex').props[0]if normal_reference=='IndexToDirect'else list(range(len(indices)))
    require(len(normal_indices)==len(indices),'Source corner normal count')
    require(len(uvid)==len(indices),'Source corner UV count');triangles=[];face=[]
    for corner_index,index in enumerate(indices):
        vertex=-index-1 if index<0 else index;ni=normal_indices[corner_index]*3;authored=[normals[ni],-normals[ni+1],normals[ni+2]]
        face.append((points[vertex],uvs[uvid[corner_index]],authored if include_authored_normals else [0,0,0]))
        if index<0:require(len(face)==3,'FBX must already be triangulated');triangles.append(face);face=[]
    require(not face and len(triangles)==asset['triangles'],'Source FBX triangle count')
    return triangles if include_authored_normals else triangle_signature(triangles)


def triangle_signature(triangles):
    def corner(c):
        p,uv,n=c; require(all(math.isfinite(x)for x in list(p)+list(uv)+list(n)),'Nonfinite corner')
        return tuple(round(x/q)for values,q in [(p,.01),(uv,.0001),(n,.002)]for x in values)
    def cyclic(triangle):
        require(len(triangle)==3,'Triangle must have three corners')
        corners=tuple(corner(c)for c in triangle)
        # Triangle list order/start corner are arbitrary; reversal is consequential.
        return min(corners[i:]+corners[:i]for i in range(3))
    return sorted(cyclic(t)for t in triangles)


def source_hulls(source, asset, include_points=False):
    import barrel_fbxparse as fbx
    path=inside(source,asset['fbx']); info=fbx.inspect(path)
    require(info['unit_scale_factor']==100 and info['up_axis']==[2,1] and info['front_axis']==[1,-1], 'FBX units/axes')
    _,top=fbx.parse(path); by={n.name:n for n in top}; models={};geometry={};links={}
    for node in by['Objects'].children:
        if node.name=='Model': models[node.props[0]]=node.props[1].split('\x00')[0]
        if node.name=='Geometry' and node.first('Vertices'):
            raw=node.first('Vertices').props[0];geometry[node.props[0]]=[[raw[i]*100,-raw[i+1]*100,raw[i+2]*100]for i in range(0,len(raw),3)]
    for c in by['Connections'].children:
        if c.name=='C' and c.props[0]=='OO' and c.props[1]in geometry and c.props[2]in models:links[models[c.props[2]]]=geometry[c.props[1]]
    hulls=[]
    for name,m in info['models'].items():
        require(m['translation']==[0,0,0] and m['rotation']==[0,0,0] and m['scaling']==[1,1,1], 'FBX nonidentity model')
        if name.startswith('UCX_'):
            points=links[name]; validate_convex_points(points);hulls.append(points if include_points else sorted(tuple(round(x/.01)for x in p)for p in points))
    require(len(hulls)==asset['hulls'],'FBX hull count')
    return sorted(hulls,key=lambda cloud:tuple(sorted(tuple(p)for p in cloud)))


def validate_convex_points(points):
    """Reject nonfinite/duplicate/flat clouds; supporting hull planes enclose all vertices."""
    import itertools
    require(4<=len(points)<=32,'Hull point count')
    require(all(math.isfinite(x)for p in points for x in p),'Nonfinite hull')
    require(len({tuple(round(x,5)for x in p)for p in points})==len(points),'Duplicate hull points')
    def sub(a,b):return [x-y for x,y in zip(a,b)]
    def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
    def dot(a,b):return sum(x*y for x,y in zip(a,b))
    support=set(); planes=0; volume_witness=False
    for ia,ib,ic in itertools.combinations(range(len(points)),3):
        a,b,c=[points[i]for i in [ia,ib,ic]];normal=cross(sub(b,a),sub(c,a));length=math.sqrt(dot(normal,normal))
        if length<1e-7:continue
        distances=[dot(normal,sub(p,a))/length for p in points]
        if max(abs(d)for d in distances)>.001:volume_witness=True
        if min(distances)>=-.001 or max(distances)<=.001:
            support.update(i for i,d in enumerate(distances)if abs(d)<.001);planes+=1
    require(volume_witness and planes>=4 and len(support)==len(points),'Degenerate/interior-point hull')
    return True


def candidate_files(plan):
    return {str(Path(p).with_suffix(s))for p in packages(plan)for s in ('.uasset','.uexp','.ubulk')}


def require_owned_content(root):
    root=Path(root).resolve();content=root/'Content'
    require(content.is_dir() and content.resolve().is_relative_to(root),'Content is not inside owned project')
    require(not content.is_symlink() and not any(p.is_symlink()for p in content.rglob('*')),'Content symlinks are not an owned import/publication stage')


def validate_closed_indices(points, indices):
    require(indices and len(indices)%3==0,'Missing/untriangulated convex IndexData')
    require(all(isinstance(i,int) and 0<=i<len(points)for i in indices),'Convex index range')
    edges=collections.Counter();directions=collections.Counter();volume6=0
    for start in range(0,len(indices),3):
        ia,ib,ic=indices[start:start+3];require(len({ia,ib,ic})==3,'Degenerate convex triangle')
        a,b,c=[points[i]for i in [ia,ib,ic]]
        ab=[b[k]-a[k]for k in range(3)];ac=[c[k]-a[k]for k in range(3)];n=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]];length=math.sqrt(sum(v*v for v in n));require(length>1e-7,'Zero-area convex triangle')
        distances=[sum(n[k]*(p[k]-a[k])for k in range(3))/length for p in points];require(min(distances)>=-.001 or max(distances)<=.001,'Concave convex element')
        volume6+=a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0])
        for i,j in [(ia,ib),(ib,ic),(ic,ia)]:edges[tuple(sorted((i,j)))]+=1;directions[(i,j)]+=1
    require(all(count==2 for count in edges.values()),'Open/nonmanifold convex indices')
    require(all(directions[(i,j)]==directions[(j,i)] for i,j in edges),'Inconsistent convex winding')
    require(abs(volume6)>1e-6,'Zero-volume convex element')
    return True


def candidate_package_pins(root, plan):
    """Inventory exactly the approved candidate package families, including sidecars."""
    root=Path(root).resolve();scope=candidate_files(plan)
    actual={relative:sha(root/relative)for relative in sorted(scope)if (root/relative).is_file()}
    require(packages(plan).issubset(actual),'Required candidate package missing')
    return actual


def verify_candidate_packages(root, plan, imported):
    """Fail on changed/added/deleted bytes; never adopt newly observed hashes."""
    require(packages(plan).issubset(imported) and set(imported).issubset(candidate_files(plan)),'Invalid import candidate package set')
    require(candidate_package_pins(root,plan)==imported,'Candidate package set/hash drift since import')
    return dict(imported)


def verify_native_front_normals(native_triangles, source_authored_triangles, matching=None):
    """Confirm loaded clockwise geometric fronts against source faces and normals.

    These are normals computed from actual loaded triangle positions, not a claim
    to read the non-reflected native per-corner shading-normal attribute array.
    Smoothed hem shading normals need not equal their geometric face normal; their
    expected alignment is measured from the source, not assumed to be1.
    """
    def key(triangle):return triangle_signature([[(p,uv,[0,0,0])for p,uv,n in triangle]])[0]
    def unit(vector):
        length=math.sqrt(sum(v*v for v in vector));require(length>1e-10,'Degenerate front normal');return [v/length for v in vector]
    def dot(a,b):return sum(x*y for x,y in zip(a,b))
    def geometric_front(triangle):
        a,b,c=[corner[0]for corner in triangle];ca=[c[i]-a[i]for i in range(3)];ba=[b[i]-a[i]for i in range(3)]
        return unit([ca[1]*ba[2]-ca[2]*ba[1],ca[2]*ba[0]-ca[0]*ba[2],ca[0]*ba[1]-ca[1]*ba[0]])
    if matching is None:matching=match_oriented_triangles(native_triangles,source_authored_triangles)
    minimum=1.;minimum_front_agreement=1.;record=[]
    for tid,triangle in enumerate(native_triangles):
        match=matching['matches'][tid];source=source_authored_triangles[match['source_index']]
        n=unit([sum(c[2][i]for c in source)for i in range(3)]);expected_front=geometric_front(source)
        require(dot(expected_front,n)>0,'Source clockwise front disagrees with authored normal')
        front=geometric_front(triangle);alignment=dot(front,n);front_agreement=dot(front,expected_front)
        minimum=min(minimum,alignment);minimum_front_agreement=min(minimum_front_agreement,front_agreement)
        require(front_agreement>.99 and alignment>0 and abs(alignment-dot(expected_front,n))<.01,'Native clockwise front disagrees with source face/normal')
        record.append((key(source),tuple(round(v,6)for v in front)))
    require(len(native_triangles)==len(source_authored_triangles),'Front normal count')
    return {'checked_triangles':len(record),'minimum_dot_authored_source':minimum,'minimum_dot_source_geometric_front':minimum_front_agreement,'clockwise_geometric_front_sha256':canonical_hash(sorted(record)),'convention':'reflectY,keepFBXcornerorder,front=cross(C-A,B-A)','native_shading_normal_values_read':False}


def match_oriented_triangles(native_triangles, source_triangles, position_tolerance_cm=.01, uv_tolerance=.0001):
    """Bijective cyclic matching with source anchors; bins shortlist, never decide.

    Fixed rounded keys false-fail float32 conversions at half-bin boundaries.
    Search neighbouring source-position cells, then check every actual position/UV
    delta and front direction. All three cyclic starts are allowed; no reversal.
    """
    import itertools
    require(len(native_triangles)==len(source_triangles),'Triangle count mismatch')
    require(position_tolerance_cm>0 and uv_tolerance>0,'Invalid matching tolerance')
    def front(t):
        a,b,c=[v[0]for v in t];ca=[c[i]-a[i]for i in range(3)];ba=[b[i]-a[i]for i in range(3)]
        n=[ca[1]*ba[2]-ca[2]*ba[1],ca[2]*ba[0]-ca[0]*ba[2],ca[0]*ba[1]-ca[1]*ba[0]];length=math.sqrt(sum(x*x for x in n));require(length>1e-10,'Degenerate face');return [x/length for x in n]
    def cell(point):return tuple(math.floor(x/position_tolerance_cm)for x in point)
    bins=collections.defaultdict(list);source_fronts=[]
    for sid,t in enumerate(source_triangles):
        require(len(t)==3 and all(math.isfinite(v)for c in t for part in c[:2]for v in part),'Invalid source triangle')
        source_fronts.append(front(t))
        for rotation in range(3):bins[cell(t[rotation][0])].append((sid,rotation))
    all_candidates=[]
    for tid,native in enumerate(native_triangles):
        require(len(native)==3 and all(math.isfinite(v)for c in native for part in c[:2]for v in part),'Invalid native triangle')
        base=cell(native[0][0]);nf=front(native);candidates=[]
        for offset in itertools.product((-1,0,1),repeat=3):
            for sid,rotation in bins.get(tuple(base[i]+offset[i]for i in range(3)),()):
                agreement=sum(a*b for a,b in zip(nf,source_fronts[sid]))
                if agreement<=.99:continue
                source=source_triangles[sid];rotated=source[rotation:]+source[:rotation]
                pd=[abs(x-y)for n,s in zip(native,rotated)for x,y in zip(n[0],s[0])]
                ud=[abs(x-y)for n,s in zip(native,rotated)for x,y in zip(n[1],s[1])]
                if max(pd)>position_tolerance_cm or max(ud)>uv_tolerance:continue
                cost=sum(pd)/position_tolerance_cm+sum(ud)/uv_tolerance
                candidates.append((cost,sid,rotation,max(pd),max(ud),agreement))
        candidates.sort();require(candidates,'No oriented per-corner source match for native triangle'+str(tid));all_candidates.append(candidates)
    # Augmenting paths retain full one-to-one coverage if tiny adjacent triangles
    # have more than one within-tolerance candidate; an early greedy claim cannot
    # strand a later face. Sorting uses actual deltas, not rounded-bin coincidence.
    owner={};chosen={}
    def assign(tid,seen):
        for candidate in all_candidates[tid]:
            sid=candidate[1]
            if sid in seen:continue
            seen.add(sid)
            if sid not in owner or assign(owner[sid],seen):owner[sid]=tid;chosen[tid]=candidate;return True
        return False
    for tid in range(len(native_triangles)):require(assign(tid,set()),'No bijective oriented source coverage')
    require(len(owner)==len(source_triangles),'Incomplete source coverage')
    matches=[{'source_index':chosen[i][1],'cyclic_rotation':chosen[i][2]}for i in range(len(native_triangles))]
    return {'matches':matches,'summary':{'checked_triangles':len(matches),'bijective_source_coverage':True,'cyclic_only':True,'position_tolerance_cm':position_tolerance_cm,'UV_tolerance':uv_tolerance,'max_position_delta_cm':max((c[3]for c in chosen.values()),default=0),'max_UV_delta':max((c[4]for c in chosen.values()),default=0),'minimum_geometric_front_dot':min((c[5]for c in chosen.values()),default=1)}}


def match_convex_clouds(native_clouds, source_clouds, tolerance_cm=.01):
    """Bijections of hulls and vertices using actual deltas, not rounded bins."""
    require(len(native_clouds)==len(source_clouds),'Convex hull count mismatch')
    require(tolerance_cm>0 and all(c and all(math.isfinite(v)for p in c for v in p)for c in native_clouds+source_clouds),'Invalid convex cloud')
    def bounds(points):return [[min(p[k]for p in points)for k in range(3)],[max(p[k]for p in points)for k in range(3)]]
    def pair(native,source):
        if len(native)!=len(source):return None
        nb,sb=bounds(native),bounds(source)
        if any(abs(a-b)>tolerance_cm for na,sa in zip(nb,sb)for a,b in zip(na,sa)):return None
        options=[]
        for p in native:
            candidates=sorted((max(abs(a-b)for a,b in zip(p,q)),i)for i,q in enumerate(source))
            candidates=[v for v in candidates if v[0]<=tolerance_cm]
            if not candidates:return None
            options.append(candidates)
        owner={};chosen={}
        def assign(index,seen):
            for distance,sid in options[index]:
                if sid in seen:continue
                seen.add(sid)
                if sid not in owner or assign(owner[sid],seen):owner[sid]=index;chosen[index]=distance;return True
            return False
        if not all(assign(i,set())for i in range(len(native))):return None
        return max(chosen.values(),default=0)
    candidates=[]
    for native in native_clouds:
        options=[]
        for sid,source in enumerate(source_clouds):
            error=pair(native,source)
            if error is not None:options.append((error,sid))
        require(options,'Native convex cloud has no within-limit source match');candidates.append(sorted(options))
    owner={};chosen={}
    def assign(index,seen):
        for error,sid in candidates[index]:
            if sid in seen:continue
            seen.add(sid)
            if sid not in owner or assign(owner[sid],seen):owner[sid]=index;chosen[index]=(error,sid);return True
        return False
    require(all(assign(i,set())for i in range(len(native_clouds))),'No bijective convex source coverage')
    return {'checked_hulls':len(native_clouds),'checked_vertices':sum(len(c)for c in native_clouds),'bijective_hulls_and_vertices':True,'position_tolerance_cm':tolerance_cm,'max_vertex_delta_cm':max((v[0]for v in chosen.values()),default=0)}


def publication_state(document, plan):
    """Exactly three all-old or three all-new references; mixed states are invalid."""
    try:
        rewrite_house(document,plan)
        return 'unpublished'
    except ValueError:
        try:
            rewrite_house(document,plan,from_new=True)
            return 'published'
        except ValueError as error:
            raise ValueError('House is neither exact all-old nor exact all-new barrel state') from error


def verification_context(root, plan, document, content_at_entry, data_at_entry, mode, import_receipt_path):
    """Select verification trust origin before native candidate objects are loaded.

    Published clones bind current entry bytes and then validate every native asset.
    Unpublished verification still requires the author/import chain. Neither basis
    approves story, transforms or other scene edits; Data is protected context.
    """
    root=Path(root).resolve();state=publication_state(document,plan)
    require(HOUSE in data_at_entry and data_at_entry[HOUSE]==content_at_entry.get(HOUSE),'Entry house/data inventory mismatch')
    require(all(content_at_entry.get(k)==v for k,v in data_at_entry.items()),'Entry Data/Content drift')
    require(canonical_hash(json.loads((root/HOUSE).read_bytes()))==canonical_hash(document),'Entry house changed')
    require(sha(root/HOUSE)==data_at_entry[HOUSE],'Entry house bytes changed')
    scope=candidate_files(plan);entry_candidates={p:h for p,h in content_at_entry.items()if p in scope}
    if mode in {'preflight','import'}:
        require(state=='unpublished' and not entry_candidates,'Import/preflight require all-old state and empty candidate packages')
        return {'publication_state':state,'verification_basis':'import_creation','entry_package_sha256':{},'prior':None}
    require(mode=='verify','Mode');require(packages(plan).issubset(entry_candidates),'Candidate package set incomplete')
    if state=='published':
        verify_candidate_packages(root,plan,entry_candidates)
        return {'publication_state':state,'verification_basis':'published_entry_state','entry_package_sha256':dict(entry_candidates),'prior':None}
    receipt_path=Path(import_receipt_path);prior=json.loads(receipt_path.read_text())
    require(prior.get('passed')is True and prior.get('mode')=='import' and prior.get('project')==str(root),'Unpublished verification requires import receipt')
    require(prior['runtime_data_sha256']==data_at_entry,'Unpublished Data differs from import receipt')
    require(content_at_entry==dict(prior['protected_content_sha256'],**prior['saved_package_sha256']),'Unpublished Content differs from import receipt')
    verify_candidate_packages(root,plan,prior['saved_package_sha256'])
    return {'publication_state':state,'verification_basis':'import_receipt','entry_package_sha256':dict(prior['saved_package_sha256']),'prior':prior}


def validate_native_source_filename(source, relative, native_resolved_filenames, source_sha256):
    """Require the native AssetImportData getter to resolve the selected source.

    UE ResolveImportFilename owns package-relative resolution. Do not substitute a
    guessed CWD, basename match, matching bytes from another clone, or stored text.
    """
    expected=inside(source,relative);names=list(native_resolved_filenames)
    require(len(names)==1,'Exactly one resolved native source filename required')
    actual=Path(str(names[0]));require(actual.is_absolute(),'Native source getter did not resolve an absolute filename')
    require(actual.resolve()==expected,'Native source filename resolves outside selected bundle/file: '+str(actual)+' expected '+str(expected))
    require(expected.is_file() and sha(expected)==source_sha256,'Native source file hash drift')
    return {'file':relative,'resolved_filename':str(actual.resolve()),'sha256':source_sha256,'native_getter_resolved_selected_source':True}
