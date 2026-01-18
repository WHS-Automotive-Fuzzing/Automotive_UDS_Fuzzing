# uds_sender.py
import isotp
import time

WAIT_RESPONSE_TIME = 0.2  # seconds
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
        retry = 0
        
        while retry < retry_count:
            self.stack.send(bytes([0x10, session_type]))
            success, response = self.wait_response(expected_response)
            if success:
                return True, response
            time.sleep(WAIT_SLEEP)
            retry += 1
        
        return False, None
    
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
                    if (len(response) >= 3) and (response[0] == 0x7f) and (response[2] == 0x78):
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
                break
            
            self.stack.process()
            if self.stack.available():
                response = self.stack.recv(timeout=5)
                if (len(response) >= 3) and (response[0] == 0x7f) and (response[2] == 0x78):
                    start_time = time.time()
                    continue
                
                if len(response) > 0:
                    success = True
                    break
        
        return success, response
    
    def SendDTCRequest(self, timeout=WAIT_RESPONSE_TIME):
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
        self.stack.send(bytes([0x19, 0x02]))
        
        start_time = time.time()
        while True:
            self.stack.process()
            if time.time() - start_time >= timeout:
                break
  
            if self.stack.available():
                response = self.stack.recv(timeout=5)
                if (len(response) >= 3) and (response[0] == 0x7f):
                    if response[2] == 0x78:
                        start_time = time.time()
                        continue
                    elif response[2] == 0x14: # Response Too long -> Success 
                        success = True
                        break
                    else: # Other NRC -> Fail
                        break

                if (len(response) >= 3) and (response[0] == 0x59):
                    success = True
                    break
        return success, response

    def SendDTCClear(self, timeout=WAIT_RESPONSE_TIME):
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
        self.stack.send(bytes([0x14, 0xFF, 0xFF, 0xFF]))
        
        start_time = time.time()
        while True:
            self.stack.process()
            if time.time() - start_time >= timeout:
                break
  
            if self.stack.available():
                response = self.stack.recv(timeout=5)
                if (len(response) >= 3) and (response[0] == 0x7f):
                    if response[2] == 0x78:
                        start_time = time.time()
                        continue
                    else:
                        success = False
                        break

                if (len(response) >= 3) and (response[0] == 0x54):
                    success = True
                    break
        return success

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
                if (len(response) >= 3) and (response[0] == 0x7f) and (response[2] == 0x78):
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
        
        success, _ = self.SendTesterPresent(retry_count)
        if not success:
            print("[ERROR] Failed to send Tester Present")
            return False, None, diag_response
        
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