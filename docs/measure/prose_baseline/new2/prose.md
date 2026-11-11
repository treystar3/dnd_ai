| task | passages | words | repeated phrases /1k | repeated sentences /1k | shared openings | worn words | worn uses /1k | stock phrases /1k |
|---|---|---|---|---|---|---|---|---|
| narrate | 192 | 24083 | 5.86 | 0.00 | 10% | 31 | 18.73 | 0.08 |
| combat_opening | 15 | 2006 | 8.97 | 0.00 | 0% | 2 | 6.48 | 0.00 |
| combat_narrate | 21 | 3064 | 6.20 | 0.33 | 33% | 3 | 4.24 | 0.00 |
| combat_aftermath | 20 | 3148 | 25.09 | 0.00 | 30% | 9 | 20.01 | 0.00 |
| exchange | 91 | 3902 | 8.97 | 1.02 | 25% | 7 | 11.28 | 0.00 |
| dialogue_frame | 144 | 7087 | 14.39 | 0.00 | 21% | 16 | 27.37 | 0.00 |
| npc_conversation | 84 | 2031 | 0.00 | 0.00 | 5% | 3 | 5.91 | 0.00 |
| hire_chat | 117 | 1890 | 4.76 | 0.53 | 16% | 3 | 7.41 | 0.00 |
| mentor_chat | 15 | 551 | 10.89 | 0.00 | 47% | 0 | 0.00 | 0.00 |

- **narrate**: repeated phrases: at the edge of the, the center of the room, at the base of a, center of the room the, he does not look up; openings: the trading square, the king's road, the transition from, the salt road, your fingers sink; worn: heavy, sharp, steady, small, slow, rhythmic, soft, motionless
- **combat_opening**: repeated phrases: a low vibration travels through, are close enough that you, at your chest while the, close enough that you can, do not call out or; openings: none; worn: heavy, dull
- **combat_narrate**: repeated phrases: blade bites deep into the, a surge of heat travels, an arrow that streaks through, arrow that streaks through the, h it drops instantly hitting; openings: you pivot your, you lunge forward, you surge forward; worn: simultaneously, instantly, sharp
- **combat_aftermath**: repeated phrases: stands a few paces back, a few paces back her, a small leather pouch lies, as she watches the treeline, broken only by the distant; openings: you plant your, the weight of, tamstan exhales his; worn: steady, heavy, small, dull, sharp, rhythmic, handful, motionless
- **exchange**: repeated phrases: it is just a scratch, do what you have to, odo i brought someone along, what you have to do, afternoon maren hello again odo; openings: good afternoon maren, it is just, these houses look, it just feels, tamsin she is; worn: heavy, properly, steady, folks, quick, quiet, regardless
- **dialogue_frame**: repeated phrases: adjusts the strap of his, bram lets out a short, crossing his arms over his, his arms over his chest, the rough masonry of the; openings: bram shifts his, you stand near, you lean against, bram leans back, nedbert leans back; worn: heavy, gaze, slight, flat, rough, steady, sharp, slow
- **npc_conversation**: repeated phrases: none; openings: have a safe, safe travels then; worn: folk, heavy, usually
- **hire_chat**: repeated phrases: he does not waste words, does not waste words or, enough at tracking i suppose, feet dry on these mud, he is honest man he; openings: i am ready, i do not, i come from, he is honest, she did her; worn: heavy, steady, useful
- **mentor_chat**: repeated phrases: about three out of four, because they didn't know which, i've seen too many people, it gives you an edge, land about three out of; openings: i've seen too, i'm an a, i've dealt with; worn: none

## Over draws of a fixed size (mean [10th, 90th])

