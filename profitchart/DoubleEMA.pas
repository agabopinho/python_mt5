input
  Fast(55);
  Slow(144);
var
  ema_fast : Float;
  ema_slow : Float;
begin
  ema_fast := MediaExp(Fast,Close);
  ema_slow := MediaExp(Slow,Close);
  Plot(ema_fast);
  Plot2(ema_slow);
end;