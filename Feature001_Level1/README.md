# Project #3 — Feature 001 — Level 1 (all 160 cases)

## Chạy nhanh bản đầy đủ F01–F11

- `python main.py --dry-run`: kiểm tra đủ 160 test case; mặc định 153 READY, 7 blocked nếu chưa chuẩn bị fixture.
- `python main.py --group F03_RICH --group F04_IMAGE --group F05_TAG --group F06_FLAGS --group F07_SELECT --group F08_DUP --group F09_CANCEL --group F10_RECOVER --group F11_DENY`: chạy 48 ca mới, không chạy lại F01/F02.
- `python main.py --case TC-001-096`: chạy thử upload một PNG.
- `python main.py --group F04_IMAGE`: chạy nhóm upload, bao gồm các ca kiểm tra không submit.
- `python main.py`: chạy cả 11 nhóm; mỗi nhóm có phiên WebDriver riêng.
- `python test_core_fields.py`: lệnh tương thích chỉ chạy F01.
- `python -m unittest discover -s tests -v`: kiểm tra offline.

Xem `F03_F11_NOTES.md` để chuẩn bị finite M và tài khoản hạn chế cho F11. Không cần tự chọn ảnh khi chạy Selenium: các ảnh mẫu nhỏ đã nằm ở `fixtures/images/`. Cần cấu hình `.env` trên máy; không gửi mật khẩu. Nếu chạy lại, dọn đúng tài khoản tạo trong lần trước. Không có kết quả Selenium mới được tạo sẵn.

## Phạm vi và nguồn dữ liệu F01_CORE (giữ nguyên)

- 48 test case, gồm Username (12), New password (11), Email (9), First name (8), Surname (8).
- Giữ nguyên các ID `TC-001-001` đến `TC-001-029`, `TC-001-104` đến `TC-001-107` và `TC-001-109` đến `TC-001-123` được chọn từ file Katalon gốc `Feature1-Add-New-User.krecorder`.
- File `data/f01_core.csv` chứa input và Expected Result thực tế được trích từ lệnh Katalon. Giá trị Katalon `f1_${run}_NNN@example.com` được chuyển thành `f1_{run_id}_NNN@example.com` để có email duy nhất theo lượt chạy. Đây là thay đổi có chủ đích; username gốc không bị thay đổi.
- Một entry point `main.py` đọc tuần tự CSV, nhập biểu mẫu và so sánh với Expected Result trong mỗi hàng. ID, bước kiểm chứng và kết quả được ghi riêng từng ca.
- **Các kết quả trong `results/` là lịch sử từ gói gốc, chưa phải kết quả sau refactor. Chưa chạy Selenium trên Moodle của người dùng sau refactor.**

## Chuẩn bị trên Ubuntu

Dùng Python 3.10+ và Google Chrome đã cài trên máy. Tại thư mục chứa file:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py --dry-run
```

Đảm bảo Docker Moodle đang hoạt động tại `http://127.0.0.1:9502/`, giao diện tiếng Anh và tài khoản Admin có quyền tạo user. Giữ **password policy tắt** như Project #2; script không thay đổi cấu hình Moodle.

## Chạy thử một test case

Cách 1: đăng nhập thủ công trong cửa sổ Chrome mà Selenium mở:

```bash
python main.py --case TC-001-001 --manual-login
```

Cách 2: sử dụng thông tin tài khoản do bạn cung cấp qua biến môi trường. Không lưu mật khẩu trong code, file CSV hoặc báo cáo:

```bash
export MOODLE_BASE_URL=http://127.0.0.1:9502
export MOODLE_ADMIN_USERNAME=admin
export MOODLE_ADMIN_PASSWORD='your-test-admin-password'
python main.py --case TC-001-001
```

Thay `TC-001-001` bằng `TC-001-002` để kiểm tra một ca thành công. **Lưu ý:** ca thành công tạo dữ liệu thật trong hệ thống test.

## Chạy toàn nhóm F01_CORE

Sau khi chuẩn bị dữ liệu và snapshot của Moodle test:

```bash
python main.py --group F01_CORE
```

Mặc định, script thực thi 45 test case và **SKIP 3 ca** chưa đủ điều kiện để thực thi đáng tin cậy:

- `TC-001-006` thiếu lệnh submit trong Katalon gốc. Chỉ để thử một cách sửa tường minh: `--repair-missing-submit` (vẫn giữ Expected Result lỗi DB gốc, không coi đó là chuẩn hợp lý).
- `TC-001-121`, `TC-001-122` yêu cầu một user **đã tồn tại** với email `f1_existing@example.com`; trước khi chạy hai ca này cần tạo fixture và kiểm tra cấu hình Moodle từ chối trùng email. Sau đó truyền `--include-fixtures`.

