# Project #3 — Feature 001: Add New User (Moodle)

Bộ kiểm thử tự động cho chức năng tạo tài khoản trên Moodle, kế thừa 160 test case của Project #2 (103 BVA, 42 ECP, 8 Decision Table, 7 Use Case). Chỉ chạy trên Moodle local thử nghiệm do nhóm quản lý.

## 1. Cấu trúc

```text
Project3/
├── Feature001_Level1/          # Data-driven testing: dữ liệu và Expected Result trong CSV
├── Feature001_Level2/          # Level 1 + URL, locator, testing items trong CSV
├── Feature001_NonFunctional/   # NFR-01 Performance, NFR-02 Accessibility
└── README.md                  # Hướng dẫn chung cho Feature 001
```

Level 1 và Level 2 có chung 160 ID, 11 nhóm và cùng bộ dữ liệu CSV:

| Nhóm | Nội dung | Số ca |
|---|---|---:|
| F01_CORE | Username, password, first name, last name, email | 48 |
| F02_TEXT | Trường văn bản bổ sung | 64 |
| F03_RICH | Description / Rich Text Editor | 6 |
| F04_IMAGE | Upload ảnh đại diện | 10 |
| F05_TAG | Interests / tags | 4 |
| F06_FLAGS | Checkbox / decision table | 16 |
| F07_SELECT | Dropdown | 7 |
| F08_DUP | Duplicate username | 1 |
| F09_CANCEL | Cancel form | 2 |
| F10_RECOVER | Recovery sau validation error | 1 |
| F11_DENY | Access control | 1 |
| **Tổng** | | **160** |

## 2. Chuẩn bị môi trường

- Ubuntu/Linux, Python 3.12 hoặc 3.13 khuyến nghị (3.14.4 đã dùng ở lần chạy Accessibility), Google Chrome/Chromium và Docker chạy Moodle tại `http://127.0.0.1:9502`.
- Tài khoản Admin của Moodle test, giao diện tiếng Anh; giữ cấu hình password policy và dữ liệu nền nhất quán với Project #2.
- Mỗi thư mục test có môi trường Python riêng. Không dùng lại `.venv` trong ZIP từ máy khác; giải nén mã nguồn không kèm môi trường cũ (hoặc đổi tên môi trường cũ) rồi tạo mới.

Từ thư mục Project3, vào một trong ba thư mục test ở mục 1 rồi thực hiện:

```bash
cd Feature001_Level1              # Hoặc Feature001_Level2 / Feature001_NonFunctional
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
test -f .env || cp .env.example .env
nano .env
```

Cấu hình chung trong `.env` (thay bằng thông tin tài khoản test):

```dotenv
MOODLE_BASE_URL=http://127.0.0.1:9502
MOODLE_ADMIN_USERNAME=admin
MOODLE_ADMIN_PASSWORD=REPLACE_WITH_TEST_ADMIN_PASSWORD
```

Selenium Manager có thể cần Internet để chuẩn bị ChromeDriver lần đầu. Không commit hoặc chia sẻ `.env` chứa mật khẩu.

## 3. Functional Testing — Level 1 và Level 2

Chạy trong thư mục level tương ứng, sau khi kích hoạt `.venv`:

```bash
python -m unittest discover -s tests -v       # Kiểm tra logic offline
python main.py --dry-run                     # Kiểm tra CSV và danh sách ca
python main.py --case TC-001-001 --timeout 30
python main.py --group F04_IMAGE --timeout 30
python main.py --timeout 30                  # Toàn bộ 160 ca
```

Mặc định đăng nhập tự động, Chrome hiển thị. Thêm `--headless` để chạy ẩn; `--manual-login` dùng khi cần đăng nhập thủ công. Có thể lặp `--case` hoặc `--group` để chọn nhiều ca/nhóm.

- **Level 1:** `data/f*.csv` chứa input, Expected Result và semantic target; `pages/` chứa Page Objects và locator; `test_groups/` chứa workflow; `core/` phụ trách browser, dữ liệu, precondition, runner và reporter.
- **Level 2:** giữ nguyên CSV và workflow, bổ sung 82 testing item trong `config/testing_items.csv` (item_name, item_type, item_value), được kiểm tra bởi `core/testing_items.py`. Ví dụ có thể đổi `SUBMIT_ID,id,id_submitbutton` thành `SUBMIT_ID,css,#id_submitbutton` rồi chạy lại mà không sửa Python.

