import isotp
import csv
import can
import time
import signal
import sys
from collections import deque
from module.uds_isotp import *
from module.mutator import *

result_csv_path = "result.csv"
MAX_DEPTH = 10
buffer = []

def read_uds_records_from_csv(path: str):
    records = []
    with open(path, newline='') as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if not row or len(row) < 3:
                continue
            udsid = int(row[0].strip(), 16)
            sid = int(row[1].strip(), 16)
            data = [int(cell.strip(), 16) for cell in row[2:] if cell.strip()]
            depth = 0
            records.append((udsid, sid, data, depth))
    return records

def save_result(udsid, sid, data):
    global buffer
    hex_row = [f"{udsid:04X}", f"{sid:02X}"] + [f"{byte:02X}" for byte in data]
    buffer.append(hex_row)
    if len(buffer) >= 10:
        with open(result_csv_path, "a", newline='') as f:
            writer = csv.writer(f)
            writer.writerows(buffer)
        buffer.clear()

def flush_buffer():
    global buffer
    if buffer:
        with open(result_csv_path, "a", newline='') as f:
            writer = csv.writer(f)
            writer.writerows(buffer)
        buffer.clear()

def save_and_exit(signum, frame):
    flush_buffer()
    sys.exit(0)

def main():
    seed_csv_path = "seed.csv"
    signal.signal(signal.SIGINT, save_and_exit)

    with open(result_csv_path, "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['udsid', 'sid', 'data0', 'data1', 'data2', 'data3', 'data4', 'data5', 'data6', 'data7'])

    bus = can.interface.Bus(channel='can0', bustype='socketcan')
    records = read_uds_records_from_csv(seed_csv_path)
    dq = deque(records)

    while dq:
        udsid, sid, data, depth = dq.popleft()
        msg = UDSMessage(udsid, sid, data, depth, bus)
        fail_detection = msg.CheckUDSMessage()
        mutated_data_list = mutator(data)

        if fail_detection:
            print(f"Fail Detected! [{hex(udsid)}][{hex(sid)}] [Depth: {depth}] [{data}]")
            save_result(udsid, sid, data)
            for mutated_data in mutated_data_list:
                dq.appendleft((udsid, sid, mutated_data, 0))
        else:
            if depth < MAX_DEPTH:
                for mutated_data in mutated_data_list:
                    dq.append((udsid, sid, mutated_data, depth + 1))

    flush_buffer()

if __name__ == "__main__":
    main()
