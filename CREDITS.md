# Credits

This work includes material taken from the System Reference Document 5.1 ("SRD 5.1") by
Wizards of the Coast LLC and available at https://dnd.wizards.com/resources/systems-reference-document.
The SRD 5.1 is licensed under the Creative Commons Attribution 4.0 International License available at
https://creativecommons.org/licenses/by/4.0/legalcode.

Creature data was read from the 5e-database project (https://github.com/5e-bits/5e-database, MIT License)
and reclassified for Meravia in data/world/bestiary.yaml. Only creature names, types, sizes, challenge
ratings, attack names and ability-score proportions are used; game statistics are computed by this engine.

The window's reading face is Literata (https://github.com/googlefonts/literata), copyright 2017 The Literata Project
Authors, licensed under the SIL Open Font License 1.1 (ui/gui/web/fonts/OFL.txt). The four files there are the latin
subsets packaged by Fontsource (https://fontsource.org).

The game's name on the home page is set in Cinzel Decorative (https://github.com/NDISCOVER/Cinzel), copyright 2012
Natanael Gama, with Reserved Font Name "Cinzel", licensed under the SIL Open Font License 1.1
(ui/gui/web/fonts/OFL-CinzelDecorative.txt). The file is the bold latin subset packaged by Fontsource, unmodified.

## The model server and the models

The game runs its model on llama.cpp's `llama-server` (https://github.com/ggml-org/llama.cpp), copyright 2023-2026 The ggml authors,
MIT License. The build under runtime/<build>/ is llama.cpp's own release of the commit data/runtime/server.yaml pins (on Linux, built from
that commit). Its CUDA build carries NVIDIA's CUDA runtime libraries (cudart, cuBLAS), redistributed under the redistribution terms of the
NVIDIA CUDA Toolkit End User License Agreement (https://docs.nvidia.com/cuda/eula/); its Vulkan build uses the Vulkan loader
(https://github.com/KhronosGroup/Vulkan-Loader, Apache License 2.0).

The model that writes the prose and reads what the player types is Google's Gemma 4 (the 12B weights, as a GGUF file pinned by its
sha256 in data/runtime/server.yaml), used under the Gemma Terms of Use (https://ai.google.dev/gemma/terms). The game is not made,
sponsored or endorsed by Google. The embedding model is Nomic AI's nomic-embed-text v1.5
(https://huggingface.co/nomic-ai/nomic-embed-text-v1.5), Apache License 2.0. The licences of the model, the embedder, llama.cpp and the
GPU runtimes are confirmed before the game goes on Steam (GOALS.md, the owner's decision of 5 Nov); this file is corrected then if any
wording above is.
