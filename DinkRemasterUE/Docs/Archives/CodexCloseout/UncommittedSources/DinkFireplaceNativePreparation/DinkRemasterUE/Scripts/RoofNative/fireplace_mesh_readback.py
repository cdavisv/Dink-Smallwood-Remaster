"""Actual binary FBX to RAW/built static-mesh correspondence, including UV1 and Color0.
No native call or mutation at module load. Position+material alone selects corners.
"""
from pathlib import Path
import importlib.util,hashlib,math,json
from geometry_only_match_v11 import candidates
from fireplace_contract import SOURCE,require,fbx_model_metadata
from native_built_buffer_reader_v11 import FLAGS
from native_collision_readback_v11 import inspect_collision
from relative_source_metadata import inspect_relative_sources
import vista_geometry

PARSER=Path('SourceAssets/Art/Stonebrook/Refinements/InteriorRoofSharedV1/fbxparse.py')

def fbx_color_to_raw_linear(rgba):
    """Legacy importer: truncate clamped FBX channels to FColor, then sRGB RGB->linear.
    Alpha is normalized directly. This is RAW storage only; shader Color0 bytes
    are re-encoded by the mesh builder and retain the original semantic values.
    """
    require(len(rgba)==4 and all(math.isfinite(v)for v in rgba),'Invalid source FBX color')
    values=[int(max(0.,min(1.,float(v)))*255)/255 for v in rgba]
    def decode(v):return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
    return [decode(v)for v in values[:3]]+[values[3]]


def decode_source(root,record):
    root=Path(root);file=root/SOURCE/record['file'];require(hashlib.sha256(file.read_bytes()).hexdigest()==record['source_sha256'],'Actual source FBX bytes differ')
    spec=importlib.util.spec_from_file_location('house439_binary_source',root/PARSER);F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F);_,nodes=F.parse(file);top={n.name:n for n in nodes};objects={n.props[0]:n for n in top['Objects'].children};connections=top['Connections'].children
    def linked(model,kind):return[objects[c.props[1]]for c in connections if len(c.props)>2 and c.props[0]=='OO'and c.props[2]==model.props[0]and c.props[1]in objects and objects[c.props[1]].name==kind]
    def layer(g,kind,index,field,indices,width,count):
        n=next(n for n in g.children if n.name==kind and n.props[0]==index);values=n.first(field).props[0];rows=[list(values[i:i+width])for i in range(0,len(values),width)];mode=n.first('ReferenceInformationType').props[0]
        if mode=='IndexToDirect':rows=[rows[i]for i in n.first(indices).props[0]]
        else:require(mode=='Direct','Unsupported raw FBX attribute indexing')
        mapping=n.first('MappingInformationType').props[0]
        if mapping=='AllSame':rows=rows[:1]*count
        else:require(mapping=='ByPolygonVertex','Unsupported raw FBX attribute mapping')
        require(len(rows)==count,'Incomplete raw FBX corner attribute');return rows,n
    require(fbx_model_metadata(root,record)==record['FBX_metadata'],'FBX unit/pivot policy differs');source=[];hulls=[]
    for model in [n for n in objects.values()if n.name=='Model']:
        name=model.props[1].split('\0')[0];g,=linked(model,'Geometry');raw=g.first('Vertices').props[0];points=[[raw[i]*100,-raw[i+1]*100,raw[i+2]*100]for i in range(0,len(raw),3)]
        if name.startswith('UCX_'+record['name']+'_'):hulls.append(points);continue
        require(name==record['name'],'Unexpected source render mesh');polys=[];current=[]
        for vi in g.first('PolygonVertexIndex').props[0]:
            current.append(vi if vi>=0 else-vi-1)
            if vi<0:polys.append(current);current=[]
        require(not current and all(len(p)==3 for p in polys),'Explicit source triangles required');count=3*len(polys)
        u0,_=layer(g,'LayerElementUV',0,'UV','UVIndex',2,count);u1,_=layer(g,'LayerElementUV',1,'UV','UVIndex',2,count);u2,_=layer(g,'LayerElementUV',2,'UV','UVIndex',2,count);colors,color_node=layer(g,'LayerElementColor',0,'Colors','ColorIndex',4,count);normals,_=layer(g,'LayerElementNormal',0,'Normals','NormalsIndex',3,count);require(color_node.first('Name').props[0]=='SharedSurfaceData','Raw source Color0 role differs');names=[n.props[1].split('\0')[0]for n in linked(model,'Material')];ids=g.first('LayerElementMaterial').first('Materials').props[0];require(len(ids)==len(polys),'Incomplete source material IDs')
        for i,polygon in enumerate(polys):
            corners=[]
            for k,vi in enumerate(polygon):
                j=3*i+k;n=normals[j];corners.append(dict(position_cm=points[vi],normal=[n[0],-n[1],n[2]],UV0=[u0[j][0],1-u0[j][1]],UV1=[u1[j][0],1-u1[j][1]],UVMap=[u2[j][0],1-u2[j][1]],color=colors[j],raw_color=fbx_color_to_raw_linear(colors[j])))
            source.append(dict(material=names[ids[i]],corners=corners))
    require(len(source)==record['triangles']and len(hulls)==record['UCX'],'Actual fireplace FBX inventory differs');return source,hulls


