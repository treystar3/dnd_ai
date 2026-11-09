# Playing Meravia (notes for testers)

1. Run `Meravia_<version>_setup.exe`. Windows may show "Windows protected your PC" because the file is not code-signed:
   click **More info**, then **Run anyway**.
2. The installer downloads the game's model files (about 8 GB) while it installs, and checks each against its fingerprint. Nothing else
   is needed: the game runs its own model server from its install folder.
3. Start the game. The world loads behind the home page; Continue waits for it, and New Game starts at once.
4. A graphics card of 12 GB (an NVIDIA RTX 3060) or 16 GB (an AMD RX 7600 XT), or better, plays the game in full. Below that, or
   with no graphics card, it plays slowly and says so once when it starts.
5. Your saves are kept in the `saves` folder inside the install folder, and survive uninstalling.
