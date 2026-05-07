#!/usr/bin/env python3
"""
Startup script for PDF2MD Converter
Starts both backend and frontend servers
"""

import subprocess
import sys
import os
import time
import signal
from pathlib import Path

def start_backend():
    """Start the FastAPI backend server"""
    print("🚀 Starting backend server...")
    backend_dir = Path(__file__).parent / "backend"
    
    # Check if virtual environment exists
    venv_python = backend_dir / "venv" / "Scripts" / "python.exe"  # Windows
    if not venv_python.exists():
        venv_python = backend_dir / "venv" / "bin" / "python"  # Linux/Mac
    
    if venv_python.exists():
        python = str(venv_python)
    else:
        python = sys.executable
    
    cmd = [
        python, "-m", "uvicorn",
        "app.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
    ]
    
    return subprocess.Popen(
        cmd,
        cwd=str(backend_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

def start_frontend():
    """Start the React frontend development server"""
    print("🚀 Starting frontend server...")
    frontend_dir = Path(__file__).parent / "frontend"
    
    cmd = ["npm", "start"]
    
    return subprocess.Popen(
        cmd,
        cwd=str(frontend_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

def main():
    """Main function to start both servers"""
    print("=" * 60)
    print("📝 PDF2MD Converter - Starting servers...")
    print("=" * 60)
    
    processes = []
    
    try:
        # Start backend
        backend_proc = start_backend()
        processes.append(("Backend", backend_proc))
        time.sleep(2)  # Wait for backend to initialize
        
        # Start frontend
        frontend_proc = start_frontend()
        processes.append(("Frontend", frontend_proc))
        
        print("\n" + "=" * 60)
        print("✅ Both servers started successfully!")
        print("=" * 60)
        print("\n📱 Frontend: http://localhost:3000")
        print("🔌 Backend API: http://localhost:8000")
        print("📚 API Docs: http://localhost:8000/docs")
        print("\nPress Ctrl+C to stop all servers\n")
        
        # Wait for processes and print output
        while True:
            for name, proc in processes:
                # Check if process is still running
                if proc.poll() is not None:
                    print(f"\n❌ {name} server stopped unexpectedly!")
                    return 1
                
                # Print output
                try:
                    stdout_line = proc.stdout.readline()
                    if stdout_line:
                        print(f"[{name}] {stdout_line.strip()}")
                except:
                    pass
                
                try:
                    stderr_line = proc.stderr.readline()
                    if stderr_line:
                        print(f"[{name} ERROR] {stderr_line.strip()}", file=sys.stderr)
                except:
                    pass
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down servers...")
        
        # Terminate all processes
        for name, proc in processes:
            print(f"  Stopping {name}...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except:
                proc.kill()
        
        print("✅ All servers stopped")
        return 0
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        
        # Cleanup
        for name, proc in processes:
            proc.terminate()
        
        return 1

if __name__ == "__main__":
    sys.exit(main())