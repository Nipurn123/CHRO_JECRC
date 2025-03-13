import os
import json
import logging
import time
from typing import Optional, List, Dict, Any, Union
import subprocess
import shutil
import glob
import tempfile

logger = logging.getLogger(__name__)

class FileSystemAgent:
    """Enhanced agent responsible for file system operations through terminal commands"""
    
    def __init__(self, base_dir: str = "research_output"):
        self.base_dir = os.path.abspath(base_dir)
        self.current_session = None
        self.session_dirs = {
            'data': 'data',
            'logs': 'logs', 
            'reports': 'reports',
            'temp': 'temp',
            'cache': 'cache'
        }
        self.status_file = 'fs_status.log'
        self._initialize_agent()
        
    def _initialize_agent(self):
        """Initialize the file system agent"""
        try:
            # Create base directory structure
            self._run_command(f"mkdir -p {self.base_dir}")
            
            # Initialize status logging
            status_path = os.path.join(self.base_dir, self.status_file)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            init_status = f"[{timestamp}] FileSystemAgent initialized at: {self.base_dir}\n"
            self._run_command(f"echo '{init_status}' > {status_path}")
            
        except Exception as e:
            logger.error(f"Initialization failed: {str(e)}")
            raise
        
    def create_session(self, prefix: str = "") -> str:
        """Create a new session directory with timestamp and optional prefix"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        session_name = f"session_{prefix}_{timestamp}" if prefix else f"session_{timestamp}"
        session_path = os.path.join(self.base_dir, session_name)
        
        try:
            # Create session directory with all subdirectories
            for dir_name in self.session_dirs.values():
                dir_path = os.path.join(session_path, dir_name)
                result = self._run_command(f"mkdir -p {dir_path}")
                if result is None:
                    raise Exception(f"Failed to create directory: {dir_path}")
            
            self.current_session = session_path
            self._log_status(f"Created new session at: {session_path}")
            
            # Create session metadata
            metadata = {
                'created_at': time.strftime("%Y-%m-%d %H:%M:%S"),
                'prefix': prefix,
                'directories': list(self.session_dirs.values()),
                'status': 'active'
            }
            self.save_content(metadata, 'session_metadata.json', 'json')
            
            return session_path
            
        except Exception as e:
            error_msg = f"Session creation failed: {str(e)}"
            self._log_status(error_msg, is_error=True)
            raise Exception(error_msg)
        
    def save_content(self, content: Any, filename: str, content_type: str = 'text', backup: bool = True) -> bool:
        """Enhanced save content with backup option"""
        if not self.current_session:
            self.create_session()
            
        try:
            file_path = os.path.join(self.current_session, filename)
            
            # Create backup if file exists and backup is requested
            if backup and os.path.exists(file_path):
                backup_path = f"{file_path}.bak.{int(time.time())}"
                self._run_command(f"cp {file_path} {backup_path}")
            
            # Prepare content based on type
            if content_type == 'json':
                json_str = json.dumps(content, indent=2, ensure_ascii=False)
                # Use temporary file for atomic write
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
                    temp.write(json_str)
                    temp_path = temp.name
                self._run_command(f"mv {temp_path} {file_path}")
            else:
                # Escape content and use temporary file
                escaped_content = str(content).replace("'", "'\\''")
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
                    temp.write(escaped_content)
                    temp_path = temp.name
                self._run_command(f"mv {temp_path} {file_path}")
            
            self._log_status(f"Saved {content_type} content to: {file_path}")
            return True
            
        except Exception as e:
            self._log_status(f"Error saving content: {str(e)}", is_error=True)
            return False
        
    def append_content(self, content: str, filename: str, with_timestamp: bool = True) -> bool:
        """Enhanced append content with timestamp option"""
        if not self.current_session:
            self.create_session()
            
        try:
            file_path = os.path.join(self.current_session, filename)
            
            # Prepare content with optional timestamp
            timestamp = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] " if with_timestamp else ""
            escaped_content = f"{timestamp}{content}".replace("'", "'\\''")
            
            # Use temporary file for atomic append
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
                temp.write(escaped_content + "\n")
                temp_path = temp.name
            
            self._run_command(f"cat {temp_path} >> {file_path}")
            self._run_command(f"rm {temp_path}")
            
            self._log_status(f"Appended content to: {file_path}")
            return True
            
        except Exception as e:
            self._log_status(f"Error appending content: {str(e)}", is_error=True)
            return False
        
    def read_content(self, filename: str, content_type: str = 'text', tail_lines: int = None) -> Optional[Any]:
        """Enhanced read content with tail option"""
        if not self.current_session:
            return None
            
        try:
            file_path = os.path.join(self.current_session, filename)
            
            if not os.path.exists(file_path):
                self._log_status(f"File not found: {file_path}", is_error=True)
                return None
            
            # Build command based on options
            if tail_lines:
                command = f"tail -n {tail_lines} {file_path}"
            else:
                command = f"cat {file_path}"
                
            result = self._run_command(command)
            
            if content_type == 'json' and result:
                return json.loads(result)
            return result
            
        except Exception as e:
            self._log_status(f"Error reading content: {str(e)}", is_error=True)
            return None
        
    def _run_command(self, command: str, capture_error: bool = True) -> Optional[str]:
        """Enhanced command execution with error capture"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                capture_output=True,
                text=True
            )
            
            if result.stderr and capture_error:
                self._log_status(f"Command warning: {result.stderr}", is_error=True)
                
            return result.stdout.strip()
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Command failed: {str(e)}\nOutput: {e.output}\nError: {e.stderr}"
            self._log_status(error_msg, is_error=True)
            return None
        
    def _log_status(self, message: str, is_error: bool = False):
        """Log status to status file"""
        try:
            status_path = os.path.join(self.base_dir, self.status_file)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            status_line = f"[{timestamp}] {'ERROR: ' if is_error else ''}{message}\n"
            
            # Append status to log file
            self._run_command(f"echo '{status_line}' >> {status_path}", capture_error=False)
            
            # Also log to python logger
            if is_error:
                logger.error(message)
            else:
                logger.info(message)
                
        except Exception as e:
            logger.error(f"Status logging failed: {str(e)}")
        
    def get_session_path(self) -> Optional[str]:
        """Get the current session path"""
        return self.current_session
        
    def create_file_structure(self, structure: Dict[str, Any], base_path: str = "") -> bool:
        """Enhanced file structure creation with validation"""
        if not self.current_session:
            self.create_session()
            
        try:
            for name, content in structure.items():
                path = os.path.join(self.current_session, base_path, name)
                
                if isinstance(content, dict):
                    # Create directory and recurse
                    result = self._run_command(f"mkdir -p {path}")
                    if result is None:
                        raise Exception(f"Failed to create directory: {path}")
                    self.create_file_structure(content, os.path.join(base_path, name))
                else:
                    # Create file with content
                    self.save_content(content, os.path.join(base_path, name))
                    
            self._log_status(f"Created file structure at: {base_path or 'root'}")
            return True
            
        except Exception as e:
            self._log_status(f"Error creating file structure: {str(e)}", is_error=True)
            return False
            
    def cleanup_old_sessions(self, days_old: int = 7) -> bool:
        """Clean up old session directories"""
        try:
            # Find old sessions
            find_cmd = f"find {self.base_dir} -type d -name 'session_*' -mtime +{days_old}"
            old_sessions = self._run_command(find_cmd)
            
            if not old_sessions:
                self._log_status(f"No sessions older than {days_old} days found")
                return True
                
            # Remove old sessions
            for session in old_sessions.split('\n'):
                if session.strip():
                    self._run_command(f"rm -rf {session}")
                    self._log_status(f"Removed old session: {session}")
                    
            return True
            
        except Exception as e:
            self._log_status(f"Cleanup failed: {str(e)}", is_error=True)
            return False
            
    def compress_session(self, compression: str = 'gzip') -> Optional[str]:
        """Compress current session directory"""
        if not self.current_session:
            return None
            
        try:
            session_name = os.path.basename(self.current_session)
            archive_name = f"{session_name}.tar.gz"
            archive_path = os.path.join(self.base_dir, archive_name)
            
            # Create tar archive
            tar_cmd = f"tar -czf {archive_path} -C {os.path.dirname(self.current_session)} {session_name}"
            self._run_command(tar_cmd)
            
            self._log_status(f"Compressed session to: {archive_path}")
            return archive_path
            
        except Exception as e:
            self._log_status(f"Compression failed: {str(e)}", is_error=True)
            return None 