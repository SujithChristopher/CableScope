// -------------------- Your angle function (unchanged) --------------------
float angle_motor()
{
   long _enccount;
  _enccount = angle.read();
  if (_enccount >= ENC1MAXCOUNT) {
    angle.write(_enccount - ENC1MAXCOUNT);
  } else if (_enccount <= - ENC1MAXCOUNT) {
    angle.write(_enccount + ENC1MAXCOUNT);
  }
  return ENC1COUNT2DEG * _enccount; // degrees
}
