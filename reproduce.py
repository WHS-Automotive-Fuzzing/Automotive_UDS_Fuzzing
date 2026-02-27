import isotp
import can
import csv
import os
from module.uds_isotp import UDSMessage, Response_ID
from module.uds_send import UDSSender

WAIT_RESPONSE_TIME = 0.2


def get_output_path():
    base = "reproduction.csv"
    if not os.path.exists(base):
        return base
    i = 1
    while os.path.exists(f"reproduction_{i}.csv"):
        i += 1
    return f"reproduction_{i}.csv"


def read_result_csv(path="result.csv"):
    """result.csv에서 전체 레코드 읽기
    format: idx(dec), fail_level(dec), udsid(hex), sid(hex), data(space-sep hex), response
    """
    all_records = []
    with open(path, newline='') as f:
        reader = csv.reader(f)
        next(reader, None)  # 헤더 스킵
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
                all_records.append((idx, fail_level, udsid, sid, data))
            except (ValueError, IndexError):
                continue
    return all_records


def send_context_message(bus, udsid, sid, data):
    """컨텍스트 메시지 전송 — 진단모드 진입 후 UDS 메시지 전송만 (DTC 비교, ECUReset 없음)"""
    addr   = isotp.Address(isotp.AddressingMode.Normal_11bits, txid=udsid, rxid=Response_ID[udsid])
    stack  = isotp.CanStack(bus=bus, address=addr, params={"tx_padding": 0xFF})
    sender = UDSSender(stack)
    sender.EnterDiagnosticSession(session_type=0x03, retry_count=3)
    success, response = sender.SendUDSMessage(sid, data, timeout=WAIT_RESPONSE_TIME)
    return success, response


def run_fail_detection(bus, udsid, sid, data):
    """기존 fuzzer와 동일한 fail 판정 — 진단모드 + DTC 비교 + ECUReset"""
    msg = UDSMessage(udsid, sid, data, 0, bus)
    fail_level = msg.CheckUDSMessage()
    return fail_level


def write_results(output_path, results):
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['version', 'idx', 'udsid', 'sid', 'data', 'result'])
        writer.writerows(results)
    print(f"\n[저장 완료] {output_path}")


# ──────────────────────────────────────────────
# Version 1: fail 메시지만 N번 반복 재전송
# ──────────────────────────────────────────────
def version1(bus, fail_records, repeat_count):
    output_path = get_output_path()
    results = []
    total = len(fail_records)

    for i, (idx, _, udsid, sid, data) in enumerate(fail_records):
        data_str = ' '.join(f"{b:02X}" for b in data)
        print(f"\n[{i+1}/{total}] idx={idx}  0x{udsid:03X}  SID=0x{sid:02X}  [{data_str}]")

        fail_count = 0
        for r in range(repeat_count):
            fl = run_fail_detection(bus, udsid, sid, data)
            if fl > 0:
                fail_count += 1
            print(f"  [{r+1}/{repeat_count}] fail_level={fl}  (누적 fail: {fail_count})")

        results.append(['1', idx, f"0x{udsid:03X}", f"0x{sid:02X}", data_str, f"{fail_count}/{repeat_count}"])
        print(f"  => {fail_count}/{repeat_count}")

    write_results(output_path, results)


# ──────────────────────────────────────────────
# Version 2: 이전/이후 컨텍스트 포함 N번 반복
# ──────────────────────────────────────────────
def version2(bus, all_records, fail_records, repeat_count, pre_count, post_count):
    output_path = get_output_path()

    idx_map     = {r[0]: r for r in all_records}
    sorted_idxs = sorted(idx_map.keys())
    idx_pos     = {idx: pos for pos, idx in enumerate(sorted_idxs)}

    results = []
    total = len(fail_records)

    for i, (idx, _, udsid, sid, data) in enumerate(fail_records):
        data_str = ' '.join(f"{b:02X}" for b in data)
        print(f"\n[{i+1}/{total}] idx={idx}  0x{udsid:03X}  SID=0x{sid:02X}  [{data_str}]")

        pos = idx_pos.get(idx)
        if pos is None:
            print("  [WARN] idx를 로그에서 찾을 수 없음, 스킵")
            continue

        pre_idxs  = sorted_idxs[max(0, pos - pre_count) : pos]
        post_idxs = sorted_idxs[pos + 1 : pos + 1 + post_count]
        print(f"  pre={len(pre_idxs)}개, post={len(post_idxs)}개")

        fail_count = 0
        for r in range(repeat_count):
            print(f"  --- [{r+1}/{repeat_count}] ---")

            # pre 메시지 전송 (컨텍스트 재현, reset 없음)
            for pidx in pre_idxs:
                _, _, p_udsid, p_sid, p_data = idx_map[pidx]
                print(f"  [pre ] 0x{p_udsid:03X}  SID=0x{p_sid:02X}")
                send_context_message(bus, p_udsid, p_sid, p_data)

            # fail 메시지: 기존 방식 그대로 fail detection + ECUReset
            fl = run_fail_detection(bus, udsid, sid, data)
            if fl > 0:
                fail_count += 1
            print(f"  [fail] fail_level={fl}  (누적 fail: {fail_count})")

            # post 메시지 전송 (ECUReset 이후 상태에서)
            for nidx in post_idxs:
                _, _, n_udsid, n_sid, n_data = idx_map[nidx]
                print(f"  [post] 0x{n_udsid:03X}  SID=0x{n_sid:02X}")
                send_context_message(bus, n_udsid, n_sid, n_data)

        results.append(['2', idx, f"0x{udsid:03X}", f"0x{sid:02X}", data_str, f"{fail_count}/{repeat_count}"])
        print(f"  => {fail_count}/{repeat_count}")

    write_results(output_path, results)


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
    print("2. Version 2: 이전/이후 컨텍스트 포함 반복 재전송")

    while True:
        version = input("\n버전 선택 (1 or 2): ").strip()
        if version in ('1', '2'):
            break
        print("  1 또는 2를 입력하세요.")

    repeat_count = input_int("반복 횟수: ", min_val=1)

    pre_count = post_count = 0
    if version == '2':
        pre_count  = input_int("이전 로그 개수: ", min_val=0)
        post_count = input_int("이후 로그 개수: ", min_val=0)

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
            version2(bus, all_records, fail_records, repeat_count, pre_count, post_count)
    finally:
        bus.shutdown()


if __name__ == "__main__":
    main()
