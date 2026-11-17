//Old Burt, sealed in Murkwood with the forest (text approved by the owner, 16 Nov 2026)

void main( void )
{
 sp_base_walk(&current_sprite, 330);
 sp_speed(&current_sprite, 1);
}

void talk( void )
{
 freeze(1);
 freeze(&current_sprite);
 if (&x3_burt == 0)
 {
  say_stop("`3Well I'll be. A visitor! Nobody visits.", &current_sprite);
  wait(250);
  say_stop("`3Not since King Daniel sealed the forest. With me in it.", &current_sprite);
  wait(250);
  say_stop("You've been stuck in here the whole time?", 1);
  wait(250);
  say_stop("`3Went out for kindling. Came back, there's a magic wall. Nobody told me.", &current_sprite);
  wait(250);
  say_stop("Uh, where's your other leg?", 1);
  wait(250);
  say_stop("`3Boar ate it. Big ugly thing, up in the wallow north of the trail.", &current_sprite);
  say_stop("`3Had my good boot on, too. Bring 'em back and I'll make it worth your while.", &current_sprite);
  wait(250);
  say_stop("You want me to fetch your leg. Out of a boar.", 1);
  wait(250);
  say_stop("`3Leg AND boot. The boot's the important bit.", &current_sprite);
  &x3_burt = 1;
  unfreeze(1);
  unfreeze(&current_sprite);
  return;
 }
 if (&x3_burt == 2)
 {
  say_stop("`3Isn't she lovely? Gonna hang her right over the fire.", &current_sprite);
  wait(250);
  say_stop("It's a leg, Burt.", 1);
  unfreeze(1);
  unfreeze(&current_sprite);
  return;
 }
 choice_start()
 (&x3_leg == 1) "Give Burt his leg"
 "Ask about the seal"
 "Leave"
 choice_end()
 if (&result == 1)
 {
  say_stop("Here. One leg, slightly chewed. Boot included.", 1);
  wait(250);
  say_stop("`3My boot! Still laced, too. Look at that.", &current_sprite);
  wait(250);
  say_stop("Are you going to... put it back on?", 1);
  wait(250);
  say_stop("`3Don't be daft, boy. I'm having it stuffed. Over the fireplace.", &current_sprite);
  wait(250);
  say_stop("`3Here. Took this off a tax collector the boar didn't finish.", &current_sprite);
  &gold += 150;
  say_stop("150 gold! Your leg was worth every bite.", 1);
  &x3_leg = 2;
  &x3_burt = 2;
 }
 if (&result == 2)
 {
  say_stop("Why'd the King seal this place, anyway?", 1);
  wait(250);
  say_stop("`3Folk say it's to keep people out.", &current_sprite);
  wait(250);
  say_stop("`3Folk are idiots. You don't build a wall that strong to keep a thing OUT.", &current_sprite);
  wait(250);
  say_stop("I'm going to pretend you didn't say that.", 1);
 }
 unfreeze(1);
 unfreeze(&current_sprite);
}
