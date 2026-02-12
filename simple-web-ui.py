#!/usr/bin/env python3
"""
Simple web UI for Kimi - works with just Python standard library
No FastAPI needed - uses http.server
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import json
import urllib.parse

HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Kimi K2.5 Chat</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #1a1a2e;
            color: #eee;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            background: #16213e;
            padding: 20px;
            border-bottom: 2px solid #0f3460;
        }
        .header h1 { color: #00d9ff; }
        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
        }
        .message {
            margin: 15px 0;
            padding: 15px;
            border-radius: 10px;
            max-width: 70%;
        }
        .user-message {
            background: #0f3460;
            margin-left: auto;
            text-align: right;
        }
        .ai-message {
            background: #16213e;
            border-left: 4px solid #00d9ff;
        }
        .input-container {
            background: #16213e;
            padding: 20px;
            border-top: 2px solid #0f3460;
            display: flex;
            gap: 10px;
        }
        #messageInput {
            flex: 1;
            padding: 15px;
            background: #0f3460;
            border: none;
            border-radius: 8px;
            color: #eee;
            font-size: 16px;
        }
        #sendButton {
            padding: 15px 30px;
            background: #00d9ff;
            color: #000;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            cursor: pointer;
            font-size: 16px;
        }
        #sendButton:hover { background: #00b8d4; }
        #sendButton:disabled { opacity: 0.5; cursor: not-allowed; }
        .loading { animation: pulse 1.5s infinite; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 Kimi K2.5 - Local AI Chat</h1>
        <p>100% local • Zero cost • Complete privacy</p>
    </div>

    <div class="chat-container" id="chatContainer"></div>

    <div class="input-container">
        <input type="text" id="messageInput" placeholder="Type your message..." />
        <button id="sendButton">Send</button>
    </div>

    <script>
        const chatContainer = document.getElementById('chatContainer');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');

        function addMessage(text, isUser) {
            const div = document.createElement('div');
            div.className = `message ${isUser ? 'user-message' : 'ai-message'}`;
            div.textContent = text;
            chatContainer.appendChild(div);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        async function sendMessage() {
            const message = messageInput.value.trim();
            if (!message) return;

            addMessage(message, true);
            messageInput.value = '';
            sendButton.disabled = true;
            sendButton.textContent = 'Thinking...';
            sendButton.classList.add('loading');

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message })
                });

                const data = await response.json();
                addMessage(data.response, false);
            } catch (error) {
                addMessage('Error: ' + error.message, false);
            } finally {
                sendButton.disabled = false;
                sendButton.textContent = 'Send';
                sendButton.classList.remove('loading');
                messageInput.focus();
            }
        }

        sendButton.addEventListener('click', sendMessage);
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        // Add welcome message
        addMessage('Hello! I\\'m Kimi K2.5, your local AI assistant. How can I help you today?', false);
    </script>
</body>
</html>
"""

class KimiHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/api/chat':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())

            message = data.get('message', '')

            try:
                # Call Ollama
                result = subprocess.run(
                    ['ollama', 'run', 'llava:13b', message],
                    capture_output=True,
                    text=True,
                    timeout=120
                )

                response = {'response': result.stdout.strip()}

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())

            except Exception as e:
                error_response = {'response': f'Error: {str(e)}'}
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(error_response).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress logs

def main():
    port = 8000
    server = HTTPServer(('localhost', port), KimiHandler)
    print("=" * 60)
    print("🚀 Kimi K2.5 Web UI Running!")
    print("=" * 60)
    print(f"\n✅ Open your browser: http://localhost:{port}")
    print("\n💡 Features:")
    print("  • Chat with Kimi K2.5 (local LLM)")
    print("  • Zero cost, complete privacy")
    print("  • No API keys needed")
    print("\n⏹️  Press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped")
        server.shutdown()

if __name__ == "__main__":
    main()
