from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import math, json, zipfile, shutil

OUT = Path('/mnt/data/rose_kunoichi_frames_pack')
FIGHTER_ID = 'rose_kunoichi'
if OUT.exists():
    shutil.rmtree(OUT)
BASE = OUT / 'assets' / 'fighters' / FIGHTER_ID
(BASE/'frames').mkdir(parents=True, exist_ok=True)
(BASE/'sheets').mkdir(parents=True, exist_ok=True)
(OUT/'docs').mkdir(parents=True, exist_ok=True)

W,H=256,256
S=4
SW,SH=W*S,H*S
GROUND_Y=214
ANCHOR=(128,GROUND_Y)

# Original character: athletic pink-haired kunoichi in a sport/swimsuit-inspired shinobi suit.
# "Forte pointure" interpreted as big boots / powerful athletic stance.
C={
    'shadow': (0,0,0,72),
    'outline': (38,19,45,255),
    'outline_soft': (72,36,82,230),
    'skin': (222,164,130,255),
    'skin_shadow': (174,104,91,255),
    'skin_light': (244,194,164,255),
    'hair': (245,84,166,255),
    'hair_dark': (152,34,111,255),
    'hair_light': (255,154,215,255),
    'suit': (39,28,79,255),
    'suit_dark': (22,19,50,255),
    'suit_light': (91,68,157,255),
    'accent': (245,70,178,255),
    'accent_dark': (160,34,112,255),
    'metal': (190,204,228,255),
    'metal_dark': (83,94,126,255),
    'boot': (45,31,70,255),
    'boot_light': (100,79,138,255),
    'eye': (79,235,240,255),
    'effect': (245,80,190,90),
    'effect2': (130,240,255,70),
    'star': (255,226,120,220),
}

def sc(p): return (int(round(p[0]*S)), int(round(p[1]*S)))
def sw(v): return max(1,int(round(v*S)))
def lerp(a,b,t): return a+(b-a)*t
def lerpp(p,q,t): return (lerp(p[0],q[0],t), lerp(p[1],q[1],t))
def ease(t): return 0.5-0.5*math.cos(math.pi*t)
def pulse(t): return math.sin(math.pi*t)

def poly(draw, pts, fill, outline=None, width=1):
    pts2=[sc(p) for p in pts]
    draw.polygon(pts2, fill=fill)
    if outline:
        draw.line(pts2+[pts2[0]], fill=outline, width=sw(width), joint='curve')

def ellipse(draw,bbox,fill,outline=None,width=1):
    b=[int(round(x*S)) for x in bbox]
    draw.ellipse(b, fill=fill, outline=outline, width=sw(width) if outline else 1)

def line(draw, pts, fill, width=1):
    draw.line([sc(p) for p in pts], fill=fill, width=sw(width), joint='curve')

def rounded_line(draw, pts, width, fill, outline=None):
    if outline:
        line(draw, pts, outline, width+5)
        r=(width+5)/2
        for p in pts:
            ellipse(draw,(p[0]-r,p[1]-r,p[0]+r,p[1]+r),outline)
    line(draw, pts, fill, width)
    r=width/2
    for p in pts:
        ellipse(draw,(p[0]-r,p[1]-r,p[0]+r,p[1]+r),fill)

def rotated_rect(cx,cy,w,h,ang):
    ca,sa=math.cos(ang),math.sin(ang)
    pts=[]
    for x,y in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]:
        pts.append((cx+x*ca-y*sa, cy+x*sa+y*ca))
    return pts

def capsule(draw,p1,p2,width,fill,outline=None):
    rounded_line(draw,[p1,p2],width,fill,outline)

def draw_short_blade(draw,p1,p2,width=3):
    line(draw,[p1,p2],C['outline'],width+2)
    line(draw,[p1,p2],C['metal'],width)
    line(draw,[lerpp(p1,p2,0.08),lerpp(p1,p2,0.78)],(240,245,255,240),max(1,width-1))

def base_pose():
    return {
        'head': (127,78), 'neck': (128,101),
        'shoulder_front': (140,111), 'shoulder_back': (117,112),
        'hip_front': (135,156), 'hip_back': (119,156),
        'hand_front': (174,130), 'elbow_front': (155,128),
        'hand_back': (124,145), 'elbow_back': (109,132),
        'foot_front': (168,210), 'knee_front': (151,183),
        'foot_back': (88,210), 'knee_back': (104,184),
        'torso_angle': -0.08, 'head_angle': 0,
        'crouch': 0, 'effect': None, 'guard': None, 'ko': False,
        'hair_action': 0.0, 'anim_t': 0.0, 'anim_name': 'idle'
    }

