"""The stats window (#stats): every number combat uses for you, and the same sheet for a hired adventurer on hover in the party pane."""
from engine import combat, statsheet
from ui import console


class StatsActions:
    def player_sheet(self) -> dict:
        c = self.player.character
        return statsheet.sheet(combat.fighter_from_character(c))

    def member_sheet(self, m: dict) -> dict:
        from engine import party as rules
        return statsheet.sheet(rules.fighter(m, minutes=self.minutes))

    def show_stats(self) -> None:
        s = self.player_sheet()
        c = self.player.character
        if console.panel("stats", {"title": s["title"], "sections": s["sections"], "unspent": c.unspent_points}):
            return
        console.note(s["title"].upper())
        for sec in s["sections"]:
            console.note("")
            console.note(sec["title"].upper())
            if sec["title"] == "Attributes":
                console.note("  " + "   ".join(f"{r[0][:3].upper()} {r[1]}" for r in sec["rows"]))
                continue
            for label, value, note in sec["rows"]:
                console.note(f"  {label:<18} {value!s:<10} {note}")
