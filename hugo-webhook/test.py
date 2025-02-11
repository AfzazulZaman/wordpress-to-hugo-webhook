import json
import logging
import os
import http.server
import requests
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import frontmatter
import html2text
import subprocess

# Configuration
API_KEY = "cbcaafhwsllintiybhs9hmvz3slesmkalverqwrzlc460fyagtxw8lgttdypm6r8"  # Replace with your actual API key
HUGO_BASE_DIR = Path("./hugo")  # Replace with your Hugo site path
HUGO_CONTENT_DIR = HUGO_BASE_DIR / "content" / "posts"
HUGO_STATIC_DIR = HUGO_BASE_DIR / "static" / "uploads"
PORT = 8083

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("webhook.log"),
        logging.StreamHandler()
    ]
)

class WebhookHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests with a friendly message"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        message = """
        <html>
            <body>
                <h1>WordPress to Hugo Webhook Server</h1>
                <p>This is a webhook endpoint that accepts POST requests from WordPress to update Hugo content.</p>
                <p>To use this webhook:</p>
                <ol>
                    <li>Configure your WordPress webhook to send POST requests to this URL</li>
                    <li>Include your API key in the request URL: ?api_key=your_key_here</li>
                    <li>Make sure to send the post data in the request body</li>
                </ol>
                <p>Status: Server is running and ready to accept POST requests.</p>
            </body>
        </html>
        """
        self.wfile.write(message.encode())

    def do_POST(self):
        """Handle POST requests from WordPress"""
        try:
            # Parse query parameters for API key
            parsed_path = urlparse(self.path)
            query_params = parse_qs(parsed_path.query)
            received_api_key = query_params.get('api_key', [None])[0]

            # Log the received request
            logging.info(f"Received POST request at: {self.path}")
            logging.info(f"Headers: {self.headers}")

            # Check API key
            if received_api_key != API_KEY:
                logging.warning("Invalid API key received")
                self.send_error(401, "Unauthorized: Invalid API key")
                return

            # Read and parse the request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length).decode('utf-8')
                logging.info(f"Received data: {post_data[:200]}...")  # Log first 200 chars
                
                try:
                    wp_data = json.loads(post_data)
                except json.JSONDecodeError as e:
                    logging.error(f"Failed to parse JSON: {e}")
                    self.send_error(400, "Invalid JSON data")
                    return

                # Send successful response
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {"status": "success", "message": "Webhook received successfully"}
                self.wfile.write(json.dumps(response).encode())

                # Process the data
                self.process_wordpress_data(wp_data)
            else:
                self.send_error(400, "Empty request body")

        except Exception as e:
            logging.error(f"Error processing webhook: {e}")
            self.send_error(500, f"Internal Server Error: {str(e)}")

    def process_wordpress_data(self, data):
        """Process the WordPress webhook data"""
        try:
            logging.info("Processing WordPress data...")
            # Log the structure of received data
            logging.info(f"Received data structure: {list(data.keys())}")
            
            # Extract post data - adjust these based on your actual WordPress webhook data structure
            post_title = data.get('post_title', '')
            post_content = data.get('post_content', '')
            post_status = data.get('post_status', '')
            post_slug = data.get('post_name', '')

            logging.info(f"Processing post: {post_title}")

            # Only process published posts
            if post_status != 'publish':
                logging.info(f"Skipping non-published post: {post_title}")
                return

            # Create Hugo markdown file
            self.create_hugo_post(post_title, post_content, post_slug)

        except Exception as e:
            logging.error(f"Error processing WordPress data: {e}")
            raise

    def create_hugo_post(self, title, content, slug):
        """Create a Hugo post file"""
        try:
            # Ensure content directory exists
            HUGO_CONTENT_DIR.mkdir(parents=True, exist_ok=True)
            
            # Create file path
            file_path = HUGO_CONTENT_DIR / f"{slug}.md"
            
            # Create front matter
            front_matter = {
                'title': title,
                'date': self.headers.get('Date', ''),
                'draft': False
            }
            
            # Convert HTML to Markdown if content is HTML
            h = html2text.HTML2Text()
            h.body_width = 0
            markdown_content = h.handle(content)
            
            # Create the post
            post = frontmatter.Post(markdown_content, **front_matter)
            
            # Write the file
            with open(file_path, 'wb') as f:
                frontmatter.dump(post, f)
                
            logging.info(f"Created Hugo post: {file_path}")
            
            # Rebuild Hugo site
            self.rebuild_hugo_site()
            
        except Exception as e:
            logging.error(f"Error creating Hugo post: {e}")
            raise

    def rebuild_hugo_site(self):
        """Rebuild the Hugo site"""
        try:
            result = subprocess.run(
                ['hugo', '--source', str(HUGO_BASE_DIR)],
                capture_output=True,
                text=True,
                check=True
            )
            logging.info("Hugo site rebuilt successfully")
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to rebuild Hugo site: {e}")
            logging.error(f"Hugo output: {e.stdout}\n{e.stderr}")

def run_server():
    server_address = ('', PORT)
    httpd = http.server.HTTPServer(server_address, WebhookHandler)
    logging.info(f"Starting webhook server on port {PORT}...")
    print(f"Server started at http://localhost:{PORT}")
    print("Press Ctrl+C to stop the server")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down the server...")
        httpd.server_close()
        print("Server stopped")

if __name__ == "__main__":
    run_server()