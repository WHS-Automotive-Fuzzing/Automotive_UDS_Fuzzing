#!/usr/bin/env python3
"""
CAN DTC (Diagnostic Trouble Code) Parser
Parses ISO-TP multi-frame messages and extracts DTC information
"""

import re
from typing import List, Dict, Tuple

class CANDTCParser:
    def __init__(self):
        self.messages = []
        self.multi_frame_buffer = {}
        
    def parse_can_line(self, line: str) -> Dict:
        """Parse a single CAN bus line"""
        # Example: can0  778   [8]  10 27 59 02 19 01 08 97
        pattern = r'(\w+)\s+(\w+)\s+\[(\d+)\]\s+((?:[0-9A-F]{2}\s*)+)'
        match = re.match(pattern, line.strip())
        
        if match:
            interface, can_id, dlc, data_str = match.groups()
            data_bytes = [int(b, 16) for b in data_str.split()]
            
            return {
                'interface': interface,
                'can_id': can_id,
                'dlc': int(dlc),
                'data': data_bytes
            }
        return None
    
    def is_iso_tp_first_frame(self, data: List[int]) -> bool:
        """Check if this is an ISO-TP first frame (starts with 0x10-0x1F)"""
        return len(data) > 0 and (data[0] & 0xF0) == 0x10
    
    def is_iso_tp_consecutive_frame(self, data: List[int]) -> bool:
        """Check if this is an ISO-TP consecutive frame (starts with 0x20-0x2F)"""
        return len(data) > 0 and (data[0] & 0xF0) == 0x20
    
    def parse_iso_tp_message(self, frames: List[List[int]]) -> List[int]:
        """Reconstruct full message from ISO-TP frames"""
        if not frames:
            return []
        
        full_message = []
        
        # First frame
        first_frame = frames[0]
        length = ((first_frame[0] & 0x0F) << 8) | first_frame[1]
        full_message.extend(first_frame[2:])
        
        # Consecutive frames
        for frame in frames[1:]:
            if self.is_iso_tp_consecutive_frame(frame):
                full_message.extend(frame[1:])
        
        return full_message[:length]
    
    def parse_dtc_response(self, data: List[int]) -> Dict:
        """Parse DTC response data"""
        if len(data) < 3:
            return None
            
        # Check for service 0x59 (Read DTC Information)
        if data[0] == 0x59:
            sub_function = data[1]
            
            if sub_function == 0x02:  # Report DTC by status mask
                return self.parse_dtc_list(data[2:])
            elif sub_function == 0x06:  # Report DTC extended data
                return self.parse_dtc_extended(data[2:])
                
        return None
    
    def parse_dtc_list(self, data: List[int]) -> Dict:
        """Parse DTC list from service 0x59 subfunction 0x02"""
        dtcs = []
        i = 1  # Skip status mask
        
        while i + 3 < len(data):
            dtc_high = data[i]
            dtc_mid = data[i+1]
            dtc_low = data[i+2]
            status = data[i+3] if i+3 < len(data) else 0
            
            # Convert to standard DTC format
            dtc_code = self.convert_to_dtc_format(dtc_high, dtc_mid, dtc_low)
            
            dtcs.append({
                'code': dtc_code,
                'raw': f"{dtc_high:02X}{dtc_mid:02X}{dtc_low:02X}",
                'status': status
            })
            
            i += 4
            
        return {'type': 'dtc_list', 'dtcs': dtcs}
    
    def parse_dtc_extended(self, data: List[int]) -> Dict:
        """Parse extended DTC data from service 0x59 subfunction 0x06"""
        if len(data) < 4:
            return None
            
        dtc_high = data[0]
        dtc_mid = data[1]
        dtc_low = data[2]
        record_number = data[3] if len(data) > 3 else 0
        
        dtc_code = self.convert_to_dtc_format(dtc_high, dtc_mid, dtc_low)
        
        # Extract extended data
        extended_data = data[4:] if len(data) > 4 else []
        
        return {
            'type': 'dtc_extended',
            'dtc': dtc_code,
            'raw': f"{dtc_high:02X}{dtc_mid:02X}{dtc_low:02X}",
            'record': record_number,
            'data': extended_data
        }
    
    def convert_to_dtc_format(self, high: int, mid: int, low: int) -> str:
        """Convert 3-byte DTC to standard format (e.g., P0123)"""
        # First two bits determine the prefix letter
        prefix_map = {0: 'P', 1: 'C', 2: 'B', 3: 'U'}
        prefix_bits = (high >> 6) & 0x03
        prefix = prefix_map[prefix_bits]
        
        # Next two bits are the first digit
        first_digit = (high >> 4) & 0x03
        
        # Remaining bits form the rest of the code
        second_digit = high & 0x0F
        third_digit = (mid >> 4) & 0x0F
        fourth_digit = mid & 0x0F
        
        return f"{prefix}{first_digit}{second_digit:X}{third_digit:X}{fourth_digit:X}"
    
    def process_can_data(self, lines: List[str]) -> List[Dict]:
        """Process all CAN data lines and extract DTCs"""
        current_frames = []
        results = []
        
        for line in lines:
            parsed = self.parse_can_line(line)
            if not parsed:
                continue
                
            data = parsed['data']
            
            # Check for ISO-TP first frame
            if self.is_iso_tp_first_frame(data):
                # Start new multi-frame message
                current_frames = [data]
            elif self.is_iso_tp_consecutive_frame(data) and current_frames:
                # Add to current multi-frame message
                current_frames.append(data)
                
                # Check if this might be the last frame
                frame_seq = data[0] & 0x0F
                if frame_seq >= 5 or 'AA' in [f"{b:02X}" for b in data]:
                    # Reconstruct full message
                    full_message = self.parse_iso_tp_message(current_frames)
                    
                    # Try to parse as DTC response
                    dtc_info = self.parse_dtc_response(full_message)
                    if dtc_info:
                        results.append(dtc_info)
                    
                    # Reset for next message
                    current_frames = []
            else:
                # Single frame message
                if len(data) >= 3 and data[0] in [0x03, 0x04, 0x05, 0x06, 0x07]:
                    # Single frame format: [length, data...]
                    length = data[0]
                    message_data = data[1:length+1]
                    
                    # Check for diagnostic responses
                    if len(message_data) >= 2:
                        if message_data[0] == 0x7F:  # Negative response
                            results.append({
                                'type': 'negative_response',
                                'service': f"{message_data[1]:02X}",
                                'nrc': f"{message_data[2]:02X}" if len(message_data) > 2 else 'Unknown'
                            })
                        elif message_data[0] in [0x50, 0x6E, 0x62]:  # Positive responses
                            results.append({
                                'type': 'positive_response',
                                'service': f"{message_data[0]:02X}",
                                'data': message_data[1:]
                            })
        
        return results


