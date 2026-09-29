# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

## 1. Thông tin học viên

- **Họ và tên:** Trần Nguyễn Tiến Đức
- **MSSV:** 2A202602871
- **Lớp:** K4-L3A
- **Repository:** https://github.com/TNTD-dev/K4-L3A-Day13-TranNguyenTienDuc-2A202602871-Monitoring-LLMOps
- **Commit SHA cuối:** lấy từ `git rev-parse HEAD` của bản đã push và gửi cùng URL repository trên LMS; không tự ghi SHA vào chính commit vì thao tác đó sẽ đổi SHA.
- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
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
| 07 — Waterfall Langfuse | [ảnh giao diện](evidence/07-langfuse-waterfall.png), [đối chiếu API](evidence/07-trace-waterfall.txt) |
| 08 — Metadata generation Langfuse | [ảnh giao diện](evidence/08-langfuse-generation-metadata.png), [đối chiếu API](evidence/08-trace-metadata.txt) |
| 09 — Prompt versions | [09-prompt-versions.png](evidence/09-prompt-versions.png) |
| 10 — Promote và rollback | [promote](evidence/10-prompt-promoted.png), [rollback](evidence/10-prompt-rollback.png) |
| 11 — Dashboard runtime | [ảnh](evidence/11-dashboard-overview.png), [scenario](evidence/11-practice-scenarios.txt) |
| 12 — Incident metric và workload | [ảnh dashboard](evidence/12-incident-metric.png), [metric](evidence/12-incident-metric.txt), [workload](evidence/12-challenge-workload.txt), [injection](evidence/12-incident-injection.txt) |
| 13 — Incident log | [ảnh](evidence/13-incident-log.png), [text đầy đủ](evidence/13-incident-log.txt) |
| 14 — Incident trace và khôi phục | [ảnh timeline Langfuse](evidence/14-incident-langfuse-timeline.png), [trace API](evidence/14-incident-trace.txt), [cả 5 trace](evidence/14-challenge-trace-list.txt), [disable](evidence/12-incident-disabled.txt), [post-disable](evidence/14-post-disable-metrics.txt) |

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

Tôi tạo workload trong project cá nhân `day13-k4-l3a-2A202602871` và đối chiếu [12 trace IDs với correlation IDs](evidence/06-trace-ids.txt) qua Langfuse. [Ảnh waterfall](evidence/07-langfuse-waterfall.png) hiển thị root `lab-agent-run` có child `retrieval` và `llm-generation`; [ảnh metadata](evidence/08-langfuse-generation-metadata.png) hiển thị model, 130 tokens, cost 0.001614 USD, prompt v1 nhãn `production` và `correlation_id=req-b2fb4a6a`. Metadata retrieval ghi doc count và success. `correlation_id` nối response header, log và trace.

Prompt `day13-chat` v1 là `baseline`, v2 là `candidate`. Cùng input “Explain how monitoring identifies a slow request.” đã tạo v1 trace `a54db286469527380fcf28a697520e07` (`req-b63178fb`) và v2 trace `fac7b3cf83786d6f32b42266ae5c2657` (`req-c39746ff`). Tôi promote `production` sang v2 rồi rollback về v1. Trạng thái cuối là v1 `baseline` + `production`, v2 `candidate` + `latest`: [ảnh promote](evidence/10-prompt-promoted.png), [ảnh rollback](evidence/10-prompt-rollback.png).

LLM của lab là FakeLLM; token/cost là mô phỏng, không phải hóa đơn model thật.

## 6. Dashboard, SLO và alerts

`/dashboard` dùng `/dashboard/data` từ `data/logs.jsonl`, mặc định 60 phút và làm mới mỗi 30 giây. Sáu panel: latency/TTFT, traffic, errors/retrieval, cost, tokens, quality. Có đơn vị và threshold. [Ảnh dashboard](evidence/11-dashboard-overview.png) là snapshot sau challenge chính thức và sau khi tắt incident, vì vậy hiển thị cả 10 request trong cùng cửa sổ 60 phút. [Output scenario CP2](evidence/11-practice-scenarios.txt) ghi riêng: `rag_slow` tăng latency lên khoảng 2.66 s; `tool_fail` tạo 3 lỗi và giảm retrieval success còn 84.21%; `cost_spike` tạo cost/request 0.007425–0.009885 USD. Xem [nguồn tính toán](../app/dashboard_data.py) và [contract](../config/dashboard.yaml).

