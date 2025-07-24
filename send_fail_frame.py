import isotp
import csv
import can
import time
import signal
import sys
from collections import deque
from module.uds_isotp import *
from module.mutator import *

records = []
with open('result.csv', newline='') as f:
  reader = csv.reader(f)
  next(reader, None)
  for row in reader:
    if not row or len(row) < 3:
      continue
    msg_idx = int(row[0].strip(), 16)
    udsid = int(row[1].strip(), 16)
    sid = int(row[2].strip(), 16)
    data = [int(cell.strip(), 16) for cell in row[3:] if cell.strip()]
    records.append((msg_idx, udsid, sid, data))

bus = can.interface.Bus(channel='can0', bustype='socketcan')

while records:
    msg_idx, udsid, sid, data = records.pop(0)
    msg = UDSMessage(udsid, sid, data, 0, bus)
    
    msg.Debug_fail()
    input("Waiting...")
