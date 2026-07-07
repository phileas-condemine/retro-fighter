from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import math, json, zipfile, shutil, os

OUT = Path('/mnt/data/shinobi_frames_pack')
if OUT.exists():
    shutil.rmtree(OUT)
(OUT/'assets/fighters/shinobi/frames').mkdir(parents=True, exist_ok=True)
(OUT/'assets/fighters/shinobi/sheets').mkdir(parents=True, exist_ok=True)
(OUT/'docs').mkdir(parents=True, exist_ok=True)

W,H=256,256
S=4
SW,SH=W*S,H*S
GROUND_Y=214
ANCHOR=(128,GROUND_Y)

# Palette: stylized dark shinobi with crimson scarf and muted highlights
C = {
    'shadow': (0,0,0,70),
    'outline': (5, 8, 14, 255),
    'cloth_dark': (15, 21, 36, 255),
    'cloth': (26, 38, 67, 255),
    'cloth_light': (57, 82, 126, 255),
    'armor': (44, 50, 63, 255),
    'armor_light': (92, 101, 124, 255),
    'skin': (189, 143, 98, 255),
    'skin_shadow': (132, 91, 66, 255),
    'scarf': (178, 36, 54, 255),
    'scarf_dark': (117, 20, 37, 255),
    'metal': (176, 183, 198, 255),
    'metal_dark': (78, 86, 105, 255),
    'eye': (238, 221, 151, 255),
    'effect': (240, 80, 55, 95),
    'effect2': (248, 190, 90, 70),
}

def sc(p): return (int(round(p[0]*S)), int(round(p[1]*S)))
def sw(v): return max(1, int(round(v*S)))

def add(p,q): return (p[0]+q[0], p[1]+q[1])
def lerp(a,b,t): return a + (b-a)*t
def lerpp(p,q,t): return (lerp(p[0],q[0],t), lerp(p[1],q[1],t))
def ease(t): return 0.5 - 0.5*math.cos(math.pi*t)
def pulse(t): return math.sin(math.pi*t)

def poly(draw, pts, fill, outline=None, width=1):
    pts2=[sc(p) for p in pts]
    draw.polygon(pts2, fill=fill)
    if outline:
        draw.line(pts2+[pts2[0]], fill=outline, width=sw(width), joint='curve')

def ellipse(draw, bbox, fill, outline=None, width=1):
    b=[int(round(x*S)) for x in bbox]
    draw.ellipse(b, fill=fill, outline=outline, width=sw(width) if outline else 1)

def rounded_line(draw, pts, width, fill, outline=None):
    # optional outline pass
    if outline:
        draw.line([sc(p) for p in pts], fill=outline, width=sw(width+5), joint='curve')
        r=(width+5)/2
        for p in pts:
            ellipse(draw, (p[0]-r,p[1]-r,p[0]+r,p[1]+r), outline)
    draw.line([sc(p) for p in pts], fill=fill, width=sw(width), joint='curve')
    r=width/2
    for p in pts:
        ellipse(draw, (p[0]-r,p[1]-r,p[0]+r,p[1]+r), fill)

def rotated_rect(cx,cy,w,h,ang):
    ca,sa=math.cos(ang),math.sin(ang)
    pts=[]
    for x,y in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]:
        pts.append((cx+x*ca-y*sa, cy+x*sa+y*ca))
    return pts

def draw_blade(draw, p1, p2, width=3):
    # simple katana/kunai slash line
    draw.line([sc(p1), sc(p2)], fill=C['outline'], width=sw(width+2))
    draw.line([sc(p1), sc(p2)], fill=C['metal'], width=sw(width))
    # small bright inner line
    mid=lerpp(p1,p2,0.5)
    draw.line([sc(lerpp(p1,p2,0.05)), sc(lerpp(p1,p2,0.85))], fill=(230,235,245,230), width=sw(max(1,width-1)))

