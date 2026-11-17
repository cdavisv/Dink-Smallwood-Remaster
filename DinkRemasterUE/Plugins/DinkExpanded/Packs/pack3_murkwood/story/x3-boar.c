//The Murk boar: ate Old Burt's leg, boot and all (text approved by the owner, 16 Nov 2026)

void main( void )
{
 screenlock(1);
 int &mcounter;
 sp_brain(&current_sprite, 9);
 sp_speed(&current_sprite, 1);
 sp_nohit(&current_sprite, 0);
 sp_distance(&current_sprite, 50);
 sp_timing(&current_sprite, 33);
 sp_exp(&current_sprite, 60);
 sp_base_walk(&current_sprite, 530);
 sp_base_death(&current_sprite, 550);
 sp_base_attack(&current_sprite, 540);
 sp_defense(&current_sprite, 3);
 sp_strength(&current_sprite, 10);
 sp_touch_damage(&current_sprite, 6);
 sp_hitpoints(&current_sprite, 40);
}

void hit( void )
{
 playsound(29, 22050, 0, &current_sprite, 0);
 sp_target(&current_sprite, &enemy_sprite);
}

void die( void )
{
 if (get_sprite_with_this_brain(9, &current_sprite) == 0)
 {
  screenlock(0);
  playsound(43, 22050, 0, 0, 0);
 }
 int &hold = sp_editor_num(&current_sprite);
 if (&hold != 0)
  editor_type(&hold, 1);
 &x3_boar = 1;
 int &bx = sp_x(&current_sprite, -1);
 int &by = sp_y(&current_sprite, -1);
 int &leg = create_sprite(&bx, &by, 0, 178, 1);
 sp_script(&leg, "x3-leg");
 say("Something fell out of it. With a boot on.", 1);
}

void attack( void )
{
 playsound(31, 22050, 0, &current_sprite, 0);
 &mcounter = random(4000, 0);
 sp_attack_wait(&current_sprite, &mcounter);
}
