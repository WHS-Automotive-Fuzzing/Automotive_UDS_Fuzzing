#!/usr/bin/env python3
"""
CAN Bus DTC (Diagnostic Trouble Code) Analyzer
UDS (Unified Diagnostic Services) 프로토콜을 사용한 진단 데이터 분석
"""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class DTCStatus(Enum):
    """DTC 상태 코드"""
    PENDING = 0x01
    CONFIRMED = 0x02
    STORED = 0x04
    WARNING_LAMP = 0x80

class UDSService(Enum):
    """UDS 서비스 식별자"""
    DIAGNOSTIC_SESSION_CONTROL = 0x10
    ECU_RESET = 0x11
    READ_DTC_INFO = 0x19
    READ_DATA_BY_ID = 0x22
    TESTER_PRESENT = 0x3E
    POSITIVE_RESPONSE = 0x40  # 응답 시 원래 SID + 0x40
    NEGATIVE_RESPONSE = 0x7F

@dataclass
class CANMessage:
    """CAN 메시지 구조"""
    interface: str
    can_id: str
    dlc: int
    data: List[int]
    
    @classmethod
    def from_string(cls, line: str) -> Optional['CANMessage']:
        """CAN 메시지 문자열을 파싱"""
        # can0  778   [8]  10 27 59 02 19 01 08 97 형태의 문자열 파싱
        pattern = r'(\w+)\s+([0-9A-Fa-f]+)\s+\[(\d+)\]\s+(.+)'
        match = re.match(pattern, line.strip())
        
        if not match:
            return None
            
        interface = match.group(1)
        can_id = match.group(2)
        dlc = int(match.group(3))
        data_str = match.group(4)
        
        # 데이터 바이트 파싱
        data_bytes = []
        for byte_str in data_str.split():
            try:
                data_bytes.append(int(byte_str, 16))
            except ValueError:
                continue
                
        return cls(interface, can_id, dlc, data_bytes)

@dataclass
class DTCCode:
    """DTC 코드 정보"""
    code: str
    status: int
    description: str
    severity: str = "Unknown"
    
    def __str__(self):
        return f"DTC: {self.code} | Status: 0x{self.status:02X} | {self.description} | Severity: {self.severity}"

