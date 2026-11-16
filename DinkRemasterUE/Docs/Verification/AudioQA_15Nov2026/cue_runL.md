# Run L (16 Nov 2026, 13:57-14:00): the generated footsteps and ambience beds in the game

Recorded with SDL's disk driver (never the speakers), final tree (origin/master + this branch). Cues from the game log (footsteps at Verbose), found in the recording by `Scripts/AudioQA/cue_proof.py`. 'heard' needs a match of 0.3 or more and a window 3 dB above the second before; in the sweep the second before holds the previous item, so judge the sweep by its match.

In play: 20 wood steps in Dink's house (SCR_001), 10 grass steps outside (SCR_439), and the bed switching meadow (439), sea (352), wind (13), cave (69), meadow (10). Then all 32 takes isolated (`dink.AudioQA.Sweep`).

| asset | cue | log time (s after device open) | onset in recording (s) | match | RMS dBFS | floor (1 s before) dBFS | peak dBFS | heard |
|---|---|---|---|---|---|---|---|---|
| Step_wood_4 | game, sprite 0, pitch 1.000 | 98.8 | 100.09 | 0.289 | -28.3 | -38.5 | -11.2 | NO |
| Step_wood_3 | game, sprite 0, pitch 1.000 | 99.0 | 100.30 | 0.476 | -28.2 | -34.9 | -11.2 | yes |
| Step_wood_3 | game, sprite 0, pitch 1.000 | 99.2 | 100.30 | 0.476 | -28.2 | -34.9 | -11.2 | yes |
| Step_wood_4 | game, sprite 0, pitch 1.000 | 99.4 | 100.09 | 0.289 | -28.3 | -38.5 | -11.2 | NO |
| Step_wood_1 | game, sprite 0, pitch 1.000 | 99.6 | 100.85 | 0.595 | -30.2 | -30.0 | -10.2 | NO |
| Step_wood_3 | game, sprite 0, pitch 1.000 | 99.8 | 100.30 | 0.476 | -28.2 | -34.9 | -11.2 | yes |
| Step_wood_3 | game, sprite 0, pitch 1.000 | 106.2 | 107.61 | 0.579 | -29.2 | -36.1 | -8.5 | yes |
| Step_wood_3 | game, sprite 0, pitch 1.000 | 106.4 | 107.61 | 0.579 | -29.2 | -36.1 | -8.5 | yes |
| Step_wood_4 | game, sprite 0, pitch 1.000 | 106.6 | 107.80 | 0.464 | -28.3 | -33.5 | -10.0 | yes |
| Step_wood_2 | game, sprite 0, pitch 1.000 | 106.8 | 108.19 | 0.438 | -26.9 | -31.4 | -10.0 | yes |
| Step_wood_1 | game, sprite 0, pitch 1.000 | 106.9 | 108.18 | 0.564 | -26.9 | -31.4 | -10.0 | yes |
| Step_wood_4 | game, sprite 0, pitch 1.000 | 107.1 | 107.80 | 0.464 | -28.3 | -33.5 | -10.0 | yes |
| Step_wood_2 | game, sprite 0, pitch 1.000 | 107.3 | 108.19 | 0.438 | -26.9 | -31.4 | -10.0 | yes |
| Step_wood_1 | game, sprite 0, pitch 1.000 | 113.7 | 114.99 | 0.392 | -30.6 | -43.6 | -9.9 | yes |
| Step_wood_2 | game, sprite 0, pitch 1.000 | 114.0 | 115.29 | 0.563 | -32.3 | -36.4 | -9.9 | yes |
| Step_wood_4 | game, sprite 0, pitch 1.000 | 114.4 | 115.69 | 0.908 | -32.4 | -33.8 | -17.1 | NO |
| Step_wood_2 | game, sprite 0, pitch 1.000 | 118.2 | 119.53 | 0.637 | -30.3 | -42.6 | -10.2 | yes |
| Step_wood_2 | game, sprite 0, pitch 1.000 | 118.4 | 119.53 | 0.637 | -30.3 | -42.6 | -10.2 | yes |
| Step_wood_1 | game, sprite 0, pitch 1.000 | 118.7 | 120.02 | 0.683 | -30.1 | -34.0 | -10.3 | yes |
| Step_wood_3 | game, sprite 0, pitch 1.000 | 119.0 | 120.34 | 0.982 | -33.0 | -32.2 | -10.3 | NO |
| Bed_meadow | game, sprite 0, pitch 1.000 | 121.4 | 122.02 | 0.007 | -23.2 | -47.7 | -9.7 | NO |
| Step_grass_2 | game, sprite 0, pitch 1.000 | 131.0 | 133.69 | 0.198 | -22.9 | -23.4 | -12.5 | NO |
| Step_grass_3 | game, sprite 0, pitch 1.000 | 131.2 | 132.93 | 0.289 | -23.2 | -24.4 | -11.8 | NO |
| Step_grass_3 | game, sprite 0, pitch 1.000 | 131.4 | 132.93 | 0.289 | -23.2 | -24.4 | -11.8 | NO |
| Step_grass_1 | game, sprite 0, pitch 1.000 | 131.6 | 133.24 | 0.366 | -22.8 | -24.2 | -13.9 | NO |
| Step_grass_3 | game, sprite 0, pitch 1.000 | 131.8 | 132.93 | 0.289 | -23.2 | -24.4 | -11.8 | NO |
| Step_grass_3 | game, sprite 0, pitch 1.000 | 132.0 | 132.93 | 0.289 | -23.2 | -24.4 | -11.8 | NO |
| Step_grass_1 | game, sprite 0, pitch 1.000 | 132.2 | 133.24 | 0.366 | -22.8 | -24.2 | -13.9 | NO |
| Step_grass_3 | game, sprite 0, pitch 1.000 | 132.3 | 132.93 | 0.289 | -23.2 | -24.4 | -11.8 | NO |
| Step_grass_3 | game, sprite 0, pitch 1.000 | 132.5 | 132.93 | 0.289 | -23.2 | -24.4 | -11.8 | NO |
| Step_grass_4 | game, sprite 0, pitch 1.000 | 132.7 | 134.32 | 0.559 | -23.6 | -23.3 | -13.9 | NO |
| Bed_sea | game, sprite 0, pitch 1.000 | 139.9 | 141.09 | 0.021 | -25.7 | -26.6 | -15.5 | NO |
| Bed_wind | game, sprite 0, pitch 1.000 | 151.0 | 154.13 | 0.091 | -26.2 | -26.1 | -15.0 | NO |
| Bed_cave | game, sprite 0, pitch 1.000 | 162.2 | 163.68 | 0.181 | -24.0 | -25.7 | -14.5 | NO |
| Bed_meadow | game, sprite 0, pitch 1.000 | 173.2 | 173.12 | 0.005 | -22.0 | -21.4 | -8.8 | NO |
| Step_dirt_1 | sweep | 186.6 | 188.76 | 0.994 | -33.6 | -48.0 | -12.1 | yes |
| Step_dirt_2 | sweep | 187.5 | 189.70 | 0.998 | -33.6 | -37.4 | -15.0 | yes |
| Step_dirt_3 | sweep | 188.4 | 190.64 | 0.994 | -34.1 | -37.3 | -15.4 | yes |
| Step_dirt_4 | sweep | 189.3 | 191.56 | 0.995 | -34.1 | -37.9 | -16.2 | yes |
| Step_grass_1 | sweep | 190.3 | 192.39 | 0.999 | -31.7 | -37.9 | -17.7 | yes |
| Step_grass_2 | sweep | 191.2 | 193.33 | 0.998 | -33.9 | -35.5 | -16.6 | NO |
| Step_grass_3 | sweep | 192.1 | 194.26 | 0.998 | -32.8 | -37.6 | -14.9 | yes |
| Step_grass_4 | sweep | 193.0 | 195.20 | 1.000 | -28.8 | -36.6 | -18.4 | yes |
| Step_sand_1 | sweep | 194.0 | 196.25 | 0.964 | -36.3 | -32.6 | -24.1 | NO |
| Step_sand_2 | sweep | 194.9 | 197.19 | 0.968 | -35.9 | -40.1 | -24.8 | yes |
| Step_sand_3 | sweep | 195.8 | 198.13 | 0.974 | -36.4 | -39.7 | -27.2 | yes |
| Step_sand_4 | sweep | 196.7 | 199.07 | 0.955 | -36.8 | -40.2 | -27.2 | yes |
| Step_snow_1 | sweep | 197.7 | 200.01 | 0.990 | -35.0 | -40.6 | -20.5 | yes |
| Step_snow_2 | sweep | 198.6 | 200.94 | 0.990 | -34.7 | -38.8 | -19.4 | yes |
| Step_snow_3 | sweep | 199.5 | 201.86 | 0.996 | -34.0 | -38.4 | -15.3 | yes |
| Step_snow_4 | sweep | 200.5 | 202.80 | 0.992 | -34.5 | -37.8 | -15.6 | yes |
| Step_stone_1 | sweep | 201.4 | 203.74 | 0.998 | -33.6 | -38.3 | -13.9 | yes |
| Step_stone_2 | sweep | 202.3 | 204.68 | 0.998 | -33.9 | -37.4 | -11.7 | yes |
| Step_stone_3 | sweep | 203.2 | 205.62 | 0.993 | -33.9 | -37.7 | -12.3 | yes |
| Step_stone_4 | sweep | 204.2 | 206.55 | 0.998 | -33.4 | -37.6 | -17.3 | yes |
| Step_water_1 | sweep | 205.1 | 207.49 | 0.994 | -34.6 | -37.2 | -20.3 | NO |
| Step_water_2 | sweep | 206.0 | 208.43 | 0.993 | -35.0 | -38.4 | -20.9 | yes |
| Step_water_3 | sweep | 206.9 | 209.35 | 0.994 | -34.6 | -38.8 | -20.6 | yes |
| Step_water_4 | sweep | 207.9 | 210.29 | 0.991 | -35.2 | -38.4 | -23.5 | yes |
| Step_wood_1 | sweep | 208.8 | 211.12 | 0.999 | -33.6 | -39.0 | -16.6 | yes |
| Step_wood_2 | sweep | 209.7 | 212.06 | 0.998 | -33.9 | -37.4 | -12.7 | yes |
| Step_wood_3 | sweep | 210.6 | 213.00 | 0.999 | -33.6 | -37.6 | -13.1 | yes |
| Step_wood_4 | sweep | 211.6 | 213.93 | 0.999 | -33.0 | -37.4 | -19.4 | yes |
| Bed_cave | sweep | 212.5 | 214.87 | 0.999 | -24.5 | -36.7 | -14.8 | yes |
| Bed_meadow | sweep | 221.0 | 223.47 | 0.892 | -38.1 | -24.1 | -16.8 | NO |
| Bed_sea | sweep | 229.5 | 232.07 | 0.989 | -37.8 | -44.5 | -16.2 | yes |
| Bed_wind | sweep | 238.0 | 240.66 | 0.998 | -39.3 | -58.5 | -28.7 | yes |

Beds in play start at a random point of their loop with a 2 s fade-in (`UDinkAudioLifeSubsystem::SetBed`), so the table above, which searches for the take's first 3 s, cannot find them. Searching 3 s of the recording (from 3 s after the bed starts) across the whole looped take instead:

| bed (screen) | match | offset in the take | recording RMS |
|---|---|---|---|
| meadow (439) | 0.099 | 7.5 s | -26.6 dBFS |
| sea (352) | 0.027 | 0.4 s | -27.0 dBFS |
| wind (13) | 0.465 | 21.0 s | -27.0 dBFS |
| cave (69) | 0.700 | 11.9 s | -22.4 dBFS |
| meadow (10) | 0.114 | 21.6 s | -26.7 dBFS |

Cave and wind are found under the screen music; sea and meadow play at bed volume 0.22 and 0.14 under music and are not separable by correlation (the sweep proves both takes play: 0.989, 0.892). Grass steps come about every 0.2 s on top of the meadow bed, so the search snaps several cues to one onset; wood steps (no bed indoors) are found 19 times of 24 cues.