| task | drawn | repeated phrases /1k | repeated sentences /1k | shared openings | worn uses /1k |
|---|---|---|---|---|---|
| narrate | 40 passages of 192 | 1.80 [0.81, 2.92] | 0.00 [0.00, 0.00] | 3% [0%, 5%] | 11.94 [8.95, 14.73] |
| combat_opening | 12 fights of 15 | 7.02 [3.73, 11.11] | 0.00 [0.00, 0.00] | 0% [0%, 0%] | 5.38 [4.25, 7.03] |
| combat_narrate | 12 fights of 15 | 5.08 [4.28, 5.98] | 0.27 [0.00, 0.43] | 29% [20%, 35%] | 2.58 [1.60, 3.53] |
| combat_aftermath | 12 fights of 15 | 22.11 [18.38, 24.99] | 0.00 [0.00, 0.00] | 31% [24%, 38%] | 18.34 [15.99, 20.22] |
| exchange | 60 passages of 91 | 8.98 [5.50, 11.59] | 0.90 [0.00, 1.60] | 23% [17%, 28%] | 8.93 [6.67, 11.67] |
| dialogue_frame | 90 passages of 144 | 10.47 [8.51, 12.31] | 0.00 [0.00, 0.00] | 16% [11%, 20%] | 25.20 [23.23, 27.23] |
| npc_conversation | 30 passages of 84 | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 2% [0%, 7%] | 0.26 [0.00, 0.00] |
| hire_chat | 60 passages of 117 | 2.10 [0.00, 6.05] | 0.18 [0.00, 1.01] | 11% [7%, 17%] | 1.93 [0.00, 4.47] |
| mentor_chat | 20 passages (short: 15) | 10.89 [10.89, 10.89] | 0.00 [0.00, 0.00] | 47% [47%, 47%] | 0.00 [0.00, 0.00] |

## Sample passages
### narrate
> The leather of your glove creaks as you scoop up the final blade of grass. It feels waxy against your palm, cool enough to sting even through the fur of the hide. You tuck it away, though its value lies only in the fact that you possess it now.

Ahead, the trees lean inward, their trunks narrowing the path to a corridor of dripping wood. A thick droplet falls from a branch above, striking a protruding root with a sharp crack that echoes briefly before dying. 

The shadows beneath the overarching boughs do not shift; they remain anchored in the deep recesses between bark and mossy trunk. Every time a mist-heavy breeze stirs the fronds behind you, something deeper in the woods produces a dry snap—the sound of timber giving way under weight or pressure.

> You move among the swaying grains for half an hour, plucking at weeds as you navigate the narrow path. Each find goes straight into the lining of your clothing: first the sharp scent of yarrow, then another clove of wild garlic. 

You lean forward once more to probe the mire near the root line. The earth yields beneath your palms, swallowing several inches before holding firm. As you wrench your hands back out from the muck, there is a wet snap of soil separating from the floor. Your bear hide gloves come up heavy with grit, leaving long streaks of dark slime across the surface of the track where the dirt had been dry seconds ago.

> Your foot meets the clod of dirt, kicking away the remaining grit to reveal the underside of the husk. The shell lies split open like an empty vessel, showing nothing but pulped meat and broken fibers inside.

You move back to scanning the immediate area as shadows lengthen against the trees. After watching the surrounding foliage for some time without seeing another creature emerge, you spot evidence left behind by larger kin. Deep indentations mark the soft earth near the center of your position, formed by pointed limbs pressing down hard enough to leave lasting grooves._ Beside these marks, dollops of thick, translucent waste cling to the grass, while several nearby roots show raw gashes where heavy bodies were hauled past them.

> No single person identifies themselves clearly as an official guide or scout standing apart from the flow of the crowd. Instead, the seekers are found nestled within the throng: local traders with calloused palms and travel-worn faces leaning against cart frames, offering news for coins. Men with steady gazes stand beside piles of grain sacks, gesturing toward the road leading north past the Greywood. They speak in low tones about paths through the mire.


### combat_opening
> You move past the cooling carcass, boots crunching over dead leaves and broken twigs while you scan for anything left behind by the predators or their previous kills. Your shadow stretches thin across the forest floor as the light begins to fail.

Movement breaks the stillness twenty paces ahead. Two giant wasps hover near an old stump, their chitinous bodies gleaming dull amber against the deepening gloom. They do not strike; instead, they fan their wings in rhythmic pulses that kick up puffs of dust from the dry earth. One vibrates its thorax, producing a sharp, buzzing trill that echoes off the surrounding trunks—a warning held steady between them and your position. Beyond them, the trees grow dense enough to swallow shapes whole, leaving only patches of fallen timber scattered like discarded bones.

