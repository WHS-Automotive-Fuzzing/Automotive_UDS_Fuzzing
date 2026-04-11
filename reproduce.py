import isotp
import can
import csv
import os
from module.uds_isotp import UDSMessage, Response_ID
from module.uds_send import UDSSender

WAIT_RESPONSE_TIME = 0.2
SAVE_INTERVAL = 10


def get_output_path():
    base = "reproduction.csv"
    if not os.path.exists(base):
        return base
    i = 1
    while os.path.exists(f"reproduction_{i}.csv"):
        i += 1
    return f"reproduction_{i}.csv"


def read_result_csv(path="result.csv"):
    records = []
    with open(path, newline='') as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if not row or len(row) < 4:
                continue
            try:
                idx        = int(row[0].strip())
                fail_level = int(row[1].strip())
                udsid      = int(row[2].strip(), 16)
                sid        = int(row[3].strip(), 16)
                data_str   = row[4].strip() if len(row) > 4 else ""
                data       = [int(b, 16) for b in data_str.split() if b.strip()]
                records.append((idx, fail_level, udsid, sid, data))
            except (ValueError, IndexError):
                continue
    return records


def read_send_log_csv(path="send_log.csv"):
    records = []
    with open(path, newline='') as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if not row or len(row) < 3:
                continue
            if '---' in row[0]:
                continue
            try:
                idx      = int(row[0].strip())
                udsid    = int(row[1].strip(), 16)
                sid      = int(row[2].strip(), 16)
                data_str = row[3].strip() if len(row) > 3 else ""
                data     = [int(b, 16) for b in data_str.split() if b.strip()]
                records.append((idx, udsid, sid, data))
            except (ValueError, IndexError):
                continue
    return records


def send_context_message(bus, udsid, sid, data):
    addr   = isotp.Address(isotp.AddressingMode.Normal_11bits, txid=udsid, rxid=Response_ID[udsid])
    stack  = isotp.CanStack(bus=bus, address=addr, params={"tx_padding": 0xFF})
    sender = UDSSender(stack)
    sender.EnterDiagnosticSession(session_type=0x03, retry_count=3)
    success, response = sender.SendUDSMessage(sid, data, timeout=WAIT_RESPONSE_TIME)
    sender.SendECUReset(reset_type=0x02, retry_count=3)
    return success, response


def run_fail_detection(bus, udsid, sid, data):
    msg = UDSMessage(udsid, sid, data, 0, bus)
    fail_level = msg.CheckUDSMessage()
    return fail_level


def save_intermediate(output_path, buffer, is_first):
    """중간 저장 — 첫 저장은 헤더 포함(w), 이후는 append(a)"""
    mode = 'w' if is_first else 'a'
    with open(output_path, mode, newline='') as f:
        writer = csv.writer(f)
        if is_first:
            writer.writerow(['version', 'idx', 'udsid', 'sid', 'data', 'result'])
        writer.writerows(buffer)
    print(f"  [중간 저장] {len(buffer)}개 → {output_path}")


# ──────────────────────────────────────────────
# Version 1: fail 메시지만 N번 반복 재전송
# ──────────────────────────────────────────────
def version1(bus, fail_records, repeat_count):
    output_path = get_output_path()
    total    = len(fail_records)
    buffer   = []
    is_first = True

    try:
        for i, (idx, _, udsid, sid, data) in enumerate(fail_records):
            data_str = ' '.join(f"{b:02X}" for b in data)
            print(f"\n[{i+1}/{total}] idx={idx}  0x{udsid:03X}  SID=0x{sid:02X}  [{data_str}]")

            fail_count = 0
            for r in range(repeat_count):
                fl = run_fail_detection(bus, udsid, sid, data)
                if fl > 0:
                    fail_count += 1
                print(f"  [{r+1}/{repeat_count}] fail_level={fl}  (누적 fail: {fail_count})")

            buffer.append(['1', idx, f"0x{udsid:03X}", f"0x{sid:02X}", data_str, f"{fail_count}/{repeat_count}"])
            print(f"  => {fail_count}/{repeat_count}")

            if len(buffer) >= SAVE_INTERVAL:
                save_intermediate(output_path, buffer, is_first)
                is_first = False
                buffer.clear()

    except KeyboardInterrupt:
        print("\n\n[중단] Ctrl+C 감지")

    finally:
        if buffer:
            print(f"  버퍼에 {len(buffer)}개 남음 → 저장 중...")
            save_intermediate(output_path, buffer, is_first)

    print(f"\n[완료] {output_path}")


