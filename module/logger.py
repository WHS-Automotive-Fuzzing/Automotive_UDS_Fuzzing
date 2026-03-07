import csv 
import sys

result_csv_path = "result.csv"
send_log_path = "send_log.csv"

buffer = []
send_buffer = []

def open_csv():
    with open(result_csv_path, "w", newline='') as f: # result csv
        writer = csv.writer(f)
        writer.writerow(['idx', 'fail_level','udsid', 'sid', 'data', 'response'])
    
    with open(send_log_path, "w", newline='') as f: # send log csv
        writer = csv.writer(f)
        writer.writerow(['idx','udsid', 'sid', 'data', 'response'])

def save_result(msg_idx, msg):
    global buffer
    data_str = ' '.join(f"{byte:02X}" for byte in msg.data)
    if msg.response is not None:
        response_str = ' '.join(f"{byte:02X}" for byte in msg.response)
    else:
        response_str = ""
    hex_row = [f"{msg_idx}",f"{msg.fail_level}",f"{msg.udsid:03X}", f"{msg.sid:02X}", data_str, response_str]
    buffer.append(hex_row)
    if len(buffer) >= 10:
        with open(result_csv_path, "a", newline='') as f:
            writer = csv.writer(f)
            writer.writerows(buffer)
        buffer.clear()

def save_log(msg_idx, msg):
    global send_buffer
    data_str = ' '.join(f"{byte:02X}" for byte in msg.data)
    if msg.response is not None:
        response_str = ' '.join(f"{byte:02X}" for byte in msg.response)
    else:
        response_str = ""
    hex_row = [f"{msg_idx}",f"{msg.udsid:03X}", f"{msg.sid:02X}", data_str, response_str]
    send_buffer.append(hex_row)
    if len(send_buffer) >= 10:
        with open(send_log_path, "a", newline='') as f:
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