def draw_scarf(draw, neck, t=0, action=0, jump=0):
    # flowing scarf behind the head, mostly to the left
    x,y=neck
    wave=math.sin(t*math.tau)*4 + action*5
    tail=[(x-8,y-4), (x-38-action*10,y-15-wave-jump*0.12), (x-65-action*15,y-6+wave), (x-42,y+5+wave*0.5)]
    poly(draw, tail, C['scarf'], C['outline'], 1)
    tail2=[(x-7,y+2), (x-33-action*8,y+3-wave), (x-56-action*14,y+18+wave*0.6), (x-30,y+13)]
    poly(draw, tail2, C['scarf_dark'], C['outline'], 1)

def base_pose():
    return {
        'offset': (0,0),
        'head': (127,82), 'neck': (128,104),
        'shoulder_front': (138,112), 'shoulder_back': (119,113),
        'hip_front': (134,157), 'hip_back': (119,158),
        'hand_front': (172,130), 'elbow_front': (154,129),
        'hand_back': (128,146), 'elbow_back': (111,134),
        'foot_front': (166,210), 'knee_front': (151,184),
        'foot_back': (91,210), 'knee_back': (105,185),
        'torso_angle': -0.08, 'head_angle': 0,
        'crouch': 0, 'effect': None, 'blade': None, 'ko': False,
        'guard': None,
    }

def shift_pose(p, dx=0, dy=0):
    keys=[k for k,v in p.items() if isinstance(v, tuple) and len(v)==2 and all(isinstance(x,(int,float)) for x in v)]
    for k in keys:
        if k!='offset':
            p[k]=(p[k][0]+dx,p[k][1]+dy)
    return p

def crouch_pose(p, amount):
    # lower torso/head, widen stance
    for k in ['head','neck','shoulder_front','shoulder_back','hip_front','hip_back','hand_front','elbow_front','hand_back','elbow_back']:
        p[k]=(p[k][0], p[k][1]+amount)
    p['knee_front']=(p['knee_front'][0]+4, p['knee_front'][1]+amount*0.5)
    p['knee_back']=(p['knee_back'][0]-4, p['knee_back'][1]+amount*0.5)
    p['torso_angle']-=amount/200
    p['crouch']=amount
    return p