# ──────────────────────────────────────────────
# Version 2: 이전 컨텍스트 포함 N번 반복
# ──────────────────────────────────────────────
def version2(bus, fail_records, send_log_records, repeat_count, pre_count):
    output_path  = get_output_path()
    total        = len(fail_records)
    buffer       = []
    is_first     = True
    search_start = 0

    try:
        for i, (idx, _, udsid, sid, data) in enumerate(fail_records):
            data_str = ' '.join(f"{b:02X}" for b in data)
            print(f"\n[{i+1}/{total}] idx={idx}  0x{udsid:03X}  SID=0x{sid:02X}  [{data_str}]")

            fail_pos = None
            for j in range(search_start, len(send_log_records)):
                if send_log_records[j][0] == idx:
                    fail_pos = j
                    search_start = j
                    break

            if fail_pos is None:
                print(f"  [WARN] idx={idx}를 send_log에서 찾을 수 없음, 스킵")
                continue

            pre_records = send_log_records[max(0, fail_pos - pre_count) : fail_pos]
            print(f"  pre={len(pre_records)}개")

            fail_count = 0
            for r in range(repeat_count):
                print(f"  --- [{r+1}/{repeat_count}] ---")
                for _, p_udsid, p_sid, p_data in pre_records:
                    p_data_str = ' '.join(f"{b:02X}" for b in p_data)
                    print(f"  [pre] 0x{p_udsid:03X}  SID=0x{p_sid:02X}  [{p_data_str}]")
                    send_context_message(bus, p_udsid, p_sid, p_data)

                fl = run_fail_detection(bus, udsid, sid, data)
                if fl > 0:
                    fail_count += 1
                print(f"  [fail] fail_level={fl}  (누적 fail: {fail_count})")

            buffer.append(['2', idx, f"0x{udsid:03X}", f"0x{sid:02X}", data_str, f"{fail_count}/{repeat_count}"])
            print(f"  => {fail_count}/{repeat_count}")

            if len(buffer) >= SAVE_INTERVAL:
                save_intermediate(output_path, buffer, is_first)
                is_first = False
                buffer.clear()

    except KeyboardInterrupt:
        print("\n\n[중단] Ctrl+C 감지")

    finally:
        if buffer:
            print(f"  버퍼에 {len(buffer)}개 남음 → 저장 중...")
            save_intermediate(output_path, buffer, is_first)

    print(f"\n[완료] {output_path}")


# ──────────────────────────────────────────────
# 입력 헬퍼
# ──────────────────────────────────────────────
def input_int(prompt, min_val=0):
    while True:
        try:
            val = int(input(prompt).strip())
            if val >= min_val:
                return val
        except ValueError:
            pass
        print(f"  {min_val} 이상의 정수를 입력하세요.")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main():
    print("=== UDS Fail Reproduction Tool ===")
    print("1. Version 1: fail 메시지만 반복 재전송")
    print("2. Version 2: 이전 컨텍스트 포함 반복 재전송 (send_log 기반)")

    while True:
        version = input("\n버전 선택 (1 or 2): ").strip()
        if version in ('1', '2'):
            break
        print("  1 또는 2를 입력하세요.")

    repeat_count = input_int("반복 횟수: ", min_val=1)

    pre_count = 0
    if version == '2':
        pre_count = input_int("이전 로그 개수: ", min_val=0)

    print("\nresult.csv 읽는 중...")
    all_records  = read_result_csv("result.csv")
    fail_records = [r for r in all_records if r[1] > 0]
    print(f"전체 {len(all_records)}개 중 fail {len(fail_records)}개 발견")

    if not fail_records:
        print("fail 메시지가 없습니다.")
        return

    bus = can.interface.Bus(channel='can0', bustype='socketcan')
    try:
        if version == '1':
            version1(bus, fail_records, repeat_count)
        else:
            print("send_log.csv 읽는 중...")
            send_log_records = read_send_log_csv("send_log.csv")
            print(f"send_log: {len(send_log_records)}개 레코드")
            version2(bus, fail_records, send_log_records, repeat_count, pre_count)
    finally:
        bus.shutdown()
        print("[BUS] can0 종료")


if __name__ == "__main__":
    main()