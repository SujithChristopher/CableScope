float angle_motor()
{
  _enccount = angle.read();
  if (_enccount >= ENC1MAXCOUNT) {
    angle.write(_enccount - ENC1MAXCOUNT);
  } else if (_enccount <= - ENC1MAXCOUNT) {
    angle.write(_enccount + ENC1MAXCOUNT);
  }
  return ENC1COUNT2DEG * _enccount;
}
