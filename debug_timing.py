import time
import csv
from collections import deque
from module.uds_isotp import *
from module.mutator import *
import can

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

def debug_timing():
    """타이밍 측정을 위한 디버그 함수"""
    dq1 = deque(read_uds_records_from_csv("seed1.csv"))
    dq2 = deque(read_uds_records_from_csv("seed2.csv"))
    bus = can.interface.Bus(channel='can0', bustype='socketcan')
    
    cycle_count = 0
    
    while dq1 and dq2 and cycle_count < 10:  # 10사이클만 측정
        cycle_count += 1
        print(f"\n=== Cycle {cycle_count} ===")
        
        # DQ1 처리 타이밍
        start_time = time.time()
        udsid, sid, data, depth = dq1.popleft()
        print(f"DQ1 popleft: {time.time() - start_time:.4f}s")
        
        start_time = time.time()
        msg = UDSMessage(udsid, sid, data, depth, bus)
        print(f"DQ1 UDSMessage creation: {time.time() - start_time:.4f}s")
        
        start_time = time.time()
        fail_detection = msg.CheckUDSMessage()
        check_time = time.time() - start_time
        print(f"DQ1 CheckUDSMessage (UDS:{hex(udsid)}): {check_time:.4f}s")
        
        start_time = time.time()
        mutated_data_list = mutator(data)
        print(f"DQ1 mutator: {time.time() - start_time:.4f}s")
        
        # DQ2 처리 타이밍
        start_time = time.time()
        udsid, sid, data, depth = dq2.popleft()
        print(f"DQ2 popleft: {time.time() - start_time:.4f}s")
        
        start_time = time.time()
        msg = UDSMessage(udsid, sid, data, depth, bus)
        print(f"DQ2 UDSMessage creation: {time.time() - start_time:.4f}s")
        
        start_time = time.time()
        fail_detection = msg.CheckUDSMessage()
        check_time = time.time() - start_time
        print(f"DQ2 CheckUDSMessage (UDS:{hex(udsid)}): {check_time:.4f}s")
        
        start_time = time.time()
        mutated_data_list = mutator(data)
        print(f"DQ2 mutator: {time.time() - start_time:.4f}s")
        
        # 다음 사이클까지의 간격 측정
        print(f"--- End of cycle {cycle_count} ---")

if __name__ == "__main__":
    debug_timing()