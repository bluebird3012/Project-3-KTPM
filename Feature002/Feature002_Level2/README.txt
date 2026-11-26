Level 2 – Create Course

Cài Selenium và cấu hình .env theo README ở thư mục Feature002.
Chạy các lệnh sau từ thư mục Feature002.

    python .\run.py Level2 --dry-run
    python .\run.py Level2
    python .\run.py Level2 --case TC-002-006 --case TC-002-022

Dữ liệu test nằm trong create_course_cases.csv. Sửa base_url trong
moodle_config.json để đổi địa chỉ Moodle hoặc dùng --base-url cho một lượt.
Dùng --config nếu cần chọn file cấu hình khác.