def pose_points(p):
    return [k for k,v in p.items() if isinstance(v,tuple) and len(v)==2 and all(isinstance(x,(int,float)) for x in v)]

def shift_pose(p,dx=0,dy=0):
    for k in pose_points(p):
        p[k]=(p[k][0]+dx,p[k][1]+dy)
    return p

def crouch_pose(p,amount):
    for k in ['head','neck','shoulder_front','shoulder_back','hip_front','hip_back','hand_front','elbow_front','hand_back','elbow_back']:
        p[k]=(p[k][0],p[k][1]+amount)
    p['knee_front']=(p['knee_front'][0]+5,p['knee_front'][1]+amount*0.5)
    p['knee_back']=(p['knee_back'][0]-5,p['knee_back'][1]+amount*0.5)
    p['torso_angle']-=amount/220
    p['crouch']=amount
    return p

def build_pose(anim,idx,count):
    t=0 if count<=1 else idx/(count-1)
    p=base_pose(); p['anim_t']=t; p['anim_name']=anim
    if anim=='idle':
        b=math.sin(t*math.tau)*2.4
        shift_pose(p,0,b)
        p['hand_front']=(174,128+b*.15); p['elbow_front']=(155,127+b*.1)
        p['hand_back']=(124,145+b*.2); p['elbow_back']=(109,132+b*.1)
        p['hair_action']=.2
        return p
    if anim=='walk':
        ph=math.sin(t*math.tau)
        shift_pose(p,ph*2, -abs(ph)*1.5)
        p['foot_front']=(166+ph*15,210)
        p['knee_front']=(151+ph*8,183-abs(ph)*5)
        p['foot_back']=(90-ph*15,210)
        p['knee_back']=(104-ph*8,184-abs(ph)*4)
        p['hand_front']=(172-ph*8,128)
        p['elbow_front']=(154-ph*5,126)
        p['hand_back']=(123+ph*9,145)
        p['elbow_back']=(109+ph*4,132)
        p['hair_action']=.45
        return p
    if anim=='jump':
        j=math.sin(math.pi*t)
        shift_pose(p,0,-50*j)
        p['knee_front']=(151,183-18*j); p['foot_front']=(159,210-39*j)
        p['knee_back']=(104,184-12*j); p['foot_back']=(100,210-34*j)
        p['hand_front']=(174,126-14*j); p['elbow_front']=(155,125-10*j)
        p['hand_back']=(125,141-10*j); p['elbow_back']=(110,130-8*j)
        p['torso_angle']=-0.14-.12*j; p['hair_action']=1.0
        return p
    if anim.startswith('punch'):
        level=anim.split('_')[1]
        e=pulse(t)
        if level=='high': target=(216,96); elbow=(175,103); rest=(174,128)
        elif level=='mid': target=(221,134); elbow=(179,131); rest=(174,130)
        else:
            target=(207,169); elbow=(172,160); rest=(163,145); crouch_pose(p,15*e)
        p['hand_front']=lerpp(rest,target,e)
        p['elbow_front']=lerpp((155,128),elbow,e)
        p['shoulder_front']=(140+8*e,111-1*e)
        p['hip_front']=(135+4*e,156)
        p['torso_angle']=-0.12-.20*e
        p['effect']=('punch',level,e); p['hair_action']=.8*e
        return p
    if anim.startswith('kick'):
        level=anim.split('_')[1]
        e=pulse(t)
        p['torso_angle']=0.08+.30*e
        p['shoulder_front']=(140-9*e,111-5*e)
        p['shoulder_back']=(117-7*e,112)
        p['hand_front']=(154-34*e,129-11*e); p['elbow_front']=(144-18*e,125-7*e)
        p['hand_back']=(117-21*e,143+7*e); p['elbow_back']=(106-9*e,132+4*e)
        if level=='high': target=(221,92); knee=(175,114); rest=(168,210)
        elif level=='mid': target=(226,142); knee=(179,148); rest=(168,210)
        else:
            target=(221,185); knee=(172,176); rest=(168,210); crouch_pose(p,8*e)
        p['foot_front']=lerpp(rest,target,e)
        p['knee_front']=lerpp((151,183),knee,e)
        p['foot_back']=(88-9*e,210)
        p['knee_back']=(104-3*e,184)
        p['effect']=('kick',level,e); p['hair_action']=1.0*e
        return p
    if anim.startswith('block'):
        level=anim.split('_')[1]
        if level=='high':
            p['guard']='high'; p['hand_front']=(156,95); p['elbow_front']=(143,111)
            p['hand_back']=(121,98); p['elbow_back']=(132,112); p['torso_angle']=0.03
        elif level=='mid':
            p['guard']='mid'; p['hand_front']=(162,124); p['elbow_front']=(145,128)
            p['hand_back']=(128,129); p['elbow_back']=(135,133)
        else:
            p['guard']='low'; crouch_pose(p,25)
            p['hand_front']=(158,160); p['elbow_front']=(143,151)
            p['hand_back']=(128,160); p['elbow_back']=(136,154)
        p['hair_action']=.25
        return p
    if anim=='hitstun':
        e=1 if count==1 else t
        p['head']=(127-10*e,78-4*e); p['neck']=(128-8*e,101)
        p['shoulder_front']=(140-15*e,111); p['shoulder_back']=(117-14*e,112)
        p['hip_front']=(135-3*e,156); p['hip_back']=(119-3*e,156)
        p['hand_front']=(174-36*e,130-16*e); p['elbow_front']=(155-20*e,128-7*e)
        p['hand_back']=(124-30*e,145+10*e); p['elbow_back']=(109-14*e,132+5*e)
        p['torso_angle']=0.30*e; p['effect']=('hit','mid',.85); p['hair_action']=1.1
        return p
    if anim=='ko':
        e=ease(t)
        p['head']=(127-52*e,78+90*e)
        p['neck']=(128-45*e,101+78*e)
        p['shoulder_front']=(140-50*e,111+72*e)
        p['shoulder_back']=(117-43*e,112+73*e)
        p['hip_front']=(135-17*e,156+43*e)
        p['hip_back']=(119-15*e,156+43*e)
        p['hand_front']=(174-84*e,130+62*e); p['elbow_front']=(155-63*e,128+58*e)
        p['hand_back']=(124-58*e,145+51*e); p['elbow_back']=(109-43*e,132+51*e)
        p['knee_front']=(151-16*e,183+21*e); p['foot_front']=(168-22*e,210-3*e)
        p['knee_back']=(104-8*e,184+16*e); p['foot_back']=(88-20*e,210-3*e)
        p['torso_angle']=1.35*e; p['head_angle']=1.1*e; p['ko']=True; p['hair_action']=.7*(1-e)
        return p
    return p

