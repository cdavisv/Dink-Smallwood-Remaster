//Old Burt's leg, boot still on (text approved by the owner, 16 Nov 2026)

void main( void )
{
 sp_touch_damage(&current_sprite, -1);
}

void touch( void )
{
 &x3_leg = 1;
 Playsound(10, 22050, 0, 0, 0);
 say("Burt's leg. Still warm. I'm not thinking about why.", 1);
 sp_brain_parm(&current_sprite, 200);
 sp_brain(&current_sprite, 12);
 sp_touch_damage(&current_sprite, 0);
 sp_timing(&current_sprite, 0);
}
