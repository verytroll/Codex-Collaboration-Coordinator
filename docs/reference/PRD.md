# PRD.md

# Product Requirements Document

## 1. Tổng quan dự án

### 1.1 Tên dự án tạm thời
**Codex Collaboration Coordinator**

### 1.2 Mục tiêu
Xây dựng một hệ thống cho phép **nhiều Codex agent có thể nói chuyện, giao việc và phối hợp với nhau** trong một session chung, theo trải nghiệm gần với `codex-weave`, nhưng với kiến trúc tách lớp và dễ mở rộng hơn, học hỏi thêm từ `agentchattr`.

### 1.3 Vấn đề cần giải quyết
Hiện tại, `codex app-server` cung cấp các primitive mạnh để quản lý thread, turn, interrupt và compaction, nhưng chưa tự cung cấp lớp điều phối nhiều agent như một “phòng chat chung”.

Nếu chỉ chạy nhiều instance hoặc nhiều thread Codex:
- bạn có nhiều runtime riêng
- nhưng chưa có cơ chế để chúng tự nhắn nhau
- chưa có session chung
- chưa có routing bằng mention
- chưa có loop guard và presence

Dự án này giải quyết khoảng trống đó bằng cách xây một **coordinator/orchestrator** ở giữa.

### 1.4 Người dùng mục tiêu
- Cá nhân muốn thử nghiệm nhiều agent cộng tác local
- Nhóm kỹ thuật nhỏ muốn cho nhiều coding agents cộng tác trên cùng một bài toán
- Nhà phát triển muốn chuẩn hóa đường đi từ multi-agent collaboration sang A2A trong tương lai

### 1.5 Phạm vi phiên bản đầu
Phiên bản đầu tập trung vào **MVP local-first**:
- nhiều agent Codex
- session chung
- mention-based routing
- lead / non-lead
- interrupt / compact
- state lưu bền
- loop guard
- presence cơ bản
- output artifact tối thiểu

Không đưa vào bản đầu:
- cloud multi-tenant
- auth production-grade
- dashboard phức tạp
- fork sâu vào Codex CLI

---

## 2. Yêu cầu cốt lõi

### 2.1 Yêu cầu chức năng
Hệ thống phải cho phép:
1. Tạo và quản lý **session** cộng tác
2. Đăng ký nhiều **agent** vào cùng một session
3. Gửi tin nhắn trong session
4. Mention một agent bằng cú pháp đơn giản để giao việc
5. Chuyển output của agent A thành input cho agent B thông qua coordinator
6. Hỗ trợ role **lead** để kiểm soát relay và control actions
7. Hỗ trợ tối thiểu các control actions:
   - tạo lượt làm việc mới
   - interrupt
   - compact
8. Lưu trạng thái để có thể khôi phục sau restart
9. Theo dõi trạng thái online/offline của agent
10. Chặn vòng lặp relay quá dài giữa các agent
11. Lưu kết quả dưới dạng artifact cơ bản
12. Có đường mở rộng sang A2A ở giai đoạn sau

### 2.2 Yêu cầu phi chức năng
Hệ thống nên:
- dễ hiểu với người mới
- chạy local được trước
- có kiến trúc module rõ ràng
- tránh phụ thuộc sớm vào fork nặng
- có log đủ để debug
- có test tối thiểu cho các luồng chính
- có thể mở rộng dần thành API/A2A server

### 2.3 Tiêu chí thành công của MVP
MVP được xem là thành công khi:
- người dùng có thể tạo một session
- có thể đăng ký ít nhất 2 Codex agent
- có thể gửi `#agent` để giao việc
- agent nhận đúng context và phản hồi lại session
- lead có thể dùng interrupt/compact
- hệ thống không rơi vào relay loop vô hạn
- restart coordinator không làm mất toàn bộ trạng thái session

---

## 3. Tính năng cốt lõi

### 3.1 Session cộng tác
- Tạo session mới
- Tham gia/rời session
- Session có lịch sử chat chung
- Session có thể lưu bền qua restart

### 3.2 Agent registry
- Đăng ký agent
- Gán tên hiển thị
- Gán role
- Đánh dấu lead/non-lead
- Map agent tới runtime Codex tương ứng

### 3.3 Mention-based routing
- Phát hiện cú pháp `#agent`
- Xác định agent đích
- Tạo trigger cho agent đích
- Đưa phản hồi của agent quay lại session