def draw_effects(draw,p,before=False):
    eff=p.get('effect')
    if not eff: return
    kind,level,e=eff
    if before and kind!='kick': return
    if not before and kind=='kick': return
    if e<.15: return
    if kind=='punch':
        hand=p['hand_front']; ys={'high':-6,'mid':0,'low':9}[level]
        poly(draw,[(hand[0]-8,hand[1]-8),(hand[0]+30,hand[1]-4+ys),(hand[0]+8,hand[1]+10)],C['effect2'])
        poly(draw,[(hand[0]-2,hand[1]-4),(hand[0]+45,hand[1]+2+ys),(hand[0]+6,hand[1]+7)],C['effect'])
    elif kind=='kick':
        foot=p['foot_front']
        poly(draw,[(foot[0]-47,foot[1]+15),(foot[0]+10,foot[1]-12),(foot[0]+31,foot[1]+2),(foot[0]-25,foot[1]+25)],C['effect'])
        poly(draw,[(foot[0]-40,foot[1]+9),(foot[0]+9,foot[1]-20),(foot[0]+22,foot[1]-10),(foot[0]-24,foot[1]+16)],C['effect2'])
    elif kind=='hit':
        x,y=p['head']
        for a in range(6):
            ang=a*math.tau/6
            line(draw,[(x+24*math.cos(ang),y+20*math.sin(ang)),(x+39*math.cos(ang),y+31*math.sin(ang))],C['star'],2)

