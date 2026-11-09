"""Independent source-triangle/open-footprint tests, in centimetres.
AABBs are broad phase only. Boundary/sub0.01cm contact remains reported as potential.
"""
def overlap_xy(a,b,tolerance=.001):
    return all(a[0][k]<b[1][k]-tolerance and a[1][k]>b[0][k]+tolerance for k in [0,1])

def clip_triangle_open_rect(triangle,rect,tolerance=.01):
    """Clip the actual triangle projection to an inset open rectangle.
    Return3D clipped points, including degenerate XY projections (vertical surfaces).
    Keeping those prevents a vertical wall inside the room being incorrectly ignored.
    """
    low=[rect[0][k]+tolerance for k in [0,1]]
    high=[rect[1][k]-tolerance for k in [0,1]]
    if any(low[k]>=high[k] for k in [0,1]):raise ValueError('Invalid room rectangle/tolerance')
    polygon=[list(p) for p in triangle]
    for axis,bound,sign in [(0,low[0],1),(0,high[0],-1),(1,low[1],1),(1,high[1],-1)]:
        if not polygon:break
        result=[];previous=polygon[-1];previous_inside=sign*(previous[axis]-bound)>=0
        for current in polygon:
            inside=sign*(current[axis]-bound)>=0
            if inside!=previous_inside:
                t=(bound-previous[axis])/(current[axis]-previous[axis])
                result.append([previous[k]+t*(current[k]-previous[k]) for k in range(3)])
            if inside:result.append(current)
            previous,previous_inside=current,inside
        polygon=result
    return polygon

def lod_intersections(lod_triangles,rect,transform=lambda p:p,tolerance=.01):
    results=[]
    for lod,triangles in enumerate(lod_triangles):
        hits=0;examples=[]
        for index,triangle in enumerate(triangles):
            clipped=clip_triangle_open_rect([transform(p) for p in triangle],rect,tolerance)
            if clipped:
                hits+=1
                if len(examples)<3:examples.append({'triangle':index,'clipped_points_cm':clipped})
        results.append({'lod':lod,'triangles_tested':len(triangles),'triangle_hits':hits,'examples':examples})
    return results

def coverage_source(ground_height,step_height):
    if ground_height is not None and step_height is not None:return 'ground+step'
    if ground_height is not None:return 'ground'
    if step_height is not None:return 'step'
    return 'none'

def checked_triangle_vertices(description,triangle_id,context=''):
    # UE5.8.4's array getter SetNum(3)+Algo::Copy appends three extra entries.
    # Use the indexed API, never the malformed/uninitialized six-entry array.
    if not description.is_triangle_valid(triangle_id):
        raise ValueError('Invalid source triangle ID before editor getter: '+str(context))
    instances=[description.get_triangle_vertex_instance(triangle_id,index) for index in range(3)]
    if not all(description.is_vertex_instance_valid(instance) for instance in instances):
        raise ValueError('Invalid source triangle vertex-instance ID: '+str(context))
    vertices=[description.get_vertex_instance_vertex(instance) for instance in instances]
    if not all(description.is_vertex_valid(vertex) for vertex in vertices):
        raise ValueError('Invalid source triangle vertex ID: '+str(context))
    return vertices
