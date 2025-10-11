#!/usr/bin/env python3
"""
DTC (Diagnostic Trouble Code) Parser for CAN Bus Data
Parses ISO-TP frames and extracts DTC information from UDS responses
"""

from typing import List, Tuple, Dict
import sys

class ISOTPParser:
    """Parse ISO-TP multi-frame messages from CAN data"""
    
    def __init__(self):
        self.frames = {}  # Store frames by CAN ID
        
    def parse_frame(self, can_id: int, data: List[int]) -> Tuple[str, bytes]:
        """
        Parse a single CAN frame and return frame type and data
        Returns: (frame_type, payload_data)
        """
        if len(data) == 0:
            return ("empty", b"")
        
        pci = data[0]
        
        # Single Frame (SF): 0x0X
        if (pci & 0xF0) == 0x00:
            length = pci & 0x0F
            payload = bytes(data[1:1+length])
            return ("single", payload)
        
        # First Frame (FF): 0x1X
        elif (pci & 0xF0) == 0x10:
            length = ((pci & 0x0F) << 8) | data[1]
            payload = bytes(data[2:])
            self.frames[can_id] = {
                'length': length,
                'received': len(payload),
                'data': payload
            }
            return ("first", None)
        
        # Consecutive Frame (CF): 0x2X
        elif (pci & 0xF0) == 0x20:
            seq_num = pci & 0x0F
            payload = bytes(data[1:])
            
            if can_id in self.frames:
                self.frames[can_id]['data'] += payload
                self.frames[can_id]['received'] += len(payload)
                
                # Check if complete
                if self.frames[can_id]['received'] >= self.frames[can_id]['length']:
                    complete_data = self.frames[can_id]['data'][:self.frames[can_id]['length']]
                    del self.frames[can_id]
                    return ("complete", complete_data)
            
            return ("consecutive", None)
        
        # Flow Control (FC): 0x3X
        elif (pci & 0xF0) == 0x30:
            return ("flow_control", bytes(data[1:]))
        
        return ("unknown", b"")


