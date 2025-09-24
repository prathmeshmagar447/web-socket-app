#!/usr/bin/env python3
"""
Web Socket Application Launcher
===============================

This is the main entry point for the web socket application.
You can run either the server or client from this script.

Usage:
    python app.py server    # Start the socket server
    python app.py client    # Start the socket client
    python app.py           # Show usage information
"""

import sys
import os

def show_usage():
    """Show usage information"""
    print("""
🚀 Web Socket Application
========================

Usage:
    python app.py server    # Start the socket server
    python app.py client    # Start the socket client

Features:
    • Socket-based client-server communication
    • SQLite database for data persistence
    • User registration and authentication
    • Real-time messaging
    • Multi-client support with threading

Project Structure:
    web_socket_app/
    ├── app.py                 # Main launcher (this file)
    ├── requirements.txt       # Dependencies
    ├── database/
    │   └── db_manager.py     # Database operations
    ├── server/
    │   └── socket_server.py  # Socket server implementation
    └── client/
        └── socket_client.py  # Socket client implementation

Examples:
    # Terminal 1: Start the server
    python app.py server
    
    # Terminal 2: Start a client
    python app.py client
    
    # In client, try these commands:
    register john john@example.com
    login john
    send Hello, world!
    messages
    users
    ping
    quit
""")

def main():
    if len(sys.argv) < 2:
        show_usage()
        return
    
    mode = sys.argv[1].lower()
    
    if mode == 'server':
        print("🚀 Starting Socket Server...")
        try:
            from server.socket_server import main as server_main
            server_main()
        except ImportError as e:
            print(f"❌ Error importing server module: {e}")
            print("Make sure you're running from the web_socket_app directory")
        except Exception as e:
            print(f"❌ Error starting server: {e}")
    
    elif mode == 'client':
        print("📱 Starting Socket Client...")
        try:
            from client.socket_client import main as client_main
            client_main()
        except ImportError as e:
            print(f"❌ Error importing client module: {e}")
            print("Make sure you're running from the web_socket_app directory")
        except Exception as e:
            print(f"❌ Error starting client: {e}")
    
    else:
        print(f"❌ Unknown mode: {mode}")
        show_usage()

if __name__ == "__main__":
    main()