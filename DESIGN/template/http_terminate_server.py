import os
import sys
import argparse
import threading
import time
import signal
from flask import Flask, request, jsonify
import logging

class TerminateHttpServer:
    def __init__(self, port=8080):
        self.app = Flask("TerminateHttpServer")
        self.port = port
        self.server_thread = None
        
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        
        @self.app.route('/status', methods=['GET'])
        def get_status():
            return jsonify({
                "status": "200",
                "server": "TerminateHttpServer",
                "pid": os.getpid()
            })
        
        @self.app.route('/terminate', methods=['POST'])
        def terminate():
            data = request.json
            if not data:
                return jsonify({"status": "500", "message": "Request data is empty"}), 500
            
            process_identifier = data.get('port')
            if not process_identifier:
                return jsonify({"status": "500", "message": "Missing process identifier ('port')"}), 500
            
            threading.Thread(target=self._exit_process, args=(process_identifier,), daemon=True).start()
            return jsonify({"status": "200", "message": f"Termination signal sent to process {process_identifier}"}), 200
    
    def _exit_process(self, process_identifier):
        print(f"Received termination request for process {process_identifier}...")
        try:
            pid = int(process_identifier)
            os.kill(pid, signal.SIGTERM)
            print(f"Sent SIGTERM to PID {pid}")
        except (ValueError, TypeError):
            print(f"'{process_identifier}' is not a valid PID, attempting to terminate by name.")
            self._terminate_by_name(str(process_identifier))
        except Exception as e:
            print(f"Error terminating process: {e}")
    
    def _terminate_by_name(self, process_name):
        try:
            import psutil
            found = False
            for proc in psutil.process_iter(['pid', 'name']):
                if process_name.lower() in proc.info['name'].lower():
                    print(f"Found matching process: {proc.info['name']} (PID: {proc.info['pid']})")
                    os.kill(proc.info['pid'], signal.SIGTERM)
                    print(f"Sent SIGTERM to process {proc.info['pid']}")
                    found = True
            if not found:
                print(f"No process found with name matching '{process_name}'")
        except ImportError:
            print("`psutil` library is required to terminate by name. Please install it using `pip install psutil`.")
        except Exception as e:
            print(f"Error terminating process by name: {e}")
    
    def start(self):
        try:
            self.server_thread = threading.Thread(
                target=lambda: self.app.run(host='localhost', port=self.port, debug=False, use_reloader=False),
                daemon=True
            )
            self.server_thread.start()
            print(f"HTTP termination server started on port: {self.port}")
        except Exception as e:
            print(f"Failed to start HTTP server: {e}")
            raise
                    
    def stop(self):
        if self.server_thread:
            print("Shutting down HTTP termination server...")
            os.kill(os.getpid(), signal.SIGINT)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    
    server = None
    try:
        server = TerminateHttpServer(port=args.port)
        server.start()
        print(f"Server listening on port: {server.port}")
        print("Use Ctrl+C to stop the server")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Server runtime error: {e}")
    finally:
        if server:
            server.stop()
        print("Server has been shut down.")
        sys.exit(0)

if __name__ == "__main__":
    main()