### Tiền điều kiện và lưu ý khi chạy lại

Mặc định 153 ca READY, 7 ca blocked trên dry-run khi chưa có fixture:

| Test case | Điều kiện bổ sung |
|---|---|
| TC-001-006 | Katalon gốc thiếu submit; chỉ dùng `--repair-missing-submit` sau khi xác nhận. |
| TC-001-121, 122 | User nền có email `f1_existing@example.com`, Moodle từ chối email trùng; thêm `--include-fixtures`. |
| TC-001-098–100 | Widget có giới hạn ảnh hữu hạn M byte; đặt `MOODLE_IMAGE_MAX_BYTES=M` trong .env, chạy `python fixtures/make_size_fixtures.py M` (thay M bằng số byte thực tế). Nếu Unlimited, không áp dụng biên hữu hạn. |
| TC-001-159 | Tài khoản thường không có quyền `moodle/user:create`; đặt `MOODLE_RESTRICTED_USERNAME`, `MOODLE_RESTRICTED_PASSWORD`. |

Có thể phát sinh SKIP khác nếu điều kiện runtime không đáp ứng. Các ảnh mẫu trong `fixtures/images/` được upload tự động. F04 phân biệt generic file icon với thumbnail ảnh, không coi timeout là bằng chứng file bị từ chối. Những thay đổi oracle hoặc khác biệt với Katalon được rà soát qua `data/review_*.csv`; các trường hợp maxlength phải phản ánh hành vi nhập liệu thực tế, không ép vượt giới hạn bằng JavaScript.

**Quan trọng:** các username gốc phần lớn cố định; run ID chỉ hỗ trợ dữ liệu động ở những ca đã thiết kế. Trước khi chạy lại Level 1 hoặc chuyển sang Level 2, khôi phục snapshot Moodle test phù hợp hoặc dọn đúng tài khoản đã xác minh do ca test tạo; không xóa Admin, Guest, fixture hoặc dữ liệu người khác. Level 1/2 không có cleanup tự động; `cleanup_candidates.csv` chỉ là danh sách ứng viên, không phải bằng chứng tài khoản tồn tại.

### Kết quả Functional

Mỗi lần chạy tạo `results/run_<timestamp>_<run_id>_<execution_id>/`: `summary.csv`, `all_results.csv`, `run_info.json` và thư mục từng nhóm chứa kết quả, ảnh, traceback, cleanup candidates. Level 2 ghi thêm SHA-256 của testing_items.csv. PASS/FAIL phản ánh oracle đã đặt; ERROR là lỗi thực thi; SKIP là thiếu tiền điều kiện; not_recorded là ca chưa được ghi nhận. Offline tests không thay thế kết quả thực tế.

## 4. Non-functional Testing

Vào `Feature001_NonFunctional/`, kích hoạt môi trường riêng và cài `requirements.txt` như mục 2. File này đã gồm Locust, Requests, BeautifulSoup, python-dotenv và Selenium; không cần file requirements-accessibility riêng.

### NFR-01 — Performance Testing (Locust)

Bổ sung `MOODLE_WEB_CONTAINER` trong .env bằng tên container PHP webserver thực tế (kiểm tra bằng `docker ps --format '{{.Names}}'`, ví dụ `demo-webserver-1`). Nếu bridge không tự tìm được config.php, đặt `MOODLE_CONFIG_PATH` đúng đường dẫn trong container.

```bash
python check_environment.py
python -m performance.run_performance --smoke
python -m performance.run_performance
```

Formal run: 1, 5, 10, 20 virtual users; 60 giây tải/lượt, 3 lượt/mức (12 lượt). Locust gửi POST tạo user với dữ liệu riêng theo lượt; Moodle CLI audit xác minh bản ghi. Tiêu chí cho từng lượt: Mean ≤ 2.000 ms, P95 ≤ 5.000 ms, Error Rate ≤ 1%, không trùng tài khoản; PASS toàn bộ khi cả 12 lượt PASS. Chạy tuần tự, không chạy cùng bộ Selenium; thời gian thực tế dài hơn 12 phút do setup/audit.

