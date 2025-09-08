#!/usr/bin/env python3
"""
Enhanced UDP Video Client - Uses advanced video display capabilities
"""

import cv2
import socket
import struct
import pickle
import time
import threading
import zlib
from collections import defaultdict
from video_display import VideoDisplay, MultiWindowDisplay


class EnhancedUDPVideoClient:
    """Enhanced UDP Video Client with advanced display options"""
    
    def __init__(self, server_host, server_port=9999, client_port=0, display_mode="single"):
        self.server_host = server_host
        self.server_port = server_port
        self.client_port = client_port
        self.running = False
        
        # Socket setup
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if client_port:
            self.socket.bind(('', client_port))
        else:
            self.socket.bind(('', 0))
            self.client_port = self.socket.getsockname()[1]
            
        print(f"Client bound to port {self.client_port}")
        
        # Frame handling
        self.frame_buffers = defaultdict(dict)
        self.frame_info = {}
        
        # Statistics
        self.frames_received = 0
        self.start_time = None
        self.last_stats_time = None
        
        # Display setup
        self.display_mode = display_mode
        if display_mode == "single":
            self.display = VideoDisplay("Enhanced UDP Video Stream", (1024, 768))
            self.display.on_key_press = self._handle_key_press
        elif display_mode == "multi":
            self.multi_display = MultiWindowDisplay()
            self.main_display = self.multi_display.add_display("main", "Main Stream", (800, 600))
            self.mini_display = self.multi_display.add_display("mini", "Mini View", (400, 300))
            self.stats_display = self.multi_display.add_display("stats", "Statistics", (300, 200))
            
            # Set key handlers
            self.main_display.on_key_press = self._handle_key_press
            self.mini_display.on_key_press = self._handle_key_press
            
        # Threading
        self.stats_thread = None
        
    def _handle_key_press(self, key):
        """Handle key presses from display windows"""
        if key == ord('q') or key == 27:  # Quit
            self.running = False
            return True
        elif key == ord('m'):  # Switch display mode
            print("Display mode switching not implemented during runtime")
        elif key == ord('p'):  # Print current stats
            self._print_current_stats()
            
        return False
        
    def _print_current_stats(self):
        """Print current statistics"""
        if self.start_time:
            runtime = time.time() - self.start_time
            fps = self.frames_received / runtime if runtime > 0 else 0
            print(f"\n=== Current Stats ===")
            print(f"Frames received: {self.frames_received}")
            print(f"Runtime: {runtime:.1f}s")
            print(f"Current FPS: {fps:.1f}")
            print(f"==================\n")
        
    def start_receiving(self):
        """Start receiving video stream"""
        try:
            print(f"Requesting stream from {self.server_host}:{self.server_port}")
            print(f"Client listening on port {self.client_port}")
            
            # Register with server
            print("Registering with server...")
            self.socket.sendto(b"REGISTER_CLIENT", (self.server_host, self.server_port))
            
            # Wait for acknowledgment
            self.socket.settimeout(5.0)
            data, addr = self.socket.recvfrom(1024)
            if data == b"REGISTERED":
                print(f"Successfully registered with server {addr}")
            else:
                print(f"Unexpected response: {data}")
                return
                
            self.socket.settimeout(1.0)
            self.running = True
            
            # Start display
            if self.display_mode == "single":
                self.display.start()
            elif self.display_mode == "multi":
                self.multi_display.start_all()
            
            # Start statistics thread
            self.stats_thread = threading.Thread(target=self.display_stats, daemon=True)
            self.stats_thread.start()
            
            # Initialize statistics
            self.start_time = time.time()
            self.last_stats_time = time.time()
            
            print("Receiving video stream... Press 'h' in video window for help")
            
            while self.running:
                try:
                    data, addr = self.socket.recvfrom(65536)
                    
                    # Check for documented frame formats from the server
                    if data.startswith(b"FRAME"):
                        if len(data) >= 13:  # "FRAME" (5) + size (8) = 13 bytes minimum
                            # Extract frame size (8-byte unsigned long)
                            size = struct.unpack("Q", data[5:13])[0]
                            frame_data = data[13:]
                            
                            # Process frame
                            self.process_pickled_frame(frame_data)
                            
                    elif data.startswith(b"FRAME_START"):
                        if len(data) >= 19:  # "FRAME_START" (11) + size (4) + chunk_count (4) = 19 bytes
                            # Extract frame info
                            size, chunk_count = struct.unpack("LL", data[11:19])
                            
                            # Initialize frame buffer for this large frame
                            self.large_frame_size = size
                            self.large_frame_chunks = {}
                            self.expected_chunks = chunk_count
                            
                    elif data.startswith(b"CHUNK"):
                        if len(data) >= 9:  # "CHUNK" (5) + index (4) = 9 bytes minimum
                            # Extract chunk info
                            chunk_index = struct.unpack("L", data[5:9])[0]
                            chunk_data = data[9:]
                            
                            # Store chunk
                            if hasattr(self, 'large_frame_chunks'):
                                self.large_frame_chunks[chunk_index] = chunk_data
                                
                                # Check if we have all chunks
                                if len(self.large_frame_chunks) == self.expected_chunks:
                                    # Reassemble frame
                                    frame_data = b''.join(
                                        self.large_frame_chunks[i] 
                                        for i in range(self.expected_chunks)
                                    )
                                    
                                    # Process complete frame
                                    self.process_pickled_frame(frame_data)
                                    
                                    # Clean up
                                    del self.large_frame_chunks
                                    del self.large_frame_size
                                    del self.expected_chunks
                                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"Receive error: {e}")
                    break
                    
        finally:
            try:
                print("Disconnecting from server...")
                self.socket.sendto(b"DISCONNECT", (self.server_host, self.server_port))
            except:
                pass
            self.cleanup()
            
    def process_pickled_frame(self, pickled_data):
        """Process pickled JPEG frame data from server"""
        try:
            # Deserialize pickled JPEG buffer
            jpeg_buffer = pickle.loads(pickled_data)
            
            # Decode JPEG to image
            import numpy as np
            frame_array = np.frombuffer(jpeg_buffer, dtype=np.uint8)
            frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
            
            if frame is not None:
                # Increment frame counter
                self.frames_received += 1
                
                # Update display(s)
                if self.display_mode == "single":
                    self.display.update_frame(frame)
                elif self.display_mode == "multi":
                    # Main display gets full frame
                    self.main_display.update_frame(frame)
                    
                    # Mini display gets resized frame
                    mini_frame = cv2.resize(frame, (320, 240))
                    self.mini_display.update_frame(mini_frame)
                    
                    # Stats display gets a statistics overlay
                    self._update_stats_display()
                    
        except Exception as e:
            print(f"Frame processing error: {e}")
            
    def _update_stats_display(self):
        """Update the statistics display window"""
        if not hasattr(self, 'stats_display'):
            return
            
        # Create stats visualization
        stats_frame = np.zeros((200, 300, 3), dtype=np.uint8)
        
        # Add text information
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        color = (0, 255, 0)
        thickness = 1
        
        runtime = time.time() - self.start_time if self.start_time else 0
        fps = self.frames_received / runtime if runtime > 0 else 0
        
        texts = [
            f"Frames: {self.frames_received}",
            f"Runtime: {runtime:.1f}s",
            f"FPS: {fps:.1f}",
            f"Server: {self.server_host}",
            f"Port: {self.server_port}",
        ]
        
        y_offset = 30
        for text in texts:
            cv2.putText(stats_frame, text, (10, y_offset), font, font_scale, color, thickness)
            y_offset += 25
            
        self.stats_display.update_frame(stats_frame)
        
    def display_stats(self):
        """Display periodic statistics"""
        while self.running:
            time.sleep(5.0)
            if self.running and self.start_time:
                runtime = time.time() - self.start_time
                fps = self.frames_received / runtime if runtime > 0 else 0
                
                print(f"\n--- Video Stats ---")
                print(f"Frames received: {self.frames_received}")
                print(f"Runtime: {runtime:.1f}s")
                print(f"Average FPS: {fps:.1f}")
                print(f"------------------\n")
                
    def cleanup(self):
        """Clean up resources"""
        print("\n=== Final Statistics ===")
        if self.start_time:
            total_runtime = time.time() - self.start_time
            avg_fps = self.frames_received / total_runtime if total_runtime > 0 else 0
            print(f"Total frames received: {self.frames_received}")
            print(f"Total runtime: {total_runtime:.1f}s")
            print(f"Average FPS: {avg_fps:.1f}")
        print("========================\n")
        
        # Stop displays
        if self.display_mode == "single" and hasattr(self, 'display'):
            self.display.stop()
        elif self.display_mode == "multi" and hasattr(self, 'multi_display'):
            self.multi_display.stop_all()
            
        # Close socket
        try:
            self.socket.close()
        except:
            pass
            
        print("Stopping client...")


def main():
    """Main function with enhanced options"""
    print("Enhanced UDP Video Client")
    print("1. Single Window Mode")
    print("2. Multi-Window Mode")
    
    try:
        mode_choice = input("Choose display mode (1-2): ").strip()
        display_mode = "multi" if mode_choice == "2" else "single"
        
        server_ip = input("Enter server IP: ").strip()
        if not server_ip:
            print("Server IP is required")
            return
            
        server_port = input("Enter server port (default 9999): ").strip()
        server_port = int(server_port) if server_port else 9999
        
        client_port = input("Enter client port (default auto-assign): ").strip()
        client_port = int(client_port) if client_port else 0
        
        # Create and start client
        client = EnhancedUDPVideoClient(server_ip, server_port, client_port, display_mode)
        
        print(f"\nStarting in {display_mode} mode...")
        if display_mode == "multi":
            print("Multiple windows will open:")
            print("- Main Stream: Full video display")
            print("- Mini View: Smaller video display") 
            print("- Statistics: Real-time stats")
            
        client.start_receiving()
        
    except KeyboardInterrupt:
        print("\nShutdown requested...")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
