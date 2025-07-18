import can
import isotp
import time
import csv

# 설정값
TX_ID = 0x7E0
RX_ID = 0x7E8
VCAN_IF = 'can0'
TIMEOUT = 1.0
REQUEST_PAYLOAD = b'\x00\x00'

# 응답 분석 함수
def analyze_response(resp: bytes, sid: int) -> str:
    if not resp:
        return "Timeout"
    elif resp[0] == 0x7F:
        if len(resp) > 2:
            if resp[2] == 0x11:
                return "Unsupported (NRC 0x11)"
            else:
                return f"NRC 0x{resp[2]:02X}"
        else:
            return "Invalid NRC"
    elif resp[0] == sid + 0x40:
        return "Positive"
    else:
        return "Unknown"

# CAN 통신 초기화
bus = can.interface.Bus(channel=VCAN_IF, bustype='socketcan')
addr = isotp.Address(isotp.AddressingMode.Normal_11bits, txid=TX_ID, rxid=RX_ID)
stack = isotp.CanStack(bus=bus, address=addr)

print("진단 세션 진입 시도 (0x10 0x03)...")

# Step 1. 진단 세션 진입
stack.send(b'\x10\x03')
start_time = time.time()
response = None

while time.time() - start_time < TIMEOUT:
    stack.process()
    if stack.available():
        response = stack.recv()
        break
    time.sleep(0.01)

# 응답 확인
if response and len(response) >= 2 and response[0] == 0x50 and response[1] == 0x03:
    print("→ 진단 세션 진입 성공!\n")
else:
    print("→ 진단 세션 진입 실패. 테스트 종료.")
    bus.shutdown()
    exit()

# Step 2. SID 탐색
print("SID 탐색 시작...\n")
results = []

try:
    for sid in range(0xFF, 0x3F, -1):  # FF부터 40까지 감소
        if sid == 0x3F:
            continue  # 0x3F는 Reserved SID

        request = bytes([sid]) + REQUEST_PAYLOAD
        print(f"[+] SID 0x{sid:02X} 요청 전송")

        stack.send(request)

        start_time = time.time()
        response = None

        while time.time() - start_time < TIMEOUT:
            stack.process()
            if stack.available():
                response = stack.recv()
                break
            time.sleep(0.01)

        result = analyze_response(response, sid)
        response_hex = response.hex() if response else ""
        print(f" → 응답: {response_hex} , 결과: {result}")

        # 저장할 정보 추가
        results.append([
            f"0x{sid:02X}",         # SID
            request.hex(),          # 보낸 요청
            response_hex,           # 받은 응답
            result
        ])

        time.sleep(0.05)

finally:
    print("\nCAN 통신 종료 중...")
    bus.shutdown()

# 결과 저장
csv_filename = f"seed_pool_0x{TX_ID:X}_to_0x{RX_ID:X}.csv"
with open(csv_filename, mode='w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["SID", "Request", "Response", "Result"])
    writer.writerows(results)

print(f"\n완료! {len(results)}개의 결과가 {csv_filename}에 저장됨.")