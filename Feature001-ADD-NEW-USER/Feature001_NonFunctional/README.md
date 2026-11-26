# Feature 001 – Non-functional Testing (Project #3)

Bộ kiểm thử độc lập cho Moodle local của nhóm. Không thay đổi Level 1/2. Chỉ dùng trên instance Moodle thử nghiệm do bạn quản lý, không dùng trên hệ thống thật. Mọi tài khoản sinh ra có namespace riêng `nfr<12 hex>_<16 hex>` và email `username@example.invalid`. Không dùng tài khoản của người thật. Không khai báo PASS trên Moodle trước khi chạy thực tế.

## 1. Chuẩn bị

- Ubuntu, Docker đang chạy Moodle (webserver và database); URL mặc định `http://127.0.0.1:9502`.
- Python 3.12/3.13 khuyến nghị (Python 3.14 có thể dùng nếu cài được Locust/gevent); PHP CLI trong container Moodle.
- Tài khoản site administrator trên instance thử nghiệm. Giao diện tiếng Anh để kiểm chứng alert `Changes saved`.
- Hai tài khoản test riêng, enrolled vào một course thử nghiệm với role Student và Teacher (Teacher hoặc Non-editing teacher); không cấp `moodle/user:create` ở system context. Không dùng Admin cho các fixture này. Nếu thiếu fixture, các ca liên quan SKIP, không tính PASS.

```bash
cd Feature001_NonFunctional
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Dùng `docker ps --format '{{.Names}}'` để tìm tên container webserver Moodle (không phải db). Điền vào `.env`:

```dotenv
MOODLE_BASE_URL=http://127.0.0.1:9502
MOODLE_ADMIN_USERNAME=admin
MOODLE_ADMIN_PASSWORD=<test admin password>
MOODLE_WEB_CONTAINER=<webserver container name>
MOODLE_STUDENT_USERNAME=<test student>
MOODLE_STUDENT_PASSWORD=<test password>
MOODLE_TEACHER_USERNAME=<test teacher>
MOODLE_TEACHER_PASSWORD=<test password>
```

Nếu không tự tìm được config.php, kiểm tra trong container:

```bash
docker exec <webserver-container> sh -lc 'find /var/www /opt -name config.php 2>/dev/null | head -40'
```

Đặt `MOODLE_CONFIG_PATH` là đường dẫn config.php của site (không phải config.php của plugin). CLI bridge kiểm tra `$CFG->wwwroot` đúng URL `.env`, dùng Moodle DB API để kiểm chứng độc lập, không cần thông tin đăng nhập database, không sửa DB khi audit. Nếu wwwroot khác do cấu hình Docker, dùng chính xác URL site đã cấu hình (chỉ localhost). Không đổi cấu hình Moodle để ép test PASS. User hiện tại phải có quyền Docker như khi sử dụng `docker ps`.

```bash
python -m unittest discover -s tests -v
python check_environment.py
```

## 2. NFR-01: Response time under concurrent user creation load

**Loại:** Performance / load testing. Locust chạy các phiên HTTP riêng, không dùng browser. Mỗi virtual user đăng nhập cùng tài khoản Admin với session riêng (không phải 20 tài khoản Admin khác nhau), lấy form mới và gửi POST tạo tài khoản duy nhất; wait time 1–2 giây giữa các task. Lấy logintoken, sesskey, QuickForm marker và hidden fields từ HTML thực tế. Preflight dùng requests để xác nhận tạo đúng một tài khoản và có alert thành công; nếu thất bại không chạy tải. Admin page phải cho phép tài khoản thử nghiệm dùng email `.invalid`; nếu site có hạn chế riêng, ghi nhận blocker thay vì sửa oracle.

```bash
python -m performance.run_performance --smoke
# Sau khi smoke thành công:
python -m performance.run_performance
```

`--smoke`: 1 virtual user, 10 giây, 1 repetition; chỉ kiểm tra tích hợp. Formal run: 1, 5, 10, 20 virtual users, 60 giây/mức/repetition, 3 repetitions = 12 lượt, spawn rate bằng user count, ramp-up nằm trong 60 giây. 2 giây nghỉ giữa lượt, audit ngoài cửa sổ tải. Load runner giới hạn 20 users, 60 giây, 3 repeats, tối đa 4 mức; chỉ localhost. Có thể chạy khoảng 12 phút tải cộng thời gian setup/audit, nhưng thời gian thực tế phụ thuộc máy. Dùng instance test có tài nguyên đủ; dừng bằng Ctrl+C nếu bất thường. Chạy các bộ test nối tiếp, không chạy song song với Level 1/2.

Tiêu chí do nhóm đề xuất (không phải SLA chính thức của Moodle), áp dụng mỗi repetition:
- Mean response <= 2000 ms; P95 <= 5000 ms.
- Error rate <= 1%; không có username trùng trong các lần POST hoặc nhiều record ứng với cùng username.
- Một POST được xem là thành công khi có alert `Changes saved` và audit tìm đúng một record với username/email tương ứng. Các lỗi chuẩn bị (login/form), POST không thành công, audit không khớp được tính là thất bại logic, không đếm hai lần cho cùng POST. Error rate = (số POST + setup errors − số POST thành công đã audit) / (số POST + setup errors). Nếu thiếu audit, thiếu POST, tiến trình bất thường hoặc có request chưa kết thúc, ghi INCONCLUSIVE; không coi là PASS.
- Mean/median/P95/max đo từ thời điểm gửi POST đến lúc nhận response cuối (bao gồm redirect đến trang danh sách user, không gồm GET form, login, HTML verification, audit hoặc wait time). P95 dùng nearest-rank trên các POST có thời gian ghi nhận, kể cả POST thất bại. `throughput_per_s` là số POST hoàn tất / wall time của subprocess (bao gồm startup/ramp/stop); `successful_per_s` là số POST thành công đã audit / cùng mẫu số. Locust raw stats cho từng endpoint gồm GET form và login riêng. Không dùng thời gian chạy Selenium để thay cho phép đo này.
- Kết quả tổng thể PASS chỉ khi tất cả 12 lượt PASS; nếu lượt thiếu bằng chứng thì INCONCLUSIVE, nếu ngưỡng vượt thì FAIL (INCONCLUSIVE được ưu tiên khi dữ liệu chưa đầy đủ).

## 3. NFR-02: Protection against unauthorized user creation

**Loại:** Security (authentication, authorization, CSRF, session invalidation). Chỉ thử trên local Moodle. Không dò mật khẩu, không thử trên remote site.

```bash
python -m security.test_security
```

10 kịch bản trong `security/security_cases.csv`. SEC-10 là đối chứng dương, chạy trước: gửi form hợp lệ với admin, có alert thành công và audit chính xác. Nếu đối chứng không đạt, toàn bộ negative cases SKIP. SEC-01–03 kiểm tra truy cập trang; SEC-04–09 gửi POST với trạng thái bảo mật tương ứng, sử dụng dữ liệu form hợp lệ từ phiên Admin và token thích hợp cho từng tình huống. SEC-05 dùng token của tài khoản bị giới hạn quyền. SEC-08 kiểm chứng logout trước khi dùng lại cookie cũ. SEC-09 dùng cookie giả. Trước mỗi POST, kiểm tra username chưa tồn tại; sau POST, audit độc lập để xác nhận có/không có record. Không coi HTTP 200 là thành công và không coi HTTP 403 là bằng chứng duy nhất. Nếu server/transport lỗi hoặc không có chứng cứ từ chối GET, ghi INCONCLUSIVE. Với negative POST có response không lỗi server và không tạo record, PASS trong phạm vi kịch bản này; không khẳng định hệ thống hoàn toàn không có lỗ hổng. Nếu record trái phép xuất hiện, FAIL kể cả response báo lỗi. Kết quả NFR PASS chỉ khi 9 negative cases và đối chứng dương đều PASS; có SKIP hoặc INCONCLUSIVE thì chưa đủ bằng chứng để đạt NFR.

Acceptance criteria: 0 tài khoản được tạo trái phép; 100% chặn 9 negative scenarios và positive control thành công. Không tính SKIP như PASS.

## 4. Kết quả và cleanup

```
results/
  performance/<timestamp>_<token>/
    run_info.json
    preflight.jsonl
    summary.csv
    u01_r1/ ... u20_r3/
      attempts.jsonl
      requests.csv
      audit.json
      locust_stats.csv, locust_failures.csv, locust_stats_history.csv
      locust.log
  security/<timestamp>_<token>/
    run_info.json
    results.csv
    attempts.jsonl
