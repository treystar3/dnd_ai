"""The gear pane: what you wear, what you carry that could be worn, and buttons to swap them."""

from engine import equipment, items, sets
from ui import console

SLOT_LABEL = {"main_hand": "Main hand", "off_hand": "Off hand", "head": "Head", "body": "Body", "hands": "Hands",
              "feet": "Feet", "neck": "Neck", "ring_1": "Ring", "ring_2": "Ring"}


class GearActions:

    def gear_row(self, item) -> dict:
        return {"uid": item.uid, "name": items.display_name(item), "detail": items.summary(item), "rarity": item.rarity,
                "legendary": item.rarity == "legendary"}

    def gear_compare(self, item) -> list[list[str]]:
        """Lines for the hover: what this would replace and how the numbers change."""
        c = self.player.character
        b = items.base_of(item)
        slot = equipment._target_slot(c, item)
        worn = c.equipment.get(slot)
        lines = [["h", f"{SLOT_LABEL.get(slot, slot)}: " + (f"replaces {items.display_name(worn)}" if worn else "empty slot")]]
        word = "damage" if b.is_weapon else "ward" if b.ward else "armor" if b.base else ""
        if word:
            new, old = items.value(item), items.value(worn) if worn else 0
            if worn and items.base_of(worn).is_weapon != b.is_weapon:
                old = 0
            diff = new - old
            lines.append(["up" if diff > 0 else "down" if diff < 0 else "", f"{word}: {old} → {new} ({'+' if diff >= 0 else ''}{diff})"])
        if b.hands == 2 and c.equipment.get("off_hand"):
            lines.append(["down", f"puts away your {items.display_name(c.equipment['off_hand'])}"])
        lines.append(["", "This: " + items.summary(item)])
        if worn:
            lines.append(["dim", "Now: " + items.summary(worn)])
        return lines

    def gear_data(self) -> dict:
        c = self.player.character
        slots = [{"slot": s, "label": SLOT_LABEL[s], "item": self.gear_row(c.equipment[s]) if s in c.equipment else None, "note": ""}
                 for s in items.SLOTS]
        if equipment.two_handed_equipped(c):
            for row in slots:
                if row["slot"] == "off_hand" and not row["item"]:
                    row["note"] = f"held with both hands: {items.display_name(c.equipment['main_hand'])}"
        carried = []
        for item in c.inventory:
            if item.good or items.base_of(item).slot == "none":
                continue
            problem = equipment.check(c, item)
            row = self.gear_row(item)
            row.update(ok=problem is None, reason=problem or "", compare=self.gear_compare(item))
            carried.append(row)
        return {"slots": slots, "carried": carried, "sets": sets.summary(c.equipment)}

    def show_gear(self) -> None:
        data = self.gear_data()
        if console.panel("gear", data):
            return
        for s in data["slots"]:
            it = s["item"]
            console.note(f"  {s['label']:<10} " + (f"{it['name']} - {it['detail']}" if it else (f"-- ({s['note']})" if s["note"] else "--")))
        if data["carried"]:
            console.note("Carried gear:")
            for x in data["carried"]:
                console.note(f"  {x['name']} - {x['detail']}" + ("" if x["ok"] else f"  [{x['reason']}]"))
        console.note("  #equip <name or number>   #unequip <slot or name>")

    def gear_click(self, text: str) -> None:
        """The pane's hidden commands:  #gearequip <item uid>   #gearunequip <slot>."""
        parts = text.split()
        c = self.player.character
        if parts[0].lower() == "#gearequip" and len(parts) >= 2:
            item = next((i for i in c.inventory if i.uid == parts[1]), None)
            console.note(equipment.equip(c, item) if item else "You no longer carry that.")
        elif parts[0].lower() == "#gearunequip" and len(parts) >= 2:
            console.note(equipment.unequip(c, parts[1]))
        self.store.save_player(self.player)
        with console.scope("#gear"):
            self.show_gear()