def build_pose(anim, idx, count):
    t = 0 if count<=1 else idx/(count-1)
    p = base_pose()
    p['anim_t']=t
    p['anim_name']=anim
    # idle breathing
    if anim=='idle':
        b=math.sin(t*math.tau)*2
        shift_pose(p, 0, b)
        p['hand_front']=(172,130+b*0.2)
        p['elbow_front']=(154,129+b*0.1)
        p['hand_back']=(128,146+b*0.2)
        p['scarf_action']=0.1
        return p
    if anim=='walk':
        phase=math.sin(t*math.tau)
        shift_pose(p, phase*2, abs(phase)*-1)
        p['foot_front']=(164+phase*15,210)
        p['knee_front']=(149+phase*8,184-abs(phase)*4)
        p['foot_back']=(93-phase*15,210)
        p['knee_back']=(106-phase*8,185-abs(phase)*4)
        p['hand_front']=(169-phase*6,128)
        p['elbow_front']=(151-phase*4,126)
        p['hand_back']=(126+phase*8,145)
        p['elbow_back']=(111+phase*4,134)
        p['scarf_action']=0.3
        return p
    if anim=='jump':
        j=math.sin(math.pi*t)
        shift_pose(p, 0, -48*j)
        # tuck legs at apex
        p['knee_front']=(151,184-18*j); p['foot_front']=(158,210-36*j)
        p['knee_back']=(105,185-12*j); p['foot_back']=(101,210-30*j)
        p['hand_front']=(172,127-10*j); p['elbow_front']=(154,126-8*j)
        p['hand_back']=(130,142-8*j); p['elbow_back']=(112,132-7*j)
        p['torso_angle']=-0.12-0.1*j
        p['scarf_action']=0.8
        return p
    if anim.startswith('punch'):
        level=anim.split('_')[1]
        e=pulse(t)
        if level=='high': target=(214,98); elbow=(174,104); hand_rest=(172,127)
        elif level=='mid': target=(219,135); elbow=(178,131); hand_rest=(172,130)
        else: target=(205,169); elbow=(172,160); hand_rest=(164,145); crouch_pose(p, 15*e)
        p['hand_front']=lerpp(hand_rest,target,e)
        p['elbow_front']=lerpp((154,129),elbow,e)
        p['shoulder_front']=(138+8*e,112)
        p['hip_front']=(134+4*e,157)
        p['torso_angle']=-0.12-0.18*e
        p['effect'] = ('punch', level, e)
        p['scarf_action']=0.9*e
        return p
    if anim.startswith('kick'):
        level=anim.split('_')[1]
        e=pulse(t)
        p['torso_angle']=0.06+0.28*e
        p['shoulder_front']=(138-8*e,112-4*e)
        p['shoulder_back']=(119-6*e,113)
        # arms counterbalance
        p['hand_front']=(154-32*e,130-10*e); p['elbow_front']=(143-18*e,125-6*e)
        p['hand_back']=(117-20*e,143+6*e); p['elbow_back']=(105-9*e,134+3*e)
        if level=='high':
            target=(220,92); knee=(174,115); rest=(166,210)
        elif level=='mid':
            target=(224,143); knee=(178,148); rest=(166,210)
        else:
            target=(218,185); knee=(171,176); rest=(166,210); crouch_pose(p, 8*e)
        p['foot_front']=lerpp(rest,target,e)
        p['knee_front']=lerpp((151,184),knee,e)
        p['foot_back']=(92-8*e,210)
        p['knee_back']=(105-3*e,185)
        p['effect'] = ('kick', level, e)
        p['scarf_action']=1.0*e
        return p
    if anim.startswith('block'):
        level=anim.split('_')[1]
        if level=='high':
            p['guard']='high'
            p['hand_front']=(155,96); p['elbow_front']=(143,111)
            p['hand_back']=(120,99); p['elbow_back']=(132,112)
            p['torso_angle']=0.02
        elif level=='mid':
            p['guard']='mid'
            p['hand_front']=(161,124); p['elbow_front']=(145,128)
            p['hand_back']=(128,129); p['elbow_back']=(135,133)
        else:
            p['guard']='low'
            crouch_pose(p, 25)
            p['hand_front']=(157,160); p['elbow_front']=(143,151)
            p['hand_back']=(128,160); p['elbow_back']=(136,154)
        p['scarf_action']=0.2
        return p
    if anim=='hitstun':
        e=1 if count==1 else t
        p['head']=(127-10*e,82-4*e); p['neck']=(128-8*e,104)
        p['shoulder_front']=(138-15*e,112); p['shoulder_back']=(119-14*e,113)
        p['hip_front']=(134-3*e,157); p['hip_back']=(119-3*e,158)
        p['hand_front']=(170-35*e,130-16*e); p['elbow_front']=(154-20*e,129-7*e)
        p['hand_back']=(128-30*e,146+10*e); p['elbow_back']=(111-14*e,134+5*e)
        p['torso_angle']=0.3*e
        p['effect']=('hit', 'mid', 0.8)
        p['scarf_action']=1.0
        return p
    if anim=='ko':
        # falling over to the left, then lying down. Direct custom skeleton.
        e=ease(t)
        base_y=0
        p['head']=(127-50*e,82+88*e)
        p['neck']=(128-43*e,104+76*e)
        p['shoulder_front']=(138-48*e,112+70*e)
        p['shoulder_back']=(119-42*e,113+72*e)
        p['hip_front']=(134-16*e,157+42*e)
        p['hip_back']=(119-14*e,158+42*e)
        p['hand_front']=(172-82*e,130+62*e); p['elbow_front']=(154-61*e,129+58*e)
        p['hand_back']=(128-58*e,146+50*e); p['elbow_back']=(111-43*e,134+51*e)
        p['knee_front']=(151-16*e,184+20*e); p['foot_front']=(166-22*e,210-3*e)
        p['knee_back']=(105-8*e,185+15*e); p['foot_back']=(91-19*e,210-3*e)
        p['torso_angle']=1.35*e
        p['head_angle']=1.1*e
        p['ko']=True
        p['scarf_action']=0.5*(1-e)
        return p
    return p

