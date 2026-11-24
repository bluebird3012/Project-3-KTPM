# Project #3 — Feature 001 – Add New User — Level 2

Bản độc lập được chuyển đổi từ `Feature001_Level1.zip` mới nhất do người thực hiện cung cấp. Giữ nguyên 160 test case, dữ liệu đầu vào, Expected Result, precondition, các luồng F01–F11 và cách phân loại PASS/FAIL/ERROR/SKIP. Không có kết quả Selenium thực tế mới trong gói này.

## 1. Khác biệt so với Level 1

- Level 1: test data và Expected Result nằm trong CSV, URL mặc định, page path và locator nằm trong Python (base URL có thể override qua môi trường).
- Level 2: tái sử dụng toàn bộ CSV test data, tách 82 testing items sang `config/testing_items.csv`. File có 3 cột `item_name,item_type,item_value`. `core/testing_items.py` đọc và kiểm tra cấu hình khi khởi động, `pages/locators.py` giữ tên logic và mapping target, không chứa giá trị locator Moodle cố định. `item()` trả tuple Selenium, nên có thể thay cả chiến lược và giá trị locator. Không có fallback locator hardcode.

Ví dụ (đoạn trích file cấu hình, các giá trị CSV có dấu phẩy hoặc dấu ngoặc kép cần được escape theo CSV):

```csv
item_name,item_type,item_value
BASE_URL,url,http://127.0.0.1:9502
CREATE_USER_PATH,path,/user/editadvanced.php?id=-1
FIELD_IDS.username,id,id_username
SUBMIT_ID,id,id_submitbutton
VERIFICATION.success_message,css,div.alert-success[role='alert']
```

Ví dụ code:

```python
click_visible(self.browser, *L.item('SUBMIT_ID'), self.timeout, 'Create user')
```

Để thay selector nút tạo user sang CSS tương đương, sửa duy nhất dòng `SUBMIT_ID,id,id_submitbutton` thành `SUBMIT_ID,css,#id_submitbutton`. Restart script để đọc cấu hình mới. Verification `create_button` dùng chung item này. Các kiểm tra trước submit với field đã có cũng dùng chung item đầu vào. Nếu thay đổi layout/URL thật, rà soát các selector liên quan như LOGIN_LINK và LOGIN_PREFIX; không cần sửa logic Python nếu workflow không đổi.

Các item hỗ trợ `id`, `css`, `xpath`, `name`, `class`, `tag`, `link_text`, `partial_link_text`, `url`, `path`, `token`. `path` là đường dẫn tương đối với base URL; `token` là đoạn nhận diện phụ thuộc UI/URL (ví dụ hậu tố iframe hoặc ảnh preview). `BASE_URL` trong CSV là giá trị mặc định; biến môi trường hoặc `.env` có thể override; `--base-url` ưu tiên cao nhất. Mật khẩu luôn ở `.env` hoặc biến môi trường, không đặt trong CSV.

## 2. Cấu trúc

```text
Feature001_Level2/
├── main.py
├── config/testing_items.csv
├── core/                 # Loader, browser, runner, reporter, config
├── pages/                # Page Objects + logical item mapping
├── test_groups/          # 11 workflows trong 3 Python modules
├── data/                 # 11 CSV thực thi và review CSV từ Level 1
├── fixtures/             # Ảnh mẫu và script sinh ảnh biên
├── tests/                # Offline tests, gồm config-driven checks
├── .env.example
├── requirements.txt
└── results/              # Tạo tự động khi chạy
```

Các file `*_NOTES.md` là ghi chú lịch sử triển khai Level 1, giữ lại làm tài liệu đối chiếu; các hướng dẫn Level 1 trong đó không phải mô tả trạng thái Level 2.

## 3. Cài đặt và chạy

Dùng Ubuntu, Python 3.10+ và Chrome. Moodle phải đang hoạt động. Giải nén riêng, không chép đè project Level 1.

```bash
cd Feature001_Level2
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
# Chỉnh credentials của Moodle trong .env hoặc dùng lại .env từ Level 1.
python -m unittest discover -s tests -v
python main.py --dry-run
```

Dọn các tài khoản test cũ trước khi chạy thực tế, giữ Admin, Guest, các fixture và tài khoản không có quyền tạo user. Không xóa toàn bộ bảng MariaDB; cleanup_candidates.csv chỉ là danh sách ứng viên cần kiểm tra, không chứng minh tài khoản đã được tạo. Chưa triển khai cleanup tự động. Giữ cấu hình Moodle nhất quán với Level 1.

```bash
python main.py --case TC-001-001 --timeout 30
python main.py --group F04_IMAGE --timeout 30
python main.py --timeout 30 2>&1 | tee execution.log
```

Chạy headless bằng `--headless`; chọn nhiều nhóm hoặc ca bằng cách lặp `--group` / `--case`. Nếu chạy thử từng ca, dọn dữ liệu do chúng tạo trước khi chạy toàn bộ. Các lệnh cũ (`python test_core_fields.py`) vẫn chạy F01_CORE.

## 4. Tiền điều kiện (như Level 1)

Mặc định 153 READY, 7 blocked. TC-001-006 thiếu submit trong Katalon gốc, chỉ dùng `--repair-missing-submit` sau khi xác nhận. TC-001-121,122 cần tài khoản nền có email `f1_existing@example.com`, sau khi tạo mới dùng `--include-fixtures`. TC-001-098–100 cần giới hạn ảnh hữu hạn M thực tế trên Moodle, `python fixtures/make_size_fixtures.py M` (thay M bằng số byte), và `MOODLE_IMAGE_MAX_BYTES=M` trong `.env`. Nếu UI vẫn Unlimited thì không áp dụng biên hữu hạn. TC-001-159 cần tài khoản thường không có `moodle/user:create`, đặt `MOODLE_RESTRICTED_USERNAME`, `MOODLE_RESTRICTED_PASSWORD` trong `.env`. Không chỉnh Expected Result hay môi trường chỉ để đạt PASS.

## 5. Kết quả và kiểm tra offline

Mỗi lượt chạy tạo một thư mục `results/run_...` riêng với `summary.csv`, `all_results.csv`, `run_info.json` và thư mục theo nhóm. run_info.json cấp lượt chạy có `level=2` và SHA-256 của testing_items.csv đã nạp. Các tệp cùng schema với Level 1 để đối chiếu. Không tái sử dụng kết quả Level 1 như kết quả Level 2.

Offline checks bao gồm 29 test cũ và 3 test mới xác nhận loader, lỗi cấu hình và thay đổi CSV tác động đến thao tác/verification bằng mock. Kết quả offline không chứng minh Moodle thực tế PASS. Không đóng gói lịch sử kết quả, `.env`, `.venv` hoặc mật khẩu.