> Your gauntleted fingers press into the muck beside the pellet pile as you lean forward, searching for something more than just tracks.

A sudden crack erupts from the brush behind you. 

You turn. Two wolves emerge from the charcoal silhouettes of the pines. Their fur is matted with burs, their yellow eyes reflecting what little light remains before they snap into motion.

They do not howl. They drop onto all fours, muscles bunching under sleek coats as they eye your heavy frame. The forest path offers nothing but open dirt between you and the predators, while the narrow game run provides only enough room for one beast to lunge at once. To your side, the creek bed flows over jagged stones, its muddy bank offering the only sturdy cover near the trail.

> Your attention shifts from the shivering soldier to the heavy silence surrounding the scouting party's remains. Your gauntleted hands work the thief's equipment, moving past the dry dregs of those crackled glass tubes as you tuck the scraps into a pocket.

A low vibration travels through the soles of your sabatons before sound reaches you. From the shadows where the trees knit together like fingers, the undergrowth parts. Two wolves emerge onto the trail.

They do not bark or whine; their hackles rise in stiff ridges against their fur. They move in tandem, eyes reflecting the moon like shards of ice,

drifting out from the darkness toward your position. One circles wide towards the creek bed while the other holds center on the path. Their teeth stay bared even as they remain several paces off, measuring the distance between your iron-clad form and their reach.

> The silence that follows holds until a low vibration travels through the soles of your sabatons. From across the channel where the Great River spills into stagnant pools, something shifts in the reeds. 

A massive head breaks the surface like a mossy stone rising from the muck. It sits motionless twenty paces away, a giant toad with skin mottled like bruised plums. Its throat sac expands and contracts, pushing a wet, rhythmic croak into the chill air—a warning note aimed at the narrow causeway ahead.

The ground beneath your feet narrows to a muddy spine of earth between the channels. To your right, an ancient tree leans nearly horizontal over the path, its bark stripped away to expose silver-grey wood that offers a solid sanctuary against the dark. Beyond you, Dynn remains still as her fingers continue their silent count, but forward, the marsh feels suddenly occupied.


### combat_narrate
> The soldier who held your front snaps his spear against a tree trunk, letting it clatter into the mulch before he drops to one knee. He watches in terror as you pivot toward its companion. With a guttural heave of effort that ripples through your chest, you swing the bog iron blade. It connects with the core of the warrior's torso with such violent force that its spine buckles instantly.

The impact is absolute. Ribs cave inward and muscle tears away from bone under the weight of your strike [h1]. The creature crumples like a discarded husk, hitting the dirt hard enough to kick up a spray of needles. Nearby, the other scout reels back, eyes wide as its comrade collapses; it stands paralyzed, breathless and broken, staring at the gore blooming across the grass.

> You surge forward into the reach of the secondary threat as your shadow swallows its segmented flank.

Tamstan lifts his palm toward your group, and a low murmur leaves him;
a sudden warmth anchors your limbs, making each movement feel precise.

Jemny blurs to your side. He sinks his daggers deep into the plush underside of the moving insect;
the strike finds purchase in its core, and the creature's form buckles under the force [h1]. 
The muscle gives way completely, and the bruised purple carcass thuds onto the mulch without stirring again.

Rimali pulls back her string from the rear line. She releases an arrow that streaks through the air like a needle,
striking home where one of the primary beast’s legs meets its thorax; the impact pins the limb against the soil, and its movements falter [h2]. 
The first centipede reacts by lunging at you; its mandibles snap shut on empty space just inches from your chest plate [h3].

> You bridge the gap between yourself and the twitching horror. A warmth spreads through your limbs as Tamstan lifts his palm to the air, casting a prayer that settles into your muscles like steady iron. From the side of the clearing, Jemny blurs into motion, slipping past the creature's flank to sink both daggers deep into its thorax. The hit lands with sickening force [h1]. The second centipede buckles, its oily plates rattling against one another before it collapses onto the silt. Simultaneously, an arrow from Rimali finds the seam where those heavy legs meet the body; she pins the remaining beast to the earth with such violence that chitin splinters fly [h2]. It writhes once, then grows still in the mud. Sensing their kin falling, the first centipede lunges at you, snapping its mandibles toward your chest. You pivot just enough that its teeth find only empty space above the dirt [h3].

