# EduPath AI Chatbot - FastAPI

Chatbot tư vấn tuyển sinh đại học, hỗ trợ tiếng Việt, sử dụng OpenAI GPT, MongoDB, cấu hình linh hoạt qua file .env và JSON.

## Tính năng nổi bật

- Tư vấn chọn trường, ngành, điểm chuẩn, học phí, lịch tuyển sinh, v.v.
- Nhận diện ý định thông minh (fuzzy intent detection, keyword cấu hình ngoài)
- Giao tiếp tự nhiên, nhớ tên người dùng, cá nhân hóa hội thoại
- Lưu lịch sử chat vào MongoDB, giới hạn context cấu hình được
- Prompt hệ thống, từ khóa, knowledge base đều có thể chỉnh sửa ngoài code
- Logging chuyên nghiệp, dễ debug và mở rộng

## Yêu cầu

- Python >= 3.11.7
- MongoDB (mặc định: mongodb://localhost:27017)
- OpenAI API key (GPT-3.5, GPT-4, GPT-4o...)
- (Windows) Cần cài Rust để build pydantic-core

## Cài đặt

```bash
# Tạo virtualenv (tuỳ hệ điều hành)
python -m venv venv
source venv/bin/activate  # hoặc .\venv\Scripts\activate trên Windows
pip install -r requirements.txt
```

## Cấu hình

Tạo file `.env` ở thư mục gốc, ví dụ:

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
MONGO_URL=mongodb://localhost:27017
MONGO_DB=ai_chatbot
CHAT_HISTORY_LIMIT=30
```

## Chạy chatbot

```bash
python run.py
# hoặc
uvicorn app.main:app --reload
```

## Tùy chỉnh & mở rộng

- **Prompt hệ thống:** chỉnh sửa file `app/data/system_prompt.txt` để thay đổi phong cách, nhiệm vụ bot.
- **Từ khóa intent:** sửa file `app/data/keyword_categories.json` để thêm/bớt từ khóa nhận diện ý định.
- **Knowledge base:** cập nhật file `app/data/knowledge_base.json` để bổ sung kiến thức tư vấn.
- **Giới hạn context:** thay đổi `CHAT_HISTORY_LIMIT` trong `.env` để kiểm soát số tin nhắn nhớ trong hội thoại.

## Liên hệ

Nếu cần file dữ liệu mẫu trong thư mục `data/*.json` để training, inbox: dangkhoipham80@gmail.com
