//The Thin Place: where Dink comes through the worn-out seal (text approved by the owner, 16 Nov 2026)

void main( void )
{
 if (&x3_thin == 0)
 {
  &x3_thin = 1;
  freeze(1);
  wait(500);
  say_stop("Whoa. The air in here is all thick. Like Mom's porridge.", 1);
  wait(250);
  say_stop("So THIS is what King Daniel sealed shut.", 1);
  wait(250);
  say_stop("Nobody seals a forest unless there's something good in it.", 1);
  unfreeze(1);
 }
}
