"""Keep the pig's continuous torso volume independent of swinging limb envelopes."""
from mathutils import Vector

def smooth(value):
    t=max(0,min(1,value));return t*t*(3-2*t)

def segment_distance(point,bone):
    a=bone.head_local;d=bone.tail_local-a;t=max(0,min(1,(point-a).dot(d)/d.length_squared));return (point-a-d*t).length

def refine_torso_weights(ob,arm):
    # Largest connected component is the fused anatomical skin, not ears/eyes/hooves/stubble.
    parent=list(range(len(ob.data.vertices)))
    def find(index):
        while parent[index]!=index:parent[index]=parent[parent[index]];index=parent[index]
        return index
    for edge in ob.data.edges:
        a,b=map(find,edge.vertices)
        if a!=b:parent[b]=a
    components={}
    for vertex in ob.data.vertices:components.setdefault(find(vertex.index),[]).append(vertex.index)
    anatomical=max(components.values(),key=len)
    changed=0
    for index in anatomical:
        vertex=ob.data.vertices[index];p=vertex.co
        # A broad, rigidly supported barrel; no leg bone can pull a diagonal flap across the flank.
        if p.x<-.25:trunk={'pelvis':1}
        elif p.x<.03:
            t=smooth((p.x+.25)/.28);trunk={'pelvis':1-t,'spine':t}
        elif p.x<.25:
            t=smooth((p.x-.03)/.22);trunk={'spine':1-t,'chest':t}
        elif p.x<.35:trunk={'chest':1}
        elif p.x<.46:
            t=smooth((p.x-.35)/.11);trunk={'chest':1-t,'neck':t}
        elif p.x<.58:
            t=smooth((p.x-.46)/.12);trunk={'neck':1-t,'head':t}
        else:trunk={'head':1}
        label='l' if p.y>=0 else 'r';prefix='fore' if p.x>-.07 else 'hind'
        names=[prefix+'_'+part+'_'+label for part in ['upper','lower','foot']]
        distance=min(segment_distance(p,arm.data.bones[name]) for name in names)
        amount=(1-smooth((p.z-.32)/.13))*smooth((.18-distance)/.08)
        if abs(p.y)<.14 or p.x>.38:amount=0
        old={ob.vertex_groups[g.group].name:g.weight for g in vertex.groups if g.weight>1e-6}
        limb={name:old.get(name,0) for name in names};total=sum(limb.values())
        if total<1e-8:
            limb={name:1/(segment_distance(p,arm.data.bones[name])+.025)**5 for name in names};total=sum(limb.values())
        weights={name:weight*(1-amount) for name,weight in trunk.items()}
        for name,weight in limb.items():weights[name]=weight/total*amount
        values=sorted([(name,w) for name,w in weights.items() if w>1e-6],key=lambda item:-item[1])[:4];total=sum(w for _,w in values)
        for group in ob.vertex_groups:group.remove([index])
        for name,w in values:ob.vertex_groups[name].add([index],w/total,'REPLACE')
        changed+=1
    return {'anatomical_vertices':len(anatomical),'torso_mask_vertices':changed,'flank_limb_influence_above_45cm':0}
