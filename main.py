import isotp
import csv
import can
import time
from module.uds_isotp import UDSMessage
from module.mutator import mutate_records

# depth level for mutation
MAX_DEPTH = 3

def read_uds_records_from_csv(path: str):

   records = []
    with open(path, newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or len(row) < 3:
                continue
            udsid = int(row[0].strip(), 16)
            sid   = int(row[1].strip(), 16)
            data  = [int(cell.strip(), 16) for cell in row[2:] if cell.strip()]
            depth = 0
            records.append((udsid, sid, data, count))
    return records


def main():
    # Path for seed
    seed_csv_path = "seed.csv"
    # Path for result
    result_csv_path = "result.csv"

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
        mutated_records = mutate_records(udsid, sid, data)

        #  If fail detection is True
        if fail_detection:

            # Save Result 
            result_csv = open("result.csv", "w", newline='')
            writer = csv.writer(result_csv)
            writer.writerow(['udsid', 'sid', 'data'])

            # Give priority to the mutated record
            for m_udsid, m_sid, m_data in mutated_records:
                dq.appendleft((m_udsid, m_sid, m_data, 0))
        

        else: 
            if depth < MAX_DEPTH:
                for m_udsid, m_sid, m_data in mutated_records:
                
                dq.append((m_udsid, m_sid, m_data, m_depth + 1))
            


