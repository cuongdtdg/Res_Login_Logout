import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, FROM_EMAIL, ADMIN_EMAIL
import asyncio

async def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send email using SMTP"""
    try:
        # Create message
        message = MIMEMultipart()
        message["From"] = FROM_EMAIL
        message["To"] = to_email
        message["Subject"] = subject
        
        # Add body to email
        message.attach(MIMEText(body, "plain"))
        
        # Send email
        await aiosmtplib.send(
            message,
            hostname=SMTP_SERVER,
            port=SMTP_PORT,
            start_tls=True,
            username=SMTP_USERNAME,
            password=SMTP_PASSWORD,
        )
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

async def send_otp_email(to_email: str, otp: str, purpose: str = "verification") -> bool:
    """Send OTP via email"""
    if purpose == "registration":
        subject = "Mã xác thực đăng ký"
        body = f"""
        Chào bạn,
        
        Mã OTP để hoàn thành đăng ký tài khoản của bạn là: {otp}
        
        Mã này sẽ hết hạn sau 5 phút.
        
        Nếu bạn không thực hiện đăng ký này, vui lòng bỏ qua email này.
        
        Trân trọng,
        Đội ngũ hỗ trợ
        """
    elif purpose == "approval":
        subject = "Tài khoản của bạn đã được phê duyệt"
        body = f"""
        Chào bạn,
        
        Chúc mừng! Tài khoản của bạn đã được admin phê duyệt.
        
        Bây giờ bạn có thể đăng nhập vào hệ thống.
        
        Trân trọng,
        Đội ngũ hỗ trợ
        """
    else:  # login
        subject = "Mã xác thực đăng nhập"
        body = f"""
        Chào bạn,
        
        Mã OTP để đăng nhập vào tài khoản của bạn là: {otp}
        
        Mã này sẽ hết hạn sau 5 phút.
        
        Nếu bạn không thực hiện đăng nhập này, vui lòng bỏ qua email này.
        
        Trân trọng,
        Đội ngũ hỗ trợ
        """
    
    return await send_email(to_email, subject, body)

# Mock SMS function (you would integrate with a real SMS service)
async def send_sms(phone: str, message: str) -> bool:
    """Send SMS (mock implementation)"""
    print(f"SMS to {phone}: {message}")
    # In production, integrate with SMS service like Twilio, AWS SNS, etc.
    return True

async def send_otp_sms(phone: str, otp: str) -> bool:
    """Send OTP via SMS"""
    message = f"Mã OTP của bạn là: {otp}. Mã này sẽ hết hạn sau 5 phút."
    return await send_sms(phone, message)

async def send_admin_notification(user_data: dict) -> bool:
    """Send notification to admin when new user registers"""
    subject = "🔔 Thông báo: Có người dùng mới đăng ký"
    body = f"""
    Chào Admin,
    
    Có một người dùng mới vừa hoàn thành đăng ký và đang chờ phê duyệt:
    
    📝 Thông tin người dùng:
    • Tên: {user_data.get('name', 'N/A')}
    • Email: {user_data.get('email', 'N/A')}
    • Số điện thoại: {user_data.get('phone', 'N/A')}
    • Thời gian đăng ký: {user_data.get('created_at', 'N/A')}
    
    Vui lòng đăng nhập vào hệ thống quản trị để phê duyệt tài khoản này.
    
    🔗 Link admin panel: http://localhost:8000/docs
    
    Trân trọng,
    Hệ thống Authentication API
    """
    
    try:
        return await send_email(ADMIN_EMAIL, subject, body)
    except Exception as e:
        print(f"Error sending admin notification: {e}")
        return False
