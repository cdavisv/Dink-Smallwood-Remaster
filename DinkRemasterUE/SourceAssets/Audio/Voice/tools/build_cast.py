import csv, re, collections, random
D='/tmp/claude-1000/-home-davisc-Repos-Dink-Smallwood/74c5fee6-488a-439f-a824-7b6e9e736b70/scratchpad/voice/'
rows=list(csv.DictReader(open(D+'lines_raw.csv',encoding='utf-8')))
fields=list(rows[0].keys())

# ---------- pair table: (script,spk) -> (character, voice, kind, notes, low_confidence_note)
M={}
def add(s,p,ch,v,k='dialogue',n='',low=''):
    M[(s,p)]=(ch,v,k,n,low)
def sign(s,n='',ch='sign',p='current_sprite'): add(s,p,ch,'narrator','object',n)
DINK=('Dink','dink','dialogue','','')

add('dam-icee','temp1hold','cave prisoner','man_middle','dialogue','freed from the cave jail; the same man as the s2-cave prisoner')
add('duck','current_sprite','talking bottle','duck','object','a bottle that quacks; deadpan joke')
add('en-drag','current_sprite','dragon (spell caster)','dragon','system','only spell-cast captions')
add('en-drag','en_drag__kcrap','spell target','','system','"Magic resisted." caption')
add('en-gh','current_sprite','goblin','goblin','dialogue','GIBBERISH: invented goblin language, read as nonsense words, consistent phonetics')
add('en-gs','current_sprite','goblin','goblin','dialogue','GIBBERISH: invented goblin language, read as nonsense words, consistent phonetics')
add('s3-gh','current_sprite','goblin','goblin','dialogue','GIBBERISH: invented goblin language, read as nonsense words, consistent phonetics')
add('s3-gs','current_sprite','goblin','goblin','dialogue','GIBBERISH: invented goblin language, read as nonsense words, consistent phonetics')
add('en-gmog','current_sprite','Mog','mog','dialogue','dying; Mog surrenders and offers to reveal the Cast camp; weak, pleading')
add('king','','end card','narrator','narration','ending screen text (congratulations, thanks, sign-off), not spoken in-world')
add('king','current_sprite','King Daniel','king','dialogue')
add('poster','current_sprite','King\'s News poster','narrator','object','newspaper-style poster read aloud; lines in Dink colour (14) are Dink\'s comments and are cast as Dink')
add('s1-blove','current_sprite','Milder Flatstomp','milder','dialogue','smug, patronising, hitting on Lyna')
add('s1-blove','s1_blove__who','Lyna','woman_young','dialogue','rejecting Milder; sharp, self-possessed')
add('s1-boot','current_sprite','cobbler','merchant','dialogue','dry salesman')
add('s1-brg2','current_sprite','toll man','man_middle','dialogue','bridge toll collector; greedy then pitiful',low='toll man: role from bible, no name')
add('s1-bul','current_sprite','Milder Flatstomp','milder','dialogue','village bully taunting the pig farmer; mocking laughter (Bawahahah)')
add('s1-cavem','current_sprite','Bonca','monster','dialogue','cave beast; deep, menacing, sensing an intruder')
sign('s1-eltr','demo advert on a sign (order the full version); read as an announcement',ch='demo sign')
sign('s1-farms')
add('s1-fmons','current_sprite','farm monster','monster','dialogue','snarling beast that taunts in words; includes a growl line and a dying curse')
add('s1-gg','current_sprite','Guard Renton','guard','dialogue','amused, condescending')
add('s1-h1-m','current_sprite','Mother','mother','dialogue','brisk, dry; some lines are commands (YES, NOW.)')
add('s1-h1-m','s1_h1_m__cur_sprite','Mother','mother','dialogue','brisk, dry')
add('s1-h1-o','s1_h1_o__person1','Ethel','woman_old','dialogue','vision at the burning house; consoling, then a pointed jab about her duck',low='variable person1 is the old lady sprite; Ethel by context')
add('s1-h1-o','s1_h1_o__person2','Lyna','woman_young','dialogue','vision at the burning house; distressed',low='variable person2 is a girl sprite (colour 4 = Lyna elsewhere); best guess Lyna')
add('s1-h1-o','s1_h1_o__person3','Milder Flatstomp','milder','dialogue','vision at the burning house; the silver knight',low='variable person3 is the silver knight sprite; best guess Milder')
add('s1-h2-dk','s1_h2_dk__who','Ethel','woman_old','dialogue','SHOUTING: hysterical grief and rage when Dink kills her duck')
add('s1-h2-o','current_sprite','Ethel','woman_old','dialogue','sentimental about her missing duck; accuses Dink in some branches; one line has a tearful aside')
add('s1-h3-5','s1_h3_5__man','Mr. SmileStein','man_middle','dialogue','shouting a challenge',low='unnamed man; colour matches Mr. SmileStein')
add('s1-h3-l','current_sprite','Libby SmileStein','woman_young','dialogue','grieving, tearful, then angry when blamed')
add('s1-h3-of','current_sprite','Mr. SmileStein','man_middle','dialogue','widowed farmer, melancholy; some lines spoken to his late wife')
sign('s1-hsign','Wizard Martridge\'s keep-out sign')
add('s1-lg','current_sprite','Chealse','girl','dialogue','gossipy little girl; sassy outbursts')
add('s1-ltr','','UI hint','','system','instruction text, not voiced')
add('s1-ltr','s1_ltr__mycur','letter from Aunt Maria','woman_middle','object','letter read aloud; kind and anxious; sincere sign-off')
add('s1-mh-f','current_sprite','letter from Martridge','martridge','object','letter read aloud in Martridge\'s voice')
add('s1-mh-m','current_sprite','Wizard Martridge','martridge','dialogue','teacher of magic; patient, dry')
add('s1-oldd','current_sprite','Quackers','duck','dialogue','a duck; one line is just QUACK!!; sulky and sarcastic otherwise')
add('s1-rob2','current_sprite','rogue Royal Guard (dying)','guard','dialogue','dying scream')
add('s1-rob2','s1_rob2__bad1','rogue Royal Guard 1','guard','dialogue','bullying a traveller; mocking laughter')
add('s1-rob2','s1_rob2__bad2','rogue Royal Guard 2','guard','dialogue','bullying a traveller; mocking laughter')
add('s1-rob2','s1_rob2__guy','robbery victim','man_middle','dialogue','frightened traveller; ends with a cry for help')
sign('s1-sign2'); sign('s1-vil'); sign('s1-vil2')
add('s1-vic','current_sprite','robbery victim','man_middle','dialogue','rescued traveller; grateful')
add('s1-wand','current_sprite','traveller','traveller','dialogue','friendly lore-giver; long explanations')
add('s1-wand2','current_sprite','Chance Zands','zands','dialogue','escaped goblin prisoner; jumpy, informal, long explanations')
add('s1-wiz','current_sprite','Wizard Martridge','martridge','dialogue','tiny astral form; indignant, booms DON\'T ANGER ME, HUMAN!')

