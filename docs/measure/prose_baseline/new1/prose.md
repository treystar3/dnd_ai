| task | passages | words | repeated phrases /1k | repeated sentences /1k | shared openings | worn words | worn uses /1k | stock phrases /1k |
|---|---|---|---|---|---|---|---|---|
| narrate | 157 | 21005 | 5.67 | 0.00 | 16% | 31 | 18.71 | 0.14 |
| combat_opening | 18 | 2433 | 7.40 | 0.00 | 0% | 7 | 15.62 | 0.00 |
| combat_narrate | 33 | 5070 | 14.00 | 0.00 | 67% | 7 | 6.71 | 0.00 |
| combat_aftermath | 31 | 4628 | 22.69 | 0.00 | 19% | 17 | 26.36 | 0.00 |
| exchange | 104 | 4307 | 5.34 | 0.93 | 29% | 6 | 9.98 | 0.00 |
| dialogue_frame | 157 | 8289 | 15.08 | 0.00 | 30% | 14 | 22.08 | 0.00 |
| npc_conversation | 80 | 1827 | 1.64 | 0.00 | 16% | 2 | 6.57 | 0.00 |
| hire_chat | 124 | 2059 | 6.31 | 0.97 | 23% | 2 | 4.37 | 0.00 |
| mentor_chat | 15 | 445 | 20.23 | 6.74 | 67% | 0 | 0.00 | 0.00 |

- **narrate**: repeated phrases: at the edge of the, the center of the room, he does not look up, interior smells of dry grain, near the clerk s desk; openings: rain slicks the, the overcast sky, the heavy timber, you draw a, your fingers press; worn: heavy, sharp, steady, rhythmic, slow, small, quiet, dull
- **combat_opening**: repeated phrases: just beyond the reach of, a low hiss vibrates through, a warning meant to hold, any sound reaches your ears, as you sift through the; openings: none; worn: heavy, dull, massive, rhythmic, sharp, slight, tight
- **combat_narrate**: repeated phrases: longsword in a wide arc, and swing the bronze longsword, bronze longsword in a wide, enough power to buckle its, into the creature s chest; openings: you pivot your, you lunge forward, you step forward, the bronze blade, you plant your; worn: heavy, instantly, invisible, massive, motionless, sharp, tight
- **combat_aftermath**: repeated phrases: stands a few paces back, a few paces back his, alwick stands a few paces, alwick lowers his staff the, gran stands a few paces; openings: alwick leans his, you stand over, calsa pulls a; worn: heavy, steady, sharp, massive, rhythmic, dull, motionless, small
- **exchange**: repeated phrases: it is just a scratch, is just a scratch like, i need see wound now, just a scratch like a, makes me think of my; openings: good afternoon maren, it is just, the guild house, it's just a, good way to; worn: heavy, steady, trouble, probably, quick, regardless
- **dialogue_frame**: repeated phrases: the strap of his pack, adjusts the strap of his, crossing his arms over his, his arms over his chest, smooth wood of his staff; openings: bram leans his, you lean against, bram shifts his, frib shifts his, the scarred veteran; worn: slight, heavy, rough, gaze, flat, small, steady, sharp
- **npc_conversation**: repeated phrases: but if you're looking to, from the hills near the, the hills near the greywood; openings: i do not, you looking for, the building itself, you take contract, safe travels then; worn: folks, trouble
- **hire_chat**: repeated phrases: he is man who keeps, he knows how to read, how to read a trail, i'm ready as i'll ever, is man who keeps many; openings: i am ready, it's fine just, that's rough bandits, next time you, i do not; worn: steady, heavy
- **mentor_chat**: repeated phrases: about who has the better, because they didn't know which, didn't know which way was, i've seen enough rookies get, if you're even with someone; openings: i've seen enough, i'm an a, worried is a, it's mostly about; worn: none

## Over draws of a fixed size (mean [10th, 90th])

