# Transcriber deployment
------

The EKEEL Transcriber Service is a continuous transcription system that automates the process of converting YouTube videos into text transcripts using the Stable-Whisper model (large-v3), a state-of-the-art speech recognition model.

The service operates as a background worker that continuously polls a MongoDB database for untranscribed video jobs. 

For each video, it:
    
- Downloads the video from YouTube.
- Converts it into WAV format.
- Transcribes the audio using Whisper, generating accurate, multilingual text segments.
- Updates the database with the transcription and cleans up temporary files.

It's a standalone file that shouldn't be imported outside of this service to avoid unnecessary memory allocation.

## Restart the Transcriber Service

To restart the `ekeel-transcriber` service, use the following commands:

1. Open a terminal on the server.

2. Use `systemctl` to restart the service:

```bash
sudo systemctl restart ekeel-transcriber
```

3. Verify the service status to ensure it restarted successfully:

```bash
sudo systemctl status ekeel-transcriber
```

If the service is running correctly, you should see an active (running) status.


--------------
## Code

The code is available [here](../../../codebase/EKEELVideoAnnotation/transcribe.md)
