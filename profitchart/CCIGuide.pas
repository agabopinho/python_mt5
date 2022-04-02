input
  Period(21);
var
  scci : Float;
  color     : Integer;
begin
  scci := CCI(Period);
  Plot(scci);
  if (scci[0] > 100) and (scci[1] < 100) then
    color := ClGreen
  else if (scci[0] < - 100) and (scci[1] > - 100) then
    color := ClRed
  else 
    color := color[1];
  PaintBar(color);
end;