| task | drawn | repeated phrases /1k | repeated sentences /1k | shared openings | worn uses /1k |
|---|---|---|---|---|---|
| narrate | 40 passages of 157 | 1.91 [0.96, 2.90] | 0.00 [0.00, 0.00] | 4% [0%, 10%] | 12.47 [9.99, 14.64] |
| combat_opening | 12 fights of 18 | 4.99 [2.33, 7.62] | 0.00 [0.00, 0.00] | 0% [0%, 0%] | 8.72 [5.65, 11.39] |
| combat_narrate | 12 fights of 18 | 10.11 [8.37, 11.85] | 0.00 [0.00, 0.00] | 53% [41%, 64%] | 3.81 [2.49, 5.48] |
| combat_aftermath | 12 fights of 18 | 17.66 [15.44, 19.92] | 0.00 [0.00, 0.00] | 17% [9%, 29%] | 20.33 [17.54, 22.46] |
| exchange | 60 passages of 104 | 3.75 [1.93, 5.77] | 0.64 [0.00, 1.24] | 26% [20%, 32%] | 6.98 [4.43, 9.83] |
| dialogue_frame | 90 passages of 157 | 9.91 [7.86, 11.55] | 0.00 [0.00, 0.00] | 21% [16%, 26%] | 20.10 [18.00, 22.03] |
| npc_conversation | 30 passages of 80 | 0.56 [0.00, 2.78] | 0.00 [0.00, 0.00] | 7% [0%, 13%] | 2.10 [0.00, 6.71] |
| hire_chat | 60 passages of 124 | 2.76 [0.00, 6.56] | 0.38 [0.00, 1.06] | 13% [7%, 20%] | 0.98 [0.00, 4.14] |
| mentor_chat | 20 passages (short: 15) | 20.23 [20.23, 20.23] | 6.74 [6.74, 6.74] | 67% [67%, 67%] | 0.00 [0.00, 0.00] |

## Sample passages
### narrate
> Your gauntleted hands work methodically through the debris on the forest floor. Each handful of brittle leaves reveals more dirt and decaying matter until progress slows as your fingertips press into something firmer than mulch. A cluster of discarded husks lies half-buried beneath a layer of pine needles: segments of chitinous plating, translucent and stiff, tossed aside like waste.

Near those fragments, several elongated tracks sink into the loam. The impressions are wide, showing distinct points for multiple legs tipped with sharp spikes that have gouged shallow furrows in the earth. Next to one trail sits a pile of dark, oily droppings mixed with bits of crushed insect wings. These markings do not match the surrounding fauna; they suggest a body longer and heavier than anything native to these woods.

> A half hour passes in the dim warmth of the converted granary. Outside, the overcast sky holds the world in an even grey hue while inside, the smell of dry hay lingers beneath the tallow smoke. Shadows stretch longer over the floorboards.

The lithe scout hunches his shoulders further into his collar, continuing his study of the pins until he shifts his weight onto one hip. A few feet away, the scarred veteran pulls another section of wool taut between his hands, the cloth snapping with a dull thud as it clears of grit.

> The heavy door of the converted granary swings inward, revealing the dim interior held at bay by sunlight streaming through gaps in the timber walls. Dust motes dance in the light beams above a large board where scraps of parchment flutter like pinned moths.

Gorz reaches out first: he presses a thick hand against the frame as they cross the threshold.

The guild master stands center stage beneath the contracts; his high collar stays stiff even in the stagnant heat of the hall. His boots click once on the floorboards as he adjusts a paper with deliberate care.

A few paces away, the scarred veteran watches another trainee's feet hit the ground, moving only enough to signal a correction with a sharp grunt. Beyond them, several other figures move about near the clerk’s desk, their voices muffled into low murmurs that compete with the rhythmic clatter of carts rolling over stone in the square outside.

> Deep night has settled inside the old granary, and the clicking machinery buried in the walls provides the only rhythm to the stillness. You sink onto the floorboards beside Dynn, your weight pressing into the wood until she is merely a shape nearby.


