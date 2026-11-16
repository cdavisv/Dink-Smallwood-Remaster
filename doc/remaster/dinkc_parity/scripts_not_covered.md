| script | kind | screens / called by | probe | commands with a divergence | freeze paths |
|---|---|---|---|---|---|
| 1gold | pickup | 505 537 663 | partly: not touch |  |  |
| bar-dp | container | 156 | partly: not hit |  |  |
| bar-e | container | 34 161 162 194 196 229 409 418 419 437 439 734 | partly: not hit |  |  |
| bar-gh | container | 31 601 | never run |  |  |
| bar-m | dead |  | never run |  |  |
| bar-sh | container | 60 63 96 161 162 194 196 222 224 229 250 347 404 408 409 417 418 419 437 440 441 497 504 506 534 539 734 765 | partly: not hit |  |  |
| box2-e | container | 161 162 194 196 261 499 506 538 | partly: not hit |  |  |
| button6 | system |  | never run | open: show_bmp |  |
| ch1-g | container | 288 | never run |  |  |
| ch2-500 | container | 26 | never run |  |  |
| ch2-ap | dead |  | never run |  |  |
| ch2-sfb | dead |  | never run |  |  |
| ch3-h | container | 98 | never run |  |  |
| dam-a1 | projectile | sp_script:item-b1 sp_script:item-b2 sp_script:item-b3 | partly: not hit |  |  |
| dam-sfb | projectile | sp_script:item-sfb | never run | open: create_sprite |  |
| ddie5 | other | 307 656 | never run |  |  |
| die | other | 100 407 504 535 570 | partly: not die |  |  |
| dinfo | system |  | never run | fixed: script_attach | freeze l3 -> end of procedure; freeze l3 -> kill_this_task 25 |
| duck | dead |  | never run | open: set_callback_random |  |
| emake | library | external:bar-m external:en-bonc external:en-bonc1 external:en-boncd external:en-bong external:en-drag external:en-pbon external:en-pill external:en-pill1 external:en-pill2 external:en-pillf external:en-slay external:en-slim external:en-slimb external:en-stg external:s2-cbon external:s3-dorks external:s3-peeps external:s7-bong external:s7-dgirl external:s7-drag external:s7-duck external:s7-pill external:s7-slay external:s7-slimb external:sc-drag external:sc-lock external:sc-pill external:sc-slay | partly: not small | open: create_sprite |  |
| en-bonc | enemy | 29 306 562 648 | never run | open: sp_base_death |  |
| en-bonc1 | enemy | 302 | never run | open: sp_base_death |  |
| en-gh | enemy | 712 | partly: not attack, die, hit, talk |  |  |
| en-gs | enemy | 713 | never run |  |  |
| en-pbon | enemy | 514 515 547 577 609 | never run | open: sp_base_death |  |
| en-pill | enemy | 274 278 279 306 309 310 311 373 378 435 437 438 457 474 487 519 522 526 527 528 550 551 552 563 584 608 616 621 624 626 647 648 655 659 685 704 | partly: not die, hit | open: sp_base_death |  |
| en-pill1 | enemy | 237 270 301 303 334 | never run | open: sp_base_death |  |
| en-pill2 | enemy | 30 457 488 522 599 648 666 715 735 736 | never run | open: sp_base_death |  |
| en-pillf | enemy | 395 | partly: not die, hit | open: sp_base_death |  |
| en-slim | enemy | 192 274 347 546 610 658 660 688 | never run | open: sp_base_death |  |
| en-slimb | enemy | 458 512 599 633 652 672 695 | never run | open: sp_base_death |  |
| en-slimg | dead |  | never run | open: sp_base_death |  |
| en-stg | enemy | 178 182 183 209 211 212 213 215 242 245 246 | partly: not attack, die, hit |  |  |
| escape | system |  | never run |  |  |
| fire | dead |  | never run |  |  |
| fish1 | enemy | 634 665 697 727 | never run | open: create_sprite |  |
| get-fb | dead |  | never run |  |  |
| get-sfb | pickup | sp_script:make | never run |  |  |
| gold500 | pickup | sp_script:make | never run | open: create_sprite |  |
| item-axe | weapon | add_item:s5-st1p | never run | open: create_sprite, sp_kill_wait, sp_nocontrol |  |
| item-b1 | weapon | add_item:s2-out add_item:s3-st2p | partly: not drop | open: create_sprite |  |
| item-b2 | weapon | add_item:s6-st1p | never run | open: create_sprite |  |
| item-b3 | weapon | add_item:s8-guy | never run | open: create_sprite |  |
| item-bt | weapon | add_item:s1-boot | never run | open: sp_kill_wait, sp_nocontrol; fixed: set_dink_speed |  |
| item-fb | magic | add_magic:get-fb add_magic:s1-mh-f | partly: not drop | open: create_sprite, sp_kill_wait, sp_nocontrol |  |
| item-fst | weapon | add_item:newgame add_item:start-1 | partly: not drop | open: sp_kill_wait, sp_nocontrol |  |
| item-ice | magic | add_magic:s2-mh-m | partly: not drop | open: create_sprite, sp_kill_wait, sp_nocontrol |  |
| item-nut | item | add_item:s1-nut | partly: not arm, disarm, drop, use |  |  |
| item-p1 | magic | add_magic:s2-cave2 | partly: not arm, disarm, drop, use | open: create_sprite |  |
| item-pig | weapon | add_item:s1-sack | partly: not drop | open: create_sprite, sp_kill_wait, sp_nocontrol | freeze l83 -> end of procedure |
| item-sfb | magic | add_magic:get-sfb add_magic:s6-vend | never run | open: create_sprite, sp_kill_wait, sp_nocontrol |  |
| item-sw1 | weapon | add_item:s2-out add_item:s4-st3p | partly: not drop, holdingdrop | open: sp_kill_wait, sp_nocontrol |  |
| item-sw2 | weapon | add_item:s4-st3p | never run | open: sp_kill_wait, sp_nocontrol |  |
| item-sw3 | weapon | add_item:s6-st1p | never run | open: sp_kill_wait, sp_nocontrol |  |
| king | npc | 70 | partly: not hit | open: create_sprite |  |
| main | system |  | never run | fixed: set_dink_speed |  |
| make | library | external:bar-dp external:bar-f1 external:bar-gh external:bar-sh external:bar-sp external:box2-sp external:ch1-ap external:ch1-g external:ch1-gh external:ch1-mp external:ch1-pap external:ch1-sp external:ch2-500 external:ch2-ap external:ch2-gh external:ch2-sfb external:ch3-ap external:ch3-h external:s3-ch1 external:s4-duck external:s4-sec1 external:s5-sec1 | partly: not dpotion, food2, food7, food8, gold500, heart, lgold, lheart, mgold, sfb, sheart | open: create_sprite |  |
| pdie | other | 31 | never run |  |  |
| poster | npc | 33 195 225 226 | partly: not talk |  |  |
| s1-blove | cutscene | 410 | never run | open: move_stop |  |
| s1-bls | screen-base | 410 | never run |  |  |
| s1-boat | dead |  | never run | open: move_stop |  |
| s1-boot | shop | sp_script:s1-booth | never run |  |  |
| s1-booth | screen-base | 289 | never run | open: create_sprite |  |
| s1-brg2 | shop | sp_script:s1-brg | partly: not hit | open: create_sprite, move_stop, sp_disabled |  |
| s1-cave | screen-base | 98 99 | never run | open: set_callback_random |  |
| s1-cavem | enemy | 100 | partly: not attack |  |  |
| s1-caves | screen-base | 131 | never run | open: set_callback_random |  |
| s1-duck | dead |  | never run |  |  |
| s1-eltr | dead |  | never run | open: move_stop |  |
| s1-farm | screen-base | 437 | never run |  |  |
| s1-farm2 | dead |  | never run |  |  |
| s1-farms | npc | 437 | never run |  |  |
| s1-fmons | enemy | 437 | never run |  |  |
| s1-fount | dead |  | never run |  |  |
| s1-gg | npc | 408 | partly: not hit | open: move_stop |  |
| s1-h1-1 | object | 1 | partly: not hit, talk |  |  |
| s1-h1-2 | object | 1 | partly: not hit, talk |  |  |
| s1-h1-3 | object | 1 | partly: not hit, talk |  |  |
| s1-h1-4 | object | 1 414 446 | partly: not hit, push, talk |  |  |
| s1-h1-m | npc | 1 | partly: not hit, talk | open: move_stop |  |
| s1-h2-1 | object | 2 | partly: not hit, talk |  |  |
| s1-h2-2 | object | 2 | partly: not hit, talk |  |  |
| s1-h2-3 | object | 2 | partly: not hit, talk |  |  |
| s1-h2-dk | npc | 2 | partly: not die, talk |  |  |
| s1-h3-1 | object | 3 | never run |  |  |
| s1-h3-2 | object | 3 | never run |  |  |
| s1-h3-3 | object | 3 | never run |  |  |
| s1-h3-4 | object | 3 | never run |  |  |
| s1-h3-5 | cutscene | 3 | never run | open: move_stop |  |
| s1-h3-6 | object | 4 | never run |  |  |
| s1-h3-7 | object | 4 | never run |  |  |
| s1-h3-8 | object | 4 | never run |  |  |
| s1-h3-9 | object | 4 | never run |  |  |
| s1-h3-l | npc | 4 | never run |  |  |
| s1-h3-of | npc | 3 | never run |  |  |
| s1-h3-s | screen-base | 3 | never run |  |  |
| s1-hole | warp | 277 | never run | open: load_screen, sp_nocontrol | freeze l11 -> end of procedure |
| s1-hole3 | warp | 209 | partly: not touch | open: load_screen, sp_nocontrol; fixed: script_attach | freeze l11 -> kill_this_task 29 |
| s1-hsign | sign | 315 | never run |  |  |
| s1-lg | enemy | sp_script:s1-gate | never run |  |  |
| s1-mh-m | npc | 6 | partly: not hit | open: create_sprite |  |
| s1-mh-o | screen-base | 251 | never run |  |  |
| s1-nopas | other | 346 | never run | open: move_stop |  |
| s1-ntree | object | 410 474 | partly: not talk | open: create_sprite, move_stop |  |
| s1-oldd | npc | 409 440 441 | partly: not die | open: move_stop |  |
| s1-rand | screen-base | 378 405 406 | never run | open: create_sprite |  |
| s1-rob | screen-base | 374 | never run |  |  |
| s1-rob2 | cutscene | 342 374 | never run | open: move |  |
| s1-roc | object | 277 601 | never run | open: move_stop |  |
| s1-sack | pickup | 1 | partly: not hit, talk |  |  |
| s1-sign2 | sign | 403 | never run |  |  |
| s1-slim | dead |  | never run | open: sp_base_death |  |
| s1-ss2 | screen-base | 149 | never run |  |  |
| s1-vic | npc | 342 374 | never run | open: move_stop |  |
| s1-vil | npc | 376 | never run |  |  |
| s1-vil2 | npc | 404 | never run |  |  |
| s1-wand | npc | sp_script:s1-rand | never run | open: move; fixed: script_attach |  |
| s1-wand2 | npc | sp_script:s1-rand | never run | open: move; fixed: script_attach |  |
| s2-auntp | npc | sp_script:s2-aunt | partly: not hit, talk | open: create_sprite, move_stop |  |
| s2-bar | npc | 34 | partly: not hit, talk | open: create_sprite, load_screen, move_stop, sp_disabled; fixed: script_attach |  |
| s2-ca-g | enemy | 402 | partly: not attack, die, enter, hit | open: load_screen; fixed: script_attach |  |
| s2-cgirl | dead |  | never run |  |  |
| s2-cman | npc | sp_script:s2-cult | partly: not talk |  |  |
| s2-crime | screen-base | 68 | never run | open: create_sprite |  |
| s2-crock | dead |  | never run |  |  |
| s2-culg | npc | sp_script:s2-cult | partly: not die, hit | open: create_sprite, load_screen, move, move_stop; fixed: script_attach |  |
| s2-dams | npc | 244 | never run |  |  |
| s2-ds | npc | 625 | partly: not talk |  |  |
| s2-fgate | pickup | 366 | never run | open: create_sprite, move_stop |  |
| s2-fight | other | sp_script:s2-bar | never run |  |  |
| s2-healp | shop | 33 225 226 | partly: not buybottle, hit | open: create_sprite |  |
| s2-idol | other | 579 | partly: not push |  |  |
| s2-jack | enemy | sp_script:s2-auntp | partly: not talk | open: create_sprite, move_stop; fixed: script_attach |  |
| s2-man1 | other | sp_script:s2-bar | partly: not hit |  |  |
| s2-man2 | npc | sp_script:s2-bar | partly: not hit, talk | open: create_sprite, move_stop |  |
| s2-mdoor | npc | 530 | never run | open: load_screen, move_stop; fixed: script_attach | freeze l45 -> kill_this_task 89; freeze l97 -> kill_this_task 113 |
| s2-mybed | object | 37 | never run |  |  |
| s2-na1 | object | 66 | never run |  |  |
| s2-na2 | object | 66 | never run |  |  |
| s2-nadp | npc | sp_script:s2-nad | partly: not hit |  |  |
| s2-out | shop | 35 | never run | open: create_sprite |  |
| s2-qgirl | npc | sp_script:s2-culg sp_script:s2-nad | partly: not talk |  |  |
| s2-ryan2 | cutscene | sp_script:s2-tds | never run | open: move_stop | freeze l16 -> end of procedure |
| s2-ryan3 | cutscene | sp_script:s2-crime | never run | open: create_sprite, move, move_stop |  |
| s2-ryant | npc | sp_script:s2-bar | partly: not talk | open: move_stop |  |
| s2-sale | npc | 65 | never run |  |  |
| s2-sale2 | npc | 532 | never run |  |  |
| s2-sec1 | warp | 307 | never run | open: create_sprite, load_screen; fixed: script_attach |  |
| s2-sec2 | npc | 534 | never run |  |  |
| s2-sec3 | warp | 659 | never run | open: create_sprite, load_screen; fixed: script_attach |  |
| s2-sign3 | sign | 497 | never run |  |  |
| s2-signe | sign | 366 | never run |  |  |
| s2-sk | npc | 499 | never run |  |  |
| s2-stat | npc | 35 | never run |  |  |
| s2-t1s | npc | 467 | never run |  |  |
| s2-t2s | npc | 529 | never run |  |  |
| s2-table | object | 37 | never run |  |  |
| s2-tdoor | other | 497 | never run | open: move_stop |  |
| s2-tds | cutscene | 497 | never run | open: create_sprite, move, move_stop |  |
| s2-wand | npc | sp_script:s2-rand | never run | open: move_stop |  |
| s2-want | npc | 35 | never run |  |  |
| s2-well1 | object | 497 | never run |  |  |
| s2-wench | npc | sp_script:s2-bar | partly: not hit, talk |  |  |
| s3-1st | cutscene | 589 | never run | open: create_sprite, move, move_stop |  |
| s3-bh | cutscene | 129 | never run | open: create_sprite, move_stop |  |
| s3-block | screen-base | 590 | never run |  |  |
| s3-ch1 | dead |  | never run |  |  |
| s3-chick | npc | sp_script:s3-tc | partly: not hit | open: move_stop |  |
| s3-fount | object | 260 586 | never run |  |  |
| s3-freak | npc | sp_script:s3-h1 | never run | open: move_stop |  |
| s3-gh | enemy | 680 | partly: not talk |  |  |
| s3-gob | enemy | 748 | never run |  |  |
| s3-gob2 | npc | 588 | never run |  |  |
| s3-gobg | enemy | 712 | partly: not attack, die, hit |  |  |
| s3-gs | enemy | 680 | partly: not talk |  |  |
| s3-gsign | sign | 748 | never run |  |  |
| s3-h1 | screen-base | 161 | never run | open: create_sprite |  |
| s3-larry | npc | sp_script:s3-st3 | never run | open: create_sprite, move_stop |  |
| s3-loser | npc | sp_script:s3-tc | never run |  |  |
| s3-mayor | npc | sp_script:s3-st1 | partly: not hit | open: load_screen; fixed: script_attach | freeze l104 -> kill_this_task 147 |
| s3-mdoor | cutscene | 619 | never run | open: move_stop |  |
| s3-peeps | enemy | sp_script:s3-tc | partly: not die, hit, talk |  |  |
| s3-rock | other | 590 | never run |  |  |
| s3-sign1 | sign | 590 | never run |  |  |
| s3-sign2 | sign | 587 | partly: not talk |  |  |
| s3-sign3 | sign | 587 | partly: not hit, talk |  |  |
| s3-sign6 | sign | 588 | never run |  |  |
| s3-sign7 | sign | 712 | never run |  |  |
| s3-st1p | npc | sp_script:s3-st1 | partly: not hit |  |  |
| s3-st2p | shop | sp_script:s3-st2 | partly: not buy, hit |  |  |
| s3-st3 | screen-base | 130 | never run | open: create_sprite |  |
| s4-1st | screen-base | 533 | never run |  |  |
| s4-dg | npc | 568 | never run |  |  |
| s4-dgs | screen-base | 568 | never run |  |  |
| s4-dsign | sign | 568 | never run |  |  |
| s4-gs | dead |  | never run |  |  |
| s4-h1 | screen-base | 193 | never run | open: create_sprite |  |
| s4-h1p | npc | sp_script:s4-h1 | never run | open: create_sprite, move |  |
| s4-h2 | screen-base | 163 | never run | open: create_sprite |  |
| s4-h2p1 | npc | sp_script:s4-h2 | never run |  |  |
| s4-h2p2 | npc | sp_script:s4-h2 | never run |  |  |
| s4-h2p3 | npc | sp_script:s4-h2 | never run |  |  |
| s4-healp | shop | 195 | partly: not buybottle, hit | open: create_sprite |  |
| s4-md2 | cutscene | 501 | never run | open: move_stop |  |
| s4-md3 | cutscene | 505 | never run | open: move_stop |  |
| s4-mdoor | cutscene | 501 | never run | open: move_stop |  |
| s4-not | other | 163 | never run | open: move_stop |  |
| s4-sec1 | container | 535 | never run | open: compare_sprite_script |  |
| s4-sign1 | sign | 533 | never run |  |  |
| s4-sign2 | sign | 502 | never run |  |  |
| s4-sign3 | sign | 504 | never run |  |  |
| s4-st1 | screen-base | 162 | never run | open: create_sprite |  |
| s4-st1p | npc | sp_script:s4-st1 | never run |  |  |
| s4-st2 | screen-base | 194 | never run | open: create_sprite |  |
| s4-st2p | npc | sp_script:s4-st2 | never run |  |  |
| s4-st3p | shop | sp_script:s4-st3 | partly: not buy, buybomb, buys1, buysw2, hit |  |  |
| s4-stat | object | 536 | never run |  |  |
| s4-tree | npc | 693 | never run |  |  |
| s5-fd | enemy | sp_script:s5-jops | partly: not die, hit, talk |  |  |
| s5-fguy | enemy | sp_script:s5-jops | partly: not die | open: create_sprite, move_stop |  |
| s5-fmom | enemy | sp_script:s5-jops | partly: not die, talk |  |  |
| s5-heals | screen-base | 226 | never run |  |  |
| s5-sec1 | container | 481 | never run | open: compare_sprite_script |  |
| s5-sign1 | sign | 451 | never run |  |  |
| s5-st1 | screen-base | 228 | never run | open: create_sprite |  |
| s5-st1p | shop | sp_script:s5-st1 | never run |  |  |
| s6-fount | shop | 260 | never run |  |  |
| s6-g1 | npc | 243 | never run |  |  |
| s6-g2 | npc | 243 | never run |  |  |
| s6-hole | warp | 243 | partly: not touch | open: load_screen, sp_nocontrol; fixed: script_attach | freeze l11 -> kill_this_task 29 |
| s6-hole2 | warp | 180 | partly: not touch | open: load_screen, sp_nocontrol; fixed: script_attach | freeze l11 -> kill_this_task 29 |
| s6-sign1 | sign | 184 | never run |  |  |
| s6-sign5 | sign | 253 | never run |  |  |
| s6-st1 | screen-base | 261 | never run | open: create_sprite |  |
| s6-st1p | shop | sp_script:s6-st1 | never run |  |  |
| s6-vend | shop | 164 | never run |  |  |
| s7-boat | other | sp_script:s7-hell | never run | open: move_stop |  |
| s7-dgirl | enemy | 91 126 | never run |  |  |
| s7-dink | object | 58 | never run |  |  |
| s7-girl | other | 122 | never run |  |  |
| s7-hell | screen-base | 85 | never run | open: create_sprite |  |
| s7-mom | other | 122 | never run |  |  |
| s7-pill | enemy | 26 27 64 191 223 | never run | open: sp_base_death |  |
| s7-slimb | enemy | 32 64 123 191 | never run | open: sp_base_death |  |
| s8-da | shop | 731 | never run | open: create_sprite |  |
| s8-dish | object | 764 | never run |  |  |
| s8-duck | npc | 762 | never run |  |  |
| s8-duck2 | npc | 762 | never run | open: load_screen; fixed: script_attach | freeze l10 -> kill_this_task 66 |
| s8-duck3 | npc | 764 | never run |  |  |
| s8-duck4 | npc | sp_script:s8-da | never run |  |  |
| s8-guy | enemy | 290 | never run |  |  |
| s8-sign | sign | 759 | never run |  |  |
| s8-well | object | 766 | never run |  |  |
| savebot | npc | 37 213 252 254 344 349 408 569 588 768 | partly: not hit, talk |  |  |
| savetop | dead |  | never run |  |  |
| sc-drag | enemy | 74 | never run | open: create_sprite, set_callback_random, sp_base_death |  |
| sc-end | screen-base | 73 | never run | open: create_sprite |  |
| sc-ent | dead |  | never run |  |  |
| sc-lock | enemy | 74 137 170 | never run | open: set_callback_random, sp_base_death |  |
| sc-pill | enemy | 106 | never run | open: sp_base_death |  |
| sc-slay | enemy | 106 137 138 | never run |  |  |
| sc-wiz | npc | sp_script:sc-end | never run | open: create_sprite |  |
| sgold | pickup | 663 | partly: not touch |  |  |
| sparkle | dead |  | never run |  |  |
| spice | dead |  | never run |  |  |
| start | system |  | never run | open: create_sprite |  |
| start-1 | system | sp_script:start | never run | open: create_sprite |  |
| start-2 | system | sp_script:start | never run | open: create_sprite |  |
| start-3 | dead |  | never run | open: create_sprite, move_stop |  |
| start-4 | system | sp_script:start | never run | open: create_sprite |  |
| treeduck | dead |  | never run | open: create_sprite |  |
| water | dead |  | never run |  |  |
| xlgold | dead |  | never run | open: create_sprite |  |