add('s2-auntp','current_sprite','Aunt Maria Kneedlewood','woman_middle','dialogue','abused wife; frightened, sobbing, but fierce when she leaves her husband; some lines are stage directions')
add('s2-auntp','s2_auntp__temphold','Jack Kneedlewood','man_middle','dialogue','abusive husband; belligerent, violent, shouting (domestic violence scene)')
add('s2-bar','s2_bar__crap','Cast agent / bar thug','villain','dialogue','cold threat from a Cast agent; also the thug line "Attack him!"',low='sprite var is a created sprite reused for two different characters')
add('s2-bar','temphold','barkeep','man_middle','dialogue','gruff tavern owner; bullies the barmaid')
add('s2-ca-g','current_sprite','castle guard','guard','dialogue','proud, boastful about the castle; turns hostile when hit')
add('s2-cave','s2_cave__dude','cave prisoner','man_middle','dialogue','trapped prisoner of the Cast; desperate, then sardonic; one angry outburst')
add('s2-cave2','s2_cave2__dude','cave prisoner','man_middle','dialogue','freed prisoner; capable, brisk')
add('s2-cave2','s2_cave2__evil','Cast agent','villain','dialogue','sinister ambush; laughter')
add('s2-cave2','s2_cave2__evil2','Cast agent','villain','dialogue','LAUGHTER only (Haha ha ha)')
add('s2-cave2','s2_cave2__evil3','Cast agent','villain','dialogue','LAUGHTER only (Ha ha haaa)')
add('s2-cman','current_sprite','Bishop Nelson','nelson','dialogue','cult leader, now a slayer shapeshifter in combat; menacing sermon')
add('s2-cslay','current_sprite','Bishop Nelson','nelson','dialogue','cult leader revealing himself')
add('s2-cslay','temp6hold','Mary','girl','dialogue','screaming warning')
add('s2-culg','current_sprite','Mary','girl','dialogue','rescued little girl; cries for help, then grateful')
add('s2-culg','temp1hold','Nadine','woman_middle','dialogue','mother reunited with her daughter; relieved')
add('s2-culg','temp2hold','Mary','girl','dialogue','little girl reunited with her mother')
add('s2-cult','temphold','Jennifer','girl','dialogue','cult girl; chanting, reverent, then screaming a transformation order (transforms into a slayer)')
add('s2-cult','temp2hold','cult girl 2','girl','dialogue','cult girl; devoted chant')
add('s2-cult','temp3hold','cult girl 3','girl','dialogue','cult girl; devoted chant')
add('s2-cult','temp4hold','Cindy','girl','dialogue','cult girl; sulky, then eager')
add('s2-cult','temp5hold','Bishop Nelson','nelson','dialogue','cult leader; smooth, ominous')
add('s2-cult','temp6hold','Mary','girl','dialogue','kidnapped girl; terrified, defiant')
sign('s2-dams'); sign('s2-ds')
add('s2-fight','current_sprite','dying fighter','man_middle','dialogue','dying scream (Ahhhhhhh)',low='script is an empty death handler; no name in source, gender guessed')
add('s2-healp','temphold','healer','merchant','dialogue','polite healer',low='healer: gender not stated')
add('s2-jack','current_sprite','Jack Kneedlewood','man_middle','dialogue','abusive husband; surly, short-tempered, shouting when attacked; some lines are stage directions')
add('s2-jack','temp2hold','Aunt Maria Kneedlewood','woman_middle','dialogue','abused wife; timid, tearful when Dink fights her husband')
add('s2-man1','current_sprite','old man 1','man_old','dialogue','tipsy tavern regular; yelp')
add('s2-man2','current_sprite','Nathan','man_old','dialogue','tall-tale-telling old adventurer; boasting, tipsy; shouts FIGHT when brawling')
add('s2-man2','s2_man2__milder','Milder Flatstomp','milder','dialogue','mocking Dink in front of the tavern crowd; laughing')
add('s2-man2','temp3hold','old man 2','man_old','dialogue','sceptical drinking companion of Nathan; laughs')
add('s2-man2','temphold','barkeep','man_middle','dialogue','grumpy bar owner; sarcastic')
add('s2-mdoor','s2_mdoor__me','old magician','wizard_old','dialogue','behind a locked door at first; vague, forgetful, misnames Dink; asks "Are you high?"',low='unnamed old magician in Terris; distinct from Martridge per bible')
add('s2-mh-m','current_sprite','old magician','wizard_old','dialogue','teaches Dink magic; forgetful, mispronounces his name (Tallwood, BallWood...)')
add('s2-nadp','current_sprite','Nadine','woman_middle','dialogue','poor mother searching for her missing daughter; sad, then relieved')
add('s2-out','temphold','shopkeeper','merchant','dialogue','helpful outfitter')
add('s2-qgirl','current_sprite','girl','girl','dialogue','friendly little girl greeting Dink',low='unnamed girl')
add('s2-ryan2','current_sprite','Thief','man_middle','dialogue','shady "specialist"; whispers')
add('s2-ryan3','current_sprite','Thief','man_middle','dialogue','shady specialist picking a lock; whispers')
add('s2-ryant','current_sprite','Thief','man_middle','dialogue','shady "specialist" in the tavern; evasive, smooth')
sign('s2-sale'); sign('s2-sale2'); sign('s2-sign3'); sign('s2-signe'); sign('s2-sk'); sign('s2-t1s'); sign('s2-t2s'); sign('s2-want')
add('s2-sec2','current_sprite','talking tree','tree','dialogue','tree pun: tree years old; cackling HAW HAW HAW')
add('s2-stat','temphold','shopkeeper','merchant','dialogue','shop owner; patient with a customer attacking a stuffed slayer')
add('s2-tds','s2_tds__poop','Terris guard 1','guard','dialogue','celebrating a capture with Dink')
add('s2-tds','s2_tds__poop2','Terris guard 2','guard','dialogue','celebrating a capture with Dink')
add('s2-wand','current_sprite','hunter','man_middle','dialogue','friendly outdoorsman')
add('s2-wench','current_sprite','Terris barmaid','woman_young','dialogue','tired, overworked, a little flirty/dry')
add('s2-wench','temphold','barkeep','man_middle','dialogue','one surprised line',low='temphold in s2-wench is inherited from the bar script (the barkeep); best guess')

