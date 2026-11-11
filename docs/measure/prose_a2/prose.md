| task | passages | words | repeated phrases /1k | repeated sentences /1k | shared openings | worn words | worn uses /1k | stock phrases /1k |
|---|---|---|---|---|---|---|---|---|
| narrate | 180 | 23916 | 9.24 (+3.58) | 0.00 (+0.00) | 27% (+11%) | 31 (+0) | 23.12 (+4.41) | 0.54 (+0.40) |
| combat_opening | 29 | 4236 | 5.19 (-2.20) | 0.00 (+0.00) | 7% (+7%) | 11 (+4) | 14.87 (-0.75) | 0.00 (+0.00) |
| combat_narrate | 53 | 8223 | 17.02 (+3.02) | 0.00 (+0.00) | 51% (-16%) | 16 (+9) | 15.57 (+8.86) | 0.00 (+0.00) |
| combat_aftermath | 47 | 7535 | 31.85 (+9.16) | 0.00 (+0.00) | 32% (+12%) | 21 (+4) | 29.06 (+2.70) | 0.27 (+0.27) |
| exchange | 86 | 3621 | 9.11 (+3.77) | 0.28 (-0.65) | 33% (+4%) | 6 (+0) | 11.32 (+1.34) | 0.00 (+0.00) |
| dialogue_frame | 141 | 7393 | 18.40 (+3.32) | 0.00 (+0.00) | 30% (+1%) | 15 (+1) | 28.81 (+6.73) | 0.14 (+0.14) |
| npc_conversation | 93 | 2370 | 14.77 (+13.13) | 1.69 (+1.69) | 16% (-0%) | 3 (+1) | 6.75 (+0.18) | 0.00 (+0.00) |
| hire_chat | 111 | 1834 | 1.09 (-5.22) | 0.55 (-0.43) | 14% (-9%) | 1 (-1) | 2.18 (-2.19) | 0.00 (+0.00) |
| mentor_chat | 15 | 504 | 29.76 (+9.54) | 0.00 (-6.74) | 47% (-20%) | 0 (+0) | 0.00 (+0.00) | 0.00 (+0.00) |

- **narrate**: repeated phrases: carries the scent of damp, the board of pinned contracts, the scent of damp earth, a few paces away the, into the center of the; openings: the tilted plough, you step past, the cool air, the roar of, the heavy door; worn: heavy, steady, sharp, small, slight, rhythmic, slow, dull
- **combat_opening**: repeated phrases: detach themselves from the gloom, figures detach themselves from the, they move with fluid grace, any sound reaches your ears, before any sound reaches your; openings: you scan the; worn: heavy, rhythmic, dull, massive, sharp, slight, bare, simply
- **combat_narrate**: repeated phrases: links of your chain shirt, longsword in a wide arc, h at the same time, the bronze links of your, the force of the strike; openings: you lunge forward, you pivot your, you shift your, you step forward, you step into; worn: heavy, massive, simultaneously, dull, sharp, chitinous, instantly, harmlessly
- **combat_aftermath**: repeated phrases: stands a few paces back, a few paces back her, a few paces back his, a few feet away the, hedna stands a few paces; openings: you lower your, the wolf lies, the iron of, your arm vibrates, the bugbear lies; worn: heavy, dull, sharp, steady, small, motionless, gaze, pale
- **exchange**: repeated phrases: feels like it was kicked, if you could step back, like it was kicked by, rib feels like it was, someone who wants to get; openings: good afternoon maren, these houses look, it is just, this town has, rib feels like; worn: heavy, steady, tired, properly, sharp, slow
- **dialogue_frame**: repeated phrases: crossing his arms over his, his arms over his chest, groaning under a load of, his gaze back to the, his grip on his staff; openings: bram shifts his, bram leans his, the wind pulls, you stand in, bram leans back; worn: heavy, gaze, slight, steady, rough, slow, flat, sharp
- **npc_conversation**: repeated phrases: keep your wits about you, 'high tier' work available right, afraid our current board doesn't, available right now most were, before you head off then; openings: safe travels then, is there anything, you are welcome, of course safe, i'm afraid our; worn: folks, exactly, heavy
- **hire_chat**: repeated phrases: am ready when you are, i am ready when you; openings: it's fine just, i come from, not many people, do you want, right behind you; worn: steady
- **mentor_chat**: repeated phrases: about more than just swinging, if you're even with someone, it's about more than just, you're even with someone else, about three out of four; openings: it's about more, i'm at a, i've got my; worn: none