### 3.4 Relay engine
- Điều phối message từ người dùng hoặc agent này sang agent khác
- Giữ đúng session context
- Theo dõi chuỗi relay nhiều bước

### 3.5 Control commands
- `/new`
- `/interrupt`
- `/compact`

Các control command được thực thi thông qua coordinator và CodexBridge.

### 3.6 Codex bridge
- Kết nối tới `codex app-server`
- Tạo thread
- Bắt đầu turn
- Tiếp tục/resume
- Steer turn đang chạy
- Interrupt turn
- Compact thread

### 3.7 Presence và heartbeat
- Agent gửi heartbeat định kỳ
- Hệ thống đánh dấu online/offline
- Agent offline thì có thể được queue message

### 3.8 Loop guard
- Đếm số hop relay giữa agent
- Tạm dừng session khi vượt ngưỡng
- Yêu cầu xác nhận để tiếp tục

### 3.9 Artifact cơ bản
- Final text
- Diff
- File metadata hoặc file export tối thiểu

### 3.10 A2A-ready layer
Không cần hoàn chỉnh ngay ở MVP, nhưng thiết kế phải chừa đường cho:
- Agent Card
- message send / stream
- task status
- artifact streaming

---

## 4. Thành phần cốt lõi

### 4.1 Coordinator
Trung tâm điều phối toàn bộ hệ thống.

**Nhiệm vụ:**
- nhận message
- quản lý session
- phát hiện mention
- điều phối relay
- gọi CodexBridge
- phát control actions

### 4.2 Session Manager
Quản lý:
- session lifecycle
- lịch sử hội thoại
- membership
- current state

### 4.3 Agent Registry
Quản lý:
- agent_id
- display_name
- role
- lead status
- runtime mapping
- presence

### 4.4 Router
Phân tích message để:
- phát hiện `#agent`
- phát hiện control command
- xác định target
- xác định hành động tiếp theo

### 4.5 Relay Engine
Biến output của một agent thành input cho agent khác trong cùng session theo policy đã định.

### 4.6 CodexBridge
Lớp giao tiếp với `codex app-server`.

### 4.7 State Store
Lưu trạng thái bền cho:
- sessions
- agents
- messages
- jobs
- artifacts
- codex threads
- presence

### 4.8 Presence Service
- heartbeat
- online/offline
- crash timeout
- offline queue

### 4.9 Artifact Manager
- gom output từ Codex
- lưu artifact
- gắn artifact vào message/task/job/session

### 4.10 A2A Adapter
Lớp mở rộng về sau để public hóa hệ thống ra ngoài qua A2A.

---

## 5. Luồng ứng dụng/người dùng

### 5.1 Luồng cơ bản: tạo session và chat
1. Người dùng khởi động coordinator
2. Người dùng khởi động các agent Codex
3. Agent đăng ký vào coordinator
4. Người dùng tạo session mới
5. Người dùng gửi chat thường vào session
6. Tin nhắn được lưu vào lịch sử chung

### 5.2 Luồng giao việc qua mention
1. Người dùng gửi tin nhắn dạng `#builder sửa lỗi test này`
2. Router phát hiện mention `#builder`
3. Coordinator tạo trigger cho builder
4. CodexBridge gọi `turn/start` cho builder trên thread tương ứng
5. Builder xử lý và trả kết quả
6. Kết quả được đưa lại vào session chung
7. Nếu cần, kết quả đó lại có thể được relay tiếp cho agent khác

### 5.3 Luồng agent gọi agent khác
1. Agent A trả lời trong session
2. Trong câu trả lời có mention `#reviewer`
3. Coordinator phát hiện mention mới
4. Loop guard kiểm tra số hop
5. Nếu hợp lệ, coordinator kích hoạt agent B
6. Agent B nhận ngữ cảnh phù hợp và phản hồi

### 5.4 Luồng interrupt
1. Lead gửi `#builder /interrupt`
2. Router xác định đây là control command
3. Coordinator gọi `turn/interrupt` qua CodexBridge
4. Thread/turn được cập nhật trạng thái
5. Session nhận message hoặc status báo đã dừng

### 5.5 Luồng compact
1. Lead gửi `#builder /compact`
2. Coordinator gọi `thread/compact/start`
3. Codex app-server xử lý compaction
4. Kết quả/trạng thái compaction được ghi lại

