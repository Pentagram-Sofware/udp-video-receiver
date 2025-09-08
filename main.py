#!/usr/bin/env python3
"""
UDP Video Client - receives UDP video streams
"""

import cv2
import socket
import struct
import pickle
import time
import threading
import zlib
from collections import defaultdict

class UDPVideoClient:
    """Client for client-server UDP streaming"""
    
    def __init__(self, server_host, server_port=9999, client_port=9999):
        self.server_host = server_host
        self.server_port = server_port
        self.client_port = client_port  # 0 = auto-assign
        self.running = False

        # Socket setup
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.settimeout(5.0)
        
        # Bind to local port (so server knows where to send data)
        self.socket.bind(('', self.client_port))
        actual_port = self.socket.getsockname()[1]
        print(f"Client bound to port {actual_port}")
        
        # Frame reassembly for v1.1 protocol
        self.payload_size = 1200
        self.pending_frames = {}   # frame_id -> bytearray(frame_size)
        self.expected_chunks = {}  # frame_id -> remaining chunk count
        self.received_chunks = {}  # frame_id -> set of received chunk indices
        
        # Statistics tracking
        self.frames_received = 0
        self.start_time = None
        self.last_stats_time = 0
        
    def send_keepalive(self):
        """Send periodic keep-alive messages"""
        while self.running:
            try:
                self.socket.sendto(b"KEEPALIVE", (self.server_host, self.server_port))
                time.sleep(5)  # Send keepalive every 5 seconds
            except:
                break
                
    def display_stats(self):
        """Display statistics every 5 seconds"""
        while self.running:
            try:
                time.sleep(5)  # Update stats every 5 seconds
                if self.running and self.start_time:
                    current_time = time.time()
                    elapsed = current_time - self.start_time
                    fps = self.frames_received / elapsed if elapsed > 0 else 0
                    
                    print(f"\n--- Video Stats ---")
                    print(f"Frames received: {self.frames_received}")
                    print(f"Runtime: {elapsed:.1f}s")
                    print(f"Average FPS: {fps:.1f}")
                    print(f"------------------\n")
            except:
                break
                
    def start_receiving(self):
        """Start receiving video stream"""
        self.running = True
        
        try:
            # Get client's actual port
            client_ip, client_port = self.socket.getsockname()
            
            # Request stream start with client info
            print(f"Requesting stream from {self.server_host}:{self.server_port}")
            print(f"Client listening on port {client_port}")
            
            # Send client registration request (single-socket NAT-friendly)
            print("Registering with server...")
            self.socket.sendto(b"REGISTER_CLIENT", (self.server_host, self.server_port))
            
            # Wait for acknowledgment
            ack_data, server_addr = self.socket.recvfrom(1024)
            if ack_data == b"REGISTERED":
                print(f"Successfully registered with server {server_addr}")
            else:
                print(f"Registration failed. Server response: {ack_data}")
                return
                
            # Start keep-alive thread
            keepalive_thread = threading.Thread(target=self.send_keepalive)
            keepalive_thread.daemon = True
            keepalive_thread.start()
            
            # Start statistics thread
            stats_thread = threading.Thread(target=self.display_stats)
            stats_thread.daemon = True
            stats_thread.start()
            
            # Initialize statistics
            self.start_time = time.time()
            
            print("Receiving video stream... Press 'q' to quit")
            
            while self.running:
                try:
                    data, addr = self.socket.recvfrom(65536)
                    
                    # Skip registration acknowledgment
                    if data == b"REGISTERED":
                        continue
                    
                    # Protocol v1.1: Always-chunked format with frame_id
                    if data.startswith(b"FRAME_START"):
                        # Server uses struct.pack("LLL", frame_id, size, chunk_count)
                        # On Pi, L might be 64-bit, making packet 35 bytes: 11 + 8 + 8 + 8 = 35
                        if len(data) == 35:  # 64-bit L format
                            try:
                                frame_id, frame_size, chunk_count = struct.unpack("LLL", data[11:35])
                                if frame_size > 0:
                                    self.pending_frames[frame_id] = bytearray(frame_size)
                                    self.expected_chunks[frame_id] = chunk_count
                                    self.received_chunks[frame_id] = set()
                                    continue
                            except Exception:
                                pass
                        
                        # Fallback: try 32-bit format
                        elif len(data) >= 23:  # 32-bit format
                            try:
                                frame_id, frame_size, chunk_count = struct.unpack("III", data[11:23])
                                if frame_size > 0:
                                    self.pending_frames[frame_id] = bytearray(frame_size)
                                    self.expected_chunks[frame_id] = chunk_count
                                    self.received_chunks[frame_id] = set()
                                    continue
                            except Exception:
                                pass
                        
                    elif data.startswith(b"CHUNK"):
                        # Server uses struct.pack("LL", frame_id, chunk_index)
                        # Need to determine the header size based on L size
                        header_size = 5 + (8 * 2)  # "CHUNK" + 2 * sizeof(L) - assume 64-bit L
                        if len(data) >= header_size:
                            try:
                                frame_id, chunk_index = struct.unpack("LL", data[5:header_size])
                                payload = data[header_size:]
                                
                                if frame_id in self.pending_frames:
                                    # Avoid duplicate chunks
                                    if chunk_index not in self.received_chunks[frame_id]:
                                        offset = chunk_index * self.payload_size
                                        buf = self.pending_frames[frame_id]
                                        
                                        if offset < len(buf):
                                            end = min(offset + len(payload), len(buf))
                                            buf[offset:end] = payload[:end - offset]
                                            self.received_chunks[frame_id].add(chunk_index)
                                            
                                            # Check if frame is complete
                                            if len(self.received_chunks[frame_id]) >= self.expected_chunks[frame_id]:
                                                # Frame complete - process it
                                                frame_data = bytes(self.pending_frames.pop(frame_id))
                                                self.expected_chunks.pop(frame_id, None)
                                                self.received_chunks.pop(frame_id, None)
                                                self.process_pickled_frame(frame_data)
                            except Exception:
                                # Try 32-bit fallback
                                try:
                                    frame_id, chunk_index = struct.unpack("II", data[5:13])
                                    payload = data[13:]
                                    
                                    if frame_id in self.pending_frames:
                                        if chunk_index not in self.received_chunks[frame_id]:
                                            offset = chunk_index * self.payload_size
                                            buf = self.pending_frames[frame_id]
                                            
                                            if offset < len(buf):
                                                end = min(offset + len(payload), len(buf))
                                                buf[offset:end] = payload[:end - offset]
                                                self.received_chunks[frame_id].add(chunk_index)
                                                
                                                if len(self.received_chunks[frame_id]) >= self.expected_chunks[frame_id]:
                                                    frame_data = bytes(self.pending_frames.pop(frame_id))
                                                    self.expected_chunks.pop(frame_id, None)
                                                    self.received_chunks.pop(frame_id, None)
                                                    self.process_pickled_frame(frame_data)
                                except Exception:
                                    pass
                                    
                except socket.timeout:
                    print("Timeout waiting for data...")
                    continue
                except Exception as e:
                    print(f"Receive error: {e}")
                    break
                    
        except Exception as e:
            print(f"Connection error: {e}")
        finally:
            # Send disconnect message to server
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
                
                # Add frame counter overlay
                cv2.putText(frame, f"Frames: {self.frames_received}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                cv2.imshow('UDP Video Stream', frame)
                
                # Check for quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.running = False
        except Exception as e:
            print(f"Frame processing error: {e}")
            
    def display_frame(self, compressed_data):
        """Decompress and display frame"""
        try:
            # Decompress
            frame_data = zlib.decompress(compressed_data)
            
            # Decode JPEG
            import numpy as np
            frame_array = np.frombuffer(frame_data, dtype=np.uint8)
            frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
            
            if frame is not None:
                # Increment frame counter
                self.frames_received += 1
                
                # Add frame counter overlay to video
                cv2.putText(frame, f"Frames: {self.frames_received}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                cv2.imshow('UDP Video Stream', frame)
                
                # Check for quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.running = False
                    
        except Exception as e:
            print(f"Frame display error: {e}")
            
    def cleanup(self):
        """Clean up resources"""
        # Display final statistics
        if self.start_time:
            elapsed = time.time() - self.start_time
            fps = self.frames_received / elapsed if elapsed > 0 else 0
            print(f"\n=== Final Statistics ===")
            print(f"Total frames received: {self.frames_received}")
            print(f"Total runtime: {elapsed:.1f}s")
            print(f"Average FPS: {fps:.1f}")
            print(f"========================\n")
                
        cv2.destroyAllWindows()
        self.socket.close()
        
    def stop(self):
        self.running = False

class UDPBroadcastClient:
    """Client for broadcast UDP streaming"""
    
    def __init__(self, listen_port=9999):
        self.listen_port = listen_port
        self.running = False
        
        # Socket setup
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('', listen_port))  # Listen on all interfaces
        
    def start_receiving(self):
        """Start receiving broadcast video stream"""
        self.running = True
        print(f"Listening for broadcast on port {self.listen_port}")
        print("Press 'q' to quit")
        
        last_frame_id = None
        
        while self.running:
            try:
                data, addr = self.socket.recvfrom(65536)
                
                if len(data) < 12:  # Header is 12 bytes
                    continue
                    
                # Parse header
                frame_id, timestamp = struct.unpack('!IQ', data[:12])
                compressed_data = data[12:]
                
                # Skip duplicate frames (simple approach)
                if frame_id == last_frame_id:
                    continue
                last_frame_id = frame_id
                
                # Decompress and display
                try:
                    frame_data = zlib.decompress(compressed_data)
                    
                    import numpy as np
                    frame_array = np.frombuffer(frame_data, dtype=np.uint8)
                    frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
                    
                    if frame is not None:
                        # Add frame info overlay
                        cv2.putText(frame, f"Frame: {frame_id}", (10, 30), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        cv2.putText(frame, f"From: {addr[0]}", (10, 60), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        
                        cv2.imshow('UDP Broadcast Stream', frame)
                    
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break
                        
                except Exception as e:
                    print(f"Frame decode error: {e}")
                    
            except Exception as e:
                print(f"Receive error: {e}")
                break
                
        self.cleanup()
        
    def cleanup(self):
        """Clean up resources"""
        cv2.destroyAllWindows()
        self.socket.close()
        
    def stop(self):
        self.running = False

# Example usage
if __name__ == "__main__":
    print("UDP Video Client")
    print("1. Client-Server Mode (connect to specific server)")
    print("2. Broadcast Mode (listen for broadcasts)")
    
    choice = input("Choose mode (1-2): ").strip()
    
    try:
        if choice == "1":
            server_ip = input("Enter server IP: ").strip()
            if not server_ip:
                print("Server IP required")
                exit(1)
                
            server_port = input("Enter server port (default 9999): ").strip()
            server_port = int(server_port) if server_port else 9999
            
            # Always bind client to UDP 9999
            client = UDPVideoClient(server_ip, server_port, 9999)
            client.start_receiving()
            
        elif choice == "2":
            client = UDPBroadcastClient(listen_port=9999)
            client.start_receiving()
            
        else:
            print("Invalid choice")
            
    except KeyboardInterrupt:
        print("\nStopping client...")
        if 'client' in locals():
            client.stop()
    except Exception as e:
        print(f"Client error: {e}")