def draw_effects(draw, p, before=False):
    effect=p.get('effect')
    if not effect: return
    kind, level, e=effect
    if before and kind!='kick': return
    if not before and kind=='kick': return
    if e < 0.15: return
    if kind=='punch':
        hand=p['hand_front']
        if level=='high': ys=-5
        elif level=='mid': ys=0
        else: ys=8
        # tapered slash / speed wedge in front of fist
        poly(draw, [(hand[0]-8,hand[1]-8),(hand[0]+28,hand[1]-3+ys),(hand[0]+8,hand[1]+10)], C['effect2'])
        poly(draw, [(hand[0]-2,hand[1]-4),(hand[0]+42,hand[1]+2+ys),(hand[0]+6,hand[1]+6)], C['effect'])
    elif kind=='kick':
        foot=p['foot_front']
        # arc behind foot
        poly(draw, [(foot[0]-45,foot[1]+14),(foot[0]+10,foot[1]-10),(foot[0]+28,foot[1]+2),(foot[0]-25,foot[1]+23)], C['effect'])
        poly(draw, [(foot[0]-38,foot[1]+8),(foot[0]+8,foot[1]-18),(foot[0]+20,foot[1]-10),(foot[0]-22,foot[1]+15)], C['effect2'])
    elif kind=='hit':
        x,y=p['head']
        for a in range(6):
            ang=a*math.tau/6
            p1=(x+25*math.cos(ang),y+20*math.sin(ang))
            p2=(x+38*math.cos(ang),y+30*math.sin(ang))
            draw.line([sc(p1),sc(p2)], fill=(255,210,70,200), width=sw(2))

def draw_character(p):
    img=Image.new('RGBA',(SW,SH),(0,0,0,0))
    draw=ImageDraw.Draw(img,'RGBA')
    t=p.get('anim_t',0)
    # ground shadow
    shadow_w=72 if not p.get('ko') else 110
    shadow_y=218
    ellipse(draw, (128-shadow_w/2, shadow_y-5, 128+shadow_w/2, shadow_y+5), C['shadow'])
    draw_effects(draw,p,before=True)
    # optional katana on back
    draw_blade(draw, (102,101), (151,163), width=3)
    # back limbs
    rounded_line(draw, [p['hip_back'], p['knee_back'], p['foot_back']], 14, C['cloth_dark'], C['outline'])
    rounded_line(draw, [p['shoulder_back'], p['elbow_back'], p['hand_back']], 11, C['cloth_dark'], C['outline'])
    # torso as rotated layered armor/cloth
    # find rough center between shoulders and hips
    cx=(p['shoulder_front'][0]+p['shoulder_back'][0]+p['hip_front'][0]+p['hip_back'][0])/4
    cy=(p['shoulder_front'][1]+p['shoulder_back'][1]+p['hip_front'][1]+p['hip_back'][1])/4
    ang=p.get('torso_angle',0)
    poly(draw, rotated_rect(cx,cy,39,58,ang), C['cloth'], C['outline'], 1)
    poly(draw, rotated_rect(cx+5*math.cos(ang),cy-2,24,45,ang), C['armor'], C['outline'], 1)
    poly(draw, rotated_rect(cx+10,cy-8,8,25,ang), C['armor_light'])
    # sash/belt
    poly(draw, rotated_rect((p['hip_front'][0]+p['hip_back'][0])/2, (p['hip_front'][1]+p['hip_back'][1])/2-2, 45, 10, ang), C['scarf_dark'], C['outline'], 1)
    # scarf behind head after torso, before head
    draw_scarf(draw, p['neck'], t=t, action=p.get('scarf_action',0), jump=max(0,GROUND_Y-p['foot_front'][1]))
    # head / mask
    hx,hy=p['head']; ha=p.get('head_angle',0)
    # neck
    rounded_line(draw, [p['neck'], (hx,hy+16)], 10, C['cloth_dark'], C['outline'])
    # head hood ellipse
    ellipse(draw, (hx-18,hy-20,hx+18,hy+18), C['cloth_dark'], C['outline'], 1)
    # face opening
    poly(draw, [(hx-12,hy-4),(hx+15,hy-6),(hx+13,hy+7),(hx-12,hy+8)], C['skin'], C['outline'], 1)
    # mask lower
    poly(draw, [(hx-16,hy+4),(hx+17,hy+2),(hx+14,hy+17),(hx-12,hy+17)], C['cloth'], C['outline'], 1)
    # eye slit and eye highlight
    draw.line([sc((hx-11,hy-1)), sc((hx+13,hy-2))], fill=C['outline'], width=sw(3))
    draw.line([sc((hx+1,hy-2)), sc((hx+10,hy-3))], fill=C['eye'], width=sw(1))
    # front limbs
    rounded_line(draw, [p['hip_front'], p['knee_front'], p['foot_front']], 15, C['cloth'], C['outline'])
    # foot armor/shoe
    fx,fy=p['foot_front']
    poly(draw, [(fx-11,fy-5),(fx+18,fy-4),(fx+22,fy+3),(fx-9,fy+5)], C['cloth_dark'], C['outline'], 1)
    fxb,fyb=p['foot_back']
    poly(draw, [(fxb-13,fyb-5),(fxb+13,fyb-4),(fxb+18,fyb+3),(fxb-10,fyb+5)], C['outline'])
    # front arm/fist
    rounded_line(draw, [p['shoulder_front'], p['elbow_front'], p['hand_front']], 12, C['cloth'], C['outline'])
    # glove/fist
    hx2,hy2=p['hand_front']
    ellipse(draw, (hx2-7,hy2-7,hx2+8,hy2+8), C['armor_light'], C['outline'], 1)
    hx3,hy3=p['hand_back']
    ellipse(draw, (hx3-6,hy3-6,hx3+7,hy3+7), C['armor'], C['outline'], 1)
    # shoulder pads
    ellipse(draw, (p['shoulder_front'][0]-12,p['shoulder_front'][1]-10,p['shoulder_front'][0]+12,p['shoulder_front'][1]+10), C['armor'], C['outline'], 1)
    ellipse(draw, (p['shoulder_back'][0]-10,p['shoulder_back'][1]-8,p['shoulder_back'][0]+10,p['shoulder_back'][1]+8), C['armor'], C['outline'], 1)
    # shin guards / highlights
    for knee,foot in [(p['knee_front'],p['foot_front']),(p['knee_back'],p['foot_back'])]:
        mid=lerpp(knee,foot,0.55)
        poly(draw, rotated_rect(mid[0]+2,mid[1],10,26,math.atan2(foot[1]-knee[1],foot[0]-knee[0])+math.pi/2), C['armor'], None)
    draw_effects(draw,p,before=False)
    # high-quality downsample
    img=img.resize((W,H), Image.Resampling.LANCZOS)
    return img

