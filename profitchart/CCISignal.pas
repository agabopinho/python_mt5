input
  Period(21);
var
  scci : Float;
  signal    : Float;
begin
  scci := CCI(Period);
  signal := signal[1];
  if (scci[0] > 100) and (scci[1] < 100) then
    signal := 1
  else if (scci[0] < - 100) and (scci[1] > - 100) then
    signal := 2;
  if (signal[0] <> signal[1]) then
    begin
      if (signal[0] = 1) then
        PlotText("C",ClGreen,30,12)
      else if (signal[0] = 2) then
        PlotText("V",ClRed,30,12);
    end;
  if (signal[0] = 1) then
    PaintBar(ClGreen)
  else if (signal[0] = 2) then
    PaintBar(ClRed);
end;