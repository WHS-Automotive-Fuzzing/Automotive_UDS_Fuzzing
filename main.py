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
send_log_path = "send_log.csv"
MAX_DEPTH = 10
buffer = []
send_buffer = []

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

def save_result(msg_idx,udsid, sid, data):
    global buffer
    hex_row = [f"{msg_idx}", f"{udsid:04X}", f"{sid:02X}"] + [f"{byte:02X}" for byte in data]
    buffer.append(hex_row)
    if len(buffer) >= 10:
        with open(result_csv_path, "a", newline='') as f:
            writer = csv.writer(f)
            writer.writerows(buffer)
        buffer.clear()

def save_log(msg_idx, udsid, sid, data):
    global send_buffer
    hex_row = [f"{msg_idx}", f"{udsid:04X}", f"{sid:02X}"] + [f"{byte:02X}" for byte in data]
    send_buffer.append(hex_row)
    if len(buffer) >= 10:
        with open(result_csv_path, "a", newline='') as f:
            writer = csv.writer(f)
            writer.writerows(send_buffer)
        send_buffer.clear()

def flush_buffer():
    global buffer
    global send_buffer
    if buffer:
        with open(result_csv_path, "a", newline='') as f:
            writer = csv.writer(f)
            writer.writerows(buffer)
        buffer.clear()
    if send_buffer:
        with open(send_log_path, "a", newline='') as f:
            writer = csv.writer(f)
            writer.writerows(send_buffer)
        send_buffer.clear()

def save_and_exit(signum, frame):
    flush_buffer()
    sys.exit(0)

def main():
    msg_idx = 0
    seed_csv_path1 = "seed1.csv"
    seed_csv_path2 = "seed2.csv"
    signal.signal(signal.SIGINT, save_and_exit)

    with open(result_csv_path, "w", newline='') as f: # result csv
        writer = csv.writer(f)
        writer.writerow(['idx','udsid', 'sid', 'data0', 'data1', 'data2', 'data3', 'data4', 'data5', 'data6', 'data7'])
    
    with open(send_log_path, "w", newline='') as f: # send log csv
        writer = csv.writer(f)
        writer.writerow(['idx','udsid', 'sid', 'data'])

    dq1 = deque(read_uds_records_from_csv(seed_csv_path1)) # multi queue for seed1
    dq2 = deque(read_uds_records_from_csv(seed_csv_path2)) # multi queue for seed2

    bus = can.interface.Bus(channel='can0', bustype='socketcan')

    while dq1 and dq2: # when both queues are not empty
        # Process first queue
        udsid, sid, data, depth = dq1.popleft()
        msg = UDSMessage(udsid, sid, data, depth, bus)
        save_log(msg_idx, udsid, sid, data)
        msg_idx += 1

        fail_detection = msg.CheckUDSMessage()
        mutated_data_list = mutator(data)

        if fail_detection:
            print(f"Fail Detected! {msg_idx}: [{hex(udsid)}][{hex(sid)}] [Depth: {depth}] [{data}]")
            save_result(msg_idx, udsid, sid, data)
            for mutated_data in mutated_data_list:
                dq1.appendleft((udsid, sid, mutated_data, 0))
        else:
            if depth < MAX_DEPTH:
                for mutated_data in mutated_data_list:
                    dq1.append((udsid, sid, mutated_data, depth + 1))

        # process second queue
        udsid, sid, data, depth = dq2.popleft()
        msg = UDSMessage(udsid, sid, data, depth, bus)
        save_log(msg_idx, udsid, sid, data)
        msg_idx += 1

        fail_detection = msg.CheckUDSMessage()
        mutated_data_list = mutator(data)

        if fail_detection:
            print(f"Fail Detected! {msg_idx}: [{hex(udsid)}][{hex(sid)}] [Depth: {depth}] [{data}]")
            save_result(msg_idx, udsid, sid, data)
            for mutated_data in mutated_data_list:
                dq2.appendleft((udsid, sid, mutated_data, 0))
        else:
            if depth < MAX_DEPTH:
                for mutated_data in mutated_data_list:
                    dq2.append((udsid, sid, mutated_data, depth + 1))


    if dq1:
        while dq1:
            udsid, sid, data, depth = dq1.popleft()
            msg = UDSMessage(udsid, sid, data, depth, bus)
            save_log(msg_idx, udsid, sid, data)
            msg_idx += 1

            fail_detection = msg.CheckUDSMessage()
            mutated_data_list = mutator(data)

            if fail_detection:
                print(f"Fail Detected! {msg_idx}: [{hex(udsid)}][{hex(sid)}] [Depth: {depth}] [{data}]")
                save_result(msg_idx, udsid, sid, data)
                for mutated_data in mutated_data_list:
                    dq1.appendleft((udsid, sid, mutated_data, 0))
            else:
                if depth < MAX_DEPTH:
                    for mutated_data in mutated_data_list:
                        dq1.append((udsid, sid, mutated_data, depth + 1))
    
    else :
        while dq2:
            udsid, sid, data, depth = dq2.popleft()
            msg = UDSMessage(udsid, sid, data, depth, bus)
            save_log(msg_idx, udsid, sid, data)
            msg_idx += 1

            fail_detection = msg.CheckUDSMessage()
            mutated_data_list = mutator(data)

            if fail_detection:
                print(f"Fail Detected! {msg_idx}: [{hex(udsid)}][{hex(sid)}] [Depth: {depth}] [{data}]")
                save_result(msg_idx, udsid, sid, data)
                for mutated_data in mutated_data_list:
                    dq2.appendleft((udsid, sid, mutated_data, 0))
            else:
                if depth < MAX_DEPTH:
                    for mutated_data in mutated_data_list:
                        dq2.append((udsid, sid, mutated_data, depth + 1))

    flush_buffer()

if __name__ == "__main__":
    main()