ANIMS=[
    ('idle',4,8,True),
    ('walk',6,10,True),
    ('jump',4,10,False),
    ('punch_high',5,15,False),
    ('punch_mid',5,15,False),
    ('punch_low',5,15,False),
    ('kick_high',7,13,False),
    ('kick_mid',7,13,False),
    ('kick_low',7,13,False),
    ('block_high',1,1,True),
    ('block_mid',1,1,True),
    ('block_low',1,1,True),
    ('hitstun',2,8,False),
    ('ko',5,8,False),
]

manifest={
    'fighter_id':'shinobi',
    'display_name':'Crimson Shinobi',
    'version':'0.1.0',
    'frame_width':W,
    'frame_height':H,
    'anchor': {'x':ANCHOR[0], 'y':ANCHOR[1]},
    'facing':'right',
    'format':'individual transparent PNG frames plus horizontal spritesheets',
    'notes':'Frame pack generated as a first animation-ready asset set. Replace/paint over frames for production quality; keep names and anchor stable.',
    'animations':{}
}

all_frames=[]
global_index=0
for name,count,fps,loop in ANIMS:
    frames=[]
    imgs=[]
    for i in range(count):
        p=build_pose(name,i,count)
        img=draw_character(p)
        fname=f'{name}_{i:03d}.png'
        rel=f'frames/{fname}'
        img.save(OUT/'assets/fighters/shinobi'/rel)
        frames.append(rel)
        imgs.append(img)
        all_frames.append((name,i,img))
        global_index+=1
    # sheet horizontal
    sheet=Image.new('RGBA',(W*count,H),(0,0,0,0))
    for i,img in enumerate(imgs):
        sheet.alpha_composite(img,(i*W,0))
    sheet_path=f'sheets/{name}.png'
    sheet.save(OUT/'assets/fighters/shinobi'/sheet_path)
    manifest['animations'][name]={
        'frames':frames,
        'sheet':sheet_path,
        'frame_count':count,
        'fps':fps,
        'loop':loop,
        'gameplay_state_hint': name,
    }

