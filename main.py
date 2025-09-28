#Copyright @ISmartCoder
#Updates Channel https://t.me/abirxdhackz
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse  
from fastapi.staticfiles import StaticFiles  
import asyncio
import aiohttp
import socket
import time
import re
import base64
import json
import gzip
import brotli
import zstandard as zstd
import cloudscraper
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import threading
import uuid
import os

app = FastAPI(title="Smart TempMail API", version="1.0.0")

class TempMailService:
    def __init__(self):
        self.sessions = {}
        self.email_sessions = {}
        
    async def decode_api_url(self, encoded_url: str) -> Optional[str]:
        try:
            cleaned_url = re.sub(r'[^A-Za-z0-9+/=]', '', encoded_url)
            cleaned_url = cleaned_url.replace('f56', '6')
            cleaned_url = cleaned_url + '=' * (4 - len(cleaned_url) % 4) if len(cleaned_url) % 4 != 0 else cleaned_url
            decoded = base64.b64decode(cleaned_url).decode('utf-8')
            if not decoded.startswith('http'):
                decoded = 'https://' + decoded.lstrip('?:/')
            return decoded
        except Exception as e:
            print(f"[DEBUG] Error decoding API URL: {str(e)}")
            return None

    async def decompress_response(self, response_text: str, headers: dict) -> str:
        if headers.get('Content-Encoding') == 'gzip':
            try:
                return gzip.decompress(response_text.encode()).decode('utf-8')
            except Exception as e:
                print(f"[DEBUG] Error decompressing response: {str(e)}")
                return response_text
        return response_text

    def decompress_edu_response(self, response):
        content = response.content
        try:
            if not content:
                return None
            if response.headers.get('content-encoding') == 'gzip':
                return gzip.decompress(content).decode('utf-8')
            elif response.headers.get('content-encoding') == 'br':
                try:
                    return brotli.decompress(content).decode('utf-8')
                except brotli.error:
                    try:
                        return content.decode('utf-8')
                    except UnicodeDecodeError:
                        return None
            elif response.headers.get('content-encoding') == 'zstd':
                try:
                    dctx = zstd.ZstdDecompressor()
                    return dctx.decompress(content).decode('utf-8')
                except zstd.ZstdError:
                    try:
                        return content.decode('utf-8')
                    except UnicodeDecodeError:
                        return None
            return content.decode('utf-8')
        except Exception:
            return None

    async def extract_auth_token(self, html_content: str, cookies: dict) -> Optional[str]:
        try:
            jwt_patterns = [
                r'"jwt"\s*:\s*"(eyJ[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*\.[A-Za-z0-9_-]+)"',
                r'"token"\s*:\s*"(eyJ[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*\.[A-Za-z0-9_-]+)"',
                r'window\.token\s*=\s*[\'"]eyJ[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*\.[A-Za-z0-9_-]+[\'"]',
                r'eyJ[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*\.[A-Za-z0-9_-]+'
            ]
            for pattern in jwt_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, str) and match.startswith('eyJ'):
                        return match
            return None
        except Exception as e:
            print(f"[DEBUG] Error extracting auth token: {str(e)}")
            return None

    async def extract_email_from_html(self, soup: BeautifulSoup) -> Optional[str]:
        try:
            email_input = soup.find('input', {'id': 'mail'}) or soup.find('input', {'name': 'mail'})
            if email_input and email_input.get('value'):
                return email_input.get('value')
            email_span = soup.find('span', {'id': 'mail'})
            if email_span and email_span.get_text().strip():
                return email_span.get_text().strip()
            email_container = soup.find(['div', 'span'], class_=re.compile('email|mailbox|address|temp-mail', re.I))
            if email_container:
                email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
                match = re.search(email_pattern, email_container.get_text())
                if match:
                    return match.group()
            email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
            for text in soup.stripped_strings:
                match = re.search(email_pattern, text)
                if match and '@' in match.group() and '.' in match.group():
                    return match.group()
            return None
        except Exception as e:
            print(f"[DEBUG] Error extracting email from HTML: {str(e)}")
            return None

    async def get_mailbox_and_token(self, api_url: str, cookies: dict, scraper, ten_minute: bool = False) -> tuple:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Origin': 'https://temp-mail.org',
                'Referer': 'https://temp-mail.org/en/10minutemail' if ten_minute else 'https://temp-mail.org/en/',
                'Sec-Ch-Ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site',
                'Content-Type': 'application/json',
                'Priority': 'u=1, i'
            }
            if 'XSRF-TOKEN' in cookies:
                headers['X-XSRF-TOKEN'] = cookies['XSRF-TOKEN']
            print(f"[DEBUG] Requesting mailbox from: {api_url}/mailbox")
            response = scraper.post(f"{api_url}/mailbox", headers=headers, cookies=cookies, json={})
            print(f"[DEBUG] Mailbox response status: {response.status_code}")
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"[DEBUG] Mailbox response: {json.dumps(data, indent=2)}")
                    email = data.get('mailbox') or data.get('email') or data.get('address')
                    jwt_token = data.get('token') or data.get('jwt') or data.get('auth_token')
                    if jwt_token and jwt_token.startswith('eyJ'):
                        return email, jwt_token
                    else:
                        print(f"[DEBUG] No valid JWT token found in response")
                        return email, None
                except json.JSONDecodeError as e:
                    print(f"[DEBUG] JSON decode error: {str(e)}")
                    print(f"[DEBUG] Raw response: {response.text}")
                    return None, None
            else:
                print(f"[DEBUG] Mailbox request failed with status: {response.status_code}")
                print(f"[DEBUG] Response: {response.text}")
                response = scraper.get(f"{api_url}/mailbox", headers=headers, cookies=cookies)
                print(f"[DEBUG] GET mailbox response status: {response.status_code}")
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"[DEBUG] GET Mailbox response: {json.dumps(data, indent=2)}")
                        email = data.get('mailbox') or data.get('email') or data.get('address')
                        jwt_token = data.get('token') or data.get('jwt') or data.get('auth_token')
                        if jwt_token and jwt_token.startswith('eyJ'):
                            return email, jwt_token
                        else:
                            print(f"[DEBUG] No valid JWT token found in GET response")
                            return email, None
                    except json.JSONDecodeError as e:
                        print(f"[DEBUG] GET JSON decode error: {str(e)}")
                        print(f"[DEBUG] GET Raw response: {response.text}")
                        return None, None
                else:
                    print(f"[DEBUG] GET Mailbox request also failed with status: {response.status_code}")
                    return None, None
        except Exception as e:
            print(f"[DEBUG] Exception in get_mailbox_and_token: {str(e)}")
            return None, None

    async def check_inbox(self, api_url: str, auth_token: str, cookies: dict, email: str, scraper, ten_minute: bool = False) -> Optional[list]:
        try:
            print(f"[DEBUG] Making request to: {api_url}/messages")
            print(f"[DEBUG] Using auth token: {auth_token[:50] if auth_token else 'None'}...")
            print(f"[DEBUG] Using cookies: {list(cookies.keys())}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Origin': 'https://temp-mail.org',
                'Referer': 'https://temp-mail.org/en/10minutemail' if ten_minute else 'https://temp-mail.org/en/',
                'Sec-Ch-Ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site',
                'Priority': 'u=1, i'
            }
            if auth_token:
                headers['Authorization'] = f'Bearer {auth_token}'
            if 'XSRF-TOKEN' in cookies:
                headers['X-XSRF-TOKEN'] = cookies['XSRF-TOKEN']
            response = scraper.get(f"{api_url}/messages", headers=headers, cookies=cookies)
            print(f"[DEBUG] Response status: {response.status_code}")
            if response.status_code == 200:
                try:
                    inbox_data = response.json()
                    print(f"[DEBUG] Raw response: {json.dumps(inbox_data, indent=2)}")
                    if 'messages' in inbox_data:
                        messages = inbox_data['messages']
                        print(f"[DEBUG] Messages found: {len(messages)}")
                        if messages:
                            print(f"[DEBUG] First message: {messages[0]}")
                        return messages
                    elif isinstance(inbox_data, list):
                        messages = inbox_data
                        print(f"[DEBUG] Messages found: {len(messages)}")
                        return messages
                    else:
                        print(f"[DEBUG] No messages key found in response")
                        return []
                except json.JSONDecodeError as e:
                    print(f"[DEBUG] JSON decode error: {str(e)}")
                    print(f"[DEBUG] Raw response text: {response.text}")
                    return None
            else:
                print(f"[DEBUG] Response status: {response.status_code}")
                print(f"[DEBUG] Response headers: {dict(response.headers)}")
                print(f"[DEBUG] Raw response: {response.text[:500]}")
                return None
        except Exception as e:
            print(f"[DEBUG] Exception in check_inbox: {str(e)}")
            return None

    async def generate_temp_mail(self, ten_minute: bool = False) -> Dict[str, Any]:
        start_time = time.time()
        scraper = cloudscraper.create_scraper()
        try:
            url = 'https://temp-mail.org/en/10minutemail' if ten_minute else 'https://temp-mail.org/en/'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Sec-Ch-Ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'Priority': 'u=0, i'
            }
            response = scraper.get(url, headers=headers, allow_redirects=True)
            print(f"[DEBUG] Response status for {url}: {response.status_code}")
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Failed to connect to {url}")
            html_content = await self.decompress_response(response.text, response.headers)
            cookies = dict(response.cookies)
            print(f"[DEBUG] Captured cookies: {cookies}")
            soup = BeautifulSoup(html_content, 'html.parser')
            api_url = None
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    script_content = script.string
                    api_patterns = [
                        r"var api_url\s*=\s*'([^']+)'",
                        r'"api_url"\s*:\s*"([^"]+)"',
                        r'apiUrl\s*:\s*[\'"]([^\'"]+)[\'"]',
                        r'API_URL\s*=\s*[\'"]([^\'"]+)[\'"]'
                    ]
                    for pattern in api_patterns:
                        match = re.search(pattern, script_content)
                        if match:
                            encoded_api_url = match.group(1)
                            api_url = await self.decode_api_url(encoded_api_url)
                            if api_url:
                                print(f"[DEBUG] Captured API URL: {api_url}")
                                break
                    if api_url:
                        break
            if not api_url:
                api_url = "https://web2.temp-mail.org"
                print(f"[DEBUG] Using default API URL: {api_url}")
            email, auth_token = await self.get_mailbox_and_token(api_url, cookies, scraper, ten_minute)
            if not email or not auth_token:
                print("[DEBUG] Failed to get email/token from API, trying HTML extraction...")
                email = await self.extract_email_from_html(soup)
                if not auth_token:
                    auth_token = await self.extract_auth_token(html_content, cookies)
            if not email or not auth_token:
                raise HTTPException(status_code=500, detail="Failed to generate temporary email")
            session_data = {
                'api_url': api_url,
                'email': email,
                'cookies': cookies,
                'scraper': scraper,
                'created_at': time.time(),
                'ten_minute': ten_minute
            }
            self.sessions[auth_token] = session_data
            time_taken = f"{time.time() - start_time:.2f}s"
            return {
                "api_owner": "@ISmartCoder",
                "api_dev": "@WeSmartDevelopers",
                "temp_mail": email,
                "access_token": auth_token,
                "time_taken": time_taken,
                "expires_at": (datetime.now() + timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S') if ten_minute else "N/A"
            }
        except Exception as e:
            print(f"[DEBUG] Error in generate_temp_mail: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error generating temp mail: {str(e)}")
        finally:
            pass

    async def check_messages(self, token: str) -> Dict[str, Any]:
        if token not in self.sessions:
            raise HTTPException(status_code=404, detail="Invalid or expired token")
        session = self.sessions[token]
        if session['ten_minute'] and (time.time() - session['created_at']) > 600:
            del self.sessions[token]
            raise HTTPException(status_code=410, detail="10-minute email has expired")
        try:
            messages = await self.check_inbox(
                session['api_url'],
                token,
                session['cookies'],
                session['email'],
                session['scraper'],
                session['ten_minute']
            )
            if messages is None:
                raise HTTPException(status_code=500, detail="Failed to check inbox")
            enhanced_messages = []
            for message in messages:
                enhanced_message = message.copy()
                enhanced_message["api_dev"] = "@ISmartCoder"
                enhanced_message["api_updates"] = "@WeSmartDevelopers"
                if 'receivedAt' in enhanced_message:
                    try:
                        enhanced_message['receivedAt'] = datetime.fromtimestamp(
                            enhanced_message['receivedAt']
                        ).strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                enhanced_messages.append(enhanced_message)
            return {
                "mailbox": session['email'],
                "messages": enhanced_messages,
                "api_owner": "@ISmartCoder",
                "api_dev": "@WeSmartDevelopers"
            }
        except Exception as e:
            print(f"[DEBUG] Error in check_messages: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error checking messages: {str(e)}")

    async def get_edu_email(self):
        url = "https://etempmail.com/getEmailAddress"
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.6',
            'origin': 'https://etempmail.com',
            'referer': 'https://etempmail.com/',
            'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Brave";v="140"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest'
        }
        scraper = cloudscraper.create_scraper()
        for attempt in range(3):
            try:
                response = scraper.post(url, headers=headers)
                if response.status_code == 200:
                    decompressed = self.decompress_edu_response(response)
                    if not decompressed:
                        if attempt < 2:
                            time.sleep(2)
                            continue
                        return None, None, None
                    try:
                        data = json.loads(decompressed)
                        return data['address'], data['recover_key'], response.cookies.get_dict()
                    except json.JSONDecodeError:
                        if attempt < 2:
                            time.sleep(2)
                            continue
                        return None, None, None
                else:
                    if attempt < 2:
                        time.sleep(2)
                        continue
                    return None, None, None
            except Exception:
                if attempt < 2:
                    time.sleep(2)
                    continue
                return None, None, None
        return None, None, None

    async def check_edu_inbox(self, email, cookies):
        url = "https://etempmail.com/getInbox"
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.6',
            'origin': 'https://etempmail.com',
            'referer': 'https://etempmail.com/',
            'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Brave";v="140"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest'
        }
        scraper = cloudscraper.create_scraper()
        try:
            response = scraper.post(url, headers=headers, cookies=cookies)
            if response.status_code == 200:
                decompressed = self.decompress_edu_response(response)
                if decompressed is None:
                    return []
                try:
                    data = json.loads(decompressed)
                    return data
                except json.JSONDecodeError:
                    return []
            else:
                return []
        except Exception:
            return []

    async def generate_edu_email(self):
        try:
            email, recover_key, cookies = await self.get_edu_email()
            if not email:
                raise HTTPException(status_code=500, detail="Failed to generate email")
            access_token = str(uuid.uuid4())
            self.email_sessions[access_token] = {
                "email": email,
                "recover_key": recover_key,
                "cookies": cookies,
                "created_at": time.time()
            }
            return {
                "api_owner": "@ISmartCoder",
                "api_dev": "@TheSmartDev",
                "edu_mail": email,
                "access_token": access_token
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def check_edu_messages(self, token: str):
        try:
            if token not in self.email_sessions:
                raise HTTPException(status_code=404, detail="Invalid or expired token")
            session = self.email_sessions[token]
            email = session["email"]
            cookies = session["cookies"]
            inbox = await self.check_edu_inbox(email, cookies)
            messages = []
            for mail in inbox:
                soup = BeautifulSoup(mail['body'], 'html.parser')
                body_text = soup.get_text().strip()
                messages.append({
                    "From": mail['from'],
                    "Subject": mail['subject'],
                    "Date": mail['date'],
                    "body": body_text,
                    "Message": body_text
                })
            response_data = {
                "api_owner": "@ISmartCoder",
                "api_dev": "@TheSmartDev",
                "edu_mail": email,
                "access_token": token,
                "messages": messages
            }
            if messages:
                latest_message = messages[0]
                response_data.update({
                    "Message": latest_message["Message"],
                    "From": latest_message["From"],
                    "body": latest_message["body"],
                    "Date": latest_message["Date"],
                    "Subject": latest_message["Subject"]
                })
            else:
                response_data.update({
                    "Message": "",
                    "From": "",
                    "body": "",
                    "Date": "",
                    "Subject": ""
                })
            return response_data
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

temp_mail_service = TempMailService()

@app.get("/")
async def root():
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path)

