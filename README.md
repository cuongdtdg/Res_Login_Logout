# Authentication API với FastAPI và Admin Approval

Hệ thống xác thực hoàn chỉnh với FastAPI bao gồm đăng ký, đăng nhập, xác thực OTP và **phê duyệt admin**.

## Tính năng chính

### 🔐 Đăng ký (Cần phê duyệt admin)
- **POST /auth/register**: Đăng ký tài khoản mới
- **POST /auth/verify-registration**: Xác thực OTP đăng ký
- **POST /auth/resend-registration-otp**: Gửi lại OTP đăng ký
- ✨ **Sau khi đăng ký thành công, user cần chờ admin phê duyệt**
- 📧 **Admin sẽ nhận email thông báo khi có người dùng mới đăng ký**

### 🔑 Đăng nhập (Chỉ user đã được phê duyệt)
- **POST /auth/login**: Đăng nhập (bước 1)
- **POST /auth/verify-otp**: Xác thực OTP đăng nhập (bước 2)
- **POST /auth/resend-otp**: Gửi lại OTP đăng nhập
- **POST /auth/logout**: Đăng xuất
- ✨ **Chỉ user đã được admin phê duyệt mới có thể đăng nhập**

### 👨‍💼 Admin Panel
- **GET /auth/admin/pending-users**: Xem danh sách user chờ phê duyệt
- **POST /auth/admin/approve-user**: Phê duyệt user
- **GET /auth/admin/all-users**: Xem tất cả user

### Khác
- **GET /health**: Kiểm tra trạng thái API
- **GET /**: Thông tin API

## Cài đặt

1. **Cài đặt dependencies:**
```bash
pip install -r requirements.txt
```

2. **Cấu hình database PostgreSQL:**
   - Tạo database mới
   - Chạy script `database_schema.sql` để tạo tables

3. **Cấu hình environment variables:**
   - Sao chép `.env` và cập nhật thông tin:
   ```
   DATABASE_URL=postgresql://username:password@localhost:5432/auth_db
   SECRET_KEY=your-secret-key-here
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   FROM_EMAIL=your-email@gmail.com
   ADMIN_EMAIL=admin@example.com
   ```
   ```
   DATABASE_URL=postgresql://username:password@localhost:5432/auth_db
   SECRET_KEY=your-secret-key-here
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   FROM_EMAIL=your-email@gmail.com
   ```

4. **Tạo admin user đầu tiên:**
```bash
python create_admin.py
```

5. **Chạy ứng dụng:**
```bash
python main.py
```

API sẽ chạy tại: http://localhost:8000

## Quy trình sử dụng

### 📝 Cho User thường
1. **Đăng ký tài khoản**: Gọi `/auth/register` với thông tin cá nhân
2. **Xác thực OTP**: Nhận OTP qua email và gọi `/auth/verify-registration`
3. **Chờ phê duyệt**: Sau khi đăng ký thành công, chờ admin phê duyệt
4. **Đăng nhập**: Sau khi được phê duyệt, có thể đăng nhập bình thường

### 👨‍💼 Cho Admin
1. **Đăng nhập**: Sử dụng tài khoản admin đã tạo
2. **Xem user chờ phê duyệt**: Gọi `/auth/admin/pending-users`
3. **Phê duyệt user**: Gọi `/auth/admin/approve-user` với user_id
4. **Quản lý user**: Xem tất cả user qua `/auth/admin/all-users`

## API Documentation

Truy cập Swagger UI tại: http://localhost:8000/docs

## Cấu trúc dự án

```
├── main.py                 # Entry point
├── auth_routes.py         # Authentication routes
├── models.py              # Pydantic models
├── database.py            # Database connection và tables
├── utils.py               # Utility functions
├── email_service.py       # Email/SMS services
├── config.py              # Configuration
├── requirements.txt       # Dependencies
├── .env                   # Environment variables
├── database_schema.sql    # Database schema
└── README.md             # Documentation
```

## Security Features

- Password hashing với bcrypt
- Session-based authentication với cookies
- OTP expiration (5 phút)
- HttpOnly, Secure, SameSite cookies
- Input validation
- SQL injection protection

## Database Schema

Hệ thống sử dụng 4 bảng chính:
- `users`: Thông tin người dùng (có thêm `is_approved`, `approved_at`, `approved_by`)
- `temp_registrations`: Đăng ký tạm thời
- `temp_sessions`: Phiên đăng nhập tạm thời
- `auth_sessions`: Phiên xác thực

### Các trường mới trong bảng users:
- `is_approved`: Trạng thái phê duyệt (mặc định FALSE)
- `approved_at`: Thời gian phê duyệt
- `approved_by`: ID của admin phê duyệt

## Email Configuration

Để gửi email OTP, cần cấu hình:
- SMTP server (Gmail, Outlook, etc.)
- App password (không dùng password thường)
- Cấu hình 2FA cho email account

## Testing

### Đăng ký User
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Nguyen Van A",
    "email": "user@example.com",
    "phone": "0987654321",
    "password": "mypassword123",
    "confirm_password": "mypassword123"
  }'
```

### Xác thực đăng ký
```bash
curl -X POST "http://localhost:8000/auth/verify-registration" \
  -H "Content-Type: application/json" \
  -H "Cookie: temp_registration_id=<your-temp-id>" \
  -d '{
    "otp": "123456"
  }'
```

### Admin xem user chờ phê duyệt
```bash
curl -X GET "http://localhost:8000/auth/admin/pending-users" \
  -H "Cookie: auth_session_id=<admin-session-id>"
```

### Admin phê duyệt user
```bash
curl -X POST "http://localhost:8000/auth/admin/approve-user" \
  -H "Content-Type: application/json" \
  -H "Cookie: auth_session_id=<admin-session-id>" \
  -d '{
    "user_id": "<user-uuid>"
  }'
```

## Production Deployment

Khi deploy production:
1. Sử dụng database connection pooling
2. Cấu hình SSL/TLS
3. Sử dụng environment variables an toàn
4. Cấu hình CORS properly
5. Sử dụng reverse proxy (nginx)
6. Monitoring và logging
7. Rate limiting
8. Cleanup expired records định kỳ
