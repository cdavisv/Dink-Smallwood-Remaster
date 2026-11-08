"""Review diagram of original screen-pixel contracts; not a game screenshot."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ART=Path(__file__).resolve().parent
c=json.loads((ART/'layout_checks.json').read_text());i=json.loads((ART/'source_inventory.json').read_text())
im=Image.new('RGB',(1440,960),'#f6f4ec');d=ImageDraw.Draw(im)
fontpath='/usr/share/fonts/liberation/LiberationSans-Regular.ttf'
try:font=ImageFont.truetype(fontpath,18);title=ImageFont.truetype(fontpath,25)
except OSError:font=ImageFont.load_default();title=font
sx,sy=1.95,1.95
p=lambda xy:(int(50+xy[0]*sx),int(85+xy[1]*sy))
d.rectangle([p((0,0)),p((600,400))],fill='#dce5bf',outline='#455335',width=2)
for x in i['placements']:
 h=x['hardness']
 if h:
  a,b,r,bb=h['rect'];d.rectangle([p((a,b)),p((r,bb))],fill='#bbc2a0')
d.rectangle([p((200,180)),p((400,306))],fill='#d9c77e')
d.rectangle([p((500,160)),p((680,250))],fill='#c5b8d2')
for x in c['fences']:d.line([p(x['a_pixel']),p(x['b_pixel'])],fill='#6a4227',width=6)
d.line([p((136.5,230)),p((136.5,286))],fill='#1675b8',width=9)
route=[[420,400],[420,390],[90,390],[90,260],[200,260],[300,250]]
d.line([p(x) for x in route],fill='#c36019',width=4)
for x in i['placements']:
 if x['class_id']=='pig':
  a,b=p((x['map_x'],x['map_y']));d.ellipse((a-8,b-8,a+8,b+8),fill='#bf7886',outline='#763847');d.text((a+11,b-13),x['id'],font=font,fill='#493c39')
d.text((45,24),'Screen407 source plan: preserve the original west gate and feeding route',font=title,fill='#292e24')
d.text(p((500,170)),'Milder route\nx500+ clear',font=font,fill='#4d375f')
d.text(p((207,186)),'Original feed target\n[200,180..400,306]',font=font,fill='#665116')
d.text(p((40,235)),'West gate\n5.553m',font=font,fill='#09578c')
d.text((50,900),'Brown: authored fence centre-lines  |  Grey: source hardboxes  |  Orange: real keyboard approach',font=font,fill='#41453a')
d.text((50,930),'Source candidate only. Imported collision and after-art playthrough remain separate verification gates.',font=font,fill='#41453a')
im.save(ART/'layout_preview.png')
print('PIGPEN SOURCE PLAN:',ART/'layout_preview.png')