@app.get("/api/gen")
async def generate_mail():
    try:
        result = await temp_mail_service.generate_temp_mail(ten_minute=False)
        return JSONResponse(content=result)
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"[DEBUG] Error in /api/gen: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chk")
async def check_mail(token: str):
    try:
        result = await temp_mail_service.check_messages(token)
        return JSONResponse(content=result)
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"[DEBUG] Error in /api/chk: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/10min/gen")
async def generate_10min_mail():
    try:
        result = await temp_mail_service.generate_temp_mail(ten_minute=True)
        return JSONResponse(content=result)
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"[DEBUG] Error in /api/10min/gen: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/10min/chk")
async def check_10min_mail(token: str):
    try:
        result = await temp_mail_service.check_messages(token)
        return JSONResponse(content=result)
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"[DEBUG] Error in /api/10min/chk: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/edu/gen")
async def generate_edu_email():
    try:
        result = await temp_mail_service.generate_edu_email()
        return JSONResponse(content=result)
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"[DEBUG] Error in /api/edu/gen: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/edu/chk")
async def check_edu_messages(token: str):
    try:
        result = await temp_mail_service.check_edu_messages(token)
        return JSONResponse(content=result)
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"[DEBUG] Error in /api/edu/chk: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def cleanup_expired_sessions():
    while True:
        current_time = time.time()
        expired_tokens = []
        for token, session in temp_mail_service.email_sessions.items():
            if current_time - session["created_at"] > 7200:
                expired_tokens.append(token)
        for token in expired_tokens:
            del temp_mail_service.email_sessions[token]
        time.sleep(300)

def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    import uvicorn
    local_ip = get_local_ip()
    port = int(os.getenv("PORT", 8000))
    print(f"TempMail API Server Starting...")
    print(f"Local IP: {local_ip}")
    print(f"Server running on: http://{local_ip}:{port}")
    print(f"API Documentation: http://{local_ip}:{port}/docs")
    print(f"Generate Regular Mail: http://{local_ip}:{port}/api/gen")
    print(f"Check Regular Messages: http://{local_ip}:{port}/api/chk?token=YOUR_TOKEN")
    print(f"Generate 10-Minute Mail: http://{local_ip}:{port}/api/10min/gen")
    print(f"Check 10-Minute Messages: http://{local_ip}:{port}/api/10min/chk?token=YOUR_TOKEN")
    print(f"Generate Edu Mail: http://{local_ip}:{port}/api/edu/gen")
    print(f"Check Edu Messages: http://{local_ip}:{port}/api/edu/chk?token=YOUR_TOKEN")
    cleanup_thread = threading.Thread(target=cleanup_expired_sessions, daemon=True)
    cleanup_thread.start()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=False,
        access_log=True
    )