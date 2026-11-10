# 7. How MUDs, MMOs and play-by-post games handled time and absent players

An addendum to doc 06 (time when players split up). It's a survey of older shared worlds, what they did, and what that changes in the
design. Sources are cited in the chat answer.

## What they did

| System | Time model | Players apart / offline | Lesson for Meravia |
|---|---|---|---|
| **DikuMUD family** (CircleMUD, Smaug, MUME, Aardwolf) | **One real-time clock for everyone.** A "tick" of about 30–60 real seconds is one game hour; regeneration, weather and combat run on timers. Nothing skips time | No split problem, because no action skips time: travel is walking room to room, and resting is waiting for ticks | The split problem comes from actions that *skip* time (a 2-day walk in one line). MUDs avoided it by not having them. It's an option for an always-on server mode, not for the current design |
| **Diku zone resets** | Areas repopulate on a timer whether or not anyone's there | n/a | Timed resets everywhere waste work and pull the world away from what players did |
| **LPMud lazy resets** | `reset()` only runs on objects when they're touched (near players) | Unvisited areas cost nothing | Confirms doc 06: regions catch up only when someone arrives (`pulse.catch_up` per region) |
| **LPMud heartbeats and call_outs** | Per-object heartbeats for frequent work; scheduled call_outs for one-off delayed work | n/a | Situation stages and cross-region effects become scheduled entries ("call_outs") applied when their region catches up |
| **Circle/Diku rent and linkdead** | n/a | Quitting at an inn's receptionist **saves the character and removes them from the world**; a dropped connection goes "linkdead", and the character eventually goes into the void with their gear kept | **Offline characters leave the world** instead of standing frozen in it. That's simpler than doc 06's "downtime in place": nobody can touch them, so no ordering problem |
| **West Marches (tabletop)** | Per-group timelines that branch and fold back; groups behind are brought forward through downtime | The "end the session in town" rule, so any characters can group next time | Already in doc 06; keep the "return to a safe place to log off cleanly" incentive |
| **Play-by-post (flashback threads, timestamps)** | Threads are dated; flashbacks are allowed if they **don't contradict the established present**; anything gained in a flashback is usable only once the thread finishes | Slower players can play scenes set earlier while others are ahead | A player who's behind could play on "in the past" for things nobody touched later, which doc 06's touch rule already allows. Add the rule that gains made behind the leader only become usable on syncing |
| **World of Warcraft phasing** | Different players see different states of the same area based on quest progress | Friends in different phases **can't see each other or group**; a long-running source of complaints | Divergent views are a trap. Doc 06's perceive rule (you don't hear news from your future) is a mild phase. It's acceptable only because **two players in the same scene are always synced first** |
| **EVE Online time dilation** | When a solar system's server is overloaded, **that system's game clock slows** (down to 10%), while global timers (industry, training) keep running on server time | n/a | Local clocks can run at different rates from a global one without breaking the world. A group scene with many players can run its own slower clock (a longer input window) while the world outside keeps its own |
| **Baldur's Gate 3** | Real time, with turn-based combat that switches on **for everyone**, wherever they are | Players roam freely | Don't freeze unrelated players for one player's fight |
| **Crusader Kings III** | One clock; everyone must be present for the campaign to move | An absent player stalls the game | Avoid a single shared clock that needs everyone present |

## What changes in doc 06

1. **Offline means leaving the world, as a MUD's "rent" did.**
   - A player who stops playing at an inn, a home or a guild house is checked out. Their character is removed from the world (not
     present, not touchable) and their clock is frozen.
   - When they come back, they're checked in again at that place, at their own clock. If the place's time is ahead of them, the touch
     rule moves them forward, narrated as "you've slept late" or as days at the inn spent on a chosen downtime activity.
   - Going offline on the road or in a wild place: as with linkdead, the character makes camp at once (one night roll) and then checks
     out there. That replaces doc 06's "downtime in place": nobody can interact with an absent character, so there's nothing to order.
2. **Scheduled entries replace timers** for situation stages and cross-region effects, applied lazily when a region catches up, as with
   LPMud call_outs and lazy resets.
3. **Gains made behind the leader are held until the next sync,** following the play-by-post rule.
   - Anything a character who's behind gains (levels, items, money) is usable at once *by them*.
   - But it can't be *given* to a character who's ahead, or spent where a character who's ahead has been, until they sync.
   - That stops the trailing player's past from changing a present that's already been played.
4. **No divergent world views inside a scene.** Any two characters in one scene are synced first, so nobody ever sees a different world
   from the person beside them (avoiding WoW's phasing complaints). The perceive filter only applies to things you *hear* about.
5. **Group scenes get their own clock, as EVE's dilation does.** In a scene with several players, each beat waits for input up to a
   window (for example 20–40 real seconds, or until everyone has acted). The scene's game time advances per beat, not per player line,
   and players elsewhere are unaffected.
6. **An optional always-on server mode, the MUD model.** For a campaign hosted on an always-running server (later; not a current
   decision), the game could switch to a real-time ratio: MUME runs at about 60 times real time, so a game hour is about a real
   minute.
   - Long actions then take real time ("you'll reach Elmshade in about 30 real minutes; you can keep talking, scouting or resting
     meanwhile").
   - That removes the split problem entirely for people who play together often, at the cost of single-player pacing. It should be a
     setting per campaign, never the default.

## Updated summary of the recommended model
- **Session play (the default):** per-character clocks, the touch, perceive and window rules (doc 06), lazy regional catch-up,
  check-out when offline (from MUD rent), gains held until sync (from play-by-post), and group scenes on their own beat clock (from
  EVE).
- **Always-on server mode (later, optional):** a shared real-time clock at a ratio, with long actions taking real time (the MUD model).

## Extra tests on top of doc 06's
- `checkout_test`: going offline at an inn removes the character from every scene and query; coming back puts them in at their clock,
  moved forward if the place is ahead.
- `linkdead_test`: dropping offline on the road makes camp, rolls one night event, then checks out.
- `held_gains_test`: an item gained by the character who's behind can't be handed to the one ahead until they sync.
- `scene_sync_test`: two characters entering one scene are synced before either sees it.
- `beat_clock_test`: a scene with three players advances one beat per window; a player in another town isn't affected.