### combat_opening
> The bog iron longsword leaves its scabbard with a dry rasp as you move toward the tree line. Shadows stretch like spilled ink across the clearing floor, swallowing the base of the nearest trunks. You crouch low, your green scales dull in the fading light, watching the way the wind stirs the heavy foliage.

A skittering sound clicks through the undergrowth just beyond the reach of your torchlight. Two giant centipedes emerge from the thicket; their segmented bodies ripple with a sickening fluidity over the dirt. They do not hesitate, lurching forward from opposite sides of the scrub. Their chitinous plates scrape against wood and stone alike. One stops ten paces away, its many legs tapping a frantic rhythm on the packed earth. The other remains partially veiled by thorns, only its twitching mandibles visible.

> The bustle of Parth fades behind you, replaced by the oppressive silence of the timberline. You step onto the forest floor where the grey light struggles to penetrate the dense canopy of overlapping leaves. Ahead, the woods thin out into a small clearing. It is flat ground, stripped bare except for some fallen branches, offering no cover from whatever watches from the shadows.

A sharp snap echoes from your left. 

Two hobgoblins emerge from the thicket. They do not hesitate; their muscular frames cast long shadows against the dirt as they lunge forward with serrated blades held low. Their skin has the dull hue of bruised plums, and their eyes fix on yours with focused hunger. Behind them, just beyond the reach of easy movement, rises a jagged mound of limestone rocks that serves as high ground, its surface uneven and treacherous to navigate quickly.

> The muck beneath your sabatons gives way slightly as you shift your focus, eyes tracing the oily surfaces and tangled brush. A snap of dry wood carries over the low drone of the wetlands, sharper than any frog's cry. 

Two shapes detach themselves from the gloom just ahead. They emerge from a dense stand of reeds like slick stones cast onto the mud. Lizardfolk appear suddenly: their scales are dull ochre, smeared with river silt that clings to their jagged ridges. One crouches low, spear tip dipping toward the causeway; the other stands half-hidden by a leaning dead tree, its body coiled for a spring. Their yellow eyes catch what little light remains, fixed on your heavy frame. Behind them, the reed brake shivers, suggesting others remain submerged in shadow.

> Alwick takes a measured step forward first, testing the stability of the rot-softened earth before turning back for confirmation. Beside him, the silverish pales of the birch trunks blur into a wall of vertical lines. As the party pushes deeper into this pocket of the woods, the transition is abrupt; the crackle of dry twigs at the perimeter dies away, replaced by an oppressive hush.

You lead them toward a stand of trees whose sap drips like slow tears onto the blackened mulched ground. Your boots sink slightly into the spongey carpet, each stride muffled. In the periphery of your vision, the shadows between the white boles stretch longer as the sun dips further below the horizon line. 

A low vibration travels through the soles of your iron sabatons—not a tremor in the earth itself, but something rhythmic nearby. From a dense cluster of overlapping branches to your right, a heavy weight shifts. A black bear emerges from the gloom. It stands on its haunches just twenty paces off, massive shoulders bunching under thick fur stained with forest grime. Its head lowers, snout twitching once as it exhales a huff of hot air that carries the scent of old meat and musk.


### combat_narrate
> You push into the creature's reach. Your heavy boots churn the dirt as you bridge the gap between scale and chitin.

Tamstan throws his head back. His voice carries a resonant weight that settles over your shoulders like a mantle of warmth, steadying each limb as he calls out a prayer from his hands.

Jemny blurs past the beast’s flank. He drives both daggers deep into the soft seam where segments meet, twisting one blade to find purchase in the meat beneath. A sickening crack echoes as the primary target collapses onto its side and stays there.

Rimali pulls her string taut against her cheek. She releases an arrow that finds the heart of movement for the shadowed stalker; the shaft buried so deep it pins the many-legged horror nearly motionless, leaving it shivering and broken on the mulch [h2]. 

The veiled crawler lurches forward, snapping its mandibles at your chest. Its teeth scrape across your iron chain shirt rather than finding skin, but several needle-like stingers pierce the metal links with a sharp bite [h3]. 