def draw_hair(draw,p):
    hx,hy=p['head']; t=p.get('anim_t',0); action=p.get('hair_action',0)
    wave=math.sin(t*math.tau)*5 + action*8
    # Long pink ponytail behind head, usually trailing left.
    tail=[(hx-7,hy-18),(hx-35-action*10,hy-31-wave),(hx-65-action*12,hy-18+wave*.5),(hx-47-action*6,hy+4+wave),(hx-16,hy-4)]
    poly(draw,tail,C['hair_dark'],C['outline'],1)
    tail2=[(hx-5,hy-21),(hx-28-action*9,hy-42-wave*.7),(hx-52-action*12,hy-36+wave*.2),(hx-33,hy-15)]
    poly(draw,tail2,C['hair'],C['outline'],1)
    # hair crown / bangs
    ellipse(draw,(hx-20,hy-24,hx+19,hy+15),C['hair_dark'],C['outline'],1)
    poly(draw,[(hx-18,hy-12),(hx-4,hy-29),(hx+7,hy-12)],C['hair'],C['outline'],1)
    poly(draw,[(hx-2,hy-14),(hx+15,hy-26),(hx+13,hy-5)],C['hair_light'],C['outline'],1)

def draw_boot(draw, foot, knee, front=True):
    fx,fy=foot
    # intentionally big boots / strong shoe silhouette
    direction=1 if front else -1
    poly(draw,[(fx-15,fy-8),(fx+direction*23,fy-7),(fx+direction*32,fy+1),(fx+direction*16,fy+7),(fx-15,fy+6)],C['boot'],C['outline'],1)
    poly(draw,[(fx-4,fy-9),(fx+direction*16,fy-8),(fx+direction*19,fy-4),(fx-1,fy-3)],C['boot_light'])
    mid=lerpp(knee,foot,.62)
    ang=math.atan2(foot[1]-knee[1],foot[0]-knee[0])+math.pi/2
    poly(draw,rotated_rect(mid[0]+2,mid[1],12,28,ang),C['boot_light'],C['outline_soft'],1)

