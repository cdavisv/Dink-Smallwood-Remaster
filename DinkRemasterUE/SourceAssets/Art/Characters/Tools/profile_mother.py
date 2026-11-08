import bpy,sys,os,json
from pathlib import Path
sys.path.insert(0,'/tmp/dink-mpfb2/src')
os.environ['MPFB_USER_DATA']='/tmp/dink-mpfb-user'
original=bpy.utils.extension_path_user
bpy.utils.extension_path_user=lambda package,*a,**k: '/tmp/dink-mpfb-user' if package=='mpfb' else original(package,*a,**k)
resource=bpy.utils.resource_path
bpy.utils.resource_path=lambda which: '/tmp/dink-mpfb-user' if which=='USER' else resource(which)
import addon_utils
addon_utils.enable('mpfb',default_set=True,persistent=False)
from mpfb.services.humanservice import HumanService
from mpfb.services.targetservice import TargetService
from mpfb.entities.objectproperties import HumanObjectProperties
print('MACRODEFAULT',TargetService.get_default_macro_info_dict())
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
macro=TargetService.get_default_macro_info_dict()
macro.update(gender=0.0,age=.70,muscle=.45,weight=.6,height=.44,cupsize=.35,firmness=.35)
macro['race']={'asian':.10,'caucasian':.80,'african':.10}
body=HumanService.create_human(scale=.1,feet_on_ground=True,macro_detail_dict=macro)
print('HUMAN',body.name,list(body.dimensions),'vertices',len(body.data.vertices),'mods',[(m.name,m.type) for m in body.modifiers])
print('GROUPS',[g.name for g in body.vertex_groups][:50])
bpy.ops.wm.save_as_mainfile(filepath='/tmp/dink-art/mother_body.blend')