```

Các tệp có thể thiếu nếu quá trình dừng sớm; không tạo số liệu giả. `run_info.json` có trạng thái hoàn tất và kết luận. Giữ output terminal nếu có lỗi. Không gửi `.env` hay mật khẩu. Nén hai thư mục formal run (performance và security) riêng để làm báo cáo.

Cleanup là thao tác riêng, sau khi đã lưu minh chứng, mặc định chỉ dry-run:

```bash
python cleanup.py results/performance/<run-directory>
python cleanup.py results/performance/<run-directory> --apply
python cleanup.py results/security/<run-directory>
python cleanup.py results/security/<run-directory> --apply
```

Chỉ xóa các username được ghi trước POST trong manifest đúng namespace lần chạy và có email test đúng mẫu, không xóa tài khoản admin/guest hoặc fixture Student/Teacher. Sử dụng Moodle `delete_user()` (không SQL DELETE). Không chạy cleanup khi workload đang chạy. Nếu đã xóa tay hoặc chạy lại, tài khoản không còn tồn tại sẽ được bỏ qua. Moodle có thể giữ record soft-deleted theo cơ chế của nó. Không xóa tài khoản Level 1/2. Kết quả audit trong thư mục chạy được giữ nguyên; `cleanup.json` ghi trạng thái sau cleanup.

## 5. Giới hạn và nguồn

22 offline unit tests kiểm tra xử lý form, URL local, phân loại chỉ số, manifest và các kịch bản security bằng mock. Chúng không phải bằng chứng Moodle PASS. PHP bridge được kiểm tra cú pháp PHP, chưa chạy trên Moodle thực tế. Locust runtime chưa được chạy trong môi trường soạn code. Cần chạy readiness + smoke trên máy bạn. Cấu hình Docker/site, form plugin, theme hoặc ngôn ngữ khác có thể yêu cầu chỉnh parser. Việc audit sử dụng đúng database của instance Moodle đã cấu hình; không thu mật khẩu/hash trong kết quả. Lưu ý khai báo AI trong báo cáo theo quy định của môn học.

Nguồn đối chiếu: Project #3; mã nguồn Moodle 5.1 `public/user/editadvanced.php` (https://github.com/moodle/moodle/blob/MOODLE_501_STABLE/public/user/editadvanced.php); Level 1 và Level 2 Feature 001; tài liệu Locust (https://docs.locust.io/).
