
import time
import threading
import sys
from queue import Queue, Empty
from typing import Optional
from datetime import datetime

class StreamingLoggerWrapper:
    """
    A wrapper around the existing Logger class that provides streaming output functionality.
    This preserves the original timestamp behavior by handling terminal output separately.
    """
    
    def __init__(self, logger_instance, stream_enabled: bool = False, stream_delay: float = 0.05):
        """
        Initialize the streaming logger wrapper.
        
        :param logger_instance: The existing Logger instance
        :param stream_enabled: Whether to enable streaming output
        :param stream_delay: Delay between each line output (in seconds)
        """
        self._logger = logger_instance
        self.stream_enabled = stream_enabled
        self.stream_delay = stream_delay
        self._stream_queue = Queue()
        self._streaming_thread = None
        self._stop_streaming = threading.Event()
        
        # Get the color mapping from the original logger for terminal output
        self._color_mapping = {
            "stage": '**\n# Current Stage: {}\n',
            "action": '## Current Action: {}\n',
            "prompt": '### Prompt: \n{}\n',
            "response": '### Response: \n{}\n',
            "success": '#### Success: {}\n',
            "error": '#### Error: \n{}\n',
            "warning": '#### Warning: \n{}\n',
            "info": '#### Info: \n{}\n',
            "debug": '#### Debug: \n{}\n',
        }
        
        # Map levels to logger methods
        self._log_methods = {
            "stage": self._logger._logger.info,
            "action": self._logger._logger.debug,
            "prompt": self._logger._logger.debug,
            "response": self._logger._logger.info,
            "success": self._logger._logger.info,
            "error": self._logger._logger.error,
            "warning": self._logger._logger.warning,
            "info": self._logger._logger.info,
            "debug": self._logger._logger.debug,
        }
        
    def set_streaming(self, enabled: bool, delay: float = 0.05):
        """
        Enable or disable streaming output.
        
        :param enabled: Whether to enable streaming
        :param delay: Delay between lines when streaming
        """
        self.stream_enabled = enabled
        self.stream_delay = delay
        
    def _stream_worker(self):
        """
        Worker thread that processes the streaming queue and outputs lines one by one.
        """
        while not self._stop_streaming.is_set():
            try:
                # Get item from queue with timeout
                item = self._stream_queue.get(timeout=0.1)
                content, level, timestamp = item
                
                if content is None:  # Sentinel value to stop
                    break
                    
                # Split content into lines
                lines = content.split('\n')
                
                # Get the log method for this level
                log_method = self._log_methods.get(level, self._logger._logger.info)
                
                # Stream each line with delay and single timestamp
                for i, line in enumerate(lines):
                    if self._stop_streaming.is_set():
                        break
                    
                    # Only add timestamp to the first line
                    if i == 0:
                        content_with_timestamp = f"{timestamp}:{line}"
                        log_method(content_with_timestamp)
                    else:
                        if line.strip(): 
                            log_method(line)
                        elif line == '':
                            print()
                    
                    # Add delay between lines
                    if not self._stop_streaming.wait(self.stream_delay):
                        continue
                        
                self._stream_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                print(f"Error in streaming worker: {e}")
                
    def _start_streaming_thread(self):
        """Start the streaming worker thread if not already running."""
        if self._streaming_thread is None or not self._streaming_thread.is_alive():
            self._stop_streaming.clear()
            self._streaming_thread = threading.Thread(target=self._stream_worker, daemon=True)
            self._streaming_thread.start()
            
    def _stop_streaming_thread(self):
        """Stop the streaming worker thread."""
        if self._streaming_thread and self._streaming_thread.is_alive():
            self._stop_streaming.set()
            # Add sentinel value to wake up the worker
            self._stream_queue.put((None, None, None))
            self._streaming_thread.join(timeout=1.0)
            
    def log(self, content: str, level: str = "info", print_to_terminal: bool = True):
        """
        Log content with optional streaming output.
        
        :param content: The message content to be formatted and logged
        :param level: The log level/style
        :param print_to_terminal: Whether to print to terminal
        """
        if self.stream_enabled and print_to_terminal:
            # Generate single timestamp for the entire content
            timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S:%f]")
            
            # Start streaming thread if needed
            self._start_streaming_thread()
            
            # Add content to streaming queue with timestamp
            self._stream_queue.put((content, level, timestamp))
            
            # Log to file immediately (non-streaming, no terminal output)
            self._logger.log(content, level, print_to_terminal=False)
            
        else:
            # Use original logging behavior
            self._logger.log(content, level, print_to_terminal)
            
    def flush_streaming(self):
        """Wait for all streaming output to complete."""
        if self.stream_enabled:
            self._stream_queue.join()
            
    def cleanup(self):
        """Clean up streaming resources."""
        self._stop_streaming_thread()
        
    # Delegate other methods to the original logger
    def set_file(self, file):
        """Set the log file."""
        return self._logger.set_file(file)
        
    def is_file_exists(self):
        """Check if log file exists."""
        return self._logger.is_file_exists()
        
    def __del__(self):
        """Cleanup when object is destroyed."""
        self.cleanup()