# Playing Meravia (notes for testers)

1. Run `Meravia_<version>_setup.exe`. Windows may show "Windows protected your PC" because the file is not code-signed:
   click **More info**, then **Run anyway**.
2. Leave "Install Ollama" ticked if you don't already have it (a small Windows permission prompt may appear).
3. Start the game. The first time, it downloads its AI model (roughly 9 GB) with a progress bar. This happens once.
4. A graphics card with about 10 GB of memory or more (for example an RTX 4070 or better) runs it comfortably. Smaller or no graphics cards work but replies are slow.
5. Your saves are kept in the `saves` folder inside the install folder, and survive uninstalling.
