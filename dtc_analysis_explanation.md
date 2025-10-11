# CAN DTC 데이터 분석 과정 상세 설명

## 1. ISO-TP (ISO 15765-2) 프로토콜 이해

### Multi-Frame 메시지 구조
CAN 버스는 한 프레임당 최대 8바이트만 전송할 수 있어서, 긴 메시지는 여러 프레임으로 나누어 전송합니다.

#### First Frame (첫 번째 프레임)
```
can0  778   [8]  10 27 59 02 19 01 08 97
                 ^^ ^^
                 |  |
                 |  +-- 전체 메시지 길이 (0x027 = 39 바이트)
                 +-- First Frame 식별자 (0x10)
```

#### Consecutive Frame (연속 프레임)
```
can0  778   [8]  21 09 02 01 24 09 EA 61
                 ^^
                 |
                 +-- Consecutive Frame (0x21 = 순서번호 1)
```

## 2. UDS (Unified Diagnostic Services) 서비스 분석

### Service 0x59 - Read DTC Information
```
첫 번째 예시:
10 27 59 02 19 01 08 97  <- First Frame
      ^^ ^^
      |  |
      |  +-- Sub-function 0x02 (Report DTC by Status Mask)
      +-- Service ID 0x59 (Read DTC Information)
```

### 전체 메시지 재구성
First Frame + Consecutive Frames를 합치면:
```
59 02 19 01 08 97 09 02 01 24 09 EA 61 00 09 01 01 82 09 01 01 87 09 01 01 96 08 01 05 81 08 01 09 01 08 02 03 41 08
```

### DTC 목록 파싱
Service 0x59, Sub-function 0x02의 응답 형식:
```
59 02 [상태마스크] [DTC1_고] [DTC1_중] [DTC1_저] [DTC1_상태] [DTC2_고] [DTC2_중] [DTC2_저] [DTC2_상태] ...
```

실제 데이터에서:
```
59 02 19 | 01 08 97 09 | 02 01 24 09 | EA 61 00 09 | ...
          |<-- DTC 1 -->|<-- DTC 2 -->|<-- DTC 3 -->|
```

## 3. DTC 코드 변환 과정

### DTC 형식 변환 규칙
3바이트 DTC (예: 01 08 97)를 표준 5자리 코드로 변환:

```
바이트 1: 01 = 0000 0001
          ^^   ^^^^
          |    |
          |    +-- 두 번째와 세 번째 숫자 (01)
          +-- 시스템 분류 (00 = P: Powertrain)

바이트 2: 08 = 0000 1000
          ^    ^
          |    |
          |    +-- 네 번째 숫자 (8)
          +-- 세 번째 숫자 (0)

바이트 3: 97 = 1001 0111
          ^    ^
          |    |
          |    +-- 다섯 번째 숫자 (7)
          +-- 네 번째 숫자 (9)
```

결과: P0108

### 시스템 분류 코드
- 00 = P (Powertrain/엔진 및 변속기)
- 01 = C (Chassis/섀시)
- 10 = B (Body/차체)
- 11 = U (Network/네트워크)

## 4. 실제 파싱 예시

### 첫 번째 DTC 메시지 분석
```
원본 데이터:
10 27 59 02 19 01 08 97
21 09 02 01 24 09 EA 61
22 00 09 01 01 82 09 01
23 01 87 09 01 01 96 08
24 01 05 81 08 01 09 01
25 08 02 03 41 08 AA AA
```

재구성된 메시지 (39바이트):
```
59 02 19 | 01 08 97 09 | 02 01 24 09 | EA 61 00 09 | 01 01 82 09 | 01 01 87 09 | 01 01 96 08 | 01 05 81 08 | 01 09 01 08 | 02 03 41 08
```

파싱 결과:
1. **01 08 97** (상태: 09) → P0108
2. **02 01 24** (상태: 09) → P0201  
3. **EA 61 00** (상태: 09) → U2A61 (EA = 11101010, 상위 2비트 11 = U)
4. **01 01 82** (상태: 09) → P0101
5. **01 01 87** (상태: 09) → P0101
6. **01 01 96** (상태: 08) → P0101
7. **01 05 81** (상태: 08) → P0105
8. **01 09 01** (상태: 08) → P0109
9. **02 03 41** (상태: 08) → P0203

## 5. DTC 상태 바이트 해석

상태 바이트 비트 의미:
- Bit 0 (0x01): Test Failed (테스트 실패)
- Bit 1 (0x02): Test Failed This Operation Cycle
- Bit 2 (0x04): Pending DTC
- Bit 3 (0x08): Confirmed DTC (확정된 고장)
- Bit 4 (0x10): Test Not Completed Since Last Clear
- Bit 5 (0x20): Test Failed Since Last Clear
- Bit 6 (0x40): Test Not Completed This Operation Cycle
- Bit 7 (0x80): Warning Indicator Requested

예시:
- 상태 0x09 = 0000 1001 = Bit 0 + Bit 3 = Test Failed + Confirmed DTC
- 상태 0x08 = 0000 1000 = Bit 3 = Confirmed DTC

## 6. Extended DTC Data (Service 0x59, Sub-function 0x06)

```
10 28 59 06 01 08 97 09
      ^^ ^^ ^^^^^^^^^^^ ^^
      |  |  |           |
      |  |  |           +-- Record Number (데이터 레코드 번호)
      |  |  +-- DTC 코드
      |  +-- Sub-function 0x06 (Read DTC Extended Data)
      +-- Service ID 0x59
```

Extended Data는 DTC에 대한 추가 정보(동결 프레임 데이터 등)를 포함합니다.

## 7. 기타 진단 응답

### Negative Response
```
03 7F A8 11
   ^^ ^^ ^^
   |  |  |
   |  |  +-- NRC (Negative Response Code) 0x11 = serviceNotSupported
   |  +-- 거부된 서비스 ID (0xA8)
   +-- Negative Response Service ID (0x7F)
```

### Positive Response (Service 0x62 - Read Data By Identifier)
```
10 15 62 F1 9E 45 56 5F 42 43 4D 31 42 4F 53 43 48 41 55 36 35 31 00
      ^^ ^^^^^ ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |  |     |
      |  |     +-- 데이터: "EV_BCM1BOSCHAU651"
      |  +-- Data Identifier (F19E)
      +-- Service ID (0x62)
```

이렇게 ISO-TP 프로토콜과 UDS 표준을 사용하여 CAN 버스 데이터에서 DTC 정보를 추출하고 해석했습니다.