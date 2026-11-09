"""Pinned neutral geometry/pixel helpers extracted from reviewed feed-sack contract; no family defaults."""
import collections,hashlib,json,math,struct,zlib
from pathlib import Path

def require(condition, message):
    if not condition:
        raise ValueError(message)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def read_native_geometry(desc, vertex_id, triangle_id, include_material_ids=False):
    """Guard validity/ranges before indexed native mesh-description getters."""
    points=[]
    for i in range(desc.get_vertex_count()):
        vid=vertex_id(id_value=i);require(desc.is_vertex_valid(vid),'Unexpected sparse vertex IDs')
        v=desc.get_vertex_position(vid);p=[float(v.x),float(v.y),float(v.z)]
        require(all(math.isfinite(x)for x in p),'Nonfinite native vertex');points.append(p)
    require(points,'Empty native mesh')
    triangles=[];groups=set();material_ids=[]
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
        group=int(desc.get_triangle_polygon_group(tid).get_editor_property('id_value'));groups.add(group);material_ids.append(group);triangles.append(corners)
    return (points,triangles,groups,material_ids) if include_material_ids else (points,triangles,groups)

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

def match_oriented_triangles(native_triangles, source_triangles, position_tolerance_cm=.01, uv_tolerance=.0001, native_material_ids=None, source_material_ids=None):
    """Bijective cyclic matching with source anchors; bins shortlist, never decide.

    Fixed rounded keys false-fail float32 conversions at half-bin boundaries.
    Search neighbouring source-position cells, then check every actual position/UV
    delta and front direction. All three cyclic starts are allowed; no reversal.
    """
    import itertools
    if native_material_ids is not None or source_material_ids is not None:
        require(native_material_ids is not None and source_material_ids is not None and len(native_material_ids)==len(native_triangles) and len(source_material_ids)==len(source_triangles),'Material ID coverage')
        require(set(native_material_ids)==set(source_material_ids) and all(type(i)is int and i>=0 for i in source_material_ids),'Material ID set mismatch')
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
                if native_material_ids is not None and native_material_ids[tid]!=source_material_ids[sid]:continue
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


def inside(root,relative):
    from vista_contract import inside as checked_inside
    return checked_inside(root,relative)

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

def validated_material_bindings(record, native_polygon_group_ids, expected_mesh,expected_lod,material_names):
    """Join actual native group names to unique imported material slots, never IDs-as-slots."""
    require(isinstance(record,dict) and record.get('schema')=='dink-static-mesh-material-bindings/1' and record.get('valid')is True,'Native material binding query failed')
    if expected_mesh is not None:
        require(record.get('mesh')==expected_mesh and type(record.get('lod'))is int and record['lod']==expected_lod,'Native material binding mesh/LOD scope')
    def index(value):return isinstance(value,int) and not isinstance(value,bool) and value>=0
    slots=record.get('slots');groups=record.get('groups');triangles=record.get('triangles')
    require(isinstance(slots,list) and len(slots)==len(material_names) and isinstance(groups,list) and len(groups)==len(material_names) and isinstance(triangles,list),'Native binding arrays')
    by_slot={}
    for row in slots:
        i=row.get('slot_index');require(index(i) and i not in by_slot and i<len(material_names),'Duplicate/invalid native slot index')
        require(row.get('imported_slot_name')==material_names[i] and isinstance(row.get('slot_name'),str) and row['slot_name']not in ('','None'),'Native imported slot identity')
        by_slot[i]=row
    require(set(by_slot)==set(range(len(material_names))),'Native ordered slots incomplete')
    by_group={}
    for row in groups:
        gid=row.get('polygon_group_id');slot=row.get('slot_index')
        require(index(gid) and gid not in by_group and index(slot) and slot in by_slot,'Duplicate/invalid native group binding')
        require(row.get('imported_slot_name')==by_slot[slot]['imported_slot_name'],'Group imported name does not resolve to slot')
        by_group[gid]=slot
    require(set(by_group)==set(native_polygon_group_ids) and set(by_group.values())==set(range(len(material_names))),'Native group coverage')
    require(len(triangles)==len(native_polygon_group_ids) and native_polygon_group_ids,'Native triangle binding coverage')
    result=[None]*len(triangles)
    for row in triangles:
        tid=row.get('triangle_id');gid=row.get('polygon_group_id');slot=row.get('slot_index')
        require(index(tid) and tid<len(result) and result[tid]is None,'Duplicate/invalid triangle binding ID')
        require(index(gid) and gid==native_polygon_group_ids[tid] and gid in by_group and index(slot) and slot==by_group[gid],'Triangle group/slot binding mismatch')
        result[tid]=slot
    require(all(i is not None for i in result),'Missing triangle binding')
    return result
