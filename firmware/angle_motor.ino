// Function to read encoder angle in degrees with overflow handling
float angle_motor()
{
  _enccount = angle.read();
  
  // Handle encoder overflow/underflow
  if (_enccount >= ENC1MAXCOUNT) {
    angle.write(_enccount - ENC1MAXCOUNT);
  } else if (_enccount <= -ENC1MAXCOUNT) {
    angle.write(_enccount + ENC1MAXCOUNT);
  }
  
  // Convert encoder counts to degrees
  return ENC1COUNT2DEG * _enccount;
}