## Over draws of a fixed size (mean [10th, 90th]) against ../prose_baseline/new1/prose.json, ../prose_baseline/new2/prose.json

| task | drawn | repeated phrases /1k | repeated sentences /1k | shared openings | worn uses /1k |
|---|---|---|---|---|---|
| narrate | 40 passages of 180 | 2.87 [1.49, 4.33] holds | 0.00 [0.00, 0.00] holds | 8% [0%, 15%] holds | 17.64 [14.73, 20.76] worse |
| combat_opening | 12 fights of 29 | 2.52 [0.00, 6.13] holds | 0.00 [0.00, 0.00] holds | 2% [0%, 17%] worse | 5.34 [3.47, 7.67] holds |
| combat_narrate | 12 fights of 29 | 8.74 [5.34, 11.66] holds | 0.00 [0.00, 0.00] holds | 40% [26%, 54%] holds | 9.33 [6.63, 11.73] worse |
| combat_aftermath | 12 fights of 29 | 19.73 [15.23, 24.58] holds | 0.00 [0.00, 0.00] holds | 25% [10%, 40%] holds | 21.59 [17.59, 25.53] holds |
| exchange | 60 passages of 86 | 6.94 [4.50, 9.23] holds | 0.17 [0.00, 0.41] holds | 29% [23%, 35%] holds | 8.49 [5.93, 10.73] holds |
| dialogue_frame | 90 passages of 141 | 13.52 [10.37, 16.95] worse | 0.00 [0.00, 0.00] holds | 23% [18%, 28%] holds | 27.51 [25.37, 29.70] worse |
| npc_conversation | 30 passages of 93 | 6.01 [0.00, 21.95] worse | 0.63 [0.00, 2.47] worse | 6% [0%, 13%] holds | 1.43 [0.00, 5.51] holds |
| hire_chat | 60 passages of 111 | 0.65 [0.00, 2.07] holds | 0.33 [0.00, 1.03] holds | 8% [3%, 13%] holds | 0.38 [0.00, 0.00] holds |
| mentor_chat | 20 passages (short: 15) | 29.76 [29.76, 29.76] - | 0.00 [0.00, 0.00] - | 47% [47%, 47%] - | 0.00 [0.00, 0.00] - |

## Sample passages
### narrate
> You pull the bog iron sword toward your chest, dragging it slowly across the matted pelt. Ribbons of blood transfer from the steel to the coarse hair until the blade gleams dull and clean. You turn away from the carcass.

Jemny pulls back slightly, startled by the sudden motion. Behind him, the shadows of the Greywood press inward against the hollow. A soft rustle comes from the brush where Rimali waits; she does not lower her aim but tilts her head to track your direction.

> The ground yields beneath your slippers as you step past the dead spider, leaving the open trail for the thickening gloom of the thorn grove. Sharp briars hook at your wool hood, weaving a tangled gate that guards the interior. Beneath these protective spines, broad leaves fan out over beds of wild garlic; its pungent, earthy scent rises sharply in the cooling air to mingle with the smell of damp mulch. Shadows stretch long across the floor, swallowing the spaces between crooked trunks where moisture clings to the bark.

You move forward while scanning the gray pillars of wood behind the brambles. The overcast sky offers no help, casting a flat evenness over the forest that makes depth harder to judge. There is only the low rustle of foliage and the weight of the silence pressing against your ears.

> The search yields no secrets; every floorboard stays silent underfoot, and the few crates remaining since those contracts were posted hold nothing but dust.