Có thể chọn nhiều ca:

```bash
python main.py --case TC-001-001 --case TC-001-002 --manual-login
```

Các flag `--headless` (chỉ cho đăng nhập tự động), `--timeout 20`, `--results-dir ...` là tùy chọn.

## Kết quả kiểm thử

Mỗi lần chạy thật tạo một thư mục `results/run_<UTC>_<run_id>_<execution_id>/` riêng, kể cả khi chạy một nhóm hoặc một test case. Không ghi đè lịch sử khi dùng lại `--run-id`. `--dry-run` không tạo thư mục kết quả.

```text
results/run_<UTC>_<run_id>_<execution_id>/
├── summary.csv
├── all_results.csv
├── run_info.json
├── F01_CORE/
│   ├── results.csv
│   ├── cleanup_candidates.csv
│   ├── run_info.json
│   ├── screenshots/
│   └── tracebacks/
├── F02_TEXT/
└── ...
```

- `summary.csv`: số ca được chọn, PASS / FAIL / ERROR / SKIP và `not_recorded` theo nhóm, có dòng TOTAL. `not_recorded` là số ca chưa ghi nhận kết quả khi lần chạy bị gián đoạn, không phải SKIP.
- `all_results.csv`: toàn bộ kết quả của lần chạy hiện tại, có thêm cột `group`; chỉ chứa các ca đã ghi nhận kết quả.
- `run_info.json`: thời gian bắt đầu/kết thúc UTC, nhóm được chọn, tổng số ca và trạng thái `complete` (đã ghi nhận đầy đủ, không đồng nghĩa tất cả PASS).
- Mỗi nhóm giữ `results.csv`, `run_info.json`, ảnh FAIL/ERROR, traceback và danh sách `cleanup_candidates.csv` (chỉ dùng để kiểm tra thủ công, không tự động xóa user).
- Tổng hợp được ghi khi CLI kết thúc hoặc thoát qua exception/KeyboardInterrupt; không đảm bảo ghi được nếu tiến trình bị kill cưỡng bức hoặc mất điện.

Chú ý: Selenium chỉ xác minh theo thông báo/lỗi UI có trong Katalon gốc. Đối với các ca mong đợi thành công, để tăng sức mạnh assertion cần bổ sung bước độc lập xác nhận user được lưu trong Browse list of users (chưa cài đặt trong gói này vì chưa kiểm chứng giao diện thực tế).

## Các vấn đề cần đánh giá lại

Bảng đầy đủ trong `data/review_f01.csv`.

1. `TC-001-006` không có click `id_submitbutton`; script không chạy ca này nếu chưa cho phép sửa một cách tường minh.
2. `TC-001-019`, `025`, `029` và `006` có Expected Result là `Error writing to database`. Gói này vẫn giữ Expected Result Katalon để truy vết; PASS theo legacy assertion **không đồng nghĩa** hệ thống xử lý biên an toàn.
3. `TC-001-111` đến `114` đòi lỗi mật khẩu thiếu thành phần trong khi password policy tắt; nếu Moodle chấp nhận, đó là mâu thuẫn giữa Expected Result và cấu hình, cần ghi nhận và đối chiếu Project #2, không tự ý bật password policy.
4. `TC-001-013` có locator `id_error_newpassword` thiếu `id=` trong Katalon; đã chuẩn hóa thành `id=id_error_newpassword` và đánh dấu trong CSV.
5. Các username gốc là giá trị cố định, nên **chạy lại trên database cũ có thể gây trùng user**. `run_id` mới chỉ tránh trùng email tạo tự động, không giải quyết trùng username.

## Setup / teardown và cleanup dữ liệu

- Setup tự động: khởi tạo WebDriver, đăng nhập Admin hoặc chờ đăng nhập thủ công, mở form kiểm thử.
- Teardown tự động: đóng WebDriver và xuất báo cáo kết quả, kể cả khi có FAIL/ERROR.
- **Không tự động xóa user**: trong một site Moodle đang dùng chung, xóa user theo username sẽ có rủi ro phá hủy dữ liệu ngoài ý muốn.
- Cách an toàn nhất để chạy lại: sử dụng **riêng bản Moodle test**, sao lưu trạng thái nền trước khi chạy, và khôi phục snapshot để reset dữ liệu. Với repository Docker demo, có thể dùng `bin/backup`/`bin/restore` theo README của repo, sau khi chắc chắn không có dữ liệu cần giữ. Nếu không có snapshot, vào phần quản trị Moodle để kiểm tra và dọn đúng những tài khoản do bộ test tạo (đối chiếu `cleanup_candidates.csv`) trước khi chạy lại.

