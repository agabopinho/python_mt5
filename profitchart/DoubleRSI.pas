input
  Fast(34);
  Slow(144);
  Smooth(8);
var
  ifr_fast : Float;
  ifr_slow : Float;
begin
  ifr_fast := Media(Smooth,IFR(Fast));
  ifr_slow := Media(Smooth,IFR(Slow));
  Plot(ifr_fast);
  Plot2(ifr_slow);
  if (ifr_fast[0] > ifr_slow[0]) then
    PaintBar(ClGreen)
  else if (ifr_fast[0] < ifr_slow[0]) then
    PaintBar(ClRed);
end;