import isotp
import csv
import can
import time
import signal
from collections import deque
from module.uds_isotp import *
from module.mutator import *
from module.logger import *

MAX_DEPTH = 10
msg_idx=0

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

def fail(dq, msg_idx, msg):
    print(f"Fail Detected! {msg_idx}: [{hex(msg.udsid)}][{hex(msg.sid)}] [Depth: {msg.depth}] [{msg.data}]")
    save_result(msg_idx, msg)
    mutated_data_list = deterministic_mutator(msg)
    for mutated_data in mutated_data_list:
        dq.appendleft((msg.udsid, msg.sid, mutated_data, 0))

def deterministic_checker(dq, msg):
    global msg_idx
    mutated_data_list = deterministic_mutator(msg)
    fail_checker = False
    for mutated_data in mutated_data_list:
        msg = UDSMessage(msg.udsid, msg.sid, mutated_data, msg.depth, msg.bus)

        if msg.CheckUDSMessage():
            fail(dq, msg_idx, msg)
            fail_checker = True
        save_log(msg_idx, msg)
        msg_idx += 1
        
    return fail_checker

def test_deque(dq, bus):
    global msg_idx
    udsid, sid, data, depth = dq.popleft()
    msg = UDSMessage(udsid, sid, data, depth, bus)

    fail_detection = msg.CheckUDSMessage()
    save_log(msg_idx, msg)
    msg_idx += 1
    
    if fail_detection:
        fail(dq, msg_idx, msg)
    else:
        if depth < MAX_DEPTH:
            if not deterministic_checker(dq, msg):
                for mutated_data in nondeterministic_mutator(msg):
                    dq.append((udsid, sid, mutated_data, depth+1))

def main():
    seed_csv_path1 = "seed1.csv"
    seed_csv_path2 = "seed2.csv"
    signal.signal(signal.SIGINT, save_and_exit)
    open_csv()

    dq1 = deque(read_uds_records_from_csv(seed_csv_path1)) # multi queue for seed1
    dq2 = deque(read_uds_records_from_csv(seed_csv_path2)) # multi queue for seed2

    bus = can.interface.Bus(channel='can0', bustype='socketcan')

    while dq1 and dq2: # when both queues are not empty
        # Process first queue
        test_deque(dq1, bus)

        # process second queue
        test_deque(dq2, bus)

    if dq1:
        while dq1:
            test_deque(dq1, bus)
    
    else :
        while dq2:
            test_deque(dq2, bus)

    flush_buffer()

if __name__ == "__main__":
    main()
