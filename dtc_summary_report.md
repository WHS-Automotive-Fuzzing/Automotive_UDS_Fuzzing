# CAN Bus DTC 분석 결과 보고서

## 개요
제공해주신 CAN 버스 데이터는 **UDS (Unified Diagnostic Services)** 프로토콜을 사용한 차량 진단 데이터입니다. 
CAN ID `778`을 통해 ECU(Electronic Control Unit)와 통신하며, 주로 **BCM (Body Control Module)** 관련 진단 정보를 포함하고 있습니다.

## 주요 발견사항

### 1. ECU 정보
- **모듈명**: BCM1 (Body Control Module 1)
- **제조사**: BOSCH
- **소프트웨어 ID**: EV_BCM1BOSCHAU651
- **애플리케이션 데이터**: 017002
- **시스템명**: BCM1 MLBevo

### 2. 발견된 DTC 코드 (총 12개 고유 코드)

#### 🔴 Critical 심각도 (4개)
| DTC 코드 | 설명 | 상태 | 의미 |
|----------|------|------|------|
| **P0108** | MAP/BARO Pressure Circuit High | 0x97 | 매니폴드 절대압력 센서 회로 이상 (높은 값) |
| **P2409** | Fuel Cap Sensor Circuit | 0xEA | 연료캡 센서 회로 이상 |
| **P0101** | MAF Circuit Range/Performance | 0x82 | 질량 공기 유량 센서 성능 이상 |
| **P0105** | MAP/BARO Pressure Circuit | 0x81 | 매니폴드 절대압력 센서 회로 이상 |

#### 🟡 Medium 심각도 (1개)
| DTC 코드 | 설명 | 상태 | 의미 |
|----------|------|------|------|
| **P0108** | MAP/BARO Pressure Circuit High | 0x02 | 매니폴드 절대압력 센서 회로 이상 (확인됨) |

#### 🟢 Low 심각도 (7개)
| DTC 코드 | 설명 | 상태 | 의미 |
|----------|------|------|------|
| **P0902** | Transmission Control Module | 0x01 | 변속기 제어 모듈 통신 이상 (대기 중) |
| **C2100** | ABS/ESP System | 0x09 | ABS/ESP 시스템 이상 |
| **P0901** | Transmission Control | 0x01 | 변속기 제어 이상 (대기 중) |
| **B0709** | Body Control Module | 0x01 | 바디 컨트롤 모듈 이상 (대기 중) |
| **P0196** | Engine Oil Temperature | 0x08 | 엔진 오일 온도 센서 이상 |
| **P0801** | Reverse Inhibit Control | 0x09 | 후진 억제 제어 이상 |
| **P0341** | Camshaft Position Sensor | 0x08 | 캠샤프트 위치 센서 이상 |

## 3. 진단 세션 정보
- **활성 진단 세션**: 확장 진단 세션 활성화됨
- **통신 프로토콜**: ISO-TP (ISO 14229-2)
- **진단 응답**: 정상적인 UDS 응답 확인

## 4. 심각도별 분석

### 🔴 즉시 조치 필요 (Critical)
- **P0108/P0105**: 매니폴드 압력 센서 관련 문제로 엔진 성능에 직접적인 영향
- **P0101**: 공기 유량 센서 이상으로 연료 혼합비에 영향
- **P2409**: 연료 시스템 관련 문제

### 🟡 모니터링 필요 (Medium)
- **P0108**: 동일한 센서의 다른 상태로 지속적인 모니터링 필요

### 🟢 예방 정비 (Low)
- 대부분 통신 관련 또는 대기 상태의 오류들
- 정기 점검 시 확인 권장

## 5. 권장사항

### 즉시 조치
1. **매니폴드 압력 센서 (MAP/BARO)** 점검 및 교체
2. **질량 공기 유량 센서 (MAF)** 청소 또는 교체
3. **연료캡 및 관련 센서** 점검

### 예방 정비
1. **CAN 통신 라인** 점검
2. **센서 커넥터** 접촉 불량 확인
3. **ECU 소프트웨어** 업데이트 확인

## 6. 기술적 세부사항

### UDS 서비스 사용 현황
- **0x19**: DTC 정보 읽기 (Read DTC Information)
- **0x22**: 데이터 식별자로 데이터 읽기 (Read Data By Identifier)
- **0x10**: 진단 세션 제어 (Diagnostic Session Control)
- **0x3E**: 테스터 Present (Keep Alive)

### 확장 데이터
각 DTC에 대해 상세한 확장 데이터가 포함되어 있어, 고장 발생 시점의 엔진 상태, 센서 값 등을 추가로 분석할 수 있습니다.

---

**결론**: 이 차량은 주로 엔진 관리 시스템의 센서 관련 문제들이 발견되었으며, 특히 공기 유량 및 압력 센서 계통의 점검이 시급합니다. 대부분의 DTC는 센서 교체나 청소로 해결 가능할 것으로 판단됩니다.