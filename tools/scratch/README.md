Developer probes, not tests: scripts that drive the game and write what they see to /tmp for a human to read. They were written against
older versions of the game (camp_probe.py calls an arcs.empty() that no longer exists; prop_probe.py buys a house in a town that no longer
sells one) and are kept here for reference. The suite (tools/run_suite.py) runs only tools/sim/*_test.py; the camp approach and property
behaviour they once exercised are covered by tools/sim/arc_site_test.py and tools/sim/property_test.py.