> The mist clings thick to the pass, blurring the line between gray sky and frozen earth. You select four smooth, slate-colored rocks near a huddled clump of scrub brush and arrange them into a rough bed on the dirt.

You lie back onto them, the weight of your iron sabatons pressing into the grit while Frib pulls off his boots and sets his gear aside nearby. For nearly three hours, the world hums in a dull drone around your rest.
The frost hardens on the edges of the spilled brass gears and leaves glistening beads of ice atop the man's shivering form. Shadows shift over the ravine as the sun struggles through the fog, casting long, pale streaks across the overturned cart. By the time you stir, Dynn sits poised with her bow, watching the silence move like water along the ridge.

A dwarf hunches over a piece of timber a short distance away: he works an oily spring inside its housing with calloused fingers even as others watch from the shadows of the road.


### combat_opening
> The soft crunch of needles underfoot ceases as the density of the pines swallows the remaining grey light. You step forward, hand tight on the hilt of your longsword, searching for any movement in the tangle of branches.
A skittering sound erupts from beneath a heap of dry needles to your left. Two multi-eyed shapes peel themselves out of the leaf litter, their bodies sleek and dark. They are low to the earth, twitching their pedipalps as they fan out to flank you. 

Further back, tucked deeper within the hollow of an adjacent tree, another pair of eyes glints behind a lattice of fresh silk. These spiders do not hesitate; they rise onto their legs simultaneously, the collective clicking of their joints sharp in the still air. One moves toward your side, its front limbs reaching out like hooked fingers.

> You turn your gaze toward the crumbling ribs of the ruins, searching the hollow spaces between cracked pillars for anything with breath or scale. A sudden crack of frost splitting stone breaks the monotony of the whistling wind.

A shadow detaches itself from a pile of fallen lintels just paces away. Mud caked into its hair dries white like salt, leaving only smears across skin flushed raw by the cold. This man does not hesitate; he lunges forward, his teeth bared and hands curled into fists aimed at your chest.

The berserker's heavy boots strike the scoured shelf of rock behind him, kicking up a spray of shale bits. He moves with a desperate, clumsy speed, driven by some jagged fever.

> The silence of the woods feels heavier than before, pressing against your ears until any sound becomes an intrusion. Just as the shadows seem to settle, a wet click echoes from within the dense wall of briars to your left. The thorns do not part so much as they shudder.

A massive shape lunges forward, erupting from the dark tangle like a piece of living coal. It is a wolf spider, its body a bloated mound of mottled hair and chitinous plates. Its eight eyes catch what little light remains, reflecting amber pinpricks of focus. 

The creature lands on the trail ahead of you, its weight causing it to sink slightly into the soft earth. It arches its front segments, mandibles twitching as they drip a clear, viscous fluid onto the dirt. With a sudden, violent tremor, it prepares to spring toward your chest.

> The owl does not flee. Its pupils stretch wide, swallowing the gold of its irises even as it reacts to your motion. With a sudden snap of wings that sounds like heavy canvas tearing, it drops from the branch.

It lands a few paces away in the mulch, its talons digging deep furrows into the earth. The bird is massive, built for crushing bone rather than mere hunting, and it hunches low against the ground between your legs. Feathers flare out around its body, creating a silhouette of jagged edges in the dying orange light. A lowen hiss vibrates through its beak; the creature's weight shifts forward, preparing to spring at any moment while keeping itself anchored by its powerful grip.


### combat_narrate
> You lunge forward as the creature coils. Your longsword bites deep into its thorax, splitting more chitin in a spray of dark fluid.

Hedna releases her string from behind you; an arrow whistles through the gloom to bury itself firmly in the beast's joint.[h2]

Gwild blurs past the tangle of vines, driving both daggers home while it twists against its flank.[h3]

Gharta brings his shield up to meet a desperate lash, then swings out for a heavy strike that skims across the monster's rear.[h4]