### 5.6 Luồng restart recovery
1. Coordinator restart
2. State Store được đọc lại
3. Sessions, agents, mappings, artifacts được nạp lại
4. Agent nào chưa heartbeat trong ngưỡng thì đánh dấu offline
5. Session vẫn giữ lịch sử và có thể tiếp tục

---

## 6. Tech stack

### 6.1 Ngôn ngữ và runtime
**Python 3.11+**

Lý do:
- dễ học với người mới
- ecosystem tốt cho API, async, SQLite, testing
- dễ build coordinator/orchestrator

### 6.2 Backend framework
**FastAPI**

Dùng cho:
- API nội bộ hoặc public
- healthcheck
- session endpoints
- tương lai mở rộng sang A2A

### 6.3 Giao tiếp với Codex
**Codex app-server qua stdio/subprocess**

Lý do:
- phù hợp tài liệu hiện tại
- tránh expose websocket experimental ra ngoài sớm
- dễ cô lập trong local MVP

### 6.4 Database
**SQLite** cho V1

Lý do:
- đơn giản
- không cần dựng hạ tầng riêng
- đủ cho local/small-team MVP

### 6.5 Mô hình bất đồng bộ
- `asyncio`
- background tasks nhẹ
- event queue nội bộ cho relay

### 6.6 Testing
- `pytest`
- `pytest-asyncio`

### 6.7 Chất lượng mã nguồn
- `ruff`
- `mypy` ở giai đoạn sau nếu cần

### 6.8 Artifact storage
- file system local cho V1
- object storage hoặc service riêng ở V2+

### 6.9 Tích hợp tương lai
- A2A API layer
- SSE streaming
- webhook sau MVP

---

## 7. Kế hoạch triển khai

### Giai đoạn 1: Nền tảng coordinator
**Mục tiêu:** có server và state store cơ bản

Bao gồm:
- tạo repo
- dựng FastAPI app
- healthcheck
- SQLite schema
- Session Manager
- Agent Registry
- docs kiến trúc ban đầu

### Giai đoạn 2: Kết nối Codex
**Mục tiêu:** coordinator có thể điều khiển Codex runtime

Bao gồm:
- chạy `codex app-server` local
- tạo `CodexBridge`
- gọi được `initialize`
- gọi được `thread/start`
- gọi được `turn/start`
- nhận được phản hồi cơ bản

### Giai đoạn 3: Session và mention routing
**Mục tiêu:** nhiều agent nói chuyện được trong session

Bao gồm:
- tạo/join/leave session
- gửi message vào session
- parse `#agent`
- relay message sang đúng agent
- nhận phản hồi và đăng lại vào session

### Giai đoạn 4: Control actions và ổn định phiên
**Mục tiêu:** quản lý runtime cộng tác an toàn hơn

Bao gồm:
- `/interrupt`
- `/compact`
- lead / non-lead enforcement
- presence / heartbeat
- offline queue
- recovery sau restart

### Giai đoạn 5: Chất lượng đầu ra
**Mục tiêu:** output có cấu trúc và hữu ích hơn

Bao gồm:
- final text artifact
- diff artifact
- file artifact tối thiểu
- logging
- tests cho các luồng chính
- README hướng dẫn chạy

### Giai đoạn 6: Mở rộng chuẩn hóa
**Mục tiêu:** chuẩn bị cho tích hợp ngoài hệ thống

Bao gồm:
- Agent Card
- A2A message/task mapping
- streaming endpoint
- subscribe/cancel
- chuẩn hóa artifact model

### Mốc bàn giao MVP
MVP được coi là hoàn thành khi:
- có ít nhất 2 agent Codex đăng ký được
- có thể gửi mention giữa agent
- session lưu bền được
- lead dùng được interrupt/compact
- loop guard hoạt động
- output cuối có artifact cơ bản
- người dùng khác có thể clone repo và chạy theo README

---

## 8. Ghi chú định hướng sản phẩm

Đây không phải là một “chat app đơn thuần”.

Đây là một **lớp điều phối nhiều agent coding**, trong đó:
- Codex là execution engine
- Coordinator là collaboration engine
- Session là không gian phối hợp
- A2A là hướng chuẩn hóa giao tiếp về sau

Mục tiêu dài hạn là tạo một nền tảng:
- chạy local trước
- cộng tác nhiều agent được
- sau đó có thể public hóa ra API hoặc A2A mà không phải viết lại từ đầu
