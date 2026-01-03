import isotp
import csv
import can
import time
import signal
import sys
from collections import deque
from module.uds_sender import UDSSender

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

# ISO-TP 스택 초기화 (첫 번째 메시지의 UDS ID 사용)
if records:
    first_udsid = records[0][1]
    isotp_params = isotp.params.TransportLayerParameters(
        stmin=0,
        blocksize=0,
        tx_padding=0x00,
        rx_flowcontrol_timeout=1000,
        rx_consecutive_frame_timeout=1000
    )
    
    addr = isotp.Address(
        isotp.AddressingMode.Normal_11bits,
        txid=first_udsid,
        rxid=first_udsid + 8
    )
    
    stack = isotp.CanStack(bus=bus, address=addr, params=isotp_params)
    uds_sender = UDSSender(stack)

# 메시지 하나씩 전송
while records:
    msg_idx, udsid, sid, data = records.pop(0)
    
    # ISO-TP 주소 업데이트 (UDS ID가 변경되는 경우)
    if addr.txid != udsid:
        addr = isotp.Address(
            isotp.AddressingMode.Normal_11bits,
            txid=udsid,
            rxid=udsid + 8
        )
        stack = isotp.CanStack(bus=bus, address=addr, params=isotp_params)
        uds_sender = UDSSender(stack)
    
    # 진단 모드 진입 + 메시지 전송
    message = [sid] + data
    print(f"\n[MSG {msg_idx:04X}] Sending to 0x{udsid:03X}: {bytes(message).hex()}")
    
    success, response, diag_resp = uds_sender.StartDiagnosticAndSendMessage(
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