"""
================================================================================
 Module: consumersSurvey.py
 Description: 
        Implements an asynchronous WebSocket consumer that handles real-time audio 
        streaming from the client where user answers survey questions, sends it speech-to-text service and saves transcription,
 Author: Dominik Horut (xhorut01)
================================================================================
"""

import asyncio
import azure.cognitiveservices.speech as speechsdk
from channels.generic.websocket import AsyncWebsocketConsumer
import json
from be.settings import AZURE_API_KEY, AZURE_REGION
import django
import os
import io
import threading
import wave
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "be.settings")
django.setup()
from .utils import get_skill_names_string
from .survey_feedback_sync import create_survey_feedback, retry_pending_survey_feedback_uploads, sync_survey_feedback_to_mega

class SurveySpeechTranscriptionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Buffer for incoming audio data (for transcription)
        self.speech_data = bytearray()
        # Buffer for audio recording (for saving WAV file)
        self.audio_buffer = bytearray()

        self.full_transcript = ""

        # Survey question data
        self.question_text = ""
        self.question_type = "open-question"
        self.skills = []
        self.skill_names = ""
        self.student_id = None
        self.session_id = None

        self.loop = asyncio.get_event_loop()
        self.executor = asyncio.get_running_loop().run_in_executor
        self.language = "sk-SK"
        
        self.speech_recognizer, self.stream = self.create_speech_recognizer()
        
        await self.accept()
        print("WebSocket connection established")

    async def disconnect(self, close_code):

        # User terminated question answering - save the transcription and audio
        # Wait a bit for pending transcriptions to come through
        await asyncio.sleep(0.5)
        
        self.speech_recognizer.stop_continuous_recognition_async().get()
        self.stream.close()

        # Only save if there's actual content
        if self.full_transcript.strip() or self.audio_buffer:
            try:
                feedback = await asyncio.to_thread(
                    create_survey_feedback,
                    question_type=self.question_type or "open-question",
                    question_text=self.question_text,
                    answer=self.full_transcript.strip(),
                    skills=self.skills,
                    student_id=self.student_id,
                    session_id=self.session_id,
                    language=self.language,
                    source="voice",
                    audio_bytes=bytes(self.audio_buffer),
                    audio_format="pcm",
                )

                def _background_feedback_sync(saved_feedback):
                    try:
                        sync_survey_feedback_to_mega(saved_feedback)
                        retry_pending_survey_feedback_uploads(limit=5)
                    except Exception as feedback_error:
                        print(f"[ERROR] Background survey feedback sync failed for feedback {saved_feedback.id}: {feedback_error}")

                threading.Thread(target=_background_feedback_sync, args=(feedback,), daemon=True).start()
            except Exception as exc:
                print(f"[ERROR] Survey feedback save failed: {exc}")
        
    async def receive(self, text_data=None, bytes_data=None):

        # Metadata was received via websocket
        if text_data:
            try:
                # Parse the metadata sent from the client
                metadata = json.loads(text_data)
                if "question_text" in metadata:
                    self.question_text = metadata.get("question_text")

                if "question_type" in metadata:
                    self.question_type = metadata.get("question_type") or "open-question"

                if "skills" in metadata:
                    self.skills = metadata.get("skills")
                    self.skill_names = await get_skill_names_string(self.skills)

                if "student_id" in metadata:
                    self.student_id = metadata.get("student_id")

                if "session_id" in metadata:
                    self.session_id = metadata.get("session_id")

                # Check if language was changed
                if 'language' in metadata:
                    self.language = metadata['language']
                    self.speech_recognizer.stop_continuous_recognition()
                    self.speech_recognizer, self.stream = self.create_speech_recognizer()

            except json.JSONDecodeError:
                print("Invalid metadata received")

        # Audio data was received via websocket
        elif bytes_data:
            self.stream.write(bytes_data)
            # Also collect audio for saving WAV file
            self.audio_buffer.extend(bytes_data)

    def create_speech_recognizer(self):

        # Azure STT configuration   
        speech_config = speechsdk.SpeechConfig(subscription=AZURE_API_KEY, region=AZURE_REGION)
        audio_format = speechsdk.audio.AudioStreamFormat(samples_per_second=16000, bits_per_sample=16, channels=1)
        stream = speechsdk.audio.PushAudioInputStream(stream_format=audio_format)
        audio_config = speechsdk.audio.AudioConfig(stream=stream)
        
        speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config,
            language=self.language  
        )
        
        def recognized_cb(evt: speechsdk.SpeechRecognitionEventArgs):
            if evt.result.text:

                self.full_transcript += evt.result.text + " "
                
                asyncio.run_coroutine_threadsafe(
                    self.send(json.dumps({"transcription": evt.result.text})),
                    self.loop
                )            
        
        speech_recognizer.recognized.connect(recognized_cb)
        
        speech_recognizer.start_continuous_recognition_async()
        
        return speech_recognizer, stream
    
    def convert_pcm_to_wav(self, pcm_data):
        """Converts raw PCM data to WAV format"""
        with io.BytesIO() as wav_io:
            with wave.open(wav_io, 'wb') as wav_file:
                wav_file.setnchannels(1)        # Mono
                wav_file.setsampwidth(2)        # 16-bit
                wav_file.setframerate(16000)    # 16kHz
                wav_file.writeframes(pcm_data)
            return wav_io.getvalue()
