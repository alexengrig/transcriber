# transcriber

CLI tool for audio and video transcription using
[faster-whisper](https://github.com/SYSTRAN/faster-whisper).

On an RTX 2060 (6GB) with `large-v2`,
1 hour of audio/video is processed on average in about 9–10 minutes (≈ 6.5× realtime).

## Run in Docker

1. Put your video/audio files
   (`.mp4, .mkv, .avi, .mov, .webm, .mp3, .wav, .m4a, .aac, .flac, .ogg, .opus, .wma`)
   into `/videos`.

2. Run `docker compose run --rm worker /videos --formats txt jsonl srt` (optional: `--model medium`, `--language en`):

   ```text
   [INFO] Found 1 file(s).
   [INFO] Loading model once: large-v2 (cuda, float16)
   [INFO] Language: en
   
   [FILE 1/1]
   
   === demo.mp4 ===
   1) Preparing audio…
   [INFO] Audio duration: 00:02:47
   2) Transcribing…
   [TRANSCRIBE]  10.1% | audio 00:00:16 / 00:02:47 | rtf 3.10x | ETA 00:00:48
   [TRANSCRIBE]  17.6% | audio 00:00:29 / 00:02:47 | rtf 5.42x | ETA 00:00:25
   [TRANSCRIBE]  34.2% | audio 00:00:57 / 00:02:47 | rtf 6.42x | ETA 00:00:17
   [TRANSCRIBE]  40.8% | audio 00:01:08 / 00:02:47 | rtf 7.66x | ETA 00:00:12
   [TRANSCRIBE]  52.7% | audio 00:01:28 / 00:02:47 | rtf 7.35x | ETA 00:00:10
   [TRANSCRIBE]  70.5% | audio 00:01:57 / 00:02:47 | rtf 9.84x | ETA 00:00:05
   [TRANSCRIBE]  80.8% | audio 00:02:14 / 00:02:47 | rtf 9.01x | ETA 00:00:03
   [TRANSCRIBE]  93.7% | audio 00:02:36 / 00:02:47 | rtf 9.70x | ETA 00:00:01
   3) Writing outputs…
    → demo.txt
    → demo.jsonl
    → demo.srt
   [DONE] demo.mp4 in 00:00:16
   
   All files processed.
   ```

3. Check outputs in `/transcripts`.

### Arguments

```text
input
  Input audio or video file, directory
--outdir OUTDIR
  Output directory for transcripts
--model MODEL
  Whisper model (tiny, base, small, medium, large-v2, large-v3)
--device DEVICE
  Compute device (cpu or cuda)
--compute COMPUTE
  Compute type (gpu: float16 | cpu: int8, int8_float16, float32)
--language LANGUAGE
  Language code (auto-detect if not set)
--beam_size BEAM_SIZE
  Beam search size (higher = better quality, slower)
--no_vad
  Disable voice activity detection (VAD)
--progress_step PROGRESS_STEP
  Progress update interval in seconds
--keep_wav
  Keep extracted WAV file
--no_enhance_audio
  Disable audio enhancement
--formats {txt,jsonl,srt} [...]
  Output formats (txt, jsonl, srt)
```

## Formats

### YouTube-like text

```text
0:00 You may you use this X right here to get the oh, oh my gosh. I just do that. Hold on
0:08 You know what I'm gonna
0:12 Search for a solution. Let's see video
0:16 Maybe this guy can help me
0:19 There we go, hey
```

### [JSON lines](https://en.wikipedia.org/wiki/JSON_streaming#JSONL)

```json lines
{
  "start": 0.11,
  "end": 5.93,
  "text": "You may you use this X right here to get the oh, oh my gosh. I just do that. Hold on",
  "source": "demo.mp4"
}
{
  "start": 8.81,
  "end": 10.81,
  "text": "You know what I'm gonna",
  "source": "demo.mp4"
}
{
  "start": 12.11,
  "end": 14.37,
  "text": "Search for a solution. Let's see video",
  "source": "demo.mp4"
}
{
  "start": 16.27,
  "end": 18.27,
  "text": "Maybe this guy can help me",
  "source": "demo.mp4"
}
{
  "start": 19.29,
  "end": 21.25,
  "text": "There we go, hey",
  "source": "demo.mp4"
}
```

### [SRT](https://en.wikipedia.org/wiki/SubRip)

```text
1
00:00:00,110 --> 00:00:05,930
You may you use this X right here to get the oh, oh my gosh. I just do that. Hold on

2
00:00:08,810 --> 00:00:10,810
You know what I'm gonna

3
00:00:12,110 --> 00:00:14,370
Search for a solution. Let's see video

4
00:00:16,270 --> 00:00:18,270
Maybe this guy can help me

5
00:00:19,290 --> 00:00:21,250
There we go, hey
```

## GPU / CUDA versions

Run `nvidia-smi` on your host:

```text
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 560.70                 Driver Version: 560.70         CUDA Version: 12.6     |
+-----------------------------------------------------------------------------------------+

From the output, note:

```text
Driver Version: 560.70
CUDA Version: 12.6
```

Update `VERSION` in the [Dockerfile](Dockerfile):

```text
FROM nvidia/cuda:{VERSION}-cudnn-runtime-ubuntu22.04
```

Use the same or a lower CUDA version than reported by nvidia-smi.

Example:

- CUDA Version: 12.6 → 12.6, 12.5, 12.4, …
- If it does not start, try a lower version (recommended: 11.8).

Official NVIDIA CUDA–driver compatibility:

- https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/index.html#id8
- https://docs.nvidia.com/deploy/cuda-compatibility/index.html

## Comparison

[The original video](https://youtu.be/Z9NQatne0xg?si=DghSe81iGFmF4ISh)
is taken from YouTube.

### YouTube

```text
0:00 um you may you use this x right here to
0:02 get the uh oh oh my gosh I just do on
0:05 that hold
0:06 on U uh you know what I'm going to um
0:12 search for a solution let's see video ma
0:16 maybe this guy can help
0:18 me there we go
0:20 hey hey you hey hey hey hey do you think
0:23 you could help me I accidentally Drew on
0:25 the screen right here um I don't know
0:28 what to do
0:31 no a little bit farther down further
0:33 down right
0:35 there yeah there you
0:37 go oh that's not
0:43 working that's making it
0:46 worse um I'm not sure what to do
0:49 here what's that oh okay yeah all
0:55 right that's that's just getting the cat
0:58 dirty that's not worth
1:06 all right let's oh okay yeah let's try
1:08 that try
1:10 that
1:12 oh it's okay it's okay don't worry about
1:15 it um I don't know what to do we oh oh
1:18 you have an
1:20 idea oh okay um um yeah all
1:26 right okay let me try that
1:31 okay go grab that for
1:36 [Applause]
1:38 me all
1:40 right move out of the
1:43 way let's see if I can do
1:48 [Music]
1:56 this there we go okay okay actually let
2:00 me move this out of the way so you can
2:02 see it there move that
2:05 there there we go I think that
2:08 works all right thanks for helping you
2:11 oh oh yeah okay oh oh uh um oh sorry
2:15 yeah okay sorry um oh wait a
2:20 sec I think the lightsaber was too hot
2:23 uh-oh
2:26 uhoh
2:28 uh-oh ah he catching on fire oh
2:33 no there we go finally got rid of
2:37 it all right thank you very
2:46 much
```

### medium

```text
0:00 You may you use this X right here to get the oh, oh my gosh. I just do that. Hold on
0:08 You know what I'm gonna
0:12 Search for a solution. Let's see video
0:16 Maybe this guy can help me
0:19 There we go, hey
0:21 Hey you. Hey. Hey. Hey. Hey, do you think you could help me? I accidentally drew on the screen right here
0:27 I don't know what to do
0:30 No, a little bit farther down farther down right there. Yeah
0:38 That's not working that's making it worse
0:47 I'm not sure what to do here
0:50 What's that? Oh?
0:52 That's that's just getting the cat dirty. That's not working
1:00 All right. Oh, okay. Yeah, let's try that. Try that. Oh
1:13 It's okay, it's okay. Don't worry about it
1:16 I don't know what to do. Yeah. Oh, you have an idea. Oh, okay
1:24 Yeah, all right
1:27 Okay, let me try that
1:30 Okay, go grab that
1:32 for me
1:34 Move out of the way
1:44 Let's see if I can do this
1:57 There we go
1:59 Okay
2:05 There we go, I think that works
2:11 Oh, yeah, okay. Oh, oh, oh, sorry. Yeah, okay
2:17 Oh
2:19 wait, I
2:21 Think the lightsaber was too hot. Oh, oh, oh
2:34 There we go finally got rid of it
```

### large-v2

```text
0:00 You may, you use this X right here to get the, oh, oh my gosh, I just do that, hold on.
0:09 You know what, I'm going to search for a solution.
0:13 Let's see, video, maybe this guy can help me.
0:19 There we go, hey, hey you, hey, hey, hey, hey, do you think you could help me?
0:24 I accidentally drew on the screen right here.
0:26 I don't know what to do.
0:29 No, a little bit farther down, farther down, right there, yeah, there you go.
0:37 Oh, that's not working, that's making it worse, I'm not sure what to do here, what's that?
0:51 Oh, that's just getting the cat dirty, that's not working, all right, oh, okay, yeah, let's try that,
1:08 try that, oh, that's okay, it's okay, don't worry about it.
1:15 I don't know what to do, oh, you have an idea, oh, okay, yeah, all right, okay, let me try that.
1:31 Okay, go grab that for me, move out of the way, let's see if I can do this, there we go, okay,
2:00 actually let me move this out of the way so you can see it going,
2:05 there we go, I think that worked, all right, thanks for helping me, oh, oh, yeah, okay, oh, oh, oh, sorry, yeah, okay, yeah, sorry,
2:19 oh, wait a second, I think the lightsaber was too hot, uh-oh, uh-oh, uh-oh, ah, it's catching on fire, oh, no,
2:34 there we go, finally got rid of it, all right, thank you very much.
```

