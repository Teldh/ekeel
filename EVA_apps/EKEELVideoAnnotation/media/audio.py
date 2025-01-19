"""
Audio processing module for video files.

This module provides functionality for converting video files to audio format,
specifically focusing on MP4 to WAV conversion for further processing.

Functions
---------
convert_mp4_to_wav
    Converts MP4 video files to WAV audio format
"""

import subprocess
import os
from pathlib import Path
import json


def convert_mp4_to_wav(video_path: str, video_id: str) -> Path:
    """
    Convert MP4 video file to WAV audio format.

    Parameters
    ----------
    video_path : str
        Directory path containing the video file
    video_id : str
        Identifier of the video file

    Returns
    -------
    Path
        Path object pointing to the output WAV file

    Raises
    ------
    Exception
        If FFMPEG subprocess fails during conversion
    """
    output_file_path = Path(video_path).joinpath(video_id+'.wav')
    if os.path.isfile(output_file_path): 
        return output_file_path
    
    input_file_path = Path(video_path).joinpath(video_id+'.mp4').__str__()
    try:
        # Run ffmpeg command to convert MP4 to WAV
        subprocess.run(['ffmpeg', '-i', input_file_path, output_file_path.__str__()], 
                       check=True, 
                       stdout=subprocess.PIPE, 
                       stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(e)
        raise Exception("ERROR SUBPROCESS FFMPEG")
    return output_file_path


if __name__ == '__main__':
    pass
    
    #from segmentation import VideoAnalyzer
    #video1 = VideoAnalyzer("https://www.youtube.com/watch?v=TsONshNsHHw")
    #video1.download_video()
    #print("transcript 1")
    #video1.request_transcript()
    #
    #import time
    #time.sleep(15)
    #
    #video1 = VideoAnalyzer("https://www.youtube.com/watch?v=Gac9rynIENg")
    #video1.download_video()
    #print("transcript 2")
    #video1.request_transcript()
    
    # Opening JSON file
    #f = open('audio.json')

    # returns JSON object as 
    # a dictionary
    #data = json.load(f)
    #print(data)
    
elif False:
    #import whisper_timestamped
    #help(whisper_timestamped.transcribe)
    
    print(Path(__file__).parent.joinpath("static",'videos',"5rLub-Tz65M","5rLub-Tz65M.wav"))
    import stable_whisper
    model = stable_whisper.load_model('large-v3')
    result = model.transcribe(Path(__file__).parent.joinpath("static",'videos',"5rLub-Tz65M","5rLub-Tz65M.wav").__str__())
    result.save_as_json('audio.json')
    
    #transcript = whisper_timestamped.transcribe(model="openai/whisper-large-v3", 
    #                                            audio = Path(__file__).parent.joinpath("static",'videos',"5rLub-Tz65M","5rLub-Tz65M.wav").__str__(),
    #                                            language="it",
    #                                            compute_word_confidence=False,
    #                                            refine_whisper_precision=0.9,
    #                                            seed=42)
    
    
    
    from pprint import pprint
    pprint(result)
    
elif False:
    
    from pydub import AudioSegment, silence
    from tqdm import tqdm

    wav_path = _convert_mp4_to_wav(Path(__file__).parent.joinpath("static").joinpath('videos').joinpath("5rLub-Tz65M"), "5rLub-Tz65M")

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    print(device)
    torch_dtype = torch.float32

    model_id = "openai/whisper-large-v3"

    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
    )
    model.to(device)

    processor = AutoProcessor.from_pretrained(model_id)

    pipe = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        max_new_tokens=128,
        torch_dtype=torch_dtype,
        device=device,
    )
    
    def give_split(wav_path):
        # Load audio and split on silence
        audio = AudioSegment.from_wav(wav_path)    
        chunks = silence.split_on_silence(
            audio,
            min_silence_len=500,  # Minimum length of silence (in ms) to be used for a split
            silence_thresh=audio.dBFS-40,  # Silence threshold (in dB)
            seek_step=30
        )

        transcription = []

        for i, chunk in enumerate(tqdm(chunks, desc="Transcribing chunks", unit="chunk")):
            chunk_path = wav_path.parent.joinpath(f"chunk_{i}.wav")
            chunk.export(chunk_path, format="wav")
            result = pipe(chunk_path.__str__())
            transcription.append(result["text"])

        #print(" ".join(transcription))
        
    def give_full(wav_path):
        
        transcription = pipe(wav_path.__str__(), generate_kwargs={"language": "italian"})
        #print(" ".join(transcription))
        return
    
    import time
    #curr = time.time()
    #give_split(wav_path)
    #print("SPLIT TEXT TIME",time.time()-curr)
    
    
    curr = time.time()
    give_full(wav_path)
    print("FULL TEXT TIME",time.time()-curr)
    
    #print(Path(__file__).parent.joinpath("static").joinpath('videos').joinpath("5rLub-Tz65M").joinpath("5rLub-Tz65M.wav").__str__())
    #result = pipe(Path(__file__).parent.joinpath("static").joinpath('videos').joinpath("5rLub-Tz65M").joinpath("5rLub-Tz65M.wav").__str__())
    #print(result["text"])