The weight of your combined steel overcomes it. The giant wolf spider buckles, legs folding inward until its head strikes the mulch with a dull thud.

> You dig your heels into the dirt and pivot, putting every ounce of your weight into a sweeping strike. Your longsword carves through the air in an arc that catches the center of the boiling mass, the iron blade biting deep into several shells simultaneously to send them tumbling away from you. A sickening crunch echoes as the heavy swing shears limbs and bodies alike, collapsing their frantic motion in one violent stroke. One by one, the twitching forms fall silent against the needles, piling onto themselves until none remain moving [h1].

> You pivot your weight onto your back foot, swinging your iron longsword in an wide arc that cuts through the falling rain. The blade connects squarely against the creature’s side, meeting resistance before shearing into its flesh to drive it toward the mud. It groans under the force of the strike, legs trembling as it struggles for purchase [h1]. From behind you, Frib snaps his staff forward again, another bolt of raw energy striking home like a physical hammer to find meat between ribs [h2]. Simultaneously, Calsa lunges from her position by the barrels, bringing both shield and steel crashing down; she slams her weapon into the beast's spine with such momentum that the ground beneath them gives way further.

The lesser drake lets out one final, wet hiss. Its strength fails completely as its head drops into the mire, limbs folding limp until the body settles deep into the sludge without moving once more [h3].

> You shift your weight, muscles coiling under the iron chain shirt. Your bog iron longsword arcs in a wide, punishing sweep, catching the great bird mid-lunge. The blade bites deep into its flank, shearing through feathers and bone alike until it meets resistance elsewhere. A heavy thud follows that massive impact [h1]. The owls wings splay out like broken fans before it slams onto the dirt, motionless beneath you.

The creature lies there still even as the grit of the trail settles over its plumage. No more trills break the silence of the Greywood.


### combat_aftermath
> Your chest heaves, each breath a sharp reminder of the pressure against your ribs. The weight of the bog iron longsword feels heavy in your grip, the blade still raised as the adrenaline begins to ebb. A dull throb radiates from your side, where the centipede's mandibles buckled your chain shirt and sent a jolt of heat through your scales. 

Tamstan stands over you, his face set in a mask of concentration. He presses a hand to your side, and a soft, golden warmth flows from his palm into your skin, dulling the sharpest edge of the ache. Nearby, the two centipedes lie motionless on the dirt; their obsidian-dark plates glint in the dying light, one twisted to its side and the other pinned to the earth by Rimali's shaft. 

Jemny and Rimali move back toward you. Jemny wipes a smear of grime from his cheek, his breathing steadying as he surveys the fallen. Rimali remains a few paces back, her bow lowered, her gaze scanning the shadows of the Greywood for any lingering movement. The woods have returned to a heavy silence, broken only by the distant creak of a branch.

> The lizardfolk’s head rests at an impossible angle, eyes clouded and fixed on the black silt. It lies on its side, a heap of dull scales and cooling meat, its tail curled into the mud like a discarded rope. A few paces off, its mate remains huddled, its chest heaving in rapid, shallow bursts that stir the freezing air. The creature watches the edge of your bronze sword, its nostrils flared, shivering with a low, guttural rattle. 

Behind you, the companions shift. Alwick, Gran, and Nedbert stand in the shadows of the willow stalks, their faces unreadable in the moonlight. They wait for your word, their stances braced and ready. 

You step over the mangled corpse, the mud sucking at your iron sabatons. The lizardfolk’s belt is a mess of grime and leather, but you find the pouch. You hook a finger into the opening and draw out a small collection of coins. They are heavy, the metal slick with swamp water, and you slide them into a pocket of your hide-clad gear. 

The only sound in the wetlands is the wet rattle of the survivor’s breath and the rhythmic drip of water from the overhead branches. The swamp is a wall of grey and black, holding its breath as you stand over the dead.

> Moonlight shears through the overhead canopy, casting sharp, white needles of light across the Willowmead wetlands. The air holds a biting chill that turns the breath into pale plumes of mist. 

