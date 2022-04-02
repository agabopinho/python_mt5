input
  Fast(34);
  Slow(144);
  Smooth(8);
var
  rsi_fast    : Float;
  rsi_slow    : Float;
  ema_rsifast : Float;
  ema_rsislow : Float;
begin
  rsi_fast := RSI(Fast,0);
  rsi_slow := RSI(Slow,0);
  ema_rsifast := MediaExp(Smooth,rsi_fast);
  ema_rsislow := MediaExp(Smooth,rsi_slow);
  Plot(ema_rsifast);
  Plot2(ema_rsislow);
  if (ema_rsifast[0] > ema_rsislow[0]) then
    PaintBar(ClGreen)
  else if (ema_rsifast[0] < ema_rsislow[0]) then
    PaintBar(ClRed);
end;