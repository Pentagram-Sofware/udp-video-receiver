# Project Plan (Linear-Ready)

This plan is structured for easy transfer into Linear as Projects (milestones)
with Issues (tasks) and explicit dependencies.

## Projects (Milestones)
- M0 Decisions and Setup
- M1 Capture and Encode
- M2 WebRTC Streaming
- M3 RTSP Streaming
- M4 Reliability, Config, and Ops
- M5 Documentation and Handoff

## Issues (Tasks)

### M0 Decisions and Setup
- M0-1 Validate Pi 5 H.264 HW encoder path (Picamera2 + stack)
- M0-2 Choose WebRTC stack (GStreamer webrtcbin vs aiortc)
- M0-3 Choose RTSP server approach (mediamtx vs GStreamer RTSP server)
- M0-4 Environment setup checklist and decision log

### M1 Capture and Encode
- M1-1 Implement Picamera2 capture (configurable FPS/resolution)
- M1-2 Implement H.264 encoder config (bitrate/profile/GOP)
- M1-3 Log FPS/bitrate/encoder status

### M2 WebRTC Streaming
- M2-1 WebRTC pipeline on Pi (RTP/DTLS/SRTP)
- M2-2 Minimal signaling server
- M2-3 Browser playback client (HTML/JS)
- M2-4 Reconnect logic and basic health checks

### M3 RTSP Streaming
- M3-1 RTSP endpoint for VLC/ffplay
- M3-2 Validate selectable or parallel WebRTC/RTSP modes
- M3-3 RTSP usage documentation

### M4 Reliability, Config, and Ops
- M4-1 Config file + CLI flags
- M4-2 Health endpoint and logging improvements
- M4-3 Basic security (RTSP auth, WebRTC DTLS/SRTP config)

### M5 Documentation and Handoff
- M5-1 Update `docs/architecture/ARC42.md` and ADRs
- M5-2 Deployment instructions + usage examples
- M5-3 Release checklist

## Dependencies
- M1 depends on M0.
- M2 depends on M1.
- M3 can start after M1 and finalize after M2 decisions.
- M4 depends on stable M2 and M3 behavior.
- M5 depends on M4 completion.

## Linear Import (CSV Template)

Use this CSV format for Linear import. Fill in assignees and dates as needed.

```
issue_title,issue_description,project,status,priority,estimate,labels,blocked_by
M0-1 Validate H264 HW encoder path,Confirm Picamera2 + HW H.264 pipeline on Pi 5,M0 Decisions and Setup,Todo,High,3,architecture,
M0-2 Choose WebRTC stack,Decide between GStreamer webrtcbin or aiortc,M0 Decisions and Setup,Todo,High,2,architecture,
M0-3 Choose RTSP server,Decide between mediamtx or GStreamer RTSP server,M0 Decisions and Setup,Todo,Medium,2,architecture,
M0-4 Setup checklist and decision log,Document tooling setup and decisions,M0 Decisions and Setup,Todo,Medium,2,process,
M1-1 Picamera2 capture,Configurable FPS and resolution,M1 Capture and Encode,Todo,High,5,backend,M0-1
M1-2 H264 encoder config,Bitrate/profile/GOP settings,M1 Capture and Encode,Todo,High,3,backend,M1-1
M1-3 Encoder metrics logging,FPS/bitrate/status logging,M1 Capture and Encode,Todo,Medium,2,observability,M1-2
M2-1 WebRTC pipeline,RTP + SRTP/DTLS pipeline on Pi,M2 WebRTC Streaming,Todo,High,5,streaming,M1-2
M2-2 Signaling server,Minimal signaling for browser client,M2 WebRTC Streaming,Todo,High,3,backend,M2-1
M2-3 Browser client,Basic HTML/JS playback,M2 WebRTC Streaming,Todo,High,3,frontend,M2-2
M2-4 Reconnect and health,Reconnect logic + health checks,M2 WebRTC Streaming,Todo,Medium,2,observability,M2-3
M3-1 RTSP endpoint,Expose RTSP stream for VLC,M3 RTSP Streaming,Todo,High,3,streaming,M1-2
M3-2 Mode validation,Selectable or parallel WebRTC/RTSP,M3 RTSP Streaming,Todo,Medium,2,streaming,M3-1
M3-3 RTSP docs,Usage instructions for VLC/ffplay,M3 RTSP Streaming,Todo,Low,1,docs,M3-2
M4-1 Config + CLI,Single config file and flags,M4 Reliability, Config, and Ops,Todo,High,3,ops,"M2-4;M3-2"
M4-2 Health + logging,Health endpoint and improved logs,M4 Reliability, Config, and Ops,Todo,Medium,2,ops,M4-1
M4-3 Basic security,RTSP auth + WebRTC security config,M4 Reliability, Config, and Ops,Todo,High,3,security,M4-2
M5-1 Update ARC42 and ADRs,Architecture docs update,M5 Documentation and Handoff,Todo,Medium,2,docs,M4-3
M5-2 Deployment docs,Setup and usage examples,M5 Documentation and Handoff,Todo,Medium,2,docs,M5-1
M5-3 Release checklist,Final release readiness list,M5 Documentation and Handoff,Todo,Low,1,process,M5-2
```