def draw_character(p):
    img=Image.new('RGBA',(SW,SH),(0,0,0,0)); draw=ImageDraw.Draw(img,'RGBA')
    t=p.get('anim_t',0)
    # Shadow
    shadow_w=76 if not p.get('ko') else 112
    ellipse(draw,(128-shadow_w/2,213,128+shadow_w/2,224),C['shadow'])
    draw_effects(draw,p,before=True)
    # weapon on back: short twin blade/scabbard, not too dominant
    draw_short_blade(draw,(103,103),(150,160),3)
    draw_short_blade(draw,(111,102),(158,157),2)
    # Back leg and arm
    capsule(draw,p['hip_back'],p['knee_back'],13,C['skin_shadow'],C['outline'])
    capsule(draw,p['knee_back'],p['foot_back'],13,C['skin'],C['outline'])
    draw_boot(draw,p['foot_back'],p['knee_back'],front=False)
    capsule(draw,p['shoulder_back'],p['elbow_back'],10,C['skin_shadow'],C['outline'])
    capsule(draw,p['elbow_back'],p['hand_back'],10,C['skin'],C['outline'])
    # Torso/suit: athletic one-piece/swimsuit-inspired but with shinobi armor accents.
    cx=(p['shoulder_front'][0]+p['shoulder_back'][0]+p['hip_front'][0]+p['hip_back'][0])/4
    cy=(p['shoulder_front'][1]+p['shoulder_back'][1]+p['hip_front'][1]+p['hip_back'][1])/4
    ang=p.get('torso_angle',0)
    # hips/upper thighs suit cut
    poly(draw,rotated_rect(cx,cy+12,40,42,ang),C['suit_dark'],C['outline'],1)
    poly(draw,rotated_rect(cx,cy-9,38,52,ang),C['suit'],C['outline'],1)
    # sport front panel and straps
    poly(draw,rotated_rect(cx+6,cy-10,18,44,ang),C['suit_light'],C['outline_soft'],1)
    poly(draw,rotated_rect(cx+16,cy-14,6,34,ang),C['accent'],None)
    poly(draw,rotated_rect((p['hip_front'][0]+p['hip_back'][0])/2, (p['hip_front'][1]+p['hip_back'][1])/2-2,48,10,ang),C['accent_dark'],C['outline'],1)
    # small sash tails
    belt=((p['hip_front'][0]+p['hip_back'][0])/2, (p['hip_front'][1]+p['hip_back'][1])/2)
    poly(draw,[(belt[0]-18,belt[1]+2),(belt[0]-42,belt[1]+10),(belt[0]-33,belt[1]+22),(belt[0]-8,belt[1]+8)],C['accent_dark'],C['outline'],1)
    # Hair behind and head
    draw_hair(draw,p)
    hx,hy=p['head']
    # neck
    capsule(draw,p['neck'],(hx,hy+15),9,C['skin_shadow'],C['outline'])
    # face
    ellipse(draw,(hx-16,hy-18,hx+17,hy+17),C['skin'],C['outline'],1)
    # cheek/highlight
    ellipse(draw,(hx+2,hy-8,hx+14,hy+6),C['skin_light'])
    # bangs over face
    poly(draw,[(hx-15,hy-15),(hx-3,hy-26),(hx+6,hy-6),(hx-8,hy-3)],C['hair'],C['outline'],1)
    poly(draw,[(hx+4,hy-17),(hx+17,hy-24),(hx+12,hy-3)],C['hair_light'],C['outline'],1)
    # eyes / ninja focus
    line(draw,[(hx-10,hy-3),(hx+12,hy-4)],C['outline'],2)
    line(draw,[(hx+1,hy-4),(hx+9,hy-5)],C['eye'],1)
    # Front leg and arm
    capsule(draw,p['hip_front'],p['knee_front'],14,C['skin'],C['outline'])
    capsule(draw,p['knee_front'],p['foot_front'],14,C['skin_light'],C['outline'])
    draw_boot(draw,p['foot_front'],p['knee_front'],front=True)
    capsule(draw,p['shoulder_front'],p['elbow_front'],11,C['skin'],C['outline'])
    capsule(draw,p['elbow_front'],p['hand_front'],11,C['skin_light'],C['outline'])
    # gloves/wrist wraps
    hx2,hy2=p['hand_front']; hx3,hy3=p['hand_back']
    ellipse(draw,(hx2-7,hy2-7,hx2+8,hy2+8),C['boot_light'],C['outline'],1)
    ellipse(draw,(hx3-6,hy3-6,hx3+7,hy3+7),C['boot'],C['outline'],1)
    # shoulder pads / bands
    ellipse(draw,(p['shoulder_front'][0]-12,p['shoulder_front'][1]-9,p['shoulder_front'][0]+12,p['shoulder_front'][1]+9),C['suit_light'],C['outline'],1)
    ellipse(draw,(p['shoulder_back'][0]-10,p['shoulder_back'][1]-8,p['shoulder_back'][0]+10,p['shoulder_back'][1]+8),C['suit_dark'],C['outline'],1)
    # knee bands
    for knee in [p['knee_front'],p['knee_back']]:
        ellipse(draw,(knee[0]-8,knee[1]-7,knee[0]+8,knee[1]+7),C['accent_dark'],C['outline_soft'],1)
    draw_effects(draw,p,before=False)
    # downsample
    return img.resize((W,H),Image.Resampling.LANCZOS)

ANIMS=[
    ('idle',4,8,True),('walk',6,10,True),('jump',4,10,False),
    ('punch_high',5,15,False),('punch_mid',5,15,False),('punch_low',5,15,False),
    ('kick_high',7,13,False),('kick_mid',7,13,False),('kick_low',7,13,False),
    ('block_high',1,1,True),('block_mid',1,1,True),('block_low',1,1,True),
    ('hitstun',2,8,False),('ko',5,8,False),
]

manifest={
    'fighter_id': FIGHTER_ID,
    'display_name': 'Rose Kunoichi',
    'version': '0.1.0',
    'frame_width': W,
    'frame_height': H,
    'anchor': {'x':ANCHOR[0],'y':ANCHOR[1]},
    'facing': 'right',
    'format': 'individual transparent PNG frames plus horizontal spritesheets',
    'style_note': 'Original athletic pink-haired kunoichi, swimsuit-inspired combat outfit, large boots / strong footing. Not a direct copy of any existing character.',
    'animations': {}
}
all_frames=[]
for name,count,fps,loop in ANIMS:
    imgs=[]; frames=[]
    for i in range(count):
        p=build_pose(name,i,count)
        img=draw_character(p)
        fname=f'{name}_{i:03d}.png'
        img.save(BASE/'frames'/fname)
        frames.append(f'frames/{fname}')
        imgs.append(img)
        all_frames.append((name,i,img))
    sheet=Image.new('RGBA',(W*count,H),(0,0,0,0))
    for i,img in enumerate(imgs):
        sheet.alpha_composite(img,(i*W,0))
    sheet_path=f'sheets/{name}.png'
    sheet.save(BASE/sheet_path)
    manifest['animations'][name]={
        'frames': frames,
        'sheet': sheet_path,
        'frame_count': count,
        'fps': fps,
        'loop': loop,
        'gameplay_state_hint': name,
    }