add('s3-1st','s3_1st__evil','Cast knight','villain','dialogue','conspirators planning a raid; hushed')
add('s3-1st','s3_1st__evil2','Cast knight','villain','dialogue','conspirators planning a raid; hushed')
add('s3-bh','s3_bh__guy','grumpy homeowner','man_middle','dialogue','SHOUTING: angry at Dink barging into his house')
add('s3-camp','s3_camp__evil2','Cast knight','villain','dialogue','one shouted surprise')
add('s3-camps','s3_camps__evil','Cast knight','villain','dialogue','threatening; speaks of killing Dink')
add('s3-camps','s3_camps__evil2','Cast knight','villain','dialogue','LAUGHTER only')
add('s3-chick','current_sprite','Christina','christina','dialogue','painter and Mayor\'s daughter; earnest, sunny; one line is a debug message (system)')
add('s3-chick','s3_chick__woman','Christina','christina','dialogue','telling Dink about a rumor')
add('s3-freak','current_sprite','duck freak','man_young','dialogue','hyperactive and unhinged; SHOUTING when ducks die or Dink is rude')
add('s3-gob','current_sprite','Goblin George','goblin','dialogue','BROKEN ENGLISH, misspelled phonetically; pacifist goblin pleading with Dink; keep misspellings as pronunciation guides')
add('s3-gobg','current_sprite','Goblin gate guard','goblin','dialogue','BROKEN ENGLISH, misspelled phonetically; suspicious gate guard; shouts GATS OPAN')
sign('s3-gob2'); sign('s3-gsign','Goblin George\'s sign, misspelled on purpose')
add('s3-larry','current_sprite','Robinson Cabinets owner','man_middle','dialogue','henpecked father and furniture dealer; eager salesman, flustered by his daughter',low='owner is not named in the source (script name larry)')
add('s3-larry','s3_larry__prom','Promise','girl','dialogue','SPOILED CHILD: screeching DADDY!!!!!!!!!, demanding')
add('s3-loser','current_sprite','parade worker','man_young','dialogue','deadpan, bored')
add('s3-mayor','current_sprite','Mayor','man_middle','dialogue','pompous and cautious; panics at the news of an attack')
add('s3-mog','s3_mog__crap','Mog','mog','dialogue','king of the goblins; fluent, imperious; rages at the end')
add('s3-peeps','current_sprite','parade spectator','woman_middle','dialogue','cheerful parade crowd member; panics when Dink attacks',low='several different spectator sprites share this script; gender mixed, one voice assigned')
sign('s3-sign1'); sign('s3-sign2'); sign('s3-sign3'); sign('s3-sign6'); sign('s3-sign7'); sign('s3-st2','shop sign (no sprite)',p='')
add('s3-st1o','s3_st1o__woman','Christina','christina','dialogue','urgently showing Dink where to find the Mayor')
add('s3-st1p','current_sprite','bookstore clerk','merchant','dialogue','prim, genteel bookseller; meek when hit')
add('s3-st2p','current_sprite','Arturous','merchant','dialogue','smug bow salesman; shrugs off arrows')
add('s3-tc','s3_tc__woman','Christina','christina','dialogue','warm and proud of Dink')

