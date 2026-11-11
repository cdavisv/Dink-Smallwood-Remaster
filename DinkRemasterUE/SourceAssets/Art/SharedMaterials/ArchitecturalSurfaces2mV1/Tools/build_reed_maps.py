import numpy as np,math,json,hashlib,struct,zlib
from pathlib import Path
from PIL import Image
D=Path(__file__).resolve().parents[1];N=2048;rng=np.random.default_rng(43992);H=np.zeros((N,N),np.float32);C=np.empty((N,N,3),np.float32);C[:]=(.10,.060,.025);count=0
for row in range(74):
 for col in range(235):
  x=(col+rng.uniform(-.45,.45))/235*N;y=(row+rng.uniform(-.65,.65))/74*N;length=rng.uniform(.045,.095)*N/2;width=rng.uniform(.0045,.0095)*N/2;angle=rng.uniform(-.18,.18);co,si=math.cos(angle),math.sin(angle);rad=length+width;xs=np.arange(math.floor(x-rad*.3),math.ceil(x+rad*.3));ys=np.arange(math.floor(y-length-3),math.ceil(y+4));yy,xx=np.meshgrid(ys,xs,indexing='ij');dx=xx-x;dy=yy-y;u=dx*co+dy*si;t=(-dy*co+dx*si)/length;edge=(.5*width*(.75+.25*t));cut=.014*np.sin(u*2+rng.uniform(0,6));mask=(np.abs(u)<edge)&(t>cut)&(t<1);cross=np.sqrt(np.clip(1-(u/np.maximum(edge,.0001))**2,0,1));h=(.001+.004*(1-t))*cross*np.clip((t-cut)/.045,0,1);h+=.00016*np.sin(u*8+rng.uniform(0,6));iy=yy%N;ix=xx%N;win=mask&(h>H[iy,ix]);tint=rng.uniform(.70,1.25);color=np.array([.32,.205,.085])*tint;fiber=(.93+.07*np.cos(u*5+rng.uniform(0,6)))[:,:,None];pig=color*fiber;H[iy[win],ix[win]]=h[win];C[iy[win],ix[win]]=pig[win];count+=1
def resize(a):
 if a.ndim==2:return np.array(Image.fromarray(a.astype('float32')).resize((1024,1024),Image.Resampling.BOX))
 return np.stack([resize(a[:,:,i])for i in range(a.shape[2])],2)
h=resize(H);bc=resize(C)
weather=np.zeros((1024,1024),np.float32)
for size,weight in [(3,.55),(7,.3),(19,.15)]:
 grid=rng.random((size,size),dtype=np.float32);tiled=np.tile(grid,(3,3));expanded=np.array(Image.fromarray(tiled).resize((3072,3072),Image.Resampling.BICUBIC));weather+=weight*expanded[1024:2048,1024:2048]
weather=np.clip((weather-.2)/.6,0,1);grey=np.array([.20,.175,.125],np.float32);bc=bc*(1-.38*weather[:,:,None])+grey*(.38*weather[:,:,None]);bc*=.82+.28*(1-weather[:,:,None]);dx=(np.roll(h,-1,1)-np.roll(h,1,1))/(4/1024);dy=(np.roll(h,-1,0)-np.roll(h,1,0))/(4/1024);n=np.stack([-dx,dy,np.ones_like(h)],2);n/=np.linalg.norm(n,axis=2)[:,:,None];n=n*.5+.5;orm=np.zeros_like(n);orm[:,:,0]=1;orm[:,:,1]=.86+.08*weather;bc=np.where(bc<=.0031308,bc*12.92,1.055*np.power(np.maximum(bc,0),1/2.4)-.055)
def png(path,a):
 a=np.round(np.clip(a,0,1)*65535).astype('>u2');hh,ww,c=a.shape
 def ch(t,b):return struct.pack('>I',len(b))+t+b+struct.pack('>I',zlib.crc32(t+b)&0xffffffff)
 path.write_bytes(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',ww,hh,16,2,0,0,0))+ch(b'IDAT',zlib.compress(b''.join(b'\0'+a[i].tobytes()for i in range(hh)),6))+ch(b'IEND',b''))
for role,a in [('BC',bc),('N_GL',n),('ORM',orm)]:png(D/'Textures'/f'T_Shared_DressedReed2m_Reed_{role}.png',a)
Image.fromarray(np.round(np.clip(bc,0,1)*255).astype('uint8')).save(D/'Review/reed_BC_tile.png');(D/'Provenance/ReedRecipe_MANIFEST.json').write_text(json.dumps({'source':'Original authored overlapping tapered split-stalk height/pigment field, guided by generated art-direction image; generated pixels not used as game texture','stalk_fragments':count,'V2_changes':'Rounded elliptical cross-section height replaces flat fragments; periodic irregular random-grid10..70cm artistgray/brown/straw pigment, no Fourier stripes androughness variation. No lighting/AO baked into BC.','physical_tile_m':[2,2],'map_resolution':[1024,1024],'density_px_m':512,'artist_dimensions':'width4.5..9.5mm,length45..95mm,height1..5mm,notmeasured','maps':'BC sRGB/GLnormal linear/ORM(AO1,R.91,M0),RGB16','files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in(D/'Textures').glob('*.png')},'acceptance':'PENDING actualtile/source views'},indent=2))