for n in ['punch_high','punch_mid','punch_low']:
    manifest['animations'][n]['startup_frames']=2
    manifest['animations'][n]['active_frames']=[2,3]
    manifest['animations'][n]['recovery_frames']=1
for n in ['kick_high','kick_mid','kick_low']:
    manifest['animations'][n]['startup_frames']=3
    manifest['animations'][n]['active_frames']=[3,4]
    manifest['animations'][n]['recovery_frames']=2
manifest['animations']['jump']['airborne_frames']=[1,2]
manifest['animations']['ko']['terminal_frame']=4
with open(BASE/'manifest.json','w',encoding='utf-8') as f:
    json.dump(manifest,f,ensure_ascii=False,indent=2)

# Preview contact sheet
cols=10; rows=math.ceil(len(all_frames)/cols); cellw,cellh=166,190
prev=Image.new('RGB',(cols*cellw,rows*cellh),(238,238,240))
pd=ImageDraw.Draw(prev)
for y in range(0,prev.height,16):
    for x in range(0,prev.width,16):
        col=(250,250,252) if ((x//16+y//16)%2==0) else (225,225,232)
        pd.rectangle([x,y,x+15,y+15],fill=col)
try:
    font=ImageFont.truetype('DejaVuSans.ttf',10)
except Exception:
    font=None
for idx,(name,i,img) in enumerate(all_frames):
    r=idx//cols; c=idx%cols
    thumb=img.resize((132,132),Image.Resampling.LANCZOS)
    prev.paste(thumb,(c*cellw+17,r*cellh+8),thumb)
    pd.text((c*cellw+8,r*cellh+146),f'{idx+1:02d} {name}_{i:03d}',fill=(36,28,45),font=font)
prev.save(BASE/'preview_contact_sheet.png')

# Atlas
atlas_cols=10; atlas_rows=6
atlas=Image.new('RGBA',(atlas_cols*W,atlas_rows*H),(0,0,0,0))
index=[]
for idx,(name,i,img) in enumerate(all_frames):
    r=idx//atlas_cols; c=idx%atlas_cols
    atlas.alpha_composite(img,(c*W,r*H))
    index.append({'index':idx,'animation':name,'frame':i,'x':c*W,'y':r*H,'w':W,'h':H})
atlas.save(BASE/f'{FIGHTER_ID}_atlas_10x6.png')
with open(BASE/'atlas_index.json','w',encoding='utf-8') as f:
    json.dump({'fighter_id':FIGHTER_ID,'frame_width':W,'frame_height':H,'columns':atlas_cols,'rows':atlas_rows,'frames':index},f,ensure_ascii=False,indent=2)

readme=f'''# Rose Kunoichi — 60-frame sprite pack

Pack de 60 frames PNG transparentes pour un second personnage jouable/adversaire du prototype Pygame.

## Direction artistique

Personnage original : kunoichi adulte, cheveux roses, allure sportive, tenue de combat inspirée d'un maillot une-pièce / combinaison athlétique, grandes bottes et appuis puissants. Le design vise une évocation arcade fighting game sans reproduire un personnage existant.

## Contenu

- `assets/fighters/{FIGHTER_ID}/frames/` : 60 frames PNG transparentes.
- `assets/fighters/{FIGHTER_ID}/sheets/` : spritesheets horizontales par animation.
- `assets/fighters/{FIGHTER_ID}/manifest.json` : animations, FPS, boucle, ancre, timings gameplay indicatifs.
- `assets/fighters/{FIGHTER_ID}/{FIGHTER_ID}_atlas_10x6.png` : atlas transparent 10 × 6.
- `assets/fighters/{FIGHTER_ID}/atlas_index.json` : coordonnées des frames dans l'atlas.
- `assets/fighters/{FIGHTER_ID}/preview_contact_sheet.png` : aperçu rapide avec labels.
- `docs/INTEGRATION_SPEC.md` : notes d'intégration.

## Dimensions

- Frame : {W} × {H} px
- Fond : transparent
- Orientation source : vers la droite
- Ancre : x={ANCHOR[0]}, y={ANCHOR[1]}

## Animations

| Animation | Frames | Boucle |
|---|---:|---:|
| idle | 4 | oui |
| walk | 6 | oui |
| jump | 4 | non |
| punch_high | 5 | non |
| punch_mid | 5 | non |
| punch_low | 5 | non |
| kick_high | 7 | non |
| kick_mid | 7 | non |
| kick_low | 7 | non |
| block_high | 1 | oui |
| block_mid | 1 | oui |
| block_low | 1 | oui |
| hitstun | 2 | non |
| ko | 5 | non |

## Utilisation dans le jeu

Utilise `fighter_id = "{FIGHTER_ID}"` puis charge le `manifest.json`. La convention d'animation est identique au pack `shinobi`, donc le même renderer peut afficher les deux personnages.

Pour inverser le personnage :

```python
frame = pygame.transform.flip(frame, True, False)
```

## Limite

Ce pack est prêt pour prototypage et intégration gameplay. Pour une qualité commerciale, il faudra un pipeline d'animation plus contrôlé, des retouches frame par frame, puis des hitboxes/hurtboxes dessinées précisément par animation.
'''
(OUT/'README.md').write_text(readme,encoding='utf-8')

spec=f'''# Spécification d'intégration — Rose Kunoichi

## Objectif

Ajouter un deuxième personnage au prototype en conservant exactement la même interface d'animation que le pack `shinobi`.

## Identifiant

```text
{FIGHTER_ID}
```

## Convention de fichiers

Les frames individuelles sont dans :

```text
assets/fighters/{FIGHTER_ID}/frames/
```

Les spritesheets horizontales sont dans :

```text
assets/fighters/{FIGHTER_ID}/sheets/
```

## Mapping d'état recommandé

```python
if fighter.state == "IDLE":
    anim = "idle"
elif fighter.state == "WALK":
    anim = "walk"
elif fighter.state == "JUMP":
    anim = "jump"
elif fighter.state == "ATTACK":
    anim = f"{{fighter.attack.kind}}_{{fighter.attack.height}}"
elif fighter.state == "BLOCK":
    anim = f"block_{{fighter.block_height}}"
elif fighter.state == "HITSTUN":
    anim = "hitstun"
elif fighter.state == "KO":
    anim = "ko"
```

## Ancre

Frame 256 × 256. Ancre au sol :

```json
{{"x": {ANCHOR[0]}, "y": {ANCHOR[1]}}}
```

Le rendu doit blitter la frame à :

```python
screen_x = fighter.x - anchor_x
screen_y = fighter.ground_y - anchor_y - fighter.vertical_offset
```

## Timings gameplay

Les timings présents dans `manifest.json` sont indicatifs :

- poings : startup 2 frames, actif frames 2–3, recovery 1 frame ;
- pieds : startup 3 frames, actif frames 3–4, recovery 2 frames.

Pour la première intégration, garde les hitboxes abstraites déjà définies dans le moteur.

## Production suivante

Étapes recommandées :

1. brancher ce pack au renderer existant ;
2. tester lisibilité des trois hauteurs d'attaque ;
3. ajuster `anchor_y` si le pied glisse visuellement ;
4. ajouter hurtboxes/hitboxes par frame ;
5. séparer les effets d'attaque en sprites indépendants.
'''
(OUT/'docs'/'INTEGRATION_SPEC.md').write_text(spec,encoding='utf-8')

# Copy generator
shutil.copy(Path(__file__), OUT/'tools_generate_rose_kunoichi_frames.py')

pngs=list((BASE/'frames').glob('*.png'))
assert len(pngs)==60, f'Expected 60 frames, got {len(pngs)}'
zip_path=Path('/mnt/data/rose_kunoichi_60_frames_pack.zip')
if zip_path.exists(): zip_path.unlink()
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
    for path in OUT.rglob('*'):
        if path.is_file():
            z.write(path,path.relative_to(OUT))
print(zip_path)
print('frames',len(pngs),'files',sum(1 for p in OUT.rglob('*') if p.is_file()))