add('s4-dg','current_sprite','duck altar guard','guard','dialogue','solemn; pleads when hit')
sign('s4-dsign'); 
add('s4-end','s4_end__girl','Kelly','girl','dialogue','child; innocent, later eating meat; "Bye, Dink."')
add('s4-end','s4_end__guard','duck altar guard','guard','dialogue','SHOUTING: zealot avenging the duck')
add('s4-end','s4_end__man','Kelly\'s father','man_middle','dialogue','SHOUTING: outraged, then converted; calls to his daughter')
add('s4-h1p','current_sprite','paranoid man','man_middle','dialogue','SCREAMING while fireballing Dink; later grateful, over-friendly')
add('s4-h2p1','current_sprite','starving mother','woman_middle','dialogue','starving, meek; pleads when hit')
add('s4-h2p2','current_sprite','starving father','man_middle','dialogue','too hungry to talk; weary politeness')
add('s4-h2p3','current_sprite','starving daughter','girl','dialogue','CHILD; quiet, honest')
add('s4-healp','temphold','healer','merchant','dialogue','polite healer',low='healer: gender not stated')
add('s4-md2','current_sprite','voice behind a door 1','man_middle','dialogue','BEHIND A LOCKED DOOR (muffled); hostile, desperate for food',low='speaker unseen; gender guessed from colour/lines')
add('s4-md3','current_sprite','voice behind a door 2','woman_middle','dialogue','BEHIND A LOCKED DOOR (muffled); starving mother with children',low='speaker unseen; "My children are starving" suggests a mother')
add('s4-mdoor','temp1hold','voice behind a door 3','man_middle','dialogue','BEHIND A LOCKED DOOR (muffled); hostile or grateful depending on story; one NOOOO scream',low='temp1hold is sprite 7 (an unseen door occupant); gender unknown')
add('s4-not','temp4hold','starving father','man_middle','dialogue','one line; warning Dink away from the food',low='temp4hold; colour matches the starving father')
sign('s4-sign1'); sign('s4-sign2'); sign('s4-sign3','duck tax decree, formal herald-style proclamation')
add('s4-st1p','current_sprite','Jill','merchant','dialogue','devout, impoverished pawnbroker; trails off muttering about the ducks',low='Jill: gender not stated, bible refers to the shop only')
add('s4-st2p','current_sprite','furrier','merchant','dialogue','sensible outsider')
add('s4-st3p','current_sprite','Blistering Pete','man_old','dialogue','ex-pirate weapons dealer; PIRATE accent in the spelling (Arrr, ye); threatens to give a wooden leg')
add('s4-tree','current_sprite','talking tree','tree','dialogue','timid, hint-giving tree; yelps when hit')

