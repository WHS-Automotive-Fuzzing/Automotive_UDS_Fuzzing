import isotp
import csv
import can
import time
import signal
import sys
from collections import deque
from module.uds_send import *



Response_ID = {
    0x73E: 0x7A8,
    0x70E: 0x778,
    0x74C: 0x7B6,
    0x723: 0x78D,
    0x74B: 0x7B5,
    0x74A: 0x7B4,
    0x17FC0084: 0x17FE0084,
}
# CSV 파일 읽기
records = []
with open('test.csv', newline='') as f:
    reader = csv.reader(f)
    next(reader, None)  # 헤더 스킵
    for row in reader:
        if not row or len(row) < 3:
            continue
        msg_idx = int(row[0].strip(), 16)
        udsid = int(row[1].strip(), 16)
        sid = int(row[2].strip(), 16)
        data = [int(cell.strip(), 16) for cell in row[3:] if cell.strip()]
        records.append((msg_idx, udsid, sid, data))

# CAN 버스 및 ISO-TP 스택 설정
bus = can.interface.Bus(channel='can0', bustype='socketcan')
    

# 메시지 하나씩 전송
while records:
    msg_idx, udsid, sid, data = records.pop(0)
    
    addr = isotp.Address(isotp.AddressingMode.Normal_11bits, txid=udsid, rxid=Response_ID[udsid])
    params = {"tx_padding": 0xFF}
    stack = isotp.CanStack(bus= bus, address=addr, params=params)
    sender = UDSSender(stack)
    
   
    
    # 진단 모드 진입 + 메시지 전송
    message = [sid] + data
    print(f"\n[MSG {msg_idx:04X}] Sending to 0x{udsid:03X}: {bytes(message).hex()}")
    
    success, response, diag_resp = sender.StartDiagnosticAndSendMessage(
        message=message,
        session_type=0x03,
        retry_count=3
    )
    
    if success and response:
        print(f"[RESPONSE] {response.hex()}")
    else:
        print("[ERROR] No response or failed")
    
    # 다음 메시지 전송 대기
    input("Press Enter to continue...")

print("\n[DONE] All messages sent")
bus.shutdown()