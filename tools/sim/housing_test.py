"""The top house upgrades are far-lands only; every far-lands town sells a house."""
import sys, yaml
sys.path.insert(0, ".")
P = yaml.safe_load(open("data/rules/property.yaml"))
far = {"cinderhold", "hrimgard", "dunmarrow", "brinewatch", "amaranth"}
bad = []
for uid in ("reliquary", "banquet_hall"):
    t = set(P["upgrades"][uid].get("towns", []))
    if t != far or not t <= set(P["homes"]): bad.append(uid)
for uid in ("strongroom", "workshop", "garden", "hearth", "fortify"):
    if P["upgrades"][uid].get("towns"): bad.append(uid + " restricted")
print("FAILED" if bad else "ALL PASS", bad)
sys.exit(1 if bad else 0)