add('s5-end','temp1hold','Joppa father','man_middle','dialogue','relieved townsman explaining the dragon war')
add('s5-end','temp2hold','Joppa mother','woman_middle','dialogue','grateful',low='temp2hold colour 13 matches the mother; guess')
add('s5-end','temp3hold','Gwen','girl','dialogue','rescued daughter, overjoyed',low='temp3hold colour 13 shared with mother; guess Gwen')
add('s5-fd','current_sprite','Gwen','girl','dialogue','rescued daughter, awed')
add('s5-fguy','temp1hold','Joppa father','man_middle','dialogue','defiant; battle cry')
add('s5-fguy','temp2hold','Joppa mother','woman_middle','dialogue','calling her daughter to safety; frantic')
add('s5-fguy','temp3hold','Gwen','girl','dialogue','frightened daughter')
add('s5-fguy','temp4hold','dragon','dragon','dialogue','vengeful dragon; slow, rumbling')
add('s5-fguy','temp5hold','dragon','dragon','dialogue','vengeful dragon; slow, rumbling')
add('s5-fmom','current_sprite','Joppa mother','woman_middle','dialogue','rescued mother, grateful')
add('s5-guy','temp1hold','Joppa father','man_middle','dialogue','anxious father; his daughter is missing')
add('s5-guy','temp2hold','Joppa mother','woman_middle','dialogue','anxious mother; her daughter is missing')
add('s5-st1p','current_sprite','axe seller','merchant','dialogue','dry weapon dealer; protests when hit')
sign('s5-sign1')

add('s6-g1','current_sprite','Edge of the World guard (Tom\'s friend)','guard','dialogue','supportive; flinches when hit')
add('s6-g2','current_sprite','Edge of the World guard Tom','guard','dialogue','supportive; flinches when hit')
sign('s6-sign1'); sign('s6-sign5','warning sign from "the ancient ones"')
add('s6-st1p','current_sprite','church shopkeeper','merchant','dialogue','grave and reverent; praises Dink as a hero')
add('s6-vend','current_sprite','hellfire man','man_old','dialogue','nihilist, flat and unbothered; fatalistic')
add('s7-boss','current_sprite','Seth','seth','dialogue','final boss in combat; menacing taunts; spell-cast captions are system lines')
add('s7-boss','s7_boss__kcrap','spell target','','system','"Magic resisted." caption')
add('s7-dgirl','current_sprite','crazy ghost girl','ghost','dialogue','SCREAMING one-word demand (FOOD!)')
add('s7-drag','current_sprite','dragon (spell caster)','dragon','system','only spell-cast captions')
add('s7-drag','s7_drag__kcrap','spell target','','system','"Magic resisted." caption')
add('s7-girl','current_sprite','ghost girl','ghost','dialogue','GHOST OF A CHILD; plaintive, eerie, SHOUTING I HATE IT HERE!; hungry')
add('s7-mil','','Milder Flatstomp','milder','dialogue','DYING: whispered, broken, long pauses (ellipses mark gasps); stage direction groan; last lines are faint, then a scream NOOO!')
add('s7-mil','temp1hold','Seth','seth','dialogue','first appearance of the ancient evil; chilling and unhurried; action captions are system lines')
add('s7-mom','current_sprite','ghost mother','ghost','dialogue','GHOST OF A MOTHER; menacing, hollow; SHOUTING LOOK UPON MY DEFORMED FACE!')
add('s8-da','s8_da__duck1','giant duck','duck','dialogue','defeated duck fighter')
add('s8-da','s8_da__duck2','giant duck','duck','dialogue','defeated duck fighter')
add('s8-da','s8_da__pep','duck fight host','duck','dialogue','bloodthirsty announcer for the duck arena; hearty, rowdy')
for s in('s8-duck','s8-duck2','s8-duck3','s8-duck4'):
    add(s,'current_sprite','giant duck' if s!='s8-duck3' else 'mother duck','duck','dialogue','friendly giant duck of Koka Isle')
add('s8-guy','current_sprite','bow-maker','man_middle','dialogue','craftsman; irritable when disturbed, shouts for help when hit')
sign('s8-sign','joke graffiti sign')
add('savebot','','save machine','','system','"Game saved" caption')
add('sc-drag','current_sprite','dragon (spell caster)','dragon','system','only spell-cast captions')
add('sc-drag','sc_drag__kcrap','spell target','','system','"Magic resisted." caption')
add('sc-wiz','current_sprite','snow castle wizard','wizard_old','dialogue','centuries old, still fighting a war that ended long ago; rambling, confused')
add('spice','spice__sporty_spice','Sporty (pop-group cameo)','woman_young','dialogue','Dink\'s fantasy cameo; cheery')
add('start','','game message','','system','error text, not voiced')
add('start-1','','game message','','system','UI text, not voiced')
add('start-2','','game message','','system','UI text, not voiced')
add('start-3','','magic voice (shareware advert)','narrator','narration','voice of the shareware advert on the title screen; a prices-and-order-info announcer')
add('start-3','start_3__ddink','Dink','dink','dialogue','reacting to the advert')
add('treeduck','current_sprite','magical tree-duck','duck','dialogue','one-line exclamation when hit',low='sprite spawns a tree/duck; identity guessed')

# ---------- line-level kind overrides
SYS_RE=[r'^\*\s.*\s\*$', r'^I found (<N>|\d+) gold[.!]$', r'^Megapotion!', r'^<casts? ', r'^Magic resisted\.$', r'^Game saved$', r'^\*\* .* \*\*$',
        r'^<presses button under the counter>$', r'^<grins evilly at you>$']