Kết quả: `results/performance/<run-id>/`, gồm summary.csv, run_info.json và log/audit từng lượt. Sau khi lưu minh chứng, xem trước cleanup bằng `python cleanup.py results/performance/<run-id>` (thay run-id); chỉ thêm `--apply` khi đã xác nhận đúng các tài khoản thử nghiệm được ghi nhận trong lần chạy đó. Không dùng cleanup này cho Level 1/2.

### NFR-02 — Accessibility Testing (Selenium + axe-core)

Chỉ cần ba biến .env chung; không cần Student/Teacher, course, Moodle CLI audit hoặc tạo user hợp lệ.

```bash
python -m unittest discover -s tests -p 'test_accessibility*.py' -v
python -m accessibility.run_accessibility
# Hoặc hiển thị Chrome để quan sát:
python -m accessibility.run_accessibility --headed --timeout 45
```

Runner revision `2-scroll-click-fix` tự đăng nhập, tải hoặc dùng cache axe-core 4.10.3 đã kiểm tra hash, thực hiện click WebDriver có explicit wait và retry. Nếu không có cache, lần đầu cần Internet đến npm; có thể cấp file chính thức bằng `--axe-js /path/to/axe.min.js`.

| ID | Kịch bản |
|---|---|
| ACC-01 | Audit form mặc định |
| ACC-02 | Audit các section mở rộng |
| ACC-03 | Audit trạng thái lỗi validation khi submit form trống |
| ACC-04 | Tiếp cận 5 phần tử đích bằng Tab từ Username |
| ACC-05 | Kiểm tra liên kết của lỗi validation quan sát được |

Tiêu chí: 0 vi phạm WCAG critical/serious hoặc thuộc nhóm quy tắc trọng yếu (name, label, contrast…); 5/5 đích Tab; ít nhất một lỗi quan sát được và 100% lỗi đó có liên kết phù hợp hoặc thông báo native. Blocking incomplete không phải violation đã xác nhận. FAIL nếu có ca FAIL; PASS khi cả 5 PASS; còn lại INCONCLUSIVE. Audit tự động không chứng nhận tuân thủ WCAG đầy đủ.

Kết quả: `results/accessibility/<run-id>/`, gồm `summary.csv`, `findings.csv`, `run_info.json`, JSON và ảnh của ACC-01–05.

**Security Testing bổ sung:** thư mục `security/` vẫn được giữ nhưng không phải NFR-02 chính thức. Chỉ chạy `python -m security.test_security` nếu có nhu cầu, sau khi chuẩn bị tài khoản Student/Teacher test có role tương ứng và không có quyền tạo user; cấu hình theo .env.example.

## 5. Kết quả thực nghiệm dùng trong báo cáo

| Hạng mục | Kết quả chính thức | Run ID / thư mục |
|---|---|---|
| Level 1 | 139 PASS, 13 FAIL, 1 ERROR, 7 SKIP / 160 | run_20261124T060555Z_11240605b8f3_211bc43d |
| Level 2 | 142 PASS, 9 FAIL, 2 ERROR, 7 SKIP / 160 | run_20261124T064022Z_11240640b591_8edf650b |
| NFR-01 | FAIL: 7/12 lượt PASS, 5/12 FAIL | 20261124T072424Z_91504fda1a2c |
| NFR-02 | FAIL: 2 PASS, 1 FAIL, 2 INCONCLUSIVE / 5 | 20261126T053537Z_b5e8223733d3 |

Accessibility: ACC-02 có một violation WCAG critical (`aria-required-children`); ACC-01 và ACC-03 còn blocking incomplete; ACC-04 đạt 5/5 đích sau 37 Tab; ACC-05 liên kết đúng 3/3 thông báo lỗi quan sát được. Không quy kết mọi lỗi chạy Selenium thành bug Moodle, không điều chỉnh tiêu chí để ép PASS.

Báo cáo Project #3: [Google Docs](https://docs.google.com/document/d/1CezKTCrhhd6WGIAJLWoaHETAvrwWO_4Sd_YRMItIeU8/edit?tab=t.0).

Khi nộp, giữ Python, CSV, fixture cần thiết và minh chứng formal; loại bỏ .env, .venv, .idea, __pycache__ và thông tin nhạy cảm. Không nộp .krecorder thay mã nguồn automation. Khai báo AI Usage trung thực theo quy định môn học, gồm cả phần AI hỗ trợ sinh code, refactor, review và viết báo cáo nếu có.