Silence settles over the causeway, heavy and thick. The mud remains churned and slick where the struggle ended. The first lizardfolk lies twisted in the silt, its chest cavity opened by your bronze blade, while the third remains slumped against a reed stalk, its life spent in the muck. Between them, the second creature huddles in the reeds, its breathing shallow and ragged, scales coated in grey silt as it watches your shadow. 

Alwick, Gran, and Nedbert shift behind you. They stand clean, their gear intact, the only sign of the fray being the tension in their shoulders. 

You reach down into the mud near the fallen. Your fingers close around three coins, the metal cold and slick against your palm. You tuck them away into your pouch, the small weight a tangible prize of the skirmish. The rest of the loot remains in the dirt, overlooked and left to the swamp.

> The iron of your longsword rests against the mud, its edge coated in a slick, dark film. A few feet away, the spider lies prone, a heap of broken chitin and twitching limbs. Its thorax is split open, leaking a thick fluid that bubbles into the dirt. Beside you, Gharta, Hedna, and Gwild stand in a tight circle, their breaths coming in steady plumes. They do not speak; the only sound is the wet drip of ichor hitting a fallen branch. The overcast sky presses down, casting a flat, dull light over the carcass. No loot lies within reach, only the remains of the thing that tried to hunt you.


### exchange
> That rib feels like it was kicked by a mule again. It won't be much better until we find some actual food. Are you looking for work or just passing through?

> The timber work on these houses has a similar grain to back home in the Great River country. It looks like plenty of wood used just to keep out the damp. You're fussing over the architecture while your blade is still covered in road grit. How long do you plan on polishing that steel before we find a bed? Is there much time left before sundown? Boots here seems ready for an inn already.

> Odo was trusted to protect our path. Trust is a heavy coin when it gets traded by some clerk's hand.
How many more of these sell-outs are we going to find? Better one than any amount in the Greywood.
You think Boots saw him do it?

> The path ahead isn't looking very smooth. My boots will thank us if we find some flatter ground soon.


### dialogue_frame
> You stand beneath a sturdy lintel where the scent of roasting grain mingles with damp earth. Beside you, Bram pushes himself slightly forward from the timber wall while Isel takes a step into the curve of the archway. Tamsin stays leaned against the doorframe, hands tucked deep into the folds of a patched sleeve. Bram gives a short grunt of agreement and begins to turn away towards the center of the thoroughfare.

Tamsin shifts his weight on his heels as he watches the next merchant's wagon roll past.

> Alwick stops his circling motion on the weathered stone. He remains still for a heartbeat, looking toward a cluster of particularly tall reeds.

> Bram finds a spot beside you against the rough siding, folding his arms across his chest. The rhythmic thud of heavy wheels on dirt signals another cart moving along the trade road. Tamsin stops by the doorway where the warm air spills out over the cooling stones. Tamsin offers a faint grin and remains still, watching the shadows stretch further across the street.

> Alwick tightens his grip on his staff as he listens.


### npc_conversation
> I have that right here from this morning's notes. Everything is accounted for, and I've marked the hunt as complete.

> I do not know for certain. This inn has stood since before my memory began.

> Not at this hour. Most folk are headed home or already tucked away. If you’re looking for Geir Heyshaw, he’s usually at the trading square by now anyway.

> A room for night costs forty five copper.


### hire_chat
> Greywood holds many things that do not wish for us here. I will keep watch.

> Troll are large. Many teeth and heavy skin. We must be very careful.

> Not many people nowadays stay that long on the hill-side. Most just want the easiest path through the grass.

> Not many people anymore these days stay that long on one hillside before moving on. It's an honest enough life compared to city grime.


### mentor_chat
> I'm at A rank.

> Worried isn't usually good for business. Besides, I know these woods well enough to keep us out of trouble most of the time. Just stay close.

> I've got my brother,

> It's about more than just swinging your sword at the right time. Most of the time—about three out of four times—you'll land a solid blow if you're even with someone else like yourself.