def validate_tolerances(tolerances):
    require(isinstance(tolerances,dict),'Explicit Root-approved tolerance mapping required')
    keys={'position_cm','normal_component','UV','raw_color','built_color','frame_unit','frame_dot'}
    require(set(tolerances)==keys and all(type(v)in(int,float)and math.isfinite(v)and v>0 for v in tolerances.values()),'Explicit Root-approved typed tolerances required')
    require(tolerances['raw_color']<=1/255+1e-6 and tolerances['built_color']<=1/255+1e-6,'Color differences may not exceed byte quantization')


def as_index(value):
    require(type(value)in(int,float)and math.isfinite(value)and value>=0 and value==int(value),'Native integer ID/index invalid')
    return int(value)


def compare_snapshot(snapshot,source,roles,tolerances):
    validate_tolerances(tolerances)
    require(snapshot.get('schema')=='dink-static-mesh-geometry/1'and snapshot.get('valid')is True,'Actual RAW+built geometry snapshot unavailable')
    slots={as_index(r['slot']):r for r in snapshot['slots']};require(len(slots)==len(roles) and {r['imported_name']for r in slots.values()}==set(roles),'Actual semantic material slots differ')
    for r in slots.values():require(r['material_path'].split('.')[0]==roles[r['imported_name']],'Native material role binding differs')
    raw=snapshot['raw'];built=snapshot['built'];require(raw['uv_channels']==3 and built['uv_channels']==3 and built['color0_present']is True and built['full_precision_uvs']is True,'UV1/Color0/full precision native data missing')
    rows=raw['instances'];require(len({r[0]for r in rows})==len(rows),'Duplicate raw instance IDs');instances={as_index(r[0]):r for r in rows};native_raw=[]
    for triangle in raw['triangles']:
        corners=[]
        for vi in triangle[:3]:
            r=instances[as_index(vi)];require(len(r)==15+2*raw['uv_channels'],'Raw instance layout differs');corners.append(dict(position_cm=r[1:4],normal=r[4:7],color=r[11:15],UV0=r[15:17],UV1=r[17:19],UVMap=r[19:21]))
        native_raw.append(dict(material=slots[as_index(triangle[3])]['imported_name'],corners=corners))
    vertices=built['vertices'];indices=built['indices'];native_built=[];covered=set()
    for section in built['sections']:
        start=as_index(section['first_index']);end=start+as_index(section['triangles'])*3;require(0<=start<=end<=len(indices),'Native section escaped index buffer')
        for i in range(start,end,3):
            require(not any(j in covered for j in range(i,i+3)),'Native sections overlap');covered.update(range(i,i+3));corners=[]
            for vi in indices[i:i+3]:
                vi=as_index(vi);require(vi<len(vertices),'Invalid native vertex index');r=vertices[vi];require(len(r)==17+2*built['uv_channels'],'Built vertex layout differs');require(all(math.isfinite(v)for v in r),'Nonfinite native built data');n,t,b=r[3:6],r[6:9],r[9:12];sign=r[12]
                norm=lambda v:math.sqrt(sum(x*x for x in v));dot=lambda a,b:sum(x*y for x,y in zip(a,b));require(all(abs(norm(v)-1)<=tolerances['frame_unit']for v in (n,t,b)),'Native TBN nonunit or zero');require(abs(dot(n,t))<=tolerances['frame_dot']and abs(abs(sign)-1)<=tolerances['frame_unit'],'Native TBN/sign invalid');cross=[n[1]*t[2]-n[2]*t[1],n[2]*t[0]-n[0]*t[2],n[0]*t[1]-n[1]*t[0]];require(max(abs(b[i]-sign*cross[i])for i in range(3))<=tolerances['frame_dot'],'Stored native handedness differs from actual TangentY');require(all(type(c)in(int,float)and c==int(c)and 0<=c<=255 for c in r[13:17]),'Invalid actual Color0 bytes');corners.append(dict(position_cm=r[:3],normal=n,UV0=r[17:19],UV1=r[19:21],UVMap=r[21:23],color=[c/255 for c in r[13:17]]))
            native_built.append(dict(material=slots[as_index(section['slot'])]['imported_name'],corners=corners))
    require(covered==set(range(len(indices))),'Unaccounted native triangles');reports={}
    for label,actual,color_tol in [('raw',native_raw,tolerances['raw_color']),('built',native_built,tolerances['built_color'])]:
        require(len(actual)==len(source),'Actual source triangle counts differ');matches=candidates(actual,source,tolerances['position_cm']);require(all(len(v)==1 for v in matches)and len({v[0]['source_index']for v in matches})==len(source),'Geometry-only correspondence missing/ambiguous/not bijective');errors=dict(position_cm=0.,normal_component=0.,UV0=0.,UV1=0.,UVMap=0.,color=0.)
        for triangle,match in zip(actual,matches):
            item=match[0];corners=source[item['source_index']]['corners'];r=item['rotation'];corners=corners[r:]+corners[:r];errors['position_cm']=max(errors['position_cm'],item['position_error_cm'])
            for a,b in zip(triangle['corners'],corners):
                for key,field in [('normal_component','normal'),('UV0','UV0'),('UV1','UV1'),('UVMap','UVMap'),('color','color')]:
                    expected=b['raw_color']if field=='color'and label=='raw'else b[field];require(len(a[field])==len(expected)and all(math.isfinite(x)for x in a[field]+expected),'Nonfinite/missing corner attribute');errors[key]=max(errors[key],max(abs(x-y)for x,y in zip(a[field],expected)))
        require(errors['normal_component']<=tolerances['normal_component']and max(errors['UV0'],errors['UV1'],errors['UVMap'])<=tolerances['UV']and errors['color']<=color_tol,'Actual native corner attributes differ from raw FBX');reports[label]=dict(triangles=len(actual),UV_independent_bijection=True,errors=errors,color_reference='FColor-truncated then sRGB-decoded RAW RGB, linearAlpha'if label=='raw'else'original FBX semantic Color0 versus normalized builtRGBA8')
    return dict(passed=True,source_correspondence_passed=True,raw_Color0_import_passed=True,geometry=reports,stored_signed_TBN_valid=True,source_Mikk_tangent_direction='NOT_INDEPENDENTLY_COMPARED',scope='Actual RAW/built source position/material/UV0/UV1/Color0/normal correspondence and signed-frame validity only; source Mikk direction/GPU optics/cooked collision remain separate')