> You pivot toward the silver wood at the edge of the path. Your sabatons sink into the silt as you move past the causeway, positioning yourself beside the trunk. From his spot back near the ferns, Frib thrusts out his staff, calling forth a lance of crackling force that streaks across the marsh; the beam strikes nothing but mist before vanishing [h1]. Beside him, Calsa moves her shield forward, sliding over the mud until she takes up space against the rotting timber. She settles into an aggressive crouch behind the bark. In the distance, the bowstring snaps as Dynn releases a shot aimed at the massive throat sac, but the arrow finds only the reeds in front of the creature's head [h2]. You step out from the protection of the tree to close the gap between you and the beast. You swing your iron longsword with every ounce of weight behind your shoulders, meeting meat and bone.[h4] The strike lands like a falling hammer, carving deep through its mottled hide. Then, the air is filled by a sudden surge of motion. The toad’s jaws snap shut just inches from your chest, the teeth clicking together. It grazes your breastplate, leaving barely a scratch on any skin beneath while throwing sparks off your chain shirt.


### combat_aftermath
> The wet snap of a rib cage settling into the dirt is the last sound of the struggle. Silence returns to the Greywood, thick and heavy, broken only by the distant rush of the creek. The two wolves lie in the dirt, their fur matted with grit and cooling blood, bodies still heavy and whole against the forest floor. Tamstan lowers his hand, the faint glow of his prayer fading into the shadows. He stands a few paces back, his breathing steady as he surveys the pair of beasts. Jemny crouches nearby, his blade dripping, while Rimali remains poised with her bow, her eyes scanning the treeline for any more movement. They wait for your lead, their faces shadowed by the moon.

> Your arm thrums with a steady, heavy vibration from the impact. The bronze longsword remains leveled, its tip hovering inches from the second creature's throat. A sharp ache blooms in your shoulder, a dull protest from the muscle that drove the blade home. The lizardfolk before you lies heaving, its belly dragging in the silt, its golden eye fixed on yours in a desperate plea for life. 

Beside you, the mud is churned and slick. The first lizardfolk remains motionless, its chest cavity caved in, one arm outstretched toward the reeds. You reach down and hook your fingers into a small pouch of coins that spilled from its belt. The metal pieces are cold and slick with slime as you pull them into your palm, tucking them away. 

Alwick, Gran, and Nedbert stand in a semicircle behind you. They do not move, their breathing the only sound in the wetland besides the distant, lonely croak of a frog. They wait, eyes shifting between the fallen beast and the one still shivering in the dirt. The moon hangs high and white, casting long, jagged shadows across the reeds.

> A sliver of moonlight cuts through the cloud cover, turning the stagnant pools of the Willowmead wetlands into sheets of hammered silver. The air holds a bite that stiffens the reeds, and the only movement comes from the slow, oily ripple of water where the bodies rest. 

To your right, the first lizardfolk lies twisted in the mud, its chest cavity collapsed by Alwick's strike. A few feet away, the third creature remains pinned to the swaying stalks, its neck opened by Nedbert's daggers. You look down at the second lizardfolk; it lies on its side, chest heaving in shallow, jagged bursts. Its golden eyes are clouded, watching you with a dull, vacant stare as it waits for the end. 

Nedbert wipes a smear of dark blood from his cheek, his small frame tense as he stands over the fallen. Alwick lowers his staff, the hum of magic fading into the chill air, while Gran remains a shadow at the rear, his bow still gripped in his steady hands. 

Near the twitching claws of the yielding beast, a small leather pouch lies half-submerged in the silt. You reach down, your wolf-hide glove slick with slime, and pull it from the muck. You thumb the drawstring and find a handful of copper coins, the metal cold against your palm. You tuck them into your belt, the weight a small comfort against the oppressive quiet of the marsh.