def line_kind(x,pairkind):
    t=x['text']
    for r in SYS_RE:
        if re.search(r,t,re.I): return 'system'
    return pairkind

def lookup(x):
    k=(x['script'],x['spk'])
    if k in M: return M[k]
    if x['spk']=='1': return DINK
    raise KeyError(k)

# apply poster line-level colour rule
def line_assign(x):
    ch,v,k,n,low=lookup(x)
    if x['script']=='poster' and x['col']=='14':
        ch,v,k='Dink','dink','dialogue'
    lk=line_kind(x,k)
    if lk=='system' and x['script']=='s3-chick': pass
    return ch,(v if lk!='system' else ''),lk

pairs=collections.OrderedDict()
for x in rows: pairs.setdefault((x['script'],x['spk']),[]).append(x)
assert len(pairs)==377, len(pairs)

# ---------- voice_cast
def tokens(ts): return sorted(set(t for x in ts for t in re.findall(r'<[^>]*>',x['text']) if t!='<N>'))
def shout(x):
    t=x['text']
    return bool(re.search(r'\b[A-Z]{4,}\b',t) or re.search(r'!{3,}',t))
casts=[]
for k,ls in pairs.items():
    ch,v,kd,n,low=lookup(ls[0])
    # line-level
    assigned=[line_assign(x) for x in ls]
    kinds=collections.Counter(a[2] for a in assigned)
    if k[0]=='poster':
        # mixed: poster text + Dink comments
        pk='object'
        ch='King\'s News poster (+Dink comments)'
    else:
        pk=kinds.most_common(1)[0][0] if len(kinds)>1 else kd
        if k[1]=='1' and k not in M:
            pk=kinds.most_common(1)[0][0]
    if k[1]=='1' and k not in M:
        ch,v,n='Dink','dink',''
    notes=[n] if n else []
    if k[1]=='1' and k not in M:
        pass
    ns=kinds.get('system',0)
    if ns and pk!='system': notes.append(f'{ns} system line(s) in this pair not voiced')
    if k[0]=='poster': notes.append(f'{kinds.get("dialogue",0)} Dink-comment lines, {kinds.get("object",0)} poster lines')
    tk=tokens(ls)
    if tk: notes.append('stage directions: '+' '.join(tk))
    sh=sum(shout(x) for x,a in zip(ls,assigned) if a[2]!='system')
    if sh and 'SHOUT' not in ' '.join(notes).upper() and 'SCREAM' not in ' '.join(notes).upper():
        notes.append(f'{sh} ALL-CAPS/!!! line(s): shouting')
    if low: notes.append('LOW CONFIDENCE: '+low)
    if pk=='system' : v=''
    casts.append(dict(script=k[0],spk=k[1],character=ch,voice=v,kind=pk,lines=len(ls),chars=sum(int(x['chars']) for x in ls),notes='; '.join(notes)))
w=csv.DictWriter(open(D+'voice_cast.csv','w',newline='',encoding='utf-8'),fieldnames=['script','spk','character','voice','kind','lines','chars','notes'])
w.writeheader(); w.writerows(casts)

# ---------- tts text
TAG={'<shiver>':'[shivers]','<chuckle>':'[chuckles]','<sigh>':'[sighs]','<sob>':'[sobs]','<laugh>':'[laughs]','<chortles>':'[chortles]',
'<begins to tear up>':'[begins to tear up]','<sniff>':'[sniffs]','<grumble>':'[grumbles]','<bursts into tears>':'[bursts into tears]',
'<giggles>':'[giggles]','<groan>':'[groans]'}
def tts(t):
    def rep(m):
        s=m.group(0)
        return TAG.get(s.lower(),'['+s[1:-1].lower()+']')
    t=re.sub(r'<[^>]+>',rep,t)
    t=re.sub(r'\*(\S(?:[^*]*\S)?)\*',r'\1',t)
    t=re.sub(r' {2,}',' ',t)
    return t.strip()
out=[]
for x in rows:
    ch,v,k=line_assign(x)
    y=dict(x); y.update(character=ch,voice=v,kind=k,tts_text='' if k=='system' else tts(x['text']))
    out.append(y)
w=csv.DictWriter(open(D+'voice_lines.csv','w',newline='',encoding='utf-8'),fieldnames=fields+['character','voice','kind','tts_text'])
w.writeheader(); w.writerows(out)