A sudden white heat blooms in your marrow. The venom is not a slow seep; it strikes through your veins like liquid fire.

> The larger wolf cowers for a heartbeat before it turns. It bolts into the undergrowth, its paws kicking up mulch as it vanishes into the deep shadows to escape the carnage.

The first beast lunges forward through the gloom, teeth clicking against your iron gauntlets. You step into its path and drive your weight into an overhead strike, puting every ounce of dragonborn strength into the bog iron blade. 

The steel bites deep into the creature’s skull with enough force to buckle bone and split hide in one massive impact [h1]. Its head snaps back, eyes rolling white, then the legs fold beneath its chest like wet parchment. 

It hits the ground hard and stays there.

> You heave the weight of the sword forward. The blade bites deep into the leading beast's thorax, splitting through segments of shell in a spray of dark fluid as it buckles under the force [h1]. Its legs give out all at once, and the creature collapses onto the mulch without any further movement. Beside you, Tamstan brings his mace down on the head of the other centipede; the heavy thud echoes off the nearby trunks while the insect reels back from the impact, cracked and leaking humors [h2]. Jemny darts low to find an opening, driving one dagger home against its underside joint but he only manages to nick a trailing segment before pulling away [h3]. From the rear, Rimali lets fly another shaft aimed straight at the center mass, yet the wood meets nothing but air to splinter uselessly elsewhere. The remaining beast twists toward your position, snapping its mandibles wide, only to catch empty space where your chest had been just a heartbeat prior [h5].

> You surge forward into the muck as your blade leaves the scabbard. A crack of force erupts from Alwick's staff: the lance strikes high on the beast's flank, driving deep enough to leave a jagged furrow across its hide [h1]. From his position further back, Gran looses an arrow that finds purchase between two humps along the creature’s spine, pinning the flesh tight [h2]. As you close the gap, Nedbert darts behind the massing bulk and drives one daggers home; the point slides shallowly through skin but catches nonetheless [h3]. Stillness gives way to violence when the toad snaps its head toward you. Its jaws clamp shut over your shoulder where the bronze chain shirt meets the wolf hide cap, grinding against metal before it releases your frame. You stumble back slightly, shaking off the slime, nearly unharmed.


### combat_aftermath
> The weight of the bronze blade remains in your grip, your arm trembling as the adrenaline begins to ebb. A sharp, hot needle of pain pulses in your shoulder where the bear's teeth crushed the metal links of your chain shirt, sending a dull ache radiating down to your elbow. Your breath comes in ragged hitches, the air tasting of crushed grass and the musk of the dead animal. 

Beside you, the black bear lies heavy on the earth, its massive ribs heaving one last time before stilled. Its fur is matted with dirt, and a pool of dark blood begins to seep into the dry grass beneath its flank. 

Alwick stands a few paces away, his staff still gripped in his hand, his face pale from the effort of his casting. Gran is already moving toward the tree line, his bow lowered as he scans the woods for any other movement. Nedbert stands over the bear, his chest heaving, his eyes darting from the carcass to the path behind you.

> You exhale a plume of white mist into the cold air as your sword's weight settles in your grip. The bandits lie where they fell, two shapes of heavy cloth and stillness anchored in the mud. The man you struck remains face down, his broadsword abandoned in the muck. The other man sits propped against a roadside stone, his chest cavity ruined by Alwick's magic and Gran's arrow. 

Silence returns to the King's Road, punctuated only by the distant drip of moisture from the overhanging trees. You step toward the bodies, your iron sabatons crunching on frost. You bend down, your wolf hide gloves slick with a spray of copper-smelling life, and retrieve a small pouch from the larger man's belt. You pull out a few coins, the metal cold against your palm, and tuck them away. 

Alwick lowers his staff, the glowing core dimming as the magical discharge fades. He stands nearby, his face neutral in the gloom. Gran relaxes his stance, his bow still held ready, while Nedbert emerges from the shadows of the first bandit's heap, his expression unreadable. They wait for your lead, their figures looming as dark silhouettes against the drifting fog.