class DTCAnalyzer:
    """DTC 분석기"""
    
    def __init__(self):
        self.messages: List[CANMessage] = []
        self.dtc_codes: List[DTCCode] = []
        self.uds_sessions: Dict[str, List[CANMessage]] = {}
        
        # DTC 코드 매핑 (예시)
        self.dtc_descriptions = {
            "P0000": "No fault detected",
            "P0001": "Fuel Volume Regulator Control Circuit/Open",
            "P0002": "Fuel Volume Regulator Control Circuit Range/Performance",
            "P0003": "Fuel Volume Regulator Control Circuit Low",
            "P0004": "Fuel Volume Regulator Control Circuit High",
            "P0005": "Fuel Shutoff Valve A Control Circuit/Open",
            "P0008": "Engine Position System Performance Bank 1",
            "P0009": "Engine Position System Performance Bank 2",
            "P0010": "A Camshaft Position Actuator Circuit (Bank 1)",
            "P0011": "A Camshaft Position - Timing Over-Advanced or System Performance (Bank 1)",
            "P0012": "A Camshaft Position - Timing Over-Retarded (Bank 1)",
            "P0013": "B Camshaft Position - Actuator Circuit (Bank 1)",
            "P0014": "B Camshaft Position - Timing Over-Advanced or System Performance (Bank 1)",
            "P0015": "B Camshaft Position - Timing Over-Retarded (Bank 1)",
            "P0016": "Crankshaft Position Camshaft Position Correlation Bank 1 Sensor A",
            "P0017": "Crankshaft Position Camshaft Position Correlation Bank 1 Sensor B",
            "P0018": "Crankshaft Position Camshaft Position Correlation Bank 2 Sensor A",
            "P0019": "Crankshaft Position Camshaft Position Correlation Bank 2 Sensor B",
            "P0020": "A Camshaft Position Actuator Circuit (Bank 2)",
            "U0001": "High Speed CAN Communication Bus",
            "U0100": "Lost Communication With ECM/PCM A",
            "U0101": "Lost Communication With TCM",
            "U0102": "Lost Communication With Transfer Case Control Module",
            "U0103": "Lost Communication With Gear Shift Module",
            "U0104": "Lost Communication With Cruise Control Module",
            "U0105": "Lost Communication With Fuel Injector Control Module",
            "U0106": "Lost Communication With Glow Plug Control Module",
            "U0107": "Lost Communication With Throttle Actuator Control Module",
            "U0108": "Lost Communication With Alternative Fuel Control Module",
            "U0109": "Lost Communication With Fuel Pump Control Module",
            "U0110": "Lost Communication With Drive Motor Control Module",
            "U0111": "Lost Communication With Battery Energy Control Module A",
            "U0112": "Lost Communication With Battery Energy Control Module B",
            "U0113": "Lost Communication With Emissions Critical Control Info",
            "B0001": "Driver Airbag Squib Circuit Short to Battery",
            "B0002": "Driver Airbag Squib Circuit Short to Ground",
            "B0003": "Driver Airbag Squib Circuit Open",
            "B0004": "Driver Airbag Squib Circuit Resistance Out of Range",
            "B0005": "Passenger Airbag Squib Circuit Short to Battery",
            "B0006": "Passenger Airbag Squib Circuit Short to Ground",
            "C0001": "ABS Pump Motor Circuit",
            "C0002": "ABS Pump Motor Relay Circuit",
            "C0003": "ABS Pump Motor Relay Circuit Short to Battery",
            "C0004": "ABS Pump Motor Relay Circuit Short to Ground",
            "C0005": "ABS Pump Motor Relay Circuit Open",
        }
    
    def parse_can_data(self, can_data: str) -> None:
        """CAN 데이터 문자열을 파싱하여 메시지 리스트에 추가"""
        lines = can_data.strip().split('\n')
        
        for line in lines:
            if line.strip():
                message = CANMessage.from_string(line)
                if message:
                    self.messages.append(message)
    
    def analyze_uds_messages(self) -> None:
        """UDS 메시지 분석"""
        current_session = []
        
        for msg in self.messages:
            if not msg.data:
                continue
                
            # Multi-frame 메시지 처리
            if msg.data[0] == 0x10:  # First frame
                if current_session:
                    self._process_uds_session(current_session)
                current_session = [msg]
            elif msg.data[0] in [0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x29]:  # Consecutive frames
                current_session.append(msg)
            elif msg.data[0] == 0x30:  # Flow control
                continue
            else:  # Single frame or other
                if current_session:
                    self._process_uds_session(current_session)
                    current_session = []
                self._process_single_frame(msg)
        
        # 마지막 세션 처리
        if current_session:
            self._process_uds_session(current_session)
    
    def _process_uds_session(self, session: List[CANMessage]) -> None:
        """UDS 세션 처리 (Multi-frame)"""
        if not session:
            return
            
        # 첫 번째 프레임에서 총 길이와 서비스 정보 추출
        first_frame = session[0]
        if len(first_frame.data) < 3:
            return
            
        total_length = first_frame.data[1]
        service_id = first_frame.data[2]
        
        # 모든 프레임의 데이터 결합
        combined_data = first_frame.data[3:]  # 첫 번째 프레임의 나머지 데이터
        
        for frame in session[1:]:
            if frame.data and len(frame.data) > 1:
                combined_data.extend(frame.data[1:])  # 연속 프레임의 데이터 (첫 바이트는 시퀀스 번호)
        
        # 실제 데이터 길이만큼만 추출
        if total_length > 0 and len(combined_data) >= total_length - 1:
            actual_data = combined_data[:total_length - 1]
            self._analyze_service_data(service_id, actual_data, first_frame.can_id)
    
    def _process_single_frame(self, msg: CANMessage) -> None:
        """단일 프레임 처리"""
        if len(msg.data) < 2:
            return
            
        length = msg.data[0]
        if length == 0 or length > 7:
            return
            
        service_id = msg.data[1]
        data = msg.data[2:2+length-1] if length > 1 else []
        
        self._analyze_service_data(service_id, data, msg.can_id)
    
    def _analyze_service_data(self, service_id: int, data: List[int], can_id: str) -> None:
        """서비스 데이터 분석"""
        if service_id == 0x59:  # Read DTC Information 응답 (0x19 + 0x40)
            self._parse_dtc_response(data, can_id)
        elif service_id == 0x62:  # Read Data By Identifier 응답 (0x22 + 0x40)
            self._parse_data_by_id_response(data, can_id)
        elif service_id == 0x7F:  # Negative Response
            self._parse_negative_response(data, can_id)
    
    def _parse_dtc_response(self, data: List[int], can_id: str) -> None:
        """DTC 응답 데이터 파싱"""
        if len(data) < 2:
            return
            
        sub_function = data[0]
        
        if sub_function == 0x02:  # reportDTCByStatusMask
            self._parse_dtc_by_status_mask(data[1:], can_id)
        elif sub_function == 0x06:  # reportDTCExtDataRecordByDTCNumber
            self._parse_dtc_extended_data(data[1:], can_id)
    
    def _parse_dtc_by_status_mask(self, data: List[int], can_id: str) -> None:
        """상태 마스크별 DTC 파싱"""
        if len(data) < 1:
            return
            
        status_mask = data[0]
        dtc_data = data[1:]
        
        # DTC는 3바이트씩 구성 (DTC 2바이트 + 상태 1바이트)
        i = 0
        while i + 2 < len(dtc_data):
            dtc_high = dtc_data[i]
            dtc_low = dtc_data[i + 1]
            dtc_status = dtc_data[i + 2]
            
            # DTC 코드 생성
            dtc_code = self._format_dtc_code(dtc_high, dtc_low)
            description = self.dtc_descriptions.get(dtc_code, "Unknown DTC")
            
            # 심각도 결정
            severity = self._determine_severity(dtc_status)
            
            dtc = DTCCode(dtc_code, dtc_status, description, severity)
            self.dtc_codes.append(dtc)
            
            print(f"[CAN ID: {can_id}] {dtc}")
            
            i += 3
    
    def _parse_dtc_extended_data(self, data: List[int], can_id: str) -> None:
        """DTC 확장 데이터 파싱"""
        if len(data) < 3:
            return
            
        dtc_high = data[0]
        dtc_low = data[1]
        dtc_status = data[2]
        
        dtc_code = self._format_dtc_code(dtc_high, dtc_low)
        
        # 확장 데이터가 있는 경우
        if len(data) > 3:
            extended_data = data[3:]
            print(f"[CAN ID: {can_id}] DTC {dtc_code} Extended Data: {[hex(b) for b in extended_data]}")
    
    def _parse_data_by_id_response(self, data: List[int], can_id: str) -> None:
        """데이터 식별자 응답 파싱"""
        if len(data) < 2:
            return
            
        data_id = (data[0] << 8) | data[1]
        value_data = data[2:]
        
        # 일반적인 데이터 식별자들
        data_id_descriptions = {
            0xF190: "VIN (Vehicle Identification Number)",
            0xF18A: "Supplier Identifier",
            0xF18B: "ECU Manufacturing Date",
            0xF18C: "ECU Serial Number",
            0xF19E: "Application Software Identification",
            0xF1A2: "Application Data Identification",
            0xF1A3: "Boot Software Identification",
            0xF1A4: "Application Software Fingerprint",
            0xF1A5: "Active Diagnostic Session",
            0xF197: "System Name Or Engine Type",
            0xF1DF: "Boot Software Fingerprint",
        }
        
        description = data_id_descriptions.get(data_id, f"Unknown Data ID")
        
        if data_id == 0xF190:  # VIN
            vin = ''.join(chr(b) for b in value_data if 32 <= b <= 126)
            print(f"[CAN ID: {can_id}] VIN: {vin}")
        elif data_id in [0xF18A, 0xF18C, 0xF19E, 0xF1A2, 0xF197]:  # 텍스트 데이터
            text = ''.join(chr(b) for b in value_data if 32 <= b <= 126)
            print(f"[CAN ID: {can_id}] {description}: {text}")
        else:
            print(f"[CAN ID: {can_id}] {description}: {[hex(b) for b in value_data]}")
    
    def _parse_negative_response(self, data: List[int], can_id: str) -> None:
        """부정 응답 파싱"""
        if len(data) < 2:
            return
            
        service_id = data[0]
        nrc = data[1]  # Negative Response Code
        
        nrc_descriptions = {
            0x10: "General Reject",
            0x11: "Service Not Supported",
            0x12: "Sub-Function Not Supported",
            0x13: "Incorrect Message Length Or Invalid Format",
            0x14: "Response Too Long",
            0x21: "Busy Repeat Request",
            0x22: "Conditions Not Correct",
            0x24: "Request Sequence Error",
            0x25: "No Response From Subnet Component",
            0x26: "Failure Prevents Execution Of Requested Action",
            0x31: "Request Out Of Range",
            0x33: "Security Access Denied",
            0x35: "Invalid Key",
            0x36: "Exceed Number Of Attempts",
            0x37: "Required Time Delay Not Expired",
            0x70: "Upload Download Not Accepted",
            0x71: "Transfer Data Suspended",
            0x72: "General Programming Failure",
            0x73: "Wrong Block Sequence Counter",
            0x78: "Request Correctly Received-Response Pending",
            0x7E: "Sub-Function Not Supported In Active Session",
            0x7F: "Service Not Supported In Active Session",
        }
        
        nrc_desc = nrc_descriptions.get(nrc, f"Unknown NRC (0x{nrc:02X})")
        print(f"[CAN ID: {can_id}] Negative Response - Service: 0x{service_id:02X}, NRC: {nrc_desc}")
    
    def _format_dtc_code(self, high_byte: int, low_byte: int) -> str:
        """DTC 코드 포맷팅"""
        # DTC 형식: PXXXX, BXXXX, CXXXX, UXXXX
        dtc_number = (high_byte << 8) | low_byte
        
        # 첫 번째 니블로 DTC 타입 결정
        first_nibble = (high_byte >> 6) & 0x03
        
        dtc_type = ['P', 'C', 'B', 'U'][first_nibble]
        
        # 나머지 니블들로 숫자 부분 구성
        second_nibble = (high_byte >> 4) & 0x03
        third_nibble = high_byte & 0x0F
        fourth_nibble = (low_byte >> 4) & 0x0F
        fifth_nibble = low_byte & 0x0F
        
        return f"{dtc_type}{second_nibble}{third_nibble:X}{fourth_nibble:X}{fifth_nibble:X}"
    
    def _determine_severity(self, status: int) -> str:
        """DTC 상태로부터 심각도 결정"""
        if status & 0x80:  # Warning lamp
            return "Critical"
        elif status & 0x04:  # Stored
            return "High"
        elif status & 0x02:  # Confirmed
            return "Medium"
        elif status & 0x01:  # Pending
            return "Low"
        else:
            return "Unknown"
    
    def get_summary(self) -> Dict:
        """분석 결과 요약"""
        return {
            "total_messages": len(self.messages),
            "total_dtc_codes": len(self.dtc_codes),
            "dtc_by_severity": {
                "Critical": len([dtc for dtc in self.dtc_codes if dtc.severity == "Critical"]),
                "High": len([dtc for dtc in self.dtc_codes if dtc.severity == "High"]),
                "Medium": len([dtc for dtc in self.dtc_codes if dtc.severity == "Medium"]),
                "Low": len([dtc for dtc in self.dtc_codes if dtc.severity == "Low"]),
            },
            "unique_can_ids": list(set(msg.can_id for msg in self.messages)),
            "dtc_codes": [dtc.code for dtc in self.dtc_codes]
        }

