# Project #3 – Feature 004 (Add Quiz) – Level 1

Bộ kiểm thử tự động Data-Driven Testing (Level 1) bằng Python + Selenium WebDriver cho toàn bộ **69 test cases** (`TC-004-001` đến `TC-004-069`: 28 BVA, 24 ECP, 9 DT, 8 UC) kế thừa từ Project #2 của Feature 004 – Add Quiz trên Moodle LMS 5.1.x.

## 1. Cấu trúc thư mục
```text
Feature004_Level1/
├── main.py                      # Entry point CLI (--dry-run, --group, --case, --timeout, --headless, --base-url)
├── cleanup.py                   # Dọn Quiz thử nghiệm an toàn qua Moodle course_delete_module() (mặc định dry-run)
├── core/                        # config, browser, data_loader, preconditions, runner, reporter
├── pages/                       # Page Object Model: locators, login_page, add_quiz_page, course_page
├── test_groups/                 # 7 luồng thực thi Q01_NAME .. Q07_USECASE
├── data/                        # 7 tệp CSV chuẩn (đủ 69 test cases TC-004-001..069)
├── tests/                       # Offline unit tests (không cần Moodle chạy)
├── results/                     # Kết quả thực thi dạng Unified Results (tạo tự động khi chạy)
├── .env.example                 # Mẫu cấu hình môi trường (không chứa mật khẩu thật)
├── requirements.txt             # Thư viện Python
└── README.md
```

## 2. Phân nhóm thực thi (7 Groups = 69 Test Cases)
| Group | File CSV | Số ca | Dải mã |
|---|---|---:|---|
| `Q01_NAME` | `data/q01_name.csv` | 9 | `TC-004-001..007`, `029`, `030` |
| `Q02_DESC` | `data/q02_desc.csv` | 3 | `TC-004-031..033` |
| `Q03_TIMING` | `data/q03_timing.csv` | 14 | `TC-004-008..014`, `034..040` |
| `Q04_GRADE_APP` | `data/q04_grade_app.csv` | 20 | `TC-004-015..026`, `041..048` |
| `Q05_FEEDBACK` | `data/q05_feedback.csv` | 6 | `TC-004-027..028`, `049..052` |
| `Q06_DECISION` | `data/q06_decision.csv` | 9 | `TC-004-053..061` |
| `Q07_USECASE` | `data/q07_usecase.csv` | 8 | `TC-004-062..069` |

## 3. Cài đặt trên Windows 11 (PowerShell)
```powershell
cd Feature004_Level1
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Điền thông tin tài khoản local và tên container vào .env
```

## 4. Kiểm tra offline & thực thi trên Moodle local
```powershell
# Kiểm tra unit test offline (không cần Moodle)
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

# Kiểm tra schema CSV và danh sách 69 ca
.\.venv\Scripts\python.exe main.py --dry-run

# Chạy thử 1 ca cụ thể
.\.venv\Scripts\python.exe main.py --case TC-004-001 --timeout 30 --headless

# Chạy 1 nhóm
.\.venv\Scripts\python.exe main.py --group Q01_NAME --timeout 30 --headless

# Chạy toàn bộ 69 test cases (Full Run)
.\.venv\Scripts\python.exe main.py --timeout 30 --headless
```

## 5. Dọn dữ liệu thử nghiệm sau khi chạy
`cleanup.py` mặc định chỉ chạy chế độ **dry-run** và chỉ xóa các Quiz mang tên thử nghiệm (`f4_*`, `Q`, `Q7`) trong `course=2` bằng API chính thức `course_delete_module()` của Moodle:
```powershell
.\.venv\Scripts\python.exe cleanup.py results\run_<timestamp>
.\.venv\Scripts\python.exe cleanup.py results\run_<timestamp> --apply
# Hoặc dọn toàn bộ Quiz tiền tố thử nghiệm trong course=2:
.\.venv\Scripts\python.exe cleanup.py --by-prefix --apply
```

## 6. Xử lý lỗi phổ biến
- **`TimeoutException` khi tải trang trên Windows Docker:** Tăng `--timeout 45` hoặc `--timeout 60`.
- **Sai khác `TC-004-007` (`Name` 1.334 ký tự):** Trên Moodle 5.1.9 thực tế, `<input id="id_name">` không có thuộc tính HTML `maxlength="1333"` mà dùng QuickForm JS validation (`Maximum of 1333 characters`). Script giữ nguyên Expected Result gốc của Project #2 và ghi nhận kết quả trung thực.
- **Sai khác locator `Add 3 more feedback fields` (`TC-004-050..052`):** Moodle 5.1.9 đặt `name="boundary_add_fields"` (`id="id_boundary_add_fields"`) thay vì `name="addfeedbacks"` trong Katalon cũ.