# ---------- voices.csv
DESC={
'dink':'Teenage boy of about sixteen, cocky, flippant and sarcastic, a pig farmer\'s son convinced he is a legendary warrior, quick with jokes and insults, cracking into panic, rage or real grief in a handful of scenes.',
'christina':'Young woman, earnest and sunny, a painter and the Mayor\'s daughter, polite, a little dreamy, urgent when the town is in danger.',
'zands':'Man in his thirties, jumpy and informal, an escaped prisoner who talks a lot, dry and bitter about goblins, with lore delivered in long rambling explanations.',
'traveller':'Friendly middle-aged wanderer, chatty and relaxed, a natural lore-giver who explains things at length in a warm storytelling tone.',
'mother':'Middle-aged farm mother, brisk, dry and affectionate, with deadpan patience for a sulky teenage son.',
'milder':'Young man in his early twenties, an arrogant village bully turned knight, sneering and mocking, who later becomes weak, whispering and dying.',
'martridge':'Very old, very small wizard, prickly and pompous but kindly as a teacher, with a sudden booming temper when his size is mocked; also reads his letters aloud.',
'king':'Warm, dignified older king with a gentle sense of humor, formal in speech and grave when speaking of the lost.',
'seth':'Ancient, malevolent being with a deep, calm, resonant voice and unhurried menace that swells into a roaring taunt in combat.',
'mog':'Goblin king, deep and imperious, fluent and articulate, bellowing with rage when his brothers lie dead and reduced to a weak plea when dying.',
'goblin':'Gruff, guttural goblins; most lines are invented gibberish to be read as an alien language with consistent sounds, and a few are childlike broken English.',
'nelson':'Smooth, theatrical middle-aged cult leader, unctuous and sermonizing, with a gleeful cruelty underneath.',
'villain':'Cold, rough-voiced men of a criminal conspiracy, sneering and threatening, with short bursts of cruel laughter.',
'man_young':'Young adult man, casual, energetic and slightly deadpan or hyperactive, an everyman.',
'man_middle':'Ordinary middle-aged man, an all-purpose voice that runs from tired and polite to gruff, anxious or angry.',
'man_old':'Elderly man with a weathered, gravelly voice, cranky and rambling, a tall-tale teller or ex-sailor who has had a drink.',
'woman_young':'Young adult woman, bright, direct and spirited, able to turn sharp, sorrowful or tearful.',
'woman_middle':'Middle-aged woman, warm, worn and practical, alternating anxious motherly softness with fear or resolve.',
'woman_old':'Elderly woman, quavering, fussy and sentimental, a little nosy and fond of a drink, breaking into hysterical grief.',
'girl':'Young girl of about six to ten, high and bright, by turns chirpy and gossipy, innocent, frightened or spoiled and screeching.',
'guard':'Adult man in uniform, stolid and professional, a touch amused or wary, shouting when provoked.',
'merchant':'Shopkeeper of either sex, polite and practical, with smug or prim sales patter that turns meek when struck.',
'wizard_old':'Very old, absent-minded mage, dry and rambling, forgetful with names, muttering ancient lore.',
'monster':'Deep, slow, growling beast that speaks in words through a snarl, menacing and boastful.',
'duck':'Comic talking duck, deadpan and friendly, with a slight quacking nasal cadence, ranging from sulky to hearty.',
'ghost':'Eerie spectral voice of a dead mother or child, hollow and echoing, flat and plaintive, then shrieking.',
'dragon':'Vast, ancient dragon, a low rumbling slow voice, solemn and vengeful.',
'tree':'Creaky, comical talking tree, timid and nasal, fond of puns and a cackling laugh.',
'narrator':'Neutral, clear storyteller or reader voice for signs, posters and end-card text, warm, slightly wry and unhurried.',
}
by=collections.defaultdict(list)
for y in out:
    if y['kind']!='system' and y['voice']: by[y['voice']].append(y)
assert set(by)==set(DESC),(set(by)^set(DESC))
def ok(t): return re.match(r'^[A-Z"\'(]',t) and re.search(r'[.!?]$',t) and '<' not in t and '*' not in t
def preview(v,ls):
    rnd=random.Random(hash(v)&0xffff if False else sum(map(ord,v)))
    c=[]; seen=set()
    for y in ls:
        t=y['text']
        if t in seen or not ok(t): continue
        seen.add(t); c.append(t)
    if not c:
        c=[y['text'] for y in ls]
    plain=[t for t in c if 40<=len(t)<=90]
    angry=[t for t in c if 12<=len(t)<=110 and (re.search(r'\b[A-Z]{3,}\b',t) or '!!' in t)]
    long_=sorted([t for t in c if len(t)<=190],key=len,reverse=True)
    pick=[]
    for pool in (plain,angry,long_):
        pool=[t for t in pool if t not in pick]
        if pool: pick.append(rnd.choice(pool[:8]) if pool is not long_ else pool[0])
    rest=[t for t in c if t not in pick and len(t)>=25]; rnd.shuffle(rest)
    while len(' '.join(pick))<150 and rest: pick.append(rest.pop())
    # trim if too long
    while len(' '.join(pick))>400 and len(pick)>1:
        pick.remove(max(pick,key=len))
    # if still short, use shorter-line fill from all
    if len(' '.join(pick))<150:
        extra=[y['text'] for y in ls if y['text'] not in pick and '<' not in y['text'] and '*' not in y['text'] and len(y['text'])>=12]; extra=list(dict.fromkeys(extra)); rnd.shuffle(extra)
        while len(' '.join(pick))<150 and extra: pick.append(extra.pop())
    return ' '.join(pick)
