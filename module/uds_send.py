# uds_sender.py
import isotp
import time

WAIT_RESPONSE_TIME = 5  # seconds
RESET_WAIT_RESPONSE_TIME = 2
WAIT_SLEEP = 0.01 # Sleep for TesterPresent & DiagnosticSession

class UDSSender:
    def __init__(self, stack):
        self.stack = stack
    
    def wait_response(self, expected_data, timeout=WAIT_RESPONSE_TIME):
        """
        Wait for expected response from ECU
        
        Args:
            expected_data: List of expected bytes
            timeout: Timeout in seconds
        
        Returns:
            tuple: (success: bool, response: bytes or None)
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            self.stack.process()
            if self.stack.available():
                response = self.stack.recv(timeout=5)
                if response[:len(expected_data)] == bytes(expected_data):
                    return True, response
                else:
                    return False, response
        return False, None
    
    def SendTesterPresent(self, retry_count=3):
        """
        Send Tester Present (0x3E 0x00) to keep diagnostic session alive
        
        Args:
            retry_count: Number of retry attempts
        
        Returns:
            tuple: (success: bool, response: bytes or None)
        """
        retry = 0
        while retry < retry_count:
            self.stack.send(bytes([0x3E, 0x00]))
            success, response = self.wait_response([0x7E, 0x00])
            if success:
                return True, response
            time.sleep(WAIT_SLEEP)
            retry += 1
        
        return False, None
    
    def EnterDiagnosticSession(self, session_type=0x03, retry_count=3):
        """
        Enter diagnostic session mode
        
        Args:
            session_type: 0x01 (Default), 0x02 (Programming), 0x03 (Extended)
            retry_count: Number of retry attempts
        
        Returns:
            tuple: (success: bool, response: bytes or None)
        """
        expected_response = [0x50, session_type]
        success = False
        response = None
        retry = 0
        
        while retry < retry_count:
            self.stack.send(bytes([0x10, session_type]))
            
            # Wait for response with longer timeout for reset
            start_time = time.time()

            while True:
                self.stack.process()
                if time.time() - start_time >= WAIT_RESPONSE_TIME:
                    break
    
                if self.stack.available():
                    response = self.stack.recv(timeout=5)
                    if (len(response) >= 3) and (response[0] == 0x7f) and ((response[2] == 0x78) or (response[2] == 0x21)):
                        start_time = time.time()
                        # time.sleep(WAIT_SLEEP) # Reset 안되면 여기도 한면 sleep 추가해보기
                        continue
                        
                    elif response[:len(expected_response)] == bytes(expected_response):
                        success = True
                        return success, response
                    else:
                        print(f"[DEBUG] Diagnostic session entered: {response.hex() if response else 'None'}")
                        break
                # time.sleep(WAIT_SLEEP) # Reset 안되면 여기도 한면 sleep 추가해보기
            retry += 1
        
        return success, response
    
    def SendECUReset(self, reset_type=0x01, retry_count=3, timeout=RESET_WAIT_RESPONSE_TIME):
        """
        Send ECU Reset command
        
        Args:
            reset_type: 0x01 (Soft Reset), 0x02 (Hard Reset), 0x03 (Key Off On Reset)
            retry_count: Number of retry attempts
            timeout: Timeout for reset response
        
        Returns:
            tuple: (success: bool, response: bytes or None)
        """
        expected_response = [0x51, reset_type]
        retry = 0
        success = False
        response = None
        while retry < retry_count:
            self.stack.send(bytes([0x11, reset_type]))
            
            # Wait for response with longer timeout for reset
            start_time = time.time()

            while True:
                self.stack.process()
                if time.time() - start_time >= timeout:
                    break
    
                if self.stack.available():
                    response = self.stack.recv(timeout=5)
                    if (len(response) >= 3) and (response[0] == 0x7f) and ((response[2] == 0x78) or (response[2] == 0x21)):
                        start_time = time.time()
                        # time.sleep(WAIT_SLEEP) # Reset 안되면 여기도 한면 sleep 추가해보기
                        continue
                    elif response[:len(expected_response)] == bytes(expected_response):
                        success = True
                        return success, response
                    else:
                        break
                # time.sleep(WAIT_SLEEP) # Reset 안되면 여기도 한면 sleep 추가해보기
            retry += 1
        
        return success, response
    
    def SendUDSMessage(self, sid, data, timeout=WAIT_RESPONSE_TIME):
        """
        Send generic UDS message
        
        Args:
            sid: Service ID
            data: List of data bytes
            timeout: Timeout for response
        
        Returns:
            tuple: (success: bool, response: bytes or None)
        """
        response= None
        success = False
        send_data = [sid] + data
        self.stack.send(bytes(send_data))
        
        start_time = time.time()
        while True:
            if time.time() - start_time >= timeout:
                print(time.time() - start_time)
                break
            
            self.stack.process()
            if self.stack.available():
                response = self.stack.recv(timeout=5)
                if (len(response) >= 3) and (response[0] == 0x7f) and ((response[2] == 0x78) or (response[2] == 0x21)):
                    start_time = time.time()
                    continue
                
                if len(response) > 0:
                    success = True
                    break
        
        return success, response
    
    def SendDTCRequest(self, timeout=WAIT_RESPONSE_TIME, enter_diagnostic=True, session_type=0x03, retry_count=3, status_mask=0x20, trial = 1):
        """
        Send DTC Read request (0x19 0x02 [status_mask])
        
        Args:
            timeout: Timeout for response
            enter_diagnostic: Whether to enter diagnostic session before sending
            session_type: Diagnostic session type (default: 0x03 Extended)
            retry_count: Number of retry attempts for diagnostic session
            status_mask: DTC status mask (default: 0x30 = TestNotCompletedSinceLastClear | TestFailedSinceLastClear)
        
        Returns:
            tuple: (success: bool, response: bytes or None)
        """
        # 진단 세션 진입
        if enter_diagnostic:
            print(f"[DEBUG] Entering diagnostic session (type: 0x{session_type:02X})...")
            if trial==2:
                success, diag_resp = self.SendTesterPresent()
                if not success:
                    print(f"[DEBUG] Failed to TestPresent: {diag_resp.hex() if diag_resp else 'None'}")
                success, diag_resp = self.EnterDiagnosticSession(0x01, retry_count)
                if not success:
                    print("[ERROR] Failed to enter diagnostic session 0x10 01 for DTC request")

            success, diag_resp = self.EnterDiagnosticSession(session_type, retry_count)
            if not success:
                print("[ERROR] Failed to enter diagnostic session for DTC request")
                print(f"[DEBUG] Response was:{diag_resp.hex() if diag_resp else 'None'}")
                return False, None
            print(f"[DEBUG] Diagnostic session entered: {diag_resp.hex() if diag_resp else 'None'}")
        
        response = None
        success = False
        
        print(f"[DEBUG] Sending DTC request (0x19 0x02 0x{status_mask:02X})...")
        self.stack.send(bytes([0x19, 0x02, status_mask]))
        
        start_time = time.time()
        while True:
            self.stack.process()
            if time.time() - start_time >= timeout:
                print(f"[DEBUG] DTC request timeout after {timeout}s")
                break

            if self.stack.available():
                response = self.stack.recv(timeout=5)
                print(f"[DEBUG] DTC response received: {response.hex()}")
                
                if (len(response) >= 3) and (response[0] == 0x7f):
                    nrc = response[2]
                    print(f"[DEBUG] Received NRC: 0x{nrc:02X}")
                    
                    if nrc == 0x78 or nrc == 0x21:  # RequestCorrectlyReceived-ResponsePending
                        print("[DEBUG] Response pending (0x78), waiting...")
                        start_time = time.time()
                        continue
                    elif nrc == 0x14:  # ResponseTooLong
                        print("[DEBUG] Response too long (0x14) - treating as success")
                        success = True
                        break
                    else:  # Other NRC
                        nrc_meanings = {
                            0x11: "Service Not Supported",
                            0x12: "Sub-Function Not Supported",
                            0x13: "Incorrect Message Length Or Invalid Format",
                            0x22: "Conditions Not Correct",
                            0x31: "Request Out of Range",
                            0x33: "Security Access Denied",
                            0x7F: "Service Not Supported in Active Session"
                        }
                        print(f"[ERROR] NRC 0x{nrc:02X}: {nrc_meanings.get(nrc, 'Unknown')}")
                        break

                if (len(response) >= 3) and (response[0] == 0x59):
                    print("[DEBUG] Positive response (0x59) received")
                    success = True
                    break
        
        return success, response

    def SendDTCClear(self, timeout=WAIT_RESPONSE_TIME, enter_diagnostic=True, session_type=0x03, retry_count=3):
        """
        Send DTC Clear command (0x14 0xFF 0xFF 0xFF)
        
        Args:
            timeout: Timeout for response
            enter_diagnostic: Whether to enter diagnostic session before sending
            session_type: Diagnostic session type (default: 0x03 Extended)
            retry_count: Number of retry attempts for diagnostic session
        
        Returns:
            tuple: (success: bool, response: bytes or None)
        """
        # 진단 세션 진입
        if enter_diagnostic:
            print(f"[DEBUG] Entering diagnostic session (type: 0x{session_type:02X})...")
            success, diag_resp = self.EnterDiagnosticSession(session_type, retry_count)
            if not success:
                print("[ERROR] Failed to enter diagnostic session for DTC clear")
                return False, None
            print(f"[DEBUG] Diagnostic session entered: {diag_resp.hex() if diag_resp else 'None'}")
        
        response = None
        success = False
        
        print("[DEBUG] Sending DTC clear (0x14 0xFF 0xFF 0xFF)...")
        self.stack.send(bytes([0x14, 0xFF, 0xFF, 0xFF]))
        
        start_time = time.time()
        while True:
            self.stack.process()
            if time.time() - start_time >= timeout:
                print(f"[DEBUG] DTC clear timeout after {timeout}s")
                break
  
            if self.stack.available():
                response = self.stack.recv(timeout=5)
                print(f"[DEBUG] DTC clear response received: {response.hex()}")
                
                if (len(response) >= 3) and ((response[2] == 0x78) or (response[2] == 0x21)):
                    nrc = response[2]
                    print(f"[DEBUG] Received NRC: 0x{nrc:02X}")
                    
                    if nrc == 0x78:  # RequestCorrectlyReceived-ResponsePending
                        print("[DEBUG] Response pending (0x78), waiting...")
                        start_time = time.time()
                        continue
                    else:
                        nrc_meanings = {
                            0x11: "Service Not Supported",
                            0x12: "Sub-Function Not Supported",
                            0x13: "Incorrect Message Length Or Invalid Format",
                            0x22: "Conditions Not Correct",
                            0x31: "Request Out of Range",
                            0x33: "Security Access Denied",
                            0x7F: "Service Not Supported in Active Session"
                        }
                        print(f"[ERROR] NRC 0x{nrc:02X}: {nrc_meanings.get(nrc, 'Unknown')}")
                        success = False
                        break

                if (len(response) >= 1) and (response[0] == 0x54):
                    print("[DEBUG] Positive response (0x54) received")
                    success = True
                    time.sleep(0.1)
                    break
        
        return success, response

    def SendAndWaitResponse(self, message, expected_response=None, timeout=WAIT_RESPONSE_TIME):
        """
        Send custom message and optionally wait for expected response
        
        Args:
            message: List of bytes to send
            expected_response: List of expected bytes (None to accept any response)
            timeout: Timeout for response
        
        Returns:
            tuple: (success: bool, response: bytes or None)
        """
        response = None
        success = False
        self.stack.send(bytes(message))
        
        start_time = time.time()
        while True:
            self.stack.process()
            if time.time() - start_time >= timeout:
                break
  
            if self.stack.available():
                response = self.stack.recv(timeout=5)
                if (len(response) >= 3) and (response[0] == 0x7f) and ((response[2] == 0x78) or (response[2] == 0x21)):
                    start_time = time.time()
                    continue

                if expected_response is None:
                    return True, response
                elif response[:len(expected_response)] == bytes(expected_response):
                    return True, response
                else:
                    return False, response
        return False, None
    
    
    def StartDiagnosticAndSendMessage(self, message, session_type=0x03, retry_count=3, timeout=WAIT_RESPONSE_TIME):
        """
        Start diagnostic session and send a message
        
        Args:
            message: Message to send after entering diagnostic session
            session_type: Diagnostic session type
            retry_count: Number of retry attempts
            timeout: Timeout for message response
        
        Returns:
            tuple: (success: bool, msg_response: bytes or None, diag_response: bytes or None)
        """
        success, _ = self.SendTesterPresent(retry_count)
        if not success:
            print("[ERROR] Failed to send Tester Present")
            return False, None, None
        
        success, diag_response = self.EnterDiagnosticSession(session_type, retry_count)
        if not success:
            print("[ERROR] Failed to enter diagnostic session")
            return False, None, None

        success, msg_response = self.SendAndWaitResponse(message, timeout=timeout)
        if not success:
            print(f"[ERROR] Failed to send message: {bytes(message).hex()}")
            return False, None, diag_response
        if msg_response is not None:
            print(f"[SUCCESS] Message sent and response received: {msg_response.hex()}")
        
        return True, msg_response, diag_response
