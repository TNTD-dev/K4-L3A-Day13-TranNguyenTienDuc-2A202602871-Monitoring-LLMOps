# Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: User-facing latency degraded.
- Severity: critical; owner: AI API on-call; kênh: Slack `#llmops-alerts`.
- Điều kiện: P95 `response_sent.latency_ms` trong 5 phút > 3.000 ms, có ít nhất 5 request; duy trì 5 phút.
- SLI/SLO: fast_successful_requests, mục tiêu 99,5% trong 28 ngày.
- Ảnh hưởng: Người dùng chờ câu trả lời quá 3 giây; tiêu hao error budget.
- Ba bước kiểm tra: (1) Xem panel latency và khoảng tăng P95. (2) Lọc log `response_sent` chậm để lấy `correlation_id`. (3) Mở trace cùng ID, so sánh retrieval và generation.
- Mitigation tạm thời: Giảm concurrency hoặc chuyển sang luồng trả lời ngắn nếu generation chậm; nếu retrieval chậm, tạm bỏ nguồn retrieval lỗi và dùng fallback đã được kiểm soát. Tắt practice incident nếu đây là thử nghiệm.

## Alert 2

- Tên: Request failure rate elevated.
- Severity: critical; owner: AI API on-call; kênh: Slack `#llmops-alerts`.
- Điều kiện: `request_failed / request_received` trong 5 phút > 2%, có ít nhất 5 request; duy trì 5 phút.
- SLI/SLO: fast_successful_requests; guardrail error rate ≤ 2%.
- Ảnh hưởng: Người dùng nhận HTTP 500 hoặc không có câu trả lời.
- Ba bước kiểm tra: (1) Xem error rate, breakdown và retrieval success. (2) Lọc `request_failed` theo `error_type` và `correlation_id`. (3) Mở trace cùng ID để xác định span lỗi.
- Mitigation tạm thời: Khôi phục dependency lỗi hoặc chuyển sang fallback có kiểm soát; giảm lưu lượng nếu lỗi lan rộng. Tắt practice incident nếu đây là thử nghiệm.

## Alert 3

- Tên: Cost per answer elevated.
- Severity: warning; owner: LLMOps on-call; kênh: Slack `#llmops-alerts`.
- Điều kiện: mean `response_sent.cost_usd` trong 10 phút > $0,004, có ít nhất 5 response; duy trì 10 phút.
- SLI/SLO: guardrail daily cost ≤ $2,50; alert theo chi phí mỗi câu trả lời để phát hiện tăng token dù traffic không đổi.
- Ảnh hưởng: Ngân sách LLM tăng nhanh, có nguy cơ vượt guardrail theo ngày.
- Ba bước kiểm tra: (1) So panel cost với traffic cùng thời gian. (2) So `tokens_in`/`tokens_out` và model trong log. (3) Mở trace cùng `correlation_id` để kiểm tra generation và prompt version.
- Mitigation tạm thời: Giới hạn output token hoặc rollback prompt version làm câu trả lời dài bất thường; đối chiếu lại cost/response sau thay đổi. Tắt practice incident nếu đây là thử nghiệm.