def main():
    """메인 함수 - 제공된 CAN 데이터 분석"""
    
    # 제공된 CAN 데이터
    can_data = """can0  778   [8]  10 27 59 02 19 01 08 97
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
    
    print("=== CAN Bus DTC Analyzer ===")
    print("제공된 CAN 데이터를 분석합니다...\n")
    
    # DTC 분석기 초기화 및 실행
    analyzer = DTCAnalyzer()
    analyzer.parse_can_data(can_data)
    analyzer.analyze_uds_messages()
    
    # 결과 요약 출력
    summary = analyzer.get_summary()
    
    print("\n=== 분석 결과 요약 ===")
    print(f"총 CAN 메시지 수: {summary['total_messages']}")
    print(f"발견된 DTC 코드 수: {summary['total_dtc_codes']}")
    print(f"사용된 CAN ID: {', '.join(summary['unique_can_ids'])}")
    
    if summary['total_dtc_codes'] > 0:
        print(f"\nDTC 심각도별 분포:")
        for severity, count in summary['dtc_by_severity'].items():
            if count > 0:
                print(f"  {severity}: {count}개")
        
        print(f"\n발견된 DTC 코드: {', '.join(summary['dtc_codes'])}")
    else:
        print("\n이 데이터에서는 명시적인 DTC 코드가 발견되지 않았습니다.")
        print("대부분 ECU 정보 읽기 및 진단 세션 관련 메시지로 보입니다.")

if __name__ == "__main__":
    main()