> Alwick lowers his staff, the tip scraping against a plank as he takes a sharp breath. The heavy thrum of the fight fades into the hum of the wetlands. The crocodile lies twisted on the causeway, its massive ribs exposed where your blade sheared through the side. Blood flows into the cracks of the timber, turning the wood a dark, sodden crimson. Gran stands a few paces back, his bow half-drawn, while Nedbert crouches near the beast's head, his daggers still out. The cold air holds the metallic scent of the kill against the stagnant odor of the swamp.

> Alwick leans his staff against a clump of reeds and wipes a smear of slime from his cheek. The giant toad lies belly-up in the muck, its massive flank torn open by your blade. It remains motionless, a collapsed heap of grey skin and wet muscle that sinks slowly into the mire. Gran stands several paces back, his bow lowered as he scans the dark periphery of the wetlands, while Nedbert crouches by a stagnant pool, checking the edge of his blade for nicks. The only sound is the faint drip of fluid from the toad's carcass into the mud. The air holds a sharp, biting chill, and the stillness of the night returns, heavy and absolute.


### exchange
> My side is pretty much a mess after those blades hit home. Don't look at me like I'm falling over yet. Just find us something to eat for now.

> We require some shelter before evening arrives. Is there any temple near this square?

> The smoke from those hearths has a different scent than back home. It's all grit and dry wood without any real spark help. Makes it work just fine enough to keep your toes warm. Is there going to be ale here or are we just staring at the chimneys?

> Odo is clerk. Sold us out like meat on a hook. It was easy work for him. Boots had to see it too. We need to move before the word spreads further through Parth.


### dialogue_frame
> Tamsin leans back further against the wood grain, a slight tilt of his chin turning his gaze toward you. He reaches down to adjust the strap of his cloak, then looks away toward the fields.

> Rimali leans against her bow, looking across the cobbles where merchants argue over crates. 
Jemny remains leaned against the stone well, watching your reaction with half-closed eyes. Rimali steps away first, moving past a stack of wicker baskets without another glance.

> Gran shifts his weight or adjusts the grip on his bow.

> Bram settles into his seat against the timbering, one hand coming up to rest against a rough-hewn post as he looks at you. Isel remains still upon the ledge, eyes fixed on the rhythmic motion of the passing cart's wheels. A silence falls between the three of you. Tamsin turns toward the road once more, watching the dust cloud left by the carriage settle over the stones.


### npc_conversation
> Arguments? Usually it's just someone whining about their pay or some contract not being finished on time. Or maybe who gets to take first pick at a good haul when they come back.

> It keeps my eyes open for those who think they know more than they truly do.

> I cannot tell you any such thing. Most folks only report what they saw in passing, which is usually just a shadow or a broken branch and little else.

> Fair enough as far as they go—I like to keep things honest between friends, even if we haven't shared many stories yet. As for the old bits... well, most of my stock is fresh enough to eat before it goes south, but I reckon those sturdy oak beams holding up the main rafters are the real veterans here. They've seen more winters and damp nights than I care to count.


### hire_chat
> Fair enough. We can find somewhere decent to rest, even if we have to wait for that man in the doorway to finally fall into a deeper sleep.

> That work is for people with more strength than us. We stay on simple task.

> Not many do it as a job these days. Most people just want to get on with the farming part of it once they're grown. I haven't met someone like that since we left my home.

> I did my time there among the hills like everyone else. Most folks here lived that life before they found work elsewhere.


### mentor_chat
> I'm an A rank. It took some time, staying at F for longer than most folks I started with... but it's about getting things done right.

> Worried's a bit strong a word for it. They aren't exactly cuddly, that much is true. But I've handled my share of teeth before.

> Not many folks close by these days. Mostly just stories about them that I keep to myself.

> It's mostly about who has the better reach and more practice. Generally, if you're even with someone, you've got about a three-quarters chance to land a strike. It goes up when you have the high ground or gear that sharpens your eye for openings. If they're fast enough to dodge most things or pull off some trickery like getting blinded, it drops down quick.

