"""Original deterministic pine bark and paired-needle PBR; no photos/downloads."""
from pathlib import Path
import numpy as np,random,math,json
from PIL import Image,ImageDraw,ImageFilter
ROOT=Path(__file__).resolve().parents[1];TEX=ROOT/'Textures';TEX.mkdir(parents=True,exist_ok=True)
N=2048;rng=np.random.default_rng(47103)
def srgb(x):return np.where(x<=.0031308,x*12.92,1.055*np.maximum(0,x)**(1/2.4)-.055)
def smooth_noise(size,seed):
 rr=np.random.default_rng(seed);im=Image.fromarray((rr.random((size,size))*255).astype('uint8'));return np.asarray(im.resize((N,N),Image.Resampling.BICUBIC)).astype('float32')/255

def save_set(name,color,height,rough):
 color=np.clip(color,0,1);Image.fromarray((np.clip(srgb(color),0,1)*255).astype('uint8'),'RGB').save(TEX/(name+'_BC.png'))
 # Texture-space derivatives, modeststrength and continuousedge sampling.
 dx=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))*4;dy=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))*4
 norm=np.stack([-dx,dy,np.ones_like(dx)],axis=2);norm/=np.linalg.norm(norm,axis=2,keepdims=True);Image.fromarray(((norm*.5+.5)*255).astype('uint8'),'RGB').save(TEX/(name+'_N.png'))
 orm=np.stack([np.clip(.91+.09*height,0,1),np.clip(rough,0,1),np.zeros_like(rough)],axis=2);Image.fromarray((orm*255).astype('uint8'),'RGB').save(TEX/(name+'_ORM.png'))
# Longitudinal cracked, scaly pinebark; coordinatewarpbreaks procedural stripes.
y,x=np.mgrid[0:N,0:N].astype('float32')/N
coarse=smooth_noise(14,111);fine=smooth_noise(240,112);warp=smooth_noise(30,113)
phase=x*22+warp*.8+.12*np.sin(y*math.tau*3);groove=np.maximum(0,np.cos(phase*math.tau))**18
plates=.5+.5*np.cos((y*17+smooth_noise(22,114)*.4)*math.tau);crosscracks=(np.maximum(0,plates-.91)/.09)**2
h=np.clip(.45+.30*coarse+.16*fine-.45*groove-.12*crosscracks,0,1)
color=np.array([.055,.029,.014],dtype='float32')[None,None,:]*(.65+1.25*h[:,:,None]);color+=np.array([.018,.009,.003])[None,None,:]*coarse[:,:,None]
save_set('T_PineV3_Bark',color,h,.83+.1*fine-.04*coarse)
# Fine pairedneedles in multiplelayers, mapped to curved3Dbundles ratherthanbroadleaves.
base=smooth_noise(20,121);micro=smooth_noise(420,122);height=Image.new('L',(N,N),45);shade=Image.new('L',(N,N),50);hd=ImageDraw.Draw(height);sd=ImageDraw.Draw(shade);rnd=random.Random(47103)
for layer in range(8):
 for k in range(1100):
  ox=rnd.uniform(-N*.08,N*1.08);oy=rnd.uniform(-N*.08,N*1.08);angle=rnd.uniform(-.65,.65)+(-.9 if layer%2 else .9);length=rnd.uniform(45,135);spread=rnd.uniform(.16,.35)
  for pair in [-1,1]:
   a=angle+pair*spread;end=(ox+math.cos(a)*length,oy+math.sin(a)*length);mid=((ox+end[0])*.5+pair*3,(oy+end[1])*.5-3)
   width=rnd.choice([2,2,3,4]);value=rnd.randint(85,190);hd.line([(ox,oy),mid,end],fill=value,width=width);sd.line([(ox,oy),mid,end],fill=rnd.randint(85,185),width=width)
   hd.line([(ox,oy),mid,end],fill=min(220,value+25),width=1)