class DTCParser:
    """Parse and interpret DTC codes from UDS responses"""
    
    # DTC Status Bit Definitions (ISO 14229-1)
    STATUS_BITS = {
        0: "testFailed",
        1: "testFailedThisOperationCycle",
        2: "pendingDTC",
        3: "confirmedDTC",
        4: "testNotCompletedSinceLastClear",
        5: "testFailedSinceLastClear",
        6: "testNotCompletedThisOperationCycle",
        7: "warningIndicatorRequested"
    }
    
    # UDS Service IDs
    UDS_SERVICES = {
        0x19: "ReadDTCInformation",
        0x59: "ReadDTCInformation (Positive Response)",
        0x22: "ReadDataByIdentifier",
        0x62: "ReadDataByIdentifier (Positive Response)",
        0x10: "DiagnosticSessionControl",
        0x50: "DiagnosticSessionControl (Positive Response)",
        0x3E: "TesterPresent",
        0x7E: "TesterPresent (Positive Response)",
        0x11: "ECUReset",
        0x51: "ECUReset (Positive Response)",
        0x7F: "NegativeResponse"
    }
    
    # Service 0x19 subfunctions
    SERVICE_19_SUBFUNCTIONS = {
        0x01: "reportNumberOfDTCByStatusMask",
        0x02: "reportDTCByStatusMask",
        0x03: "reportDTCSnapshotIdentification",
        0x04: "reportDTCSnapshotRecordByDTCNumber",
        0x05: "reportDTCSnapshotRecordByRecordNumber",
        0x06: "reportDTCExtDataRecordByDTCNumber",
        0x07: "reportNumberOfDTCBySeverityMaskRecord",
        0x08: "reportDTCBySeverityMaskRecord",
        0x09: "reportSeverityInformationOfDTC",
        0x0A: "reportSupportedDTC"
    }
    
    @staticmethod
    def parse_dtc_code(dtc_bytes: bytes) -> str:
        """
        Parse 3-byte DTC code into standard format
        Format: X####
        Where X = [P,C,B,U] and #### = 4 hex digits
        """
        if len(dtc_bytes) < 3:
            return "INVALID"
        
        byte1, byte2, byte3 = dtc_bytes[0], dtc_bytes[1], dtc_bytes[2]
        
        # High 2 bits of byte1 determine prefix
        prefix_map = {0: 'P', 1: 'C', 2: 'B', 3: 'U'}
        prefix = prefix_map[(byte1 >> 6) & 0x03]
        
        # Remaining bits form the DTC number
        dtc_num = ((byte1 & 0x3F) << 8) | byte2
        
        return f"{prefix}{dtc_num:04X}"
    
    @staticmethod
    def parse_status_byte(status: int) -> List[str]:
        """Parse DTC status byte and return list of active flags"""
        active_flags = []
        for bit, flag_name in DTCParser.STATUS_BITS.items():
            if status & (1 << bit):
                active_flags.append(flag_name)
        return active_flags
    
    @staticmethod
    def parse_service_59_response(data: bytes) -> Dict:
        """
        Parse Service 0x59 (ReadDTCInformation) response
        """
        if len(data) < 2:
            return {"error": "Response too short"}
        
        service = data[0]
        subfunction = data[1]
        
        result = {
            "service": f"0x{service:02X}",
            "service_name": DTCParser.UDS_SERVICES.get(service, "Unknown"),
            "subfunction": f"0x{subfunction:02X}",
            "subfunction_name": DTCParser.SERVICE_19_SUBFUNCTIONS.get(subfunction, "Unknown"),
            "dtcs": []
        }
        
        # Service 0x59 with subfunction 0x02 (reportDTCByStatusMask)
        if subfunction == 0x02:
            if len(data) < 3:
                return result
            
            availability_mask = data[2]
            result["availability_mask"] = f"0x{availability_mask:02X}"
            
            # Parse DTCs (each DTC is 4 bytes: 3 bytes code + 1 byte status)
            idx = 3
            while idx + 3 <= len(data):
                dtc_code = DTCParser.parse_dtc_code(data[idx:idx+3])
                dtc_status = data[idx+3]
                status_flags = DTCParser.parse_status_byte(dtc_status)
                
                result["dtcs"].append({
                    "code": dtc_code,
                    "status": f"0x{dtc_status:02X}",
                    "status_flags": status_flags
                })
                idx += 4
        
        # Service 0x59 with subfunction 0x06 (reportDTCExtDataRecordByDTCNumber)
        elif subfunction == 0x06:
            if len(data) < 6:
                return result
            
            dtc_code = DTCParser.parse_dtc_code(data[2:5])
            dtc_status = data[5]
            status_flags = DTCParser.parse_status_byte(dtc_status)
            
            result["dtc"] = {
                "code": dtc_code,
                "status": f"0x{dtc_status:02X}",
                "status_flags": status_flags
            }
            
            # Extended data follows
            if len(data) > 6:
                result["extended_data"] = data[6:].hex().upper()
        
        return result
    
    @staticmethod
    def parse_service_62_response(data: bytes) -> Dict:
        """
        Parse Service 0x62 (ReadDataByIdentifier) response
        """
        if len(data) < 3:
            return {"error": "Response too short"}
        
        service = data[0]
        did = (data[1] << 8) | data[2]
        
        result = {
            "service": f"0x{service:02X}",
            "service_name": DTCParser.UDS_SERVICES.get(service, "Unknown"),
            "did": f"0x{did:04X}",
            "data": data[3:].hex().upper()
        }
        
        # Interpret common DIDs
        if did == 0xF187:
            result["did_name"] = "VehicleManufacturerSparePartNumber"
            result["value"] = data[3:].decode('ascii', errors='ignore').strip('\x00')
        elif did == 0xF189:
            result["did_name"] = "VehicleManufacturerECUSoftwareNumber"
            result["value"] = data[3:].decode('ascii', errors='ignore').strip('\x00')
        elif did == 0xF18A:
            result["did_name"] = "SystemSupplierSpecific"
        elif did == 0xF18C:
            result["did_name"] = "ECUSerialNumber"
            result["value"] = data[3:].decode('ascii', errors='ignore').strip('\x00')
        elif did == 0xF190:
            result["did_name"] = "VIN (VehicleIdentificationNumber)"
            result["value"] = data[3:].decode('ascii', errors='ignore').strip('\x00')
        elif did == 0xF191:
            result["did_name"] = "ECUHardwareNumber"
            result["value"] = data[3:].decode('ascii', errors='ignore').strip('\x00')
        elif did == 0xF197:
            result["did_name"] = "SystemNameOrEngineType"
            result["value"] = data[3:].decode('ascii', errors='ignore').strip('\x00')
        elif did == 0xF19E:
            result["did_name"] = "ECUSoftwareNumber"
            result["value"] = data[3:].decode('ascii', errors='ignore').strip('\x00')
        elif did == 0xF1A0:
            result["did_name"] = "VehicleManufacturerECUSoftwareNumber"
            result["value"] = data[3:].decode('ascii', errors='ignore').strip('\x00')
        elif did == 0xF1A2:
            result["did_name"] = "SystemSupplierECUSoftwareNumber"
            result["value"] = data[3:].decode('ascii', errors='ignore').strip('\x00')
        elif did == 0xF1A3:
            result["did_name"] = "ECUManufacturingDateAndTime"
        elif did == 0xF1A4:
            result["did_name"] = "ODXFileDataIdentifier"
        elif did == 0xF1A5:
            result["did_name"] = "ECUCoreAssembly"
        elif did == 0xF1DF:
            result["did_name"] = "TargetVehicle"
        
        return result
    
    @staticmethod
    def parse_negative_response(data: bytes) -> Dict:
        """Parse negative response (Service 0x7F)"""
        if len(data) < 3:
            return {"error": "Response too short"}
        
        service = data[0]
        requested_service = data[1]
        nrc = data[2]  # Negative Response Code
        
        nrc_map = {
            0x10: "generalReject",
            0x11: "serviceNotSupported",
            0x12: "subFunctionNotSupported",
            0x13: "incorrectMessageLengthOrInvalidFormat",
            0x14: "responseTooLong",
            0x21: "busyRepeatRequest",
            0x22: "conditionsNotCorrect",
            0x24: "requestSequenceError",
            0x25: "noResponseFromSubnetComponent",
            0x26: "failurePreventsExecutionOfRequestedAction",
            0x31: "requestOutOfRange",
            0x33: "securityAccessDenied",
            0x35: "invalidKey",
            0x36: "exceedNumberOfAttempts",
            0x37: "requiredTimeDelayNotExpired",
            0x70: "uploadDownloadNotAccepted",
            0x71: "transferDataSuspended",
            0x72: "generalProgrammingFailure",
            0x73: "wrongBlockSequenceCounter",
            0x78: "requestCorrectlyReceived-ResponsePending",
            0x7E: "subFunctionNotSupportedInActiveSession",
            0x7F: "serviceNotSupportedInActiveSession"
        }
        
        return {
            "service": f"0x{service:02X}",
            "service_name": "NegativeResponse",
            "requested_service": f"0x{requested_service:02X}",
            "nrc": f"0x{nrc:02X}",
            "nrc_description": nrc_map.get(nrc, "Unknown")
        }


