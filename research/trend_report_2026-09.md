# Chess Shorts observations (September 2026)

Historical sample, not an editing specification. View counts do not establish that duration, effect frequency, or music choice caused retention. Current editing priorities are in projectNotes/editing_priorities.md.

Scope: YouTube Shorts from **2024-01-01 to 2026-09-30** only. Data was collected on 2026-09-30 with yt-dlp. Sources: ~40 search queries, 19 hashtag Shorts feeds (#chessedit, #chessedits, #chess, #magnuscarlsen, #chessphonk, #brilliantmove, #phonkedit, …), and full metadata for 757 high-view videos (272 of them vertical Shorts from 2024–2026). From those, **30 viral chess Shorts** were downloaded and analyzed frame by frame: contact sheets, ffmpeg scene-cut detection, and Shazam song identification on 3 segments per video. 14 top general 2026 edit Shorts (#phonkedit) were also Shazam-identified. Raw data is in `research/data/`, and contact sheets are in `research/screens/`.

## 1. Key findings

1. **Board-animation edits are a proven lane and don't need footage.** 2025–26 hits include ZaveeCHESS "Most Aggressive Opening" (22.0M), Strategy Chess "Which Is The Best Chess Piece?" (22.3M), ZaveeCHESS "Beating King's Pawn…" (16.7M), ChessFXs "Most FIRE Knight FORK" (11.3M), Stixy4Squares "Tal's invincible knight" (8.2M), and Kyuto Machi "…only for elo 911" (7.0M) and "Deadly Trap only for elo 900+" (6.4M).
2. **One audio dominates chess edits: MONTAGEM PERIGOSA** (KVRXD, SEKIMANE & dj Samir). It appears in 4 of the 30 analyzed viral chess edits (≈28M combined views), mostly the *Ultra Slowed* version. Other audio in the top chess edits is also slowed Brazilian funk/phonk: Perfect Girl Funk (Ultra Slowed), VOCE NA MIRA (Super Slowed), MANDE MANDE, FUNK SIGILO (Slowed), MUTILATOR (Slowed), AURA (Super Slowed), COM MEDO!, LET THE WORLD BURN.
3. **The general 2026 edit meta is slowed Brazilian funk.** Tallying titles in the #phonkedit feed gives FUNK ABNORMAL (Slowed) at 192M views across 12 edits, HEAVENLY JUMPSTYLE at 110M (1 edit), SEM CONTROLE (Slowed) at 38M, House of Memories (Panic! At The Disco) at 29M across 12 edits, and MONTAGEM URANIUM (Slowed) at 27M. Shazam on the top untitled edits added Dia De Fiesta (Slowed), MONTAGEM DELÍRIO, SEM NADA (Super Slowed), REAL MOONSHINE (Super Slowed), ÁCIDO III, and LOUCURA LETAL.
4. **Length.** The viral chess Shorts analyzed have a **median duration of 24.5s** (mean 26s), and only 5 of 30 are 40s or longer. Very short 6–15s "💎 brilliant move" loops (MissUChess, KnightmareChess, SMART AVANI, Catur Talk) are flooding Sept 2026. This sample contains no audience-retention data and does not establish an optimal duration.
5. **Aspect ratio.** Many top chess edits are **not 9:16**. ZaveeCHESS and Strategy Chess upload 4:5 (720×900), and the "elo 900+" edits are square (1080×1080). Full 9:16 works fine but isn't required. (The project switched its Shorts to 4:5 in October 2026.)
6. **Editing rhythm.** Scene-cut detection shows almost no hard cuts in the first half (the board stays on screen and the camera tracks moves). Cuts cluster **after the drop, at beat intervals of about 0.5s**. For example, ZaveeCHESS M9F2Ux1p9f4 has 16 cuts, all after 18.3s, spaced 0.57s apart. The drop is the payoff moment and the edit accelerates into it.

## 2. What the winning chess edits look like (visual language)

See `research/screens/*.jpg` (15 frames per video; the first 5 frames cover the first 3 seconds).

- **Hook text (0–2s).** Two lines of heavy sans (Montserrat/Poppins ExtraBold style) in white, with one line or keyword in **red** ("THE MOST AGGRESSIVE OPENING / BY PAWN SACRIFICE", "THE ONLY OPENING THAT / EVERYONE FEARS", "HOW TO DESTROY / OWEN'S DEFENSE / ONLY FOR ELO 911"). It sits over a dark vignetted or tilted board that is **already moving** (`M9F2Ux1p9f4.jpg`, `2hp2oy4-m8A.jpg`, `8invqrFvVyA.jpg`).
- **Grayscale board + saturated accent colors.** White/gray squares with neo-style pieces. The only color comes from chess.com classification highlights: teal brilliant, green best, orange/brown book, yellow inaccuracy, red blunder with a full-screen red tint. Icons sit at the top-right of the destination square with a pulsing ring.
- **Close-up tracking camera.** Only 4–6 files of the board are visible, and the camera glides after each move with slight rotation. After the drop, boards tilt in 3D, rotate, and get bloom, motion blur, embers and fire (`IdoSurMUbrI.jpg`, `M9F2Ux1p9f4.jpg`).
- **Mid-video title cards.** Big 3D piece plus glowing name ("KING'S GAMBIT ACCEPTED: MODERN DEFENSE", "MARTIAN GAMBIT"), and a giant 3D "!!" brilliant icon smashing a piece (`2hp2oy4-m8A.jpg`).
- **Meme/sticker layer (a sub-style).** Sniper rifles, explosions, lightning, player photos with a bold caption ("BOBBY FISCHER BRILLIANCY", "INVINCIBLE MAGIC MOVES BY MIKHAIL TAL") (`a3OEnUe5scY.jpg`, `MCbKdlNe624.jpg`).
- **Abstract piece edits.** "The Knight – Chess Edit" (`zCx0P9MZx8A.jpg`, 74 cuts in 12s) uses black/white/red only, piece silhouettes, horizontal speed streaks, strobe flashes, and move-pattern arrows. Strategy Chess shows each piece's movement pattern as colored neon arrows on a 3D perspective board (`8b8puHCQHgQ.jpg`).
- **Concept/puzzle hooks.** ViperKing "8 Queens Puzzle!" (19.8M, live action) asks a question in the first second ("Can you place 8 queens so that no queens attack each other?") and pays it off at the end ("92 possible solutions"). This works with animation too.
- Footage-based player edits ("Kid Carlsen", "Biggest Fear of Soviet") are a separate lane that needs real footage. Not our lane.

## 3. Trending audio

### Heard in the analyzed viral chess edits (2024–2026)

| Song | Where | Views of that edit |
|---|---|---|
| MONTAGEM PERIGOSA (Ultra Slowed / original) – KVRXD, SEKIMANE & dj Samir | ZaveeCHESS, Kyuto Machi ×3 | 13.5M, 7.0M, 6.4M, 1.4M |
| Perfect Girl Funk (Ultra Slowed) – Zwella | Strategy Chess "Best Chess Piece" | 22.3M |
| Living tombstone type beat – BENZDANCE | ZaveeCHESS | 22.0M |
| MANDE MANDE – CHASHKAKEFIRA | ZaveeCHESS | 16.7M |
| AURA (Super Slowed) – Ogryzek | IChessU | 13.2M |
| LET THE WORLD BURN – Chris Grey | ChessFXs knight fork | 11.3M |
| COM MEDO! – Sayfalse & Scythermane | Aura chess "Sniper Bishop" | 4.2M |
| MUTILATOR (Slowed) – ZMAJOR & Lurk | "Kid Carlsen" | 3.1M |
| FUNK SIGILO (Slowed) – h6itam | Gukesh vs Fabiano | 1.6M (+12M general edit) |
| VOCE NA MIRA (Super Slowed) – Hwungii & DJ VGK1 | Strategy Chess (53s) | 0.8M |
| life force (slowed & reverb) – ptasinski | Ronx | 1.5M |

### Downloaded library (`assets/music/`, from official/artist uploads, not ripped from edits)

Beat/drop analysis comes from `python -m studio songs`. The drop times below are song times and mark where the bass or energy slams back in.

| slug | bpm | main drop (s) | all drops (s) | source |
|---|---|---|---|---|
| montagem_perigosa_ultra_slowed | 89.3 | 64.1 | 10.0, 21.4, 53.1, 64.1, 75.4, 86.1 | KVRXD channel |
| montagem_perigosa | 80.8 | 39.5 | 7.5, 15.8, 39.5, 48.3, 64.4 | Dj Samir channel |
| funk_abnormal_slowed | 117.5 | 33.2 | 8.3, 33.2, 58.1, 82.9 | Rubix Records |
| sem_controle_slowed | 107.8 | 8.8 | 8.8, 17.5, 43.7, 61.0, 87.3 | nightfxrce |
| montagem_uranium_slowed | 103.3 | 14.6 | 14.6, 24.5, 42.5, 79.7, 89.6 | re-upload (void) |
| house_of_memories | 107.8 | 6.2 | 6.2, 67.3, 110.9, 169.2 | Panic! At The Disco |
| heavenly_jumpstyle | 129.3 | 13.0 | 13.0, 36.5, 49.9, 71.8, 80.8 | TWXNY |
| dia_de_fiesta_slowed | 103.5 | 4.6 | 4.6, 37.5 | qaraqshy – Topic |
| montagem_delirio_super_slowed | 92.3 | 22.0 | 10.8, 22.0, 107.0 | re-upload (phonk) |
| sem_nada_super_slowed | 107.8 | 19.0 | 10.1, 19.0, 45.7, 58.2 | Ogryzek |
| real_moonshine_super_slowed | 99.5 | 53.2 | 15.7, 28.4, 53.2, 82.2 | DJ ROBE – Topic |
| perfect_girl_funk_ultra_slowed | 92.5 | – (constant groove) | – | re-upload |
| voce_na_mira_super_slowed | 83.5 | 11.3 | 11.3, 22.1, 112.6 | re-upload (Davuiside) |
| mande_mande | 86.0 | 14.8 | 7.5, 14.8, 33.4, 45.4, 59.1, 76.9 | CHASHKAKEFIRA |
| funk_sigilo_slowed | 95.8 | 35.3 | 5.3, 35.3, 50.9, 79.6 | h6itam |
| mutilator_slowed | 103.5 | 76.9 | 9.3, 27.7, 55.5, 76.9 | ZMAJOR |
| aura_super_slowed | 66.3 | 4.2 | 4.2, 31.9, 61.8, 97.2, 105.3 | Ogryzek |
| com_medo | 123.0 | 40.3 | 7.7, 26.9, 40.3, 46.6 | Sayfalse |
| let_the_world_burn | 92.3 | 46.5 | 5.2, 46.5, 108.5 | Chris Grey |
| life_force_slowed_reverb | 103.5 | 26.3 | 17.1, 26.3, 62.8, 71.9, … | ptasinski – Topic |

## 4. AbstractChess channel diagnosis

Data: `research/data/abstractchess_shorts.json`, 91 Shorts, 2,170 subscribers, no long-form.

- **Apr–Jun 2025 (daily uploads, 8–33s, 9:16).** This is where every breakout happened: "Wildest checkmate in chess" 981k, "INFINITE Brilliant moves" 920k, "BRILLIANT Counter Attack" 535k, "Grandmasters in chess be like" 394k, "Bro is a chess grandmaster" 291k, "Brilliant move speaks for itself" 285k. The format was meme-framed ("GMs be like 💀💀") with word-by-word yellow-emphasis captions on a plain blue board, and short (15–20s). Uploads stopped on Jun 8, 2025.
- **Mar–Apr 2026 revival (16–23s traps).** Every upload landed between 20k and 58k.
- **Jul–Aug 2026 (4:5, 20–58s, ZaveeCHESS-like styling).** 8k–79k. The longer 46–58s compilations ("Brilliant Moves That Win the Queen", "Best Checkmate Patterns") did slightly better than the 20s ones but still stalled. Frames show long flat stretches with a static zoomed board and captions, and no strong musical drop or payoff moment (`research/screens/abstractchess_zJRXqOmpo20.jpg`).
- Titles lean on GothamChess/Magnus name-drops ("GothamChess Is Jealous…"), and those underperform the channel's own curiosity/meme titles from 2025.

## 5. Caveats

- YouTube rate-limited the full-metadata pass (HTTP 429 / bot check), so hashtag feeds and the web_embedded client were used. The sample is skewed toward what those feeds surface.
- Shazam failed on 6 of the 30 chess edits (heavily pitched audio or original music).
- View counts are from 2026-09-30, and older videos have had more time to accumulate views.
