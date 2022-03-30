input
  Fast(100);
  Slow(400);
var
  ifr_fast : Float;
  ifr_slow : Float;
begin
  ifr_fast := IFR(Fast);
  ifr_slow := IFR(Slow);
  Plot(ifr_fast);
  Plot2(ifr_slow);
  if (ifr_fast > ifr_slow) then
    PaintBar(ClGreen)
  else if (ifr_fast < ifr_slow) then
    PaintBar(ClRed)
  else 
    PaintBar(ClWhite);
end;





