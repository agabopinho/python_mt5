input
  Fast(25);
  Slow(100);
  Smooth (5);
var
  ifr_fast : Float;
  ifr_slow : Float;
begin
  ifr_fast := Media(Smooth, IFR(Fast));
  ifr_slow := Media(Smooth, IFR(Slow));
  Plot(ifr_fast);
  Plot2(ifr_slow);
  if (ifr_fast > ifr_slow) then
    PaintBar(ClGreen)
  else if (ifr_fast < ifr_slow) then
    PaintBar(ClRed);
end;