[SLO](../config/slo.yaml): trong 28 ngày, ít nhất 99.5% request hoàn tất thành công trong ≤3 giây. Error budget 0.5% tổng request, tức tối đa 50 request lỗi hoặc chậm trên 10,000 request. Ba [alert](../config/alert_rules.yaml) theo triệu chứng: P95 latency >3 s trong 5 phút, error rate >2% trong 5 phút, cost/answer >0.004 USD trong 10 phút. Mỗi rule có severity, owner, Slack channel và [runbook](../docs/alerts.md).

## 7. Điều tra challenge chính thức

Tôi nhận nguyên file `K4-L3A-challenge.json` từ Lab Coach và đặt vào `config/challenge.json`; so sánh byte cho thấy file không đổi. ID `day13-k4-l3a-monitoring-llmops-v1`, seed 1311, feature `monitoring`, incident `rag_slow`, ngưỡng challenge 2000 ms. File gốc thuộc `.gitignore` và không được commit.

**Khoảng điều tra:** 2026-09-29 09:33:02–09:33:17 UTC. [Metric từ log và dashboard](evidence/12-incident-metric.txt) ghi 5/5 request vượt 2000 ms, latency P50 2664 ms, P95/P99 4144 ms, TTFT P95 55 ms, error rate 0%. Đây là sự cố chậm, không phải lỗi HTTP.

**Request đại diện:** [log](evidence/13-incident-log.txt) có `response_sent` 4144 ms và `correlation_id=req-4f616e78`. [Ảnh timeline Langfuse](evidence/14-incident-langfuse-timeline.png) và [trace API](evidence/14-incident-trace.txt) cùng ID là `8719140eeecfd554de8989ccffc7e4ec`: root `lab-agent-run` 4.145 s; child `retrieval` 2.505 s; child `llm-generation` 0.153 s. Span retrieval chiếm phần lớn thời gian. Request đầu còn có overhead lấy prompt, nhưng bốn trace còn lại đều có retrieval ~2.505 s và tổng ~2.66 s, nên kết luận không phụ thuộc request đầu.

**Root cause:** incident `rag_slow` bật nhánh giả lập delay 2.5 giây trong `app/mock_rag.py::retrieve`. **Fix action:** tắt `rag_slow` sau điều tra và xác minh bằng cùng 5 query; [log sau khi tắt](evidence/14-post-disable-metrics.txt) còn 156–159 ms, đều dưới ngưỡng 2000 ms. Trong hệ thống thật, xử lý nguồn retrieval chậm (vector store/index/network), đặt timeout và fallback có kiểm soát. **Preventive measure:** theo dõi P95 retrieval riêng, alert khi retrieval >2 s liên tục, kiểm tra sức khỏe/index của vector store và lưu trace có correlation ID cho mỗi request. Cờ incident hiện đã tắt.

## 8. Giải thích và tự đánh giá

Quyết định kỹ thuật chính là dùng một `correlation_id` từ response tới log và Langfuse. Metrics chỉ ra triệu chứng và thời điểm; log lọc request cụ thể; trace cùng ID chỉ ra retrieval hay generation gây ảnh hưởng. Scenario `tool_fail` tăng error rate và ghi `request_failed` cho retrieval; `rag_slow` làm span retrieval kéo dài. Kết luận CP3 phải dựa vào metric, log và trace cùng một sự cố.

Blocker thực tế: server đã ghi log nhưng Langfuse exporter có lúc chưa flush trước khi tiến trình dừng, nên trace chưa xuất hiện trên cloud. Tôi chạy workload có flush rõ ràng và kiểm tra trace ID từ Langfuse trước khi lưu evidence. Với challenge chính thức, tôi xác minh cả 5 trace trên Langfuse API trước khi kết luận. Nếu prompt fetch lỗi, ứng dụng dùng local fallback và ghi `prompt_source`/`prompt_fetch_error`; trace fallback không tính là managed-prompt trace.

Prompt version gắn kết quả với cấu hình đã dùng; promote/rollback cho phép đổi và khôi phục hành vi. Token/cost phát hiện tăng chi phí; SLO và error budget lượng hóa chất lượng phục vụ. Hạn chế: LLM và quality score chỉ là mô phỏng; SHA cuối và nộp LMS sẽ xác nhận sau push.

## 9. Checklist trước khi nộp

- [x] CP0–CP2 có source, validator, prompt và evidence runtime.
- [x] Project Langfuse cá nhân đúng quy ước, không đưa secret vào repo.
- [x] CP3 metric → log → trace và root cause từ challenge chính thức.
- [ ] Gửi SHA cuối và URL repository trên LMS/Codelabs sau khi push.

Tên repository hiện tại được giữ theo lựa chọn đã chốt, dù khác mẫu trong [hướng dẫn nộp](../docs/SUBMISSION.md); có rủi ro bị yêu cầu đổi tên.
