import isotp
import csv
import can
import time
from collections import deque
from module.uds_isotp import *
from module.mutator import *

result_csv_path = "result.csv"
# depth level for mutation
MAX_DEPTH = 3
buffer = []

def read_uds_records_from_csv(path: str):

    records = []
    with open(path, newline='') as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if not row or len(row) < 3 :
                continue
            udsid = int(row[0].strip(), 16)
            sid   = int(row[1].strip(), 16)
            data  = [int(cell.strip(), 16) for cell in row[2:] if cell.strip()]
            depth = 0
            records.append((udsid, sid, data, depth))
    return records

def save_result(udsid, sid, data):
    global buffer
    buffer.append([udsid, sid] + data)
    if len(buffer) >= 1:
        with open(result_csv_path, "a", newline='') as f:
            writer = csv.writer(f)
            writer.writerows(buffer)
        buffer.clear()

def flush_buffer():
    
    if buffer:
        with open(result_csv_path, "a", newline='') as f:
            writer = csv.writer(f)
            writer.writerows(buffer)
        buffer.clear()



def main():
    # Path for seed
    seed_csv_path = "seed.csv"
    # Path for result
    result_csv_path = "result.csv"

    # Result Header
    with open(result_csv_path, "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['udsid', 'sid', 'data0', 'data1', 'data2', 'data3', 'data4', 'data5', 'data6', 'data7'])

    # Initialize CAN bus
    bus = can.interface.Bus(channel='can0', bustype='socketcan')

    # Read UDS records from CSV
    records = read_uds_records_from_csv(seed_csv_path)

    


    dq = deque(records)
    
    
    while dq:

        udsid, sid, data, depth = dq.popleft()
        
        msg = UDSMessage(udsid, sid, data, depth, bus)

        fail_detection = msg.CheckUDSMessage()
        
        # Mutate records
        #print("before: ", data)
        mutated_data = mutator(data) 
        #print("after: ", mutated_data)
        #  If fail detection is True
        if fail_detection:

            # Save Result 
            save_result(udsid, sid, data)

            # Give priority to the mutated record
   
            dq.appendleft((udsid, sid, mutated_data, 0))
        

        else: 
            # Depth Check
            if depth < MAX_DEPTH:
                dq.append((udsid, sid, mutated_data, depth + 1))
            
    # Flush remaining buffer
    flush_buffer()


if __name__ == "__main__":
    main()