h=np.asarray(height.filter(ImageFilter.GaussianBlur(.45))).astype('float32')/255;s=np.asarray(shade.filter(ImageFilter.GaussianBlur(.35))).astype('float32')/255
color=np.array([.012,.030,.017],dtype='float32')[None,None,:]+s[:,:,None]*np.array([.030,.055,.028])[None,None,:]
color*=((.70+.5*base+.10*micro)[:,:,None]);save_set('T_PineV3_Needles',color,h,.74+.11*micro-.06*s)
materials={}
for n,tex,bc,r in [('MI_PineV3_Bark','T_PineV3_Bark',[.055,.029,.014],.86),('MI_PineV3_Needles','T_PineV3_Needles',[.024,.052,.028],.79)]:
 materials[n]={'base_color':bc,'roughness':r,'metallic':0,'masked':False,'two_sided':False,'normal_strength':.5,'normal_flip_green':True,'textures':{'BC':'Textures/'+tex+'_BC.png','N':'Textures/'+tex+'_N.png','ORM':'Textures/'+tex+'_ORM.png'}}
(ROOT/'pine_materials.json').write_text(json.dumps(materials,indent=2)+'\n');print('PINE V3 ORIGINAL PBR READY:2sets2048BC/N/ORM',flush=True)
# Pairedneedle-spray cutoutfor smallcurved3Dribbons, overanopaqueLOD-stablecore.
spray=Image.new('RGBA',(N,N),(43,66,46,0));draw=ImageDraw.Draw(spray);rnd=random.Random(47153)
draw.line([(140,N//2),(1880,N//2-35)],fill=(91,76,48,255),width=8)
for k in range(36):
 ox=180+k*46+rnd.uniform(-12,12);oy=N*.5-35*k/36
 for side in [-1,1]:
  for pair in range(2):
   length=rnd.uniform(230,390);angle=side*rnd.uniform(.60,1.13);dx=math.cos(angle)*length;dy=math.sin(angle)*length
   color=(rnd.randint(49,72),rnd.randint(78,110),rnd.randint(53,74),255);draw.line([(ox+pair*4,oy),(ox+dx*.5,oy+dy*.46),(ox+dx,oy+dy)],fill=color,width=rnd.randint(5,9))
   draw.line([(ox+pair*4,oy),(ox+dx*.5,oy+dy*.46),(ox+dx*.97,oy+dy*.97)],fill=(color[0]+12,color[1]+13,color[2]+8,255),width=2)
alpha=np.asarray(spray)[:,:,3].astype('float32')/255
spray.save(TEX/'T_PineV3_Sprays_BC.png');dummy=np.ones((N,N,3),dtype='float32')*np.array([.025,.055,.028])[None,None,:];save_set('T_PineV3_Sprays',dummy,alpha*.7,np.ones((N,N),dtype='float32')*.79);spray.save(TEX/'T_PineV3_Sprays_BC.png')
materials['MI_PineV3_Sprays']={'base_color':[.025,.055,.028],'roughness':.79,'metallic':0,'masked':True,'two_sided':True,'alpha_clip':.45,'normal_strength':.5,'normal_flip_green':True,'textures':{'BC':'Textures/T_PineV3_Sprays_BC.png','N':'Textures/T_PineV3_Sprays_N.png','ORM':'Textures/T_PineV3_Sprays_ORM.png'}}
(ROOT/'pine_materials.json').write_text(json.dumps(materials,indent=2)+'\n');print('PINE V3 NEEDLESPRAY CUTOUT READY:3slots',flush=True)

# Highcoverage needlecuticle breaks the clay-like solidcore at close range.
core=Image.open(TEX/'T_PineV3_Needles_BC.png').convert('RGBA');mask=height.point(lambda p:255 if p>115 else 0);core.putalpha(mask);core.save(TEX/'T_PineV3_Needles_BC.png')
materials['MI_PineV3_Needles'].update(masked=True,two_sided=True,alpha_clip=.12,preserve_alpha_coverage=True)
coverage=float(np.asarray(mask).mean()/255);(ROOT/'needle_alpha_coverage.json').write_text(json.dumps({'coverage':coverage,'opacity_clip':.12,'note':'Opaqueaverage must stayaboveclip atdistance; allLOD geometrycores retained. Needlecutoutcore plus finecurvedsprays, no billboardtree.'},indent=2)+'\n')
(ROOT/'pine_materials.json').write_text(json.dumps(materials,indent=2)+'\n');print('PINE CORE ALPHA COVERAGE',coverage,flush=True)