## Phạm vi Level 1 so với Level 2

Level 1: dữ liệu và Expected Result ở CSV; Selenium locator như `id_username`/`id_submitbutton` nằm trong Python.

Level 2 (chưa thực hiện): sẽ thêm file cấu hình chứa URL, locator, element type và các trường tương tác, tách ra khỏi code. Không nên nhầm gói này là Level 2.

## Quy định nộp bài và AI Usage Declaration

Đề Project #3 yêu cầu nộp các file Python + CSV/XLS, không nộp `.krecorder`. Báo cáo PDF phải có AI Usage Declaration phản ánh đúng công cụ, prompt và review/suggestions đã sử dụng. Đề bài mô tả phạm vi hỗ trợ AI là code review; nếu dùng AI để tạo mã như trong gói này, cần xin xác nhận giảng viên về sự phù hợp với quy định và khai báo trung thực.

## Bản vá Selenium: ElementClickInterceptedException (24/11/2026)

Bản vá này chỉ chỉnh hành vi nhấp nút (password toggle và Create user), không thay
đổi dữ liệu CSV/Expected Result. Trước khi nhấp, script cuộn nút vào vùng nhìn thấy
(`scrollIntoView`) và dùng explicit wait kiểm tra khả năng nhấp; nếu bị che, thử các
vị trí cuộn khác và báo phần tử che ở cuối log. Không dùng JavaScript để ép nút
submit nhận click vì như vậy không còn mô phỏng thao tác thực của người dùng.

Nếu test vẫn ERROR, xem:

- `results/run_.../F01_CORE/tracebacks/TC-001-001.txt`: đầy đủ stacktrace và thông tin che nút.
- `results/run_.../F01_CORE/screenshots/TC-001-001.png`: ảnh màn hình khi lỗi.

Chạy thử lại: `python main.py --case TC-001-001 --manual-login`.
Chưa thể xác nhận patch chạy thành công trên localhost của bạn; cần kết quả Selenium
trên máy bạn để kết luận.

## Cập nhật 24/11/2026 — Đăng nhập Moodle tự động

Bản này dùng các ID từ ảnh HTML bạn cung cấp: `username`, `password`, `loginbtn`.
Script bắt đầu từ trang chủ, nhấn liên kết `Log in` nếu tìm thấy, nhập tài khoản,
nhấn nút `Log in`, chờ đăng nhập hoàn tất rồi xác nhận mở được `Add New User`.
Không cần `--manual-login` nữa khi đã cấu hình tài khoản.

**Thiết lập một lần** (không cần lưu mật khẩu trong mã nguồn hoặc CSV):

```bash
cp .env.example .env
nano .env
```

Thay `REPLACE_WITH_TEST_ADMIN_PASSWORD` bằng mật khẩu thật của tài khoản Admin
trong Moodle test trên máy bạn, lưu tệp. `.env` đã được liệt kê trong `.gitignore`;
không tải tệp này lên GitHub hoặc gửi cho người khác.

**Chạy tự động**:

```bash
python main.py --case TC-001-001
```

Dùng `--manual-login` nếu muốn tự đăng nhập. Mọi biến môi trường được export
trong terminal sẽ ưu tiên hơn giá trị trong `.env`.

Bộ kiểm thử vẫn giữ nguyên 48 dòng CSV và Expected Result. Việc đăng nhập chỉ
là bước setup, không được tính thành một test case mới. Chưa xác nhận chạy thành công
trên máy cục bộ của người dùng từ môi trường tạo gói.


## Cấu trúc sau refactor

- `main.py`: CLI chung hỗ trợ cả 11 nhóm; chọn nhóm bằng `--group`.
- `core/`: config, CSV loader, Selenium helpers, runner và reporter.
- `pages/`: LoginPage, AddUserPage và locator Python.
- `test_groups/`: luồng F01_CORE, F02_TEXT và F03–F11, dùng chung assertion.
- `test_core_fields.py`: entry point tương thích lệnh cũ.
- `data/f01_core.csv`: `expected_target` và `target` trong pre-submit checks là tên logic; ánh xạ chính xác về locator gốc tại `pages/locators.py`.
- `results/`: giữ lịch sử gốc, không phải kết quả của bản refactor.

Kiểm tra offline: `python -m unittest discover -s tests -v`.

Không sửa test FAIL/SKIP, Expected Result, chính sách mật khẩu, cleanup hoặc logic Selenium. Level 2 chưa triển khai; F03–F11 đã có mã nhưng chưa chạy trên Moodle thực tế.