> You plant your feet, the weight of the longsword pulling at your shoulders as the final tremor leaves the insect's body. The heavy thump of its collapse settles into the mud, muffling the remaining clicks of its chitinous plates. A thick, metallic fluid pools around the broken thorax, soaking into the greywood soil. You stand tall, your green scales catching the fading evening light while the silence of the woods rushes back in to fill the space the struggle occupied. 

Tamstan exhales a steady breath, lowering his hand as the holy hum of his voice fades into the shadows. He moves to your side, his boots sinking slightly into the soft earth. Behind you, Jemny shears a stray piece of shell from his dagger and wipes the blade on his tunic, while Rimali stalks forward to inspect the fallen. She stands over the second centipede, her bow still gripped firmly in her hand, looking down at the dark line of fluid staining its shell. The two carcasses lie motionless in the loam, their segmented bodies half-buried in the dirt where they fell.


### exchange
> It still stings when I move my shoulder too fast. Let it be. We need to find an inn before dark so we can get some rest on these legs.

> It feels different than the scouts camp back home. They do everything with that stone rubbing, no sparks out of thin air. Takes more work but it means we aren't drawing unwanted eyes just by trying to start a fire like some mountain folk would. You planning on finding us something to eat first or are you looking at those fields?

> Trust is... broken. Odo sold us out like a side of beef to those bastards. We need to find where he's hiding Boots before we go looking for him again.

> Steady now. We keep our feet light until we clear the first stretch. Long-legs has led us this far enough for today. Better move while there is still some bit of day left on the road.


### dialogue_frame
> Tamsin shifts his weight onto his heels; he keeps his eyes forward until you speak. He offers a short half-smile, then takes another step toward the center of the path.

> The sharp-eyed scout pulls her gaze from the pinpricked notices on the wood. She lets one hand rest against a leather bracer before turning toward you. She shifts her weight onto one foot as she considers the question, looking past you Toward the dim warmth of the main hall's fireplace.

> Alwick shifts your weight forward, his thumb tracing the grain of his staff.

> Bram stands at ease against the timber siding, his large hands resting near the pommel of his sword. A heavy wooden cart rattles past them, leaving a thin veil of dust on their cloaks before it disappears toward the south.

You lean against the stone masonry nearby, watching the way the grey light hits the grain fields stretching out toward the Greywood. Isel smooths a wrinkle in his tunic and looks down at his own calloused palms. Beside him, Bram gives an indifferent shrug that makes the scarred skin around his eye crinkle.


### npc_conversation
> Safe travels then. Mind the mud on the roads.

> The ones listed on that board are usually straightforward enough for someone with your experience. Most folk finish them without much trouble unless they wander into a thicket where they do not belong or let their guard down when things seem quiet.

> Activity today? It sees quite a lot of use I would say. We have people coming through the doors for work every day and travelers seeking shelter when they reach Parth on the trade road.

> Do you have any other business here or shall I let you get back to your companions?


### hire_chat
> You want me to do what? You're looking to push through this even with the weather turning like that?

> That task requires rank I or higher on guild board. We do not have that status.

> I haven't. Most people around here have been busy with the grain instead of watching over the flock.

> Not many folks do that kind of work anymore without complaining about their hands getting raw. It's honest enough labor, though most people just want to see the coin instead of the fleece.


### mentor_chat
> I'm an A.

> I've dealt with enough strays in my time to know they don't care much about our feelings, though their teeth are still sharp enough to give some trouble if we aren't careful. Just keep that sword steady.

> I've got my brother out in the capital. He's always trying to keep his books straight.

> It's mostly down to grit and position. Generally, if you're matched against someone just as capable as yourself, you'll land about three out of four swings. But things change fast. If you can get some high ground—say even ten feet up—it helps with your aim. Your gear matters too; anything that adds accuracy makes it easier for your blade to find its mark. Now, keep an eye on how they move. A target that's running or shivering is going to be harder to pin down than a steady one. And if you ever manage to blind 'em... well, then their defense won't mean much at all.

