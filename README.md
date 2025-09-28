# Smart TempMail API 📧

**Generate and manage temporary email addresses effortlessly! 🚀**

Smart TempMail API is a powerful, developer-friendly tool for creating disposable and educational email addresses. Perfect for testing, privacy, and educational purposes. Built with ❤️ by [@ISmartCoder](https://t.me/ISmartCoder).

## Features ✨

- **Temporary Email** 📩: Generate disposable email addresses for short-term use.
- **10-Minute Mail** ⏰: Create emails that auto-expire after 10 minutes for quick tasks.
- **Edu Email** 🎓: Generate `.edu` email addresses for educational purposes.
- **Fast & Reliable** ⚡: Powered by FastAPI for high performance and scalability.
- **Developer-Friendly** 🛠️: Clear API endpoints with detailed documentation.

## Getting Started 🚀

### Prerequisites
- Python 3.8+ 🐍
- Dependencies: `fastapi`, `uvicorn`, `cloudscraper`, `beautifulsoup4`, `aiohttp`, `brotli`, `zstandard`

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/abirxdhack/Temp-Mail-API.git
   cd Temp-Mail-API
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the server:
   ```bash
   python main.py
   ```

### Usage
Access the API at `http://localhost:8000` (or your server's IP). Explore endpoints via the interactive docs at `/docs` 📚.

#### API Endpoints
| Endpoint                | Description                              | Parameters           |
|-------------------------|------------------------------------------|----------------------|
| `GET /api/gen`          | Generate a regular temp email 📧         | None                 |
| `GET /api/chk?token={token}` | Check messages for temp email 📥    | `token` (string)     |
| `GET /api/10min/gen`    | Generate a 10-minute temp email ⏲️      | None                 |
| `GET /api/10min/chk?token={token}` | Check messages for 10-minute email 📬 | `token` (string)     |
| `GET /api/edu/gen`      | Generate an `.edu` email 🎓             | None                 |
| `GET /api/edu/chk?token={token}` | Check messages for `.edu` email 📚 | `token` (string)     |

#### Example Request
```bash
curl http://localhost:8000/api/gen
```
**Response**:
```json
{
  "api_owner": "@ISmartCoder",
  "api_dev": "@WeSmartDevelopers",
  "temp_mail": "example@temp-mail.org",
  "access_token": "your-access-token",
  "time_taken": "0.12s",
  "expires_at": "N/A"
}
```

## Documentation 📖
Full API documentation is available at `/docs` or in the [index.html](index.html) file. It includes detailed request/response examples and use cases.

## Contributing 🤝
Contributions are welcome! Fork the repo, create a branch, and submit a pull request. For major changes, open an issue first.

## Community & Support 🌐
- **Telegram** 💬: Join our community at [t.me/abirxdhackz](https://t.me/abirxdhackz)
- **Updates** 🔔: Follow [@abirxdhackz](https://t.me/abirxdhackz) for updates
- **Issues** 🐛: Report bugs or suggest features on [GitHub Issues](https://github.com/abirxdhack/Temp-Mail-API/issues)

