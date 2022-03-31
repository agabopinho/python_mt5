input
  Period(14);
var
  cci_value : Float;
  color     : Integer;
begin
  cci_value := CCI(Period);
  Plot(cci_value);
  SetPlotColor(1,ClGreen);
  if (cci_value > - 100) and (cci_value[1] < - 100) then
    color := ClGreen
  else if (cci_value > 100) and (cci_value[1] < 100) then
    color := ClGreen
  else if (cci_value < 100) and (cci_value[1] > 100) then
    color := ClRed
  else if (cci_value < - 100) and (cci_value[1] > - 100) then
    color := ClRed;
  PaintBar(color);
end;