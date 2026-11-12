import bpy,numpy as np,json
from pathlib import Path
D=Path(__file__).resolve().parents[1];r={}
for role in ['BC','N_GL','ORM']:
 im=bpy.data.images.load(str(D/'PeriodicMaps'/('T_Candidate_ThinGlass2m_'+role+'.png')));im.colorspace_settings.name='sRGB'if role=='BC'else'Non-Color';a=np.empty(1024*1024*4,dtype=np.float32);im.pixels.foreach_get(a);a=a.reshape(1024,1024,4)[:,:,:3];edges=[np.abs(a[:,0]-a[:,-1]),np.abs(a[0]-a[-1])];inside=[np.abs(np.diff(a,axis=1)),np.abs(np.diff(a,axis=0))];stats=[]
 for boundary,ordinary in zip(edges,inside):
  b=float(boundary.max());o=float(ordinary.max());assert b<=o*1.5+2/65535,(role,b,o)
  stats.append({'repeat_jump_max':b,'interior_neighbor_jump_max':o,'interior_neighbor_jump_p99':float(np.percentile(ordinary,99)),'criterion':'repeat jump <=1.5 * observed max interior neighbor jump +2/65535'})
 r[role]=stats
(D/'SEAM_PIXEL_CHECK.json').write_text(json.dumps({'status':'PASS_no_outlier_repeat_boundary_jump','maps':r,'qualification':'Sampled adjacent texel values only; not proof of visual/native mip or derivative equivalence.'},indent=2)+'\n');print('SEAM_PIXEL_PASS')
