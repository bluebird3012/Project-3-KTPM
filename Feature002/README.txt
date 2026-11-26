Feature 002 – Create Course

Chuẩn bị

1. Cài Python 3, Chrome và mở PowerShell tại thư mục Feature002.
2. Cài Selenium.
   python -m pip install "selenium>=4.11,<5"
3. Mở Moodle test. Địa chỉ mặc định là http://127.0.0.1:9501.
4. Kiểm tra MOODLE_ADMIN_USERNAME và MOODLE_ADMIN_PASSWORD trong .env.
   Điền giá trị trực tiếp, bỏ dấu nháy bọc ngoài. Nếu mật khẩu trống,
   chương trình sẽ hỏi ở terminal.

Chạy các bộ test

    python .\run.py Level1
    python .\run.py Level2
    python .\run.py NonFunctional

Thêm --dry-run để xem các ca mà không mở Chrome. Dùng --base-url nếu
Moodle chạy ở địa chỉ khác. Xem README trong từng thư mục để chọn ca
hoặc cấu hình riêng.

Các lượt Selenium ghi kết quả vào results/ trong thư mục của bộ test.
