# Project #3 – Feature 004 (Add Quiz) – Non-Functional Testing

Gói kiểm thử phi chức năng độc lập cho **Feature 004 – Add Quiz** trên Moodle LMS 5.1.x local, gồm 2 yêu cầu phi chức năng chính thức:
- **NFR-07 – Performance / Load Testing:** Locust + Python `requests` + `BeautifulSoup4` + Moodle PHP CLI DB Audit qua `docker exec`.
- **NFR-08 – Accessibility Testing:** Python + Selenium WebDriver + `axe-core` (WCAG 2.1 Level A/AA + điều hướng bàn phím `Tab` + liên kết ARIA cho thông báo lỗi).

## 1. Cài đặt trên Windows 11 (PowerShell)
```powershell
cd Feature004_NonFunctional
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Điền thông tin local và tên container (ví dụ moodle-demo-webserver-1) vào .env

# Kiểm tra offline & môi trường (read-only)
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe check_environment.py
```

## 2. Chạy NFR-08 – Accessibility Testing
```powershell
# Smoke (ACC-01 & ACC-04)
.\.venv\Scripts\python.exe -m accessibility.run_accessibility --smoke

# Formal Run đầy đủ 5 kịch bản (ACC-01 .. ACC-05)
.\.venv\Scripts\python.exe -m accessibility.run_accessibility
```
- **5 kịch bản (`accessibility/scenarios.csv`):**
  - `ACC-01`: Trạng thái mặc định của trang `Add a new Quiz`.
  - `ACC-02`: Trạng thái mở rộng toàn bộ (`Expand all`).
  - `ACC-03`: Trạng thái hiển thị lỗi validation (Name rỗng / Close < Open / Grade to pass > 10).
  - `ACC-04`: Điều hướng tuần tự bằng phím `Tab` qua 14 điều khiển đích trọng yếu (không keyboard trap).
  - `ACC-05`: Liên kết ngữ nghĩa ARIA (`aria-invalid`, `aria-describedby` / `role="alert"`) giữa trường lỗi và thông báo lỗi.
- **Lưu ý phạm vi:** Chỉ kết luận trong phạm vi quy tắc tự động của `axe-core` và 5 kịch bản đã chạy, không tuyên bố tuân thủ toàn diện 100% WCAG 2.1.

## 3. Chạy NFR-07 – Performance / Load Testing
```powershell
# Smoke (1 virtual user x 15 giây x 1 lượt)
.\.venv\Scripts\python.exe -m performance.run_performance --smoke

# Formal Run chính thức (1, 5, 10, 20 users x 60s x 3 lượt = 12 lượt)
.\.venv\Scripts\python.exe -m performance.run_performance
```
- **Ngưỡng Acceptance Criteria (do nhóm đề xuất, giữ nguyên không sửa đổi):**
  - `Mean response time <= 2000 ms`
  - `P95 response time <= 5000 ms`
  - `Error rate <= 1%`
  - `Duplicate quizzes = 0` và `Audit failures = 0`

## 4. Dọn dữ liệu thử nghiệm sau NFR-07
```powershell
# Dry-run (mặc định)
.\.venv\Scripts\python.exe cleanup.py results\performance\<run_dir>

# Xóa thật chỉ các Quiz namespace nfr4... qua Moodle course_delete_module()
.\.venv\Scripts\python.exe cleanup.py results\performance\<run_dir> --apply
```
