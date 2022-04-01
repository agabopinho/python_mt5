input
  Period(21);
var
  cci_value : Float;
  color     : Integer;
begin
  cci_value := CCI(Period);
  Plot(cci_value);
  SetPlotColor(1,ClGreen);
  if (cci_value[0] > - 100) and (cci_value[1] < - 100) then
    color := ClGreen
  else if (cci_value[0] > 100) and (cci_value[1] < 100) then
    color := ClGreen
  else if (cci_value[0] < 100) and (cci_value[1] > 100) then
    color := ClRed
  else if (cci_value[0] < - 100) and (cci_value[1] > - 100) then
    color := ClRed
  else 
    color := color[1];
  PaintBar(color);
end;