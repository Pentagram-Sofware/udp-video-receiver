#!/usr/bin/env python3
"""
Example: How to integrate the VideoDisplay module with existing UDP client
"""

import sys
import os

# Add current directory to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import UDPVideoClient
from video_display import VideoDisplay
import cv2


class UDPClientWithEnhancedDisplay(UDPVideoClient):
    """Extended UDP client that uses the enhanced video display"""
    
    def __init__(self, server_host, server_port=9999, client_port=0, stream_format="pickle_jpeg"):
        super().__init__(server_host, server_port, client_port, stream_format=stream_format)
        
        # Replace the basic display with enhanced display
        self.video_display = VideoDisplay("Enhanced Stream View", (1024, 768))
        self.video_display.show_fps = True
        self.video_display.show_frame_count = True
        self.video_display.show_timestamp = True
        self.video_display.show_resolution = True
        
        # Set up custom key handler
        self.video_display.on_key_press = self._handle_display_keys
        
    def _handle_display_keys(self, key):
        """Handle keys from the video display"""
        if key == ord('q') or key == 27:  # Quit
            self.running = False
            return True
        elif key == ord('p'):  # Print stats
            self._print_stats()
        return False
        
    def _print_stats(self):
        """Print current statistics"""
        stats = self.video_display.get_stats()
        print(f"\n=== Display Statistics ===")
        print(f"Frames displayed: {stats['frames_displayed']}")
        print(f"Display runtime: {stats['runtime']:.1f}s")
        print(f"Current FPS: {stats['current_fps']:.1f}")
        print(f"Average FPS: {stats['average_fps']:.1f}")
        print(f"========================\n")
        
    def start_receiving(self):
        """Override to start the enhanced display"""
        # Start the video display
        self.video_display.start()
        
        # Call parent's start_receiving method
        super().start_receiving()
        
    def process_pickled_frame(self, pickled_data):
        """Override to use enhanced display"""
        try:
            # Deserialize pickled JPEG buffer
            import pickle
            import numpy as np
            
            jpeg_buffer = pickle.loads(pickled_data)
            
            # Decode JPEG to image
            frame_array = np.frombuffer(jpeg_buffer, dtype=np.uint8)
            frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
            
            if frame is not None:
                # Increment frame counter
                self.frames_received += 1
                
                # Update the enhanced display
                self.video_display.update_frame(frame)
                
                # Check if display is still running
                if not self.video_display.running:
                    self.running = False
                    
        except Exception as e:
            print(f"Frame processing error: {e}")

    def process_h264_frame(self, frame_data):
        """Override to decode H.264 frames for the enhanced display."""
        if self.h264_decoder is None:
            print("H.264 decoder not initialized. Install PyAV with: pip install av")
            self.running = False
            return

        try:
            # Parse and decode H.264 data to displayable frames.
            packets = self.h264_decoder.parse(frame_data)
            for packet in packets:
                frames = self.h264_decoder.decode(packet)
                for frame in frames:
                    image = frame.to_ndarray(format="bgr24")
                    if image is None:
                        continue

                    self.frames_received += 1
                    self.video_display.update_frame(image)

                    if not self.video_display.running:
                        self.running = False
        except Exception as e:
            print(f"H.264 frame processing error: {e}")
            
    def cleanup(self):
        """Override cleanup to stop enhanced display"""
        # Stop the video display
        if hasattr(self, 'video_display'):
            self.video_display.stop()
            
        # Call parent cleanup
        super().cleanup()


def main():
    """Main function demonstrating enhanced display integration"""
    print("UDP Video Client with Enhanced Display")
    print("Enhanced features:")
    print("- Resizable window")
    print("- Real-time FPS display")
    print("- Frame counter overlay")
    print("- Timestamp display")
    print("- Screenshot capability (press 's')")
    print("- Fullscreen toggle (press 'f')")
    print("- Statistics reset (press 'r')")
    print("- Help display (press 'h')")
    print()
    
    try:
        server_ip = input("Enter server IP: ").strip()
        if not server_ip:
            print("Server IP is required")
            return
            
        server_port = input("Enter server port (default 9999): ").strip()
        server_port = int(server_port) if server_port else 9999
        
        client_port = input("Enter client port (default auto-assign): ").strip()
        client_port = int(client_port) if client_port else 0
        
        stream_format_input = input("Stream format (jpeg/h264, default jpeg): ").strip().lower()
        stream_format = "h264" if stream_format_input == "h264" else "pickle_jpeg"

        # Create and start enhanced client
        client = UDPClientWithEnhancedDisplay(
            server_ip,
            server_port,
            client_port,
            stream_format=stream_format,
        )
        client.start_receiving()
        
    except KeyboardInterrupt:
        print("\nShutdown requested...")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