def make_mesh_verifier(U,root,contract,tolerances):
    validate_tolerances(tolerances)
    bridge=getattr(getattr(U,'DinkMaterialArtLibrary',None),'inspect_static_mesh_geometry',None);require(callable(bridge),'RAW/all-UV/Color0/signed-TBN bridge not compiled/loaded')
    sources={r['name']:decode_source(root,r)for r in contract['meshes']};all_roles={r['source_material']:r['package']for r in contract['materials']};subsystem=U.get_default_object(U.StaticMeshEditorSubsystem)
    def verify(mesh,record):
        require(mesh.get_path_name().split('.')[0]==record['package']and mesh.get_num_lods()==1,'Wrong native trial mesh/LOD')
        build=subsystem.get_lod_build_settings(mesh,0);require(all(build.get_editor_property(k)==v for k,v in FLAGS.items()),'Actual Mikk/UV0 flags differ')
        source,hulls=sources[record['name']];roles={n:all_roles[n]for n in record['material_slots']};result=compare_snapshot(json.loads(bridge(mesh,0)),source,roles,tolerances)
        if hulls:result['authored_convex']=inspect_collision(U,mesh,hulls,vista_geometry,tolerances['position_cm'])
        else:
            from native_collision_readback_v11 import capture_collision
            result['authored_convex']=capture_collision(U,mesh);require(result['authored_convex']['authored_convex_elements']==0,'Unexpected collision on source0hull LOD trial')
        result['source_known_zero_TB']=record['known_source_zero_TB'];result['source_Mikk_tangent_direction']='NOT_INDEPENDENTLY_COMPARED'
        data=mesh.get_editor_property('asset_import_data');translation=data.get_editor_property('import_translation')
        require([translation.x,translation.y,translation.z]==record['import_translation_cm']and data.get_editor_property('transform_vertex_to_absolute')is True and data.get_editor_property('import_uniform_scale')==1.,'Actual pivot/unit import compensation differs')
        result['relative_sources']=inspect_relative_sources(U,mesh,[Path(root)/SOURCE/record['file']],Path(root)/'SourceAssets/Art')
        require(subsystem.get_collision_complexity(mesh)==U.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX and mesh.get_editor_property('nanite_settings').get_editor_property('enabled')is False,'Actual mesh policy differs')
        result.update(triangles=len(source),UCX=len(hulls),normal_tangent_basis='UV0');return result
    return verify


def make_pixel_verifier(U,diagnostic_root,contract,guard):
    """Concrete bounded30 Texture.Source check; no arbitrary callback success flag."""
    from native_texture_tools_v11 import _verify_pixels_profile,_configure_profile
    from png_source_v11 import png_rgb
    directory=Path(diagnostic_root);require(directory.is_absolute()and directory.resolve()==directory and directory.is_dir()and not any(directory.iterdir())and callable(guard),'Empty explicit Root-owned diagnostic directory required')
    recipes={r['package']:r for r in contract['textures']};require(len(recipes)==24,'Exact twenty-four texture scope required')
    def configure(U,texture,recipe,guard,configure=False):
        require(recipe['package']in recipes and recipe==recipes[recipe['package']],'Texture recipe escaped frozen scope');return _configure_profile(U,texture,recipe,guard,configure,1024)
    def verify(texture,source,recipe):
        output=directory/(recipe['package'].rsplit('/',1)[-1]+'_TextureSource.png');result=_verify_pixels_profile(U,texture,source,recipe,output,directory,png_rgb,guard,configure);result['passed']=True;return result
    return verify