def main():
    # Read CAN data
    can_data = """  can0  778   [8]  10 27 59 02 19 01 08 97
  can0  778   [8]  21 09 02 01 24 09 EA 61
  can0  778   [8]  22 00 09 01 01 82 09 01
  can0  778   [8]  23 01 87 09 01 01 96 08
  can0  778   [8]  24 01 05 81 08 01 09 01
  can0  778   [8]  25 08 02 03 41 08 AA AA
  can0  778   [8]  10 28 59 06 01 08 97 09
  can0  778   [8]  21 01 06 01 02 00 00 01
  can0  778   [8]  22 21 00 00 66 88 F8 A0
  can0  778   [8]  23 71 10 00 90 3A E4 96
  can0  778   [8]  24 00 67 10 01 00 9A 2B
  can0  778   [8]  25 16 00 00 3A CF 15 AA
  can0  778   [8]  10 28 59 06 02 01 24 09
  can0  778   [8]  21 01 05 01 02 00 00 01
  can0  778   [8]  22 21 00 00 66 88 F8 9E
  can0  778   [8]  23 71 10 00 90 3A E4 96
  can0  778   [8]  24 00 67 10 01 00 9A 2B
  can0  778   [8]  25 16 00 00 3A CF 15 AA
  can0  778   [8]  10 28 59 06 EA 61 00 09
  can0  778   [8]  21 01 04 01 02 00 00 01
  can0  778   [8]  22 21 00 00 66 88 F8 9E
  can0  778   [8]  23 71 10 00 90 3A E4 96
  can0  778   [8]  24 00 67 10 01 00 9A 2B
  can0  778   [8]  25 16 00 00 3A CF 15 AA
  can0  778   [8]  10 28 59 06 01 01 82 09
  can0  778   [8]  21 01 04 01 02 00 00 01
  can0  778   [8]  22 21 00 00 66 88 F8 9E
  can0  778   [8]  23 71 10 00 90 3A E4 96
  can0  778   [8]  24 00 67 10 01 00 9A 2B
  can0  778   [8]  25 16 00 00 3A CF 15 AA
  can0  778   [8]  10 28 59 06 01 01 87 09
  can0  778   [8]  21 01 05 01 02 00 00 01
  can0  778   [8]  22 21 00 00 66 88 F8 A2
  can0  778   [8]  23 71 10 00 90 3A E4 96
  can0  778   [8]  24 00 68 10 01 00 9A 2B
  can0  778   [8]  25 16 00 00 3A CF 15 AA
  can0  778   [8]  10 28 59 06 01 01 96 08
  can0  778   [8]  21 01 05 01 02 28 00 01
  can0  778   [8]  22 21 00 00 66 89 13 9D
  can0  778   [8]  23 71 10 00 81 3A E4 CD
  can0  778   [8]  24 00 20 10 01 00 9D 2B
  can0  778   [8]  25 16 00 00 3A CF 15 AA
  can0  778   [8]  10 28 59 06 01 05 81 08
  can0  778   [8]  21 01 04 01 02 28 00 01
  can0  778   [8]  22 21 00 00 66 89 13 97
  can0  778   [8]  23 71 10 00 82 3A E4 CC
  can0  778   [8]  24 00 21 10 01 00 9D 2B
  can0  778   [8]  25 16 00 00 3A CF 15 AA
  can0  778   [8]  03 7F A8 11 AA AA AA AA
  can0  778   [8]  02 7E 00 AA AA AA AA AA
  can0  778   [8]  06 50 03 00 32 01 F4 AA
  can0  778   [8]  30 0F 05 AA AA AA AA AA
  can0  778   [8]  03 6E F1 98 AA AA AA AA
  can0  778   [8]  03 6E F1 99 AA AA AA AA
  can0  778   [8]  10 15 62 F1 9E 45 56 5F
  can0  778   [8]  21 42 43 4D 31 42 4F 53
  can0  778   [8]  22 43 48 41 55 36 35 31
  can0  778   [8]  23 00 AA AA AA AA AA AA
  can0  778   [8]  10 09 62 F1 A2 30 31 37
  can0  778   [8]  21 30 30 32 AA AA AA AA
  can0  778   [8]  10 0E 62 F1 87 38 57 31
  can0  778   [8]  21 39 30 37 30 36 33 41
  can0  778   [8]  22 47 AA AA AA AA AA AA
  can0  778   [8]  07 62 F1 89 30 37 31 32
  can0  778   [8]  10 0E 62 F1 91 38 57 31
  can0  778   [8]  21 39 30 37 30 36 33 47
  can0  778   [8]  22 20 AA AA AA AA AA AA
  can0  778   [8]  06 62 F1 A3 48 31 30 AA
  can0  778   [8]  10 09 62 F1 A5 00 00 0E
  can0  778   [8]  21 2C 18 BF AA AA AA AA
  can0  778   [8]  10 10 62 F1 97 42 43 4D
  can0  778   [8]  21 31 20 4D 4C 42 65 76
  can0  778   [8]  22 6F 20 20 AA AA AA AA
  can0  778   [8]  10 1A 62 F1 7C 42 58 4A
  can0  778   [8]  21 2D 35 39 36 32 37 2E
  can0  778   [8]  22 30 39 2E 32 30 39 35
  can0  778   [8]  23 31 34 30 31 48 46 AA
  can0  778   [8]  04 62 F1 DF 40 AA AA AA
  can0  778   [8]  10 44 62 06 00 07 00 11
  can0  778   [8]  21 43 E1 39 00 CD 05 0D
  can0  778   [8]  22 57 88 18 AD 88 E9 11
  can0  778   [8]  23 0B 31 08 00 00 00 94
  can0  778   [8]  24 01 01 0A 00 20 00 1C
  can0  778   [8]  25 01 08 44 01 22 02 57
  can0  778   [8]  26 05 00 00 00 00 00 00
  can0  778   [8]  27 00 00 00 00 00 00 00
  can0  778   [8]  28 00 00 00 00 00 00 00
  can0  778   [8]  29 00 00 00 00 00 00 AA
  can0  778   [8]  10 0E 62 F1 A0 38 57 36
  can0  778   [8]  21 39 30 39 35 31 34 43
  can0  778   [8]  22 20 AA AA AA AA AA AA
  can0  778   [8]  07 62 F1 A1 30 30 31 32
  can0  778   [8]  10 0F 62 F1 A4 00 00 00
  can0  778   [8]  21 00 00 00 00 00 00 00
  can0  778   [8]  22 00 00 AA AA AA AA AA
  can0  778   [8]  10 44 62 06 00 07 00 11
  can0  778   [8]  21 43 E1 39 00 CD 05 0D
  can0  778   [8]  22 57 88 18 AD 88 E9 11
  can0  778   [8]  23 0B 31 08 00 00 00 94
  can0  778   [8]  24 01 01 0A 00 20 00 1C
  can0  778   [8]  25 01 08 44 01 22 02 57
  can0  778   [8]  26 05 00 00 00 00 00 00
  can0  778   [8]  27 00 00 00 00 00 00 00
  can0  778   [8]  28 00 00 00 00 00 00 00
  can0  778   [8]  29 00 00 00 00 00 00 AA
  can0  778   [8]  10 27 59 02 19 01 08 97
  can0  778   [8]  21 09 02 01 24 09 EA 61
  can0  778   [8]  22 00 09 01 01 82 09 01
  can0  778   [8]  23 01 87 09 01 01 96 08
  can0  778   [8]  24 01 05 81 08 01 09 01
  can0  778   [8]  25 08 02 03 41 08 AA AA
  can0  778   [8]  10 28 59 06 01 08 97 09
  can0  778   [8]  21 01 06 01 02 00 00 01
  can0  778   [8]  22 21 00 00 66 88 F8 A0
  can0  778   [8]  23 71 10 00 90 3A E4 96
  can0  778   [8]  24 00 67 10 01 00 9A 2B
  can0  778   [8]  25 16 00 00 3A CF 15 AA
  can0  778   [8]  10 28 59 06 02 01 24 09
  can0  778   [8]  21 01 05 01 02 00 00 01
  can0  778   [8]  22 21 00 00 66 88 F8 9E
  can0  778   [8]  23 71 10 00 90 3A E4 96
  can0  778   [8]  24 00 67 10 01 00 9A 2B
  can0  778   [8]  25 16 00 00 3A CF 15 AA
  can0  778   [8]  10 28 59 06 EA 61 00 09
  can0  778   [8]  21 01 04 01 02 00 00 01
  can0  778   [8]  22 21 00 00 66 88 F8 9E
  can0  778   [8]  23 71 10 00 90 3A E4 96
  can0  778   [8]  24 00 67 10 01 00 9A 2B
  can0  778   [8]  25 16 00 00 3A CF 15 AA
  can0  778   [8]  10 28 59 06 01 01 82 09
  can0  778   [8]  21 01 04 01 02 00 00 01
  can0  778   [8]  22 21 00 00 66 88 F8 9E
  can0  778   [8]  23 71 10 00 90 3A E4 96
  can0  778   [8]  24 00 67 10 01 00 9A 2B
  can0  778   [8]  25 16 00 00 3A CF 15 AA
  can0  778   [8]  10 28 59 06 01 01 87 09
  can0  778   [8]  21 01 05 01 02 00 00 01
  can0  778   [8]  22 21 00 00 66 88 F8 A2
  can0  778   [8]  23 71 10 00 90 3A E4 96
  can0  778   [8]  24 00 68 10 01 00 9A 2B
  can0  778   [8]  25 16 00 00 3A CF 15 AA
  can0  778   [8]  10 28 59 06 01 01 96 08
  can0  778   [8]  21 01 05 01 02 28 00 01
  can0  778   [8]  22 21 00 00 66 89 13 9D
  can0  778   [8]  23 71 10 00 81 3A E4 CD
  can0  778   [8]  24 00 20 10 01 00 9D 2B
  can0  778   [8]  25 16 00 00 3A CF 15 AA
  can0  778   [8]  10 28 59 06 01 05 81 08
  can0  778   [8]  21 01 04 01 02 28 00 01
  can0  778   [8]  22 21 00 00 66 89 13 97
  can0  778   [8]  23 71 10 00 82 3A E4 CC
  can0  778   [8]  24 00 21 10 01 00 9D 2B
  can0  778   [8]  25 16 00 00 3A CF 15 AA
  can0  778   [8]  10 2E 59 06 01 09 01 08
  can0  778   [8]  21 01 04 01 02 28 00 01
  can0  778   [8]  22 21 00 00 66 89 16 99
  can0  778   [8]  23 71 10 00 82 3A E4 C6
  can0  778   [8]  24 00 24 10 01 00 9E 2B
  can0  778   [8]  25 16 00 00 3A CF 15 26
  can0  778   [8]  26 50 00 00 00 00 AA AA
  can0  778   [8]  10 2E 59 06 02 03 41 08
  can0  778   [8]  21 01 04 02 02 28 00 01
  can0  778   [8]  22 21 00 00 66 89 12 B0
  can0  778   [8]  23 71 10 00 81 3A E4 D1
  can0  778   [8]  24 00 1E 10 01 00 9D 2B
  can0  778   [8]  25 16 00 00 3A CF 15 26
  can0  778   [8]  26 50 FF FF FF FF AA AA"""
    
    lines = can_data.strip().split('\n')
    
    parser = CANDTCParser()
    results = parser.process_can_data(lines)
    
    print("=== CAN DTC Analysis Results ===\n")
    
    # Extract unique DTCs from the data
    dtc_summary = {}
    
    for i, result in enumerate(results):
        if result['type'] == 'dtc_list':
            print(f"DTC List Response #{i+1}:")
            for dtc in result['dtcs']:
                print(f"  - {dtc['code']} (Raw: {dtc['raw']}, Status: 0x{dtc['status']:02X})")
                if dtc['code'] not in dtc_summary:
                    dtc_summary[dtc['code']] = {'raw': dtc['raw'], 'status': dtc['status']}
                    
        elif result['type'] == 'dtc_extended':
            print(f"\nExtended DTC Data #{i+1}:")
            print(f"  DTC: {result['dtc']} (Raw: {result['raw']})")
            print(f"  Record: 0x{result['record']:02X}")
            print(f"  Data: {' '.join([f'{b:02X}' for b in result['data']])}")
            
        elif result['type'] == 'negative_response':
            print(f"\nNegative Response:")
            print(f"  Service: 0x{result['service']}")
            print(f"  NRC: 0x{result['nrc']}")
            
        elif result['type'] == 'positive_response':
            print(f"\nPositive Response:")
            print(f"  Service: 0x{result['service']}")
            print(f"  Data: {' '.join([f'{b:02X}' for b in result['data']])}")
    
    # Print summary of unique DTCs found
    print("\n=== Unique DTCs Found ===")
    for dtc, info in dtc_summary.items():
        print(f"{dtc} - Raw: {info['raw']}, Last Status: 0x{info['status']:02X}")
        
        # Interpret status byte
        status = info['status']
        status_bits = []
        if status & 0x01: status_bits.append("Test Failed")
        if status & 0x02: status_bits.append("Test Failed This Operation Cycle")
        if status & 0x04: status_bits.append("Pending DTC")
        if status & 0x08: status_bits.append("Confirmed DTC")
        if status & 0x10: status_bits.append("Test Not Completed Since Last Clear")
        if status & 0x20: status_bits.append("Test Failed Since Last Clear")
        if status & 0x40: status_bits.append("Test Not Completed This Operation Cycle")
        if status & 0x80: status_bits.append("Warning Indicator Requested")
        
        if status_bits:
            print(f"  Status: {', '.join(status_bits)}")

    # Analyze the specific DTCs found
    print("\n=== DTC Interpretation ===")
    dtc_meanings = {
        "P0108": "MAP/Barometric Pressure Circuit High Input",
        "P0124": "Throttle Position Sensor Circuit Intermittent",
        "C2A61": "Chassis/Body Control Module Communication",
        "P0101": "Mass Air Flow Circuit Range/Performance",
        "P0187": "Fuel Temperature Sensor B Circuit Low",
        "P0196": "Engine Oil Temperature Sensor Range/Performance",
        "P0581": "Cruise Control Multifunction Input A Circuit High",
        "P0109": "Manifold Absolute Pressure/Barometric Pressure Circuit Intermittent",
        "P0341": "Camshaft Position Sensor Circuit Range/Performance"
    }
    
    for dtc in dtc_summary:
        if dtc in dtc_meanings:
            print(f"{dtc}: {dtc_meanings[dtc]}")
        else:
            print(f"{dtc}: (Description not available in database)")


if __name__ == "__main__":
    main()