def parse_can_line(line: str) -> Tuple[str, int, List[int]]:
    """
    Parse a single line of CAN data
    Format: can0  778   [8]  10 27 59 02 19 01 08 97
    Returns: (interface, can_id, data_bytes)
    """
    parts = line.strip().split()
    if len(parts) < 4:
        return None, None, None
    
    interface = parts[0]
    can_id = int(parts[1], 16)
    
    # Find data bytes (after [X])
    data_start = 3
    data_bytes = []
    for i in range(data_start, len(parts)):
        try:
            data_bytes.append(int(parts[i], 16))
        except ValueError:
            continue
    
    return interface, can_id, data_bytes


def main():
    """Main function to parse CAN data and extract DTC information"""
    
    # Read input - either from file or stdin
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            lines = f.readlines()
    else:
        print("Reading from stdin... (paste CAN data and press Ctrl+D)")
        lines = sys.stdin.readlines()
    
    isotp_parser = ISOTPParser()
    dtc_parser = DTCParser()
    
    print("="*80)
    print("CAN Bus DTC Parser - UDS Diagnostic Data Analysis")
    print("="*80)
    print()
    
    message_count = 0
    
    for line_num, line in enumerate(lines, 1):
        if not line.strip():
            continue
        
        interface, can_id, data_bytes = parse_can_line(line)
        if can_id is None:
            continue
        
        # Parse ISO-TP frame
        frame_type, payload = isotp_parser.parse_frame(can_id, data_bytes)
        
        # Process complete messages
        if frame_type == "single" or frame_type == "complete":
            message_count += 1
            
            if len(payload) == 0:
                continue
            
            service_id = payload[0]
            
            print(f"[Message #{message_count}] CAN ID: 0x{can_id:03X} | Length: {len(payload)} bytes")
            print(f"Raw Data: {payload.hex().upper()}")
            
            # Parse based on service ID
            if service_id == 0x59:  # ReadDTCInformation response
                result = dtc_parser.parse_service_59_response(payload)
                print(f"Service: {result['service_name']} ({result['service']})")
                print(f"Subfunction: {result['subfunction_name']} ({result['subfunction']})")
                
                if "availability_mask" in result:
                    print(f"Availability Mask: {result['availability_mask']}")
                
                if "dtcs" in result and result["dtcs"]:
                    print(f"\nFound {len(result['dtcs'])} DTC(s):")
                    for i, dtc in enumerate(result['dtcs'], 1):
                        print(f"  DTC #{i}: {dtc['code']}")
                        print(f"    Status: {dtc['status']}")
                        print(f"    Flags: {', '.join(dtc['status_flags'])}")
                
                if "dtc" in result:
                    dtc = result["dtc"]
                    print(f"\nDTC: {dtc['code']}")
                    print(f"  Status: {dtc['status']}")
                    print(f"  Flags: {', '.join(dtc['status_flags'])}")
                    
                    if "extended_data" in result:
                        print(f"  Extended Data: {result['extended_data']}")
            
            elif service_id == 0x62:  # ReadDataByIdentifier response
                result = dtc_parser.parse_service_62_response(payload)
                print(f"Service: {result['service_name']} ({result['service']})")
                print(f"DID: {result['did']}")
                if "did_name" in result:
                    print(f"DID Name: {result['did_name']}")
                if "value" in result:
                    print(f"Value: {result['value']}")
                else:
                    print(f"Data: {result['data']}")
            
            elif service_id == 0x7F:  # Negative Response
                result = dtc_parser.parse_negative_response(payload)
                print(f"Service: {result['service_name']}")
                print(f"Requested Service: {result['requested_service']}")
                print(f"NRC: {result['nrc']} - {result['nrc_description']}")
            
            elif service_id in DTCParser.UDS_SERVICES:
                service_name = DTCParser.UDS_SERVICES[service_id]
                print(f"Service: {service_name} (0x{service_id:02X})")
                if len(payload) > 1:
                    print(f"Data: {payload[1:].hex().upper()}")
            
            else:
                print(f"Unknown Service: 0x{service_id:02X}")
            
            print("-" * 80)
            print()
    
    print("="*80)
    print(f"Analysis Complete - Processed {message_count} messages")
    print("="*80)


if __name__ == "__main__":
    main()
