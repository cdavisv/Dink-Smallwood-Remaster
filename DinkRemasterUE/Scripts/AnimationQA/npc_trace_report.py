"""npc_trace_report.py <trace.csv> ...: numbers of an NPC walk trace (console command dink.Npc.Trace): how the shown body moves frame to frame."""
import csv, math, statistics as st, sys
def load(fn):
    R=list(csv.DictReader(open(fn)))
    return [r for r in R if r['handle']==R[0]['handle']]
def report(fn):
    R=load(fn); f=lambda r,k: float(r[k])
    n=len(R); T=f(R[-1],'time')-f(R[0],'time')
    walk=[]; back=0; still=0; yawpop=[]; acc=[]
    prev_v=None
    # frames since the script last changed what she does (stand / walk / direction): the 0.6 s after a change is the eased start or turn, not steady walking
    since=[0]*len(R)
    for i in range(1,len(R)):
        same = R[i]['action']==R[i-1]['action'] and R[i]['dir']==R[i-1]['dir']
        since[i] = since[i-1]+1 if same else 0
    for i,(a,b) in enumerate(zip(R,R[1:])):
        dt=f(b,'dt')
        dx=f(b,'body_x')-f(a,'body_x'); dy=f(b,'body_y')-f(a,'body_y')
        d=math.hypot(dx,dy)
        dyaw=abs((f(b,'body_yaw')-f(a,'body_yaw')+180)%360-180)
        yawpop.append(dyaw/dt)
        if a['action']=='2' and b['action']=='2' and a['dir']==b['dir'] and since[i]>=36:
            # heading of the scripted walk in world space, from the actor's own travel over the segment
            hx=math.cos(math.radians(f(b,'actor_yaw'))); hy=math.sin(math.radians(f(b,'actor_yaw')))
            along=dx*hx+dy*hy
            walk.append(along/dt)
            if along<-0.05: back+=1
            if abs(along)<0.05: still+=1
    print('%s: %d frames, %.1f s, %.1f fps' % (fn,n,T,(n-1)/T))
    if walk:
        m=st.mean(walk); sd=st.pstdev(walk)
        ch=[abs(b-a) for a,b in zip(walk,walk[1:])]
        print('  steady walking frames (0.6 s or more after the script last changed her action or direction): %d; shown speed along the heading: mean %.1f cm/s, deviation %.1f, min %.1f, max %.1f' % (len(walk),m,sd,min(walk),max(walk)))
        print('  frames on which the body moves BACKWARDS: %.1f%%; stands still: %.1f%%; worst frame-to-frame speed change %.0f cm/s (median %.0f)' % (100*back/len(walk),100*still/len(walk),max(ch),st.median(ch)))
    big=[y for y in yawpop if y>330]
    print('  facing: fastest turn %.0f deg/s; frames turning faster than the 300 deg/s limit: %d' % (max(yawpop),len(big)))
    # gait state flips: frames where the walk cycle starts or stops (anim speed crossing 15 cm/s)
    moving=[f(r,'anim_speed')>15 for r in R]; flips=sum(1 for a,b in zip(moving,moving[1:]) if a!=b)
    script=[(r['action']=='2' or r['moving']=='1') for r in R]; sflips=sum(1 for a,b in zip(script,script[1:]) if a!=b)
    print('  walk cycle starts+stops: %d (script walk starts+stops: %d)' % (flips,sflips))
for fn in sys.argv[1:]: report(fn)