vrows=[]
for v in DESC:
    ls=by[v]
    chars=collections.Counter(y['character'] for y in ls)
    ex=', '.join(c for c,_ in chars.most_common(7))
    pv=preview(v,ls)
    vrows.append(dict(voice=v,description=DESC[v],example_characters=ex,lines=len(ls),chars=sum(int(y['chars']) for y in ls),preview_text=pv))
w=csv.DictWriter(open(D+'voices.csv','w',newline='',encoding='utf-8'),fieldnames=['voice','description','example_characters','lines','chars','preview_text'])
w.writeheader(); w.writerows(vrows)

# ---------- report
kinds=collections.Counter(y['kind'] for y in out)
kchars=collections.Counter()
for y in out: kchars[y['kind']]+=int(y['chars'])
tokcount=collections.Counter(t for x in rows for t in re.findall(r'<[^>]*>',x['text']))
lows=[(c['script'],c['spk'],c['character'],c['voice'],c['notes'].split('LOW CONFIDENCE: ')[1]) for c in casts if 'LOW CONFIDENCE' in c['notes']]
longest=sorted(rows,key=lambda x:int(x['chars']),reverse=True)[:10]
tokmap_lines=collections.defaultdict(list)
for x in rows:
    for t in re.findall(r'<[^>]*>',x['text']): tokmap_lines[t].append(x['id'])
R=[]
R.append('# Voice report\n')
R.append(f'- Source lines: {len(rows)}; distinct (script, spk) pairs: {len(pairs)}; distinct voices: {len(DESC)}.')
R.append(f'- voices.csv counts only voiced lines (kind dialogue, object, narration); `system` lines are excluded there and have an empty `voice` and empty `tts_text` in voice_lines.csv. voice_cast.csv counts every line in the pair.\n')
R.append('## Lines per kind\n\n| kind | lines | chars |\n|---|---|---|')
for k in ('dialogue','object','narration','system'): R.append(f'| {k} | {kinds[k]} | {kchars[k]} |')
R.append('\n## Lines per voice (voiced lines only)\n\n| voice | lines | chars |\n|---|---|---|')
for r in sorted(vrows,key=lambda r:-r['lines']): R.append(f"| {r['voice']} | {r['lines']} | {r['chars']} |")
R.append('\n## Stage-direction tokens and mapping\n\n| token | occurrences | action | lines |\n|---|---|---|---|')
for t,n in sorted(tokcount.items()):
    if t=='<N>': act='kept (runtime number placeholder; line is system, never voiced)'
    elif re.match(r'<casts? ',t,re.I): act='line is a spell-cast caption: kind system, never voiced'
    elif t in('<presses button under the counter>','<grins evilly at you>'): act='whole line is a non-vocal action caption: kind system, never voiced (voice director may re-add as an animation cue)'
    else: act=f'tts tag {TAG[t]}'
    R.append(f'| `{t}` | {n} | {act} | {", ".join(tokmap_lines[t])} |')
R.append('\nOther text rules applied: runs of two or more spaces collapse to one (including after `!` and `?`, not only after a full stop); `*word*` loses its asterisks (only `*HATE*` occurs in voiced text; `* ... *` banner lines are system); ALL-CAPS words kept; no word added, changed or removed. No `<sigh>` occurs in this data, but the mapping `<sigh>` to `[sighs]` is implemented.\n')
R.append('## System lines (never voiced)\n')
sysl=[y for y in out if y['kind']=='system']
R.append(f'{len(sysl)} lines: gold pickups, potion/stat notice, `* ... *` banners, spell captions, "Magic resisted.", game messages, the debug line in s3-chick, two action captions.\n')
R.append('## Pairs attributed with low confidence (best guess is the assigned character)\n')
R.append('| script | spk | best guess | voice | why |\n|---|---|---|---|---|')
for s,p,c,v,wy in lows: R.append(f'| {s} | `{p}` | {c} | {v} | {wy} |')
R.append('\nAlso worth a listen-check: scripts where one sprite variable is reused (`s2-bar` `crap`: Cast agent and bar thug), and `s3-peeps` where several different spectator sprites share one script.\n')
R.append('Preview note: the `dragon` voice has only two lines in the whole game (45 characters), so its preview_text is below the 150-character minimum and is simply both lines.\n')
R.append('## Ten longest lines\n\n| id | chars | text |\n|---|---|---|')
for x in longest: R.append(f"| {x['id']} | {x['chars']} | {x['text']} |")
open(D+'voice_report.md','w',encoding='utf-8').write('\n'.join(R)+'\n')
print(kinds, len(casts), len(vrows))
for r in vrows: print(r['voice'],r['lines'],r['chars'],len(r['preview_text']))