# Add gameplay hitbox timing hints
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

with open(OUT/'assets/fighters/shinobi/manifest.json','w',encoding='utf-8') as f:
    json.dump(manifest,f,ensure_ascii=False,indent=2)

# Contact sheet preview with checker bg and labels
cols=10; rows=math.ceil(len(all_frames)/cols)
cellw,cellh=160,186
prev=Image.new('RGB',(cols*cellw, rows*cellh),(235,235,235))
pd=ImageDraw.Draw(prev)
# checker
for y in range(0,prev.height,16):
    for x in range(0,prev.width,16):
        col=(248,248,248) if ((x//16+y//16)%2==0) else (224,224,224)
        pd.rectangle([x,y,x+15,y+15], fill=col)
try:
    font=ImageFont.truetype('DejaVuSans.ttf',10)
except Exception:
    font=None
for idx,(name,i,img) in enumerate(all_frames):
    r=idx//cols; c=idx%cols
    thumb=img.resize((128,128), Image.Resampling.LANCZOS)
    prev.paste(thumb,(c*cellw+16,r*cellh+8),thumb)
    label=f'{idx+1:02d} {name}_{i:03d}'
    pd.text((c*cellw+8,r*cellh+142),label,fill=(30,30,30),font=font)
prev.save(OUT/'assets/fighters/shinobi/preview_contact_sheet.png')

# Full atlas grid for convenience, transparent
atlas_cols=10; atlas_rows=6
atlas=Image.new('RGBA',(atlas_cols*W,atlas_rows*H),(0,0,0,0))
atlas_index=[]
for idx,(name,i,img) in enumerate(all_frames):
    r=idx//atlas_cols; c=idx%atlas_cols
    atlas.alpha_composite(img,(c*W,r*H))
    atlas_index.append({'index':idx,'animation':name,'frame':i,'x':c*W,'y':r*H,'w':W,'h':H})
atlas.save(OUT/'assets/fighters/shinobi/shinobi_atlas_10x6.png')
with open(OUT/'assets/fighters/shinobi/atlas_index.json','w',encoding='utf-8') as f:
    json.dump({'frame_width':W,'frame_height':H,'columns':atlas_cols,'rows':atlas_rows,'frames':atlas_index},f,indent=2)

# Integration docs
readme = f"""# Crimson Shinobi — 60-frame sprite pack

Ce dossier contient un premier pack exploitable pour intégrer un personnage `shinobi` dans le prototype Pygame.

## Contenu

- `frames/` : 60 frames PNG transparentes nommées par animation.
- `sheets/` : une spritesheet horizontale par animation.
- `manifest.json` : description des animations, FPS, boucle, ancrage et timings gameplay indicatifs.
- `shinobi_atlas_10x6.png` : atlas transparent de toutes les frames en grille 10 × 6.
- `atlas_index.json` : coordonnées des frames dans l'atlas.
- `preview_contact_sheet.png` : aperçu rapide avec labels.

## Dimensions

- Taille frame : `{W} × {H}` px
- Fond : transparent
- Orientation source : personnage tourné vers la droite
- Ancre recommandée : `x={ANCHOR[0]}`, `y={ANCHOR[1]}`

## Animations

| Animation | Frames | Boucle | Usage |
|---|---:|---:|---|
| idle | 4 | oui | attente |
| walk | 6 | oui | marche avant/arrière |
| jump | 4 | non | saut |
| punch_high | 5 | non | coup de poing haut |
| punch_mid | 5 | non | coup de poing moyen |
| punch_low | 5 | non | coup de poing bas |
| kick_high | 7 | non | coup de pied haut |
| kick_mid | 7 | non | coup de pied moyen |
| kick_low | 7 | non | coup de pied bas |
| block_high | 1 | oui | garde haute |
| block_mid | 1 | oui | garde moyenne |
| block_low | 1 | oui | garde basse |
| hitstun | 2 | non | personnage touché |
| ko | 5 | non | chute / KO |

## Intégration Pygame

Principe minimal : charger le `manifest.json`, charger les images listées dans `frames`, puis choisir l'animation selon l'état du combattant.

Exemple de mapping :

```python
if fighter.state == "IDLE":
    anim = "idle"
elif fighter.state == "WALK":
    anim = "walk"
elif fighter.state == "JUMP":
    anim = "jump"
elif fighter.state == "ATTACK":
    anim = f"{{fighter.attack.kind}}_{{fighter.attack.height}}"  # punch_high, kick_low, etc.
elif fighter.state == "BLOCK":
    anim = f"block_{{fighter.block_height}}"
elif fighter.state == "HITSTUN":
    anim = "hitstun"
elif fighter.state == "KO":
    anim = "ko"
```

Pour afficher le personnage côté gauche/droite, garde les images source tournées vers la droite et utilise :

```python
frame = pygame.transform.flip(frame, True, False)
```

quand le personnage doit regarder vers la gauche.

## Limite importante

Ce pack est une première base stylisée et cohérente techniquement. Pour atteindre une qualité vraiment proche d'un jeu de combat commercial, il faudra ensuite :

1. redessiner ou régénérer les frames avec un pipeline image dédié plus contrôlé ;
2. harmoniser précisément les volumes du personnage entre frames ;
3. définir les hitboxes/hurtboxes par frame ;
4. ajouter des frames d'anticipation, d'impact et de recovery plus détaillées ;
5. créer des effets séparés pour impacts, poussière, dash et projectiles.
"""
(OUT/'README.md').write_text(readme,encoding='utf-8')

spec = """# Spécification d'intégration — personnage Shinobi

## Objectif
Remplacer le rendu géométrique du prototype par un rendu sprite animé sans modifier la logique centrale du jeu.

## Décision technique
Le moteur de combat conserve ses états et timings. Le renderer ne dessine plus des rectangles : il sélectionne une animation et affiche la frame correspondante.

## Convention de nommage
Les animations suivent la convention :

- `idle`
- `walk`
- `jump`
- `punch_high`, `punch_mid`, `punch_low`
- `kick_high`, `kick_mid`, `kick_low`
- `block_high`, `block_mid`, `block_low`
- `hitstun`
- `ko`

Cette convention correspond directement aux actions déjà prévues dans le prototype.

## Ancre
L'ancre est le point de contact au sol, placé à `x=128`, `y=214` dans chaque frame 256 × 256. Le renderer doit positionner le sprite ainsi :

```python
screen_x = fighter.x - anchor_x
screen_y = fighter.ground_y - anchor_y - fighter.vertical_offset
```

## Animation
Chaque animation a un FPS propre. Pour un prototype, il est acceptable de lier l'index de frame au `state_frame` du combattant.

## Hitboxes
Première intégration : conserver les hitboxes abstraites existantes.

Deuxième intégration : ajouter dans `manifest.json` des rectangles par frame :

```json
"hitboxes": {
  "punch_mid_002": [{"x": 160, "y": 120, "w": 55, "h": 25, "height": "mid"}]
}
```

## Effets séparés
À terme, les effets de coup ne devraient pas être inclus dans les frames du personnage. Ils devraient devenir des sprites séparés pour faciliter la synchronisation, la couleur, le scaling et la réutilisation.
"""
(OUT/'docs/INTEGRATION_SPEC.md').write_text(spec,encoding='utf-8')

# Include generation script itself for reproducibility
script_path = Path('/mnt/data/tmp_generate_shinobi.py')
if script_path.exists():
    shutil.copy(script_path, OUT/'tools_generate_shinobi_frames.py')

# validate count
pngs=list((OUT/'assets/fighters/shinobi/frames').glob('*.png'))
assert len(pngs)==60, len(pngs)

zip_path=Path('/mnt/data/shinobi_60_frames_pack.zip')
if zip_path.exists(): zip_path.unlink()
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
    for path in OUT.rglob('*'):
        if path.is_file():
            z.write(path,path.relative_to(OUT))
print('Created',zip_path, 'files', sum(1 for _ in OUT.rglob('*') if _.is_file()), 'frames', len(pngs))
