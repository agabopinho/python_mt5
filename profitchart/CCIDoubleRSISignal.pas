input
  CCIPeriod(21);
  RSIFast(34);
  RSISlow(144);
  RSISmooth(8);
var
  scci   : Float;
  rsi_fast    : Float;
  rsi_slow    : Float;
  ema_rsifast : Float;
  ema_rsislow : Float;
  signal      : Integer;
  plotted     : Integer;
begin
  scci := CCI(CCIPeriod);
  rsi_fast := RSI(RSIFast,0);
  rsi_slow := RSI(RSISlow,0);
  ema_rsifast := MediaExp(RSISmooth,rsi_fast);
  ema_rsislow := MediaExp(RSISmooth,rsi_slow);
  signal := signal[1];
  plotted := plotted[1];
  if (scci[0] > 100) and (scci[1] < 100) then
    signal := 1
  else if (scci[0] < - 100) and (scci[1] > - 100) then
    signal := 2;
  if (signal[0] = 1) and (plotted[0] <> 1) and (ema_rsifast[0] > ema_rsislow[0]) then
    begin
      PlotText("C",ClGreen,10,12);
      plotted := 1;
    end;
  if (signal[0] = 2) and (plotted[0] <> 2) and (ema_rsifast[0] < ema_rsislow[0]) then
    begin
      PlotText("V",ClRed,10,12);
      plotted := 2;
    end;
  if (plotted[0] = 1) then
    PaintBar(ClGreen)
  else if (plotted[0] = 2) then
    PaintBar(ClRed);
end;