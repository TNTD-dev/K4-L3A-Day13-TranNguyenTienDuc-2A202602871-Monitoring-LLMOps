# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

## 1. Thông tin học viên

- **Họ và tên:** Trần Nguyễn Tiến Đức
- **MSSV:** 2A202602871
- **Lớp:** K4-L3A
- **Repository:** https://github.com/TNTD-dev/K4-L3A-Day13-TranNguyenTienDuc-2A202602871-Monitoring-LLMOps
- **Commit SHA cuối:** chờ CP3 và bản nộp cuối
- **Challenge ID:** chờ file gốc từ Lab Coach
- **Project Langfuse cá nhân:** `day13-k4-l3a-2A202602871`

## 2. Evidence index

| Nội dung | Evidence |
|---|---|
| CP0 baseline | [load](evidence/00-baseline-load-test.txt), [log validator](evidence/00-baseline-log-validator.txt), [dashboard validator](evidence/00-baseline-dashboard-validator.txt), [pytest](evidence/00-baseline-pytest.txt) |
| 01 — Pytest CP2 | [01-pytest.txt](evidence/01-pytest.txt) |
| 02 — Log validator | [02-log-validator.txt](evidence/02-log-validator.txt) |
| 03 — Dashboard validator | [03-dashboard-validator.txt](evidence/03-dashboard-validator.txt) |
| 04 — Structured log | [04-structured-log.txt](evidence/04-structured-log.txt) |
| 05 — PII redaction | [05-pii-redaction.txt](evidence/05-pii-redaction.txt) |
| 06 — Trace IDs và workload | [06-trace-ids.txt](evidence/06-trace-ids.txt), [06-flushed-workload.txt](evidence/06-flushed-workload.txt) |
| 07 — Quan hệ observation từ Langfuse API | [07-trace-waterfall.txt](evidence/07-trace-waterfall.txt) |
| 08 — Metadata từ Langfuse API | [08-trace-metadata.txt](evidence/08-trace-metadata.txt) |
| 09 — Prompt versions | [09-prompt-versions.png](evidence/09-prompt-versions.png) |
| 10 — Promote và rollback | [promote](evidence/10-prompt-promoted.png), [rollback](evidence/10-prompt-rollback.png) |
| 11 — Dashboard runtime | [ảnh](evidence/11-dashboard-overview.png), [scenario](evidence/11-practice-scenarios.txt) |
| 12–14 — Challenge chính thức | chờ CP3 |

## 3. Kết quả kỹ thuật tại CP2

| Chỉ số | Baseline CP0 | CP2 |
|---|---:|---:|
| Log validator | 30/100 | 100/100 |
| Dashboard validator | 6/6 | 6/6 |
| Pytest | 22 pass | 28 pass |
| Managed-prompt traces | 0 | 12 (11 v1, 1 v2) |
| PII leak | chưa có log baseline | 0 trên 44 log records |
| Correlation IDs | thiếu | 25 ID duy nhất |
| Latency P95 / TTFT P95 | chưa đo | 2663 ms / 55 ms |
| Retrieval success | chưa đo | 84.21% |

Workload thực hành có 19 requests, 3 lỗi, error rate 15.79%, tổng cost 0.053835 USD. Các cờ scenario đều đã tắt sau khi chạy. Số liệu này là [scenario luyện tập](evidence/11-practice-scenarios.txt), không phải challenge CP3.

## 4. Logging và PII

[Middleware](../app/middleware.py) nhận `x-request-id` đúng mẫu `req-<8 hex>` hoặc sinh ID mới, truyền qua context request và trả trong response header. Context được reset để tránh rò giữa request đồng thời. Structured log có `ts`, `level`, `event`, `correlation_id`, `user_id_hash`, `session_id`, `feature`, `model`, `env`, latency, TTFT, token, cost và tool outcome khi có. Xem [log thực tế](evidence/04-structured-log.txt) và [kiểm thử](../tests/test_correlation_and_traces.py).

`scrub_event` đệ quy qua string trong dict/list trước JSON renderer ghi file; rule che email, điện thoại Việt Nam, CCCD và thẻ. Trace tắt capture input/output thô, chỉ ghi metadata đã scrub. [Evidence redaction](evidence/05-pii-redaction.txt) chỉ lưu tên loại input giả và output đã che; [validator](evidence/02-log-validator.txt) báo 0 leak. [Test PII](../tests/test_pii.py) chứa các trường hợp cụ thể.

## 5. Tracing và prompt versioning

Tôi tạo workload trong project cá nhân `day13-k4-l3a-2A202602871` và đối chiếu [12 trace IDs với correlation IDs](evidence/06-trace-ids.txt) qua Langfuse. Root `lab-agent-run` có child `retrieval` (doc count, success) và `llm-generation` (model, token, cost, prompt name/version/label). `correlation_id` nối response header, log và trace.

Prompt `day13-chat` v1 là `baseline`, v2 là `candidate`. Cùng input “Explain how monitoring identifies a slow request.” đã tạo v1 trace `a54db286469527380fcf28a697520e07` (`req-b63178fb`) và v2 trace `fac7b3cf83786d6f32b42266ae5c2657` (`req-c39746ff`). Tôi promote `production` sang v2 rồi rollback về v1. Trạng thái cuối là v1 `baseline` + `production`, v2 `candidate` + `latest`: [ảnh promote](evidence/10-prompt-promoted.png), [ảnh rollback](evidence/10-prompt-rollback.png).

LLM của lab là FakeLLM; token/cost là mô phỏng, không phải hóa đơn model thật.

## 6. Dashboard, SLO và alerts

`/dashboard` dùng `/dashboard/data` từ `data/logs.jsonl`, mặc định 60 phút và làm mới mỗi 30 giây. Sáu panel: latency/TTFT, traffic, errors/retrieval, cost, tokens, quality. Có đơn vị và threshold. [Ảnh dashboard](evidence/11-dashboard-overview.png) là snapshot trước đợt scenario; [output scenario](evidence/11-practice-scenarios.txt) ghi số liệu mới: `rag_slow` tăng latency lên khoảng 2.66 s; `tool_fail` tạo 3 lỗi và giảm retrieval success còn 84.21%; `cost_spike` tạo cost/request 0.007425–0.009885 USD. Xem [nguồn tính toán](../app/dashboard_data.py) và [contract](../config/dashboard.yaml).

[SLO](../config/slo.yaml): trong 28 ngày, ít nhất 99.5% request hoàn tất thành công trong ≤3 giây. Error budget 0.5% tổng request, tức tối đa 50 request lỗi hoặc chậm trên 10,000 request. Ba [alert](../config/alert_rules.yaml) theo triệu chứng: P95 latency >3 s trong 5 phút, error rate >2% trong 5 phút, cost/answer >0.004 USD trong 10 phút. Mỗi rule có severity, owner, Slack channel và [runbook](../docs/alerts.md).

## 7. Challenge chính thức — chờ CP3

Lab Coach chưa phát file `config/challenge.json` gốc. Tôi không suy diễn challenge ID hoặc dùng scenario luyện tập thay thế. Khi nhận nguyên file, sẽ chạy workload, thu metric bất thường (12), log có correlation ID (13), trace cùng ID và span gây ảnh hưởng (14), rồi ghi khoảng thời gian, root cause, fix action và preventive measure. File gốc thuộc `.gitignore` và không commit.

## 8. Giải thích và tự đánh giá

Quyết định kỹ thuật chính là dùng một `correlation_id` từ response tới log và Langfuse. Metrics chỉ ra triệu chứng và thời điểm; log lọc request cụ thể; trace cùng ID chỉ ra retrieval hay generation gây ảnh hưởng. Scenario `tool_fail` tăng error rate và ghi `request_failed` cho retrieval; `rag_slow` làm span retrieval kéo dài. Kết luận CP3 phải dựa vào metric, log và trace cùng một sự cố.

Blocker thực tế: server đã ghi log nhưng Langfuse exporter có lúc chưa flush trước khi tiến trình dừng, nên trace chưa xuất hiện trên cloud. Tôi chạy workload có flush rõ ràng và kiểm tra trace ID từ Langfuse trước khi lưu evidence. Nếu prompt fetch lỗi, ứng dụng dùng local fallback và ghi `prompt_source`/`prompt_fetch_error`; trace fallback không tính là managed-prompt trace.

Prompt version gắn kết quả với cấu hình đã dùng; promote/rollback cho phép đổi và khôi phục hành vi. Token/cost phát hiện tăng chi phí; SLO và error budget lượng hóa chất lượng phục vụ. Hạn chế: LLM và quality score chỉ là mô phỏng; CP3, SHA cuối và LMS còn chờ challenge gốc.

## 9. Checklist trước khi nộp

- [x] CP0–CP2 có source, validator, prompt và evidence runtime.
- [x] Project Langfuse cá nhân đúng quy ước, không đưa secret vào repo.
- [ ] CP3 metric → log → trace và root cause từ challenge chính thức.
- [ ] Cập nhật SHA cuối, kiểm tra mọi evidence thuộc commit đó, push và tự nộp LMS.

Tên repository hiện tại được giữ theo lựa chọn đã chốt, dù khác mẫu trong [hướng dẫn nộp](../docs/SUBMISSION.md); có rủi ro bị yêu cầu đổi tên.
