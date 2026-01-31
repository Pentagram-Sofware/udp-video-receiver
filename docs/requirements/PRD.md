# Product Requirements Document (PRD)

## Product Name
Raspberry Pi Camera Streamer

## Problem Statement
We need a product that captures video from a Raspberry Pi compatible camera and encodes it efficiently for internet streaming using a standard format. The current codebase focuses on receiving and displaying JPEG frames over UDP and lacks a production-grade capture, encoding, and streaming pipeline.

## Key Source Facts From This Project
- **Camera/Platform**: Raspberry Pi 5 + Pi Camera v2.1
- **Capture Stack**: Picamera2 is referenced in project docs

## Goals
- Capture live video from the Pi Camera v2.1 on Raspberry Pi 5.
- Encode video with an efficient, standard codec suitable for internet streaming.
- Stream over common protocols with reasonable latency and robustness.
- Provide a receiver client or standard player compatibility.

## Non-Goals
- Implement advanced video analytics or AI inference.
- Provide full web UI for configuration (CLI or config file is sufficient for MVP).
- Multi-camera aggregation (single camera stream first).

## Users
- Developers building a Pi-based camera stream.
- End users who view live camera streams on desktop or mobile.

## Assumptions
- The device is a Raspberry Pi 5 with a connected Pi Camera v2.1.
- The network environment can be variable (WAN, NAT, jitter).
- Hardware-accelerated encoding (where available) is preferred.

## Functional Requirements
1. **Camera Capture**
   - Use Pi Camera v2.1 via `Picamera2`.
   - Support configurable resolution and frame rate (e.g., 1280x720 @ 30 FPS).
2. **Encoding**
   - Encode using **H.264/AVC** (baseline or main profile).
   - Configurable bitrate, keyframe interval, and profile.
3. **Transport / Streaming**
   - Provide at least one standard streaming protocol:
     - **RTSP (RTP over UDP/TCP)** OR **WebRTC**.
   - Allow selecting transport at runtime.
4. **Client Playback**
   - Stream playable in standard players (e.g., VLC for RTSP).
   - Provide a simple receiver/preview client (CLI is acceptable).
5. **Configuration**
   - Single config file (YAML/JSON) or CLI flags for camera + encoding + transport.
6. **Logging & Metrics**
   - Log frame rate, bitrate, and encoder stats.
   - Basic health status (camera ready, streaming active).

## Non-Functional Requirements
1. **Latency**
   - Target < 500 ms end-to-end in LAN conditions.
2. **Reliability**
   - Recover from temporary network dropouts without crashing.
3. **Security**
   - If internet-exposed, provide at least one of:
     - Password-protected RTSP
     - DTLS/SRTP in WebRTC
4. **Resource Usage**
   - Prefer hardware-accelerated encoding to keep CPU < 50% on Pi 5.
5. **Extensibility**
   - Design the capture pipeline to optionally fork frames for future AI processing.
   - Ensure the AI path can be enabled without disrupting streaming.

## Constraints
- Must run on Raspberry Pi 5 OS with Python 3.x.
- Camera is Pi Camera v2.1, accessed via Picamera2.

## Out of Scope (for MVP)
- Multi-user access control or user management.
- Video recording / archival.
- Advanced QoS or adaptive bitrate streaming.
 - AI inference on-device (future extension only).

## Missing Elements in the Current Project
1. **Server-Side Capture Pipeline**
   - No server component for camera capture or streaming.
2. **Standard Video Encoding**
   - Current design uses JPEG-per-frame, which is bandwidth heavy.
3. **Streaming Protocol Support**
   - No RTSP/WebRTC pipeline; current code uses custom UDP chunks.
4. **Network Robustness**
   - No FEC/retransmit or jitter buffer for WAN.
5. **Security**
   - No authentication or encryption.
6. **Operational Controls**
   - No configuration, health checks, or telemetry.
7. **Extensible Frame Pipeline**
   - No hook or interface to branch frames for future AI processing.

## Open Questions
- Preferred streaming protocol for MVP: RTSP or WebRTC?
- Required latency budget (real-time vs. near-real-time)?
- Is VLC compatibility sufficient, or do we need a browser-based client?

