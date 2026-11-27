# Project #3 – Feature 004 (Add Quiz) – Level 2

Gói độc lập triển khai **Level 2 Data-Driven Testing với Externalized Testing Items** cho toàn bộ **69 test cases** (`TC-004-001` đến `TC-004-069`) của Feature 004 – Add Quiz trên Moodle LMS 5.1.x.

## 1. Khác biệt cốt lõi so với Level 1
- **Giữ nguyên 100%:** 69 Test Case ID, 7 tệp `data/q01..q07.csv`, 7 nhóm luồng thực thi (`Q01_NAME`..`Q07_USECASE`), logic xác minh và cấu trúc Unified Results.
- **Tách hoàn toàn Testing Items ra ngoài mã Python:** Toàn bộ URL, đường dẫn trang, token nhận diện và mọi locator (`id`, `css`, `xpath`) đều nằm trong `config/testing_items.csv` (3 cột: `item_name,item_type,item_value`).
- **Kiểm tra cấu hình nghiêm ngặt (`core/testing_items.py`):** Chặn trùng key, giá trị rỗng, chiến lược không hợp lệ, URL/path sai định dạng; khóa bất biến bằng `MappingProxyType`; **nghiêm cấm fallback sang locator hardcode**; tính `SHA-256` của `config/testing_items.csv` và ghi vào `run_info.json` (`level=2`, `testing_items_file`, `testing_items_sha256`).

## 2. Cài đặt & Chạy trên Windows 11 (PowerShell)
```powershell
cd Feature004_Level2
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env

# Kiểm tra offline (gồm chống hardcode & mock đổi locator)
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

# Dry-run 69 ca
.\.venv\Scripts\python.exe main.py --dry-run

# Chạy 1 ca hoặc toàn bộ 69 ca
.\.venv\Scripts\python.exe main.py --case TC-004-004 --timeout 45 --headless
.\.venv\Scripts\python.exe main.py --timeout 45 --headless
```

## 3. Minh chứng thay đổi Testing Items không sửa Python
Chỉ cần sửa đúng 1 dòng trong `config/testing_items.csv`:
- Trước: `SUBMIT_RETURN_BUTTON,id,id_submitbutton2`
- Sau: `SUBMIT_RETURN_BUTTON,css,input[name='submitbutton2']`

Chạy lại `main.py --case TC-004-004` mà không chỉnh bất kỳ tệp `.py` nào → mã `testing_items_sha256` trong `run_info.json` thay đổi và test vẫn PASS.

## 4. Dọn dữ liệu thử nghiệm
```powershell
.\.venv\Scripts\python.exe cleanup.py results\run_<timestamp> --apply
.\.venv\Scripts\python.exe cleanup.py --by-prefix --apply
```
