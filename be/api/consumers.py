"""
================================================================================
 Module: consumers.py
 Description: 
        Implements an asynchronous WebSocket consumer that handles real-time audio 
        streaming from the client where user answers example answers, sends it speech-to-text service and gets transcription,
        evaluates the transcribed answer and sends result back to client. 
 Author: Dominik Horut (xhorut01)
================================================================================
"""

import asyncio
import threading
import azure.cognitiveservices.speech as speechsdk
from channels.generic.websocket import AsyncWebsocketConsumer
from be.settings import AZURE_API_KEY, AZURE_REGION
from datetime import datetime
import os
from concurrent.futures import ThreadPoolExecutor
import json
import django
import io
import wave
import uuid
import re
from django.test import RequestFactory

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "be.settings")
django.setup()

from .views import skip_example, delete_example_record
from .answerChecker import GeminiRateLimitError
from .attempt_cloud_sync import retry_pending_attempt_uploads, sync_attempt_to_mega

AUDIO_DIR = "audioprompts"
os.makedirs(AUDIO_DIR, exist_ok=True)
ATTEMPT_AUDIO_DIR = "attempt_audio"
os.makedirs(ATTEMPT_AUDIO_DIR, exist_ok=True)

# Set to True to enable audio dumping
DUMP_AUDIO=False

class SpeechRecognitionConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # Buffer for incoming audio data
        self.speech_data = bytearray()

        self.loop = asyncio.get_event_loop()
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.language = "sk-SK"
        
        # Metadata about language, user and currently solved example
        self.metadata = {}
        self.audio_format = None

        # Set up Azure speech recognizer and audio stream
        self.speech_recognizer, self.stream = self.create_speech_recognizer()
        
        await self.accept()
        
        # Start receiving audio
        self.receive_task = asyncio.create_task(self.receive_audio())

    async def disconnect(self, close_code):
        self.receive_task.cancel()
        try:
            await self.receive_task
        except asyncio.CancelledError:
            pass
        try:
            self.stream.close()
        except Exception:
            pass
        try:
            self.speech_recognizer.stop_continuous_recognition()
        except Exception:
            pass
        self.executor.shutdown(wait=False)
        del self.speech_recognizer
        del self.stream
        print("Speech recognition stopped.")

    def _resolve_student_example(self, student_id, session_id, example_id, record_date):
        from .models import StudentExample

        records = StudentExample.objects.prefetch_related('practiced_skills').filter(
            example_id=example_id,
        )

        if student_id and student_id != 'unknown':
            records = records.filter(student__id=student_id)
        elif session_id:
            records = records.filter(anonymous_session__session_id=session_id)
        else:
            return None

        if record_date:
            exact_match = records.filter(date=record_date).first()
            if exact_match:
                return exact_match

        # Fallback for races or stale frontend metadata: if the record was just
        # created for the same example/session but the exact timestamp differs,
        # pair the speech attempt with the most recent matching StudentExample.
        fallback_match = records.order_by('-date', '-id').first()
        if fallback_match and record_date:
            print(
                f"[WARN] StudentExample exact date miss for example={example_id}, "
                f"record_date={record_date}; using latest id={fallback_match.id}."
            )
        return fallback_match

    def _save_attempt_audio(self, student_id, session_id, example_id, audio_bytes):
        if not audio_bytes:
            return ""

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        owner = str(student_id) if student_id and student_id != 'unknown' else f"anon_{(session_id or 'unknown')[:12]}"
        audio_filename = f"{owner}_{example_id}_{timestamp}_{uuid.uuid4().hex[:8]}.wav"
        audio_filepath = os.path.join(ATTEMPT_AUDIO_DIR, audio_filename)

        wav_data = self.convert_pcm_to_wav(audio_bytes)
        with open(audio_filepath, "wb") as f:
            f.write(wav_data)

        return audio_filepath

    def _serialize_answer(self, answer_value):
        if answer_value is None:
            return ""
        if isinstance(answer_value, (dict, list)):
            return json.dumps(answer_value, ensure_ascii=False)
        return str(answer_value)

    def _get_example_context(self, example_id):
        from .models import Example, Answer

        try:
            example = Example.objects.get(id=example_id)
            answer = Answer.objects.filter(example=example).first()
            return example.example, (answer.answer if answer else "No correct answer found")
        except Exception:
            return "Example not found", "No correct answer found"

    def _is_comparison_speech(self, text_value):
        text = (text_value or "").lower()
        comparison_roots = [
            'väčšie', 'vacsie', 'vetšie', 'vetsie',
            'menšie', 'mensie',
            'rovné', 'rovne', 'rovna', 'rovná',
            'väčší', 'vacsi', 'vetší', 'vetsi',
            'menší', 'mensi',
            'rovný', 'rovny',
        ]
        return any(keyword in text for keyword in comparison_roots)

    def _should_ignore_speech_attempt(self, action, transcription):
        # Hard fail-safe: ignore random speech that has no digits and is not
        # a comparison answer. This prevents false "evaluated=false" entries.
        if action != 'evaluated':
            return False
        has_digits = bool(re.search(r'\d', transcription or ''))
        if has_digits:
            return False
        return not self._is_comparison_speech(transcription)

    def _store_attempt_log(
        self,
        student_id,
        session_id,
        example_id,
        record_date,
        duration,
        input_type,
        language,
        action,
        is_correct,
        transcription,
        parsed_answer,
        example_text,
        correct_answer,
        audio_bytes,
        audio_format,
        meta=None,
    ):
        from .models import ExampleAttempt, ExampleSkill, Skill

        if self._should_ignore_speech_attempt(action, transcription):
            print(f"[DEBUG] Ignoring non-numeric speech log: '{transcription}'")
            return

        student_example = self._resolve_student_example(student_id, session_id, example_id, record_date)
        if not student_example:
            print(f"[WARN] StudentExample not found for logging: example={example_id}, date={record_date}")
            return

        skill_ids = list(student_example.practiced_skills.values_list('id', flat=True))
        if not skill_ids:
            skill_ids = list(
                ExampleSkill.objects.filter(example_id=example_id).values_list('skill_id', flat=True).distinct()
            )
        skill_names = list(Skill.objects.filter(id__in=skill_ids).values_list('name', flat=True))

        audio_file_path = self._save_attempt_audio(student_id, session_id, example_id, audio_bytes)

        attempt = ExampleAttempt.objects.create(
            student_example=student_example,
            student=student_example.student,
            anonymous_session=student_example.anonymous_session,
            example_id=example_id,
            attempt_number=max(student_example.attempts, 1),
            duration=duration or 0,
            source='speech',
            input_type=input_type or '',
            language=language or '',
            action=action,
            is_correct=is_correct,
            transcription=transcription or '',
            parsed_answer=self._serialize_answer(parsed_answer),
            example_text=example_text or '',
            correct_answer=correct_answer or '',
            audio_file_path=audio_file_path,
            audio_format=audio_format or '',
            practiced_skill_ids=skill_ids,
            practiced_skill_names=skill_names,
            meta=meta or {},
        )

        # Cloud sync runs in a background daemon thread so it never blocks
        # the WebSocket callback or the user-facing result.
        def _background_cloud_sync(att):
            try:
                sync_attempt_to_mega(att)
                retry_pending_attempt_uploads(limit=5)
            except Exception as cloud_error:
                print(f"[ERROR] Background cloud sync failed for attempt {att.id}: {cloud_error}")

        threading.Thread(target=_background_cloud_sync, args=(attempt,), daemon=True).start()

        return attempt

    async def receive(self, text_data=None, bytes_data=None):

        # Metadata was received via websocket
        if text_data:
            try:
                new_metadata = json.loads(text_data)
                self.metadata.update(new_metadata)
            
                if 'format' in new_metadata:
                    self.audio_format = new_metadata['format']
                
                # Check if language was changed
                if 'language' in new_metadata:
                    requested_lang = new_metadata['language']
                    supported_langs = ['cs-CZ', 'en-US', 'sk-SK']

                    if requested_lang not in supported_langs:
                        print(f"Unsupported language '{requested_lang}', defaulting to sk-SK")
                        requested_lang = 'sk-SK'

                    # Nastav nový jazyk pre rozpoznávanie
                    self.language = requested_lang
                    print(f"ASR language changed to: {self.language}")

                    try:
                        self.speech_recognizer.stop_continuous_recognition()
                    except Exception:
                        pass  # ak ešte nebežal

                    try:
                        self.stream.close()
                    except Exception:
                        pass

                    del self.speech_recognizer
                    del self.stream

                    # Vytvor nový recognizer s novým jazykom (automatically starts via create_speech_recognizer)
                    self.speech_recognizer, self.stream = self.create_speech_recognizer()

            except json.JSONDecodeError:
                print("Invalid metadata received.")

        # Audio data was received via websocket
        elif bytes_data:
            #print(f"[DEBUG] Received {len(bytes_data)} bytes of audio data")
            # Send raw PCM data directly to Azure
            self.stream.write(bytes_data)
            #print(f"[DEBUG] Written {len(bytes_data)} bytes to Azure stream")
            
            # Accumulate audio data to dump
            self.speech_data.extend(bytes_data)

    async def receive_audio(self):
        while True:
            await asyncio.sleep(0.1)

    def create_speech_recognizer(self):

        # Azure STT configuration
        speech_config = speechsdk.SpeechConfig(subscription=AZURE_API_KEY, region=AZURE_REGION)
        speech_config.output_format = speechsdk.OutputFormat.Detailed
        format = speechsdk.audio.AudioStreamFormat(samples_per_second=16000, bits_per_sample=16, channels=1)
        stream = speechsdk.audio.PushAudioInputStream(stream_format=format)
        audio_config = speechsdk.audio.AudioConfig(stream=stream)

        speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config,
            language=self.language
        )

        def recognized_cb(evt: speechsdk.SpeechRecognitionEventArgs):
            print(f"[DEBUG] recognized_cb fired: result={evt.result.text}, reason={evt.result.reason}")

            # Extract Azure confidence score from detailed JSON result
            azure_confidence = None
            try:
                json_result_str = evt.result.properties.get(
                    speechsdk.PropertyId.SpeechServiceResponse_JsonResult, ''
                )
                if json_result_str:
                    json_result = json.loads(json_result_str)
                    nbest = json_result.get('NBest', [])
                    if nbest:
                        azure_confidence = nbest[0].get('Confidence', None)
            except Exception as conf_err:
                print(f"[DEBUG] Could not extract Azure confidence: {conf_err}")

            # Log all possible outcomes
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                print(f"[DEBUG] SUCCESS: Azure recognized: '{evt.result.text}' (confidence={azure_confidence})")
            elif evt.result.reason == speechsdk.ResultReason.NoMatch:
                print(f"[DEBUG] NO_MATCH: Azure did not understand anything")
                print(f"[DEBUG] NoMatch details: {evt.result.no_match_details if hasattr(evt.result, 'no_match_details') else 'N/A'}")

                student_id = self.metadata.get('student_id', 'unknown')
                session_id = self.metadata.get('session_id', None)
                example_id = self.metadata.get('example_id', 'unknown')
                input_type = self.metadata.get('input_type', '')
                record_date = self.metadata.get('record_date')
                audio_bytes = bytes(self.speech_data)

                try:
                    from .utils import calculate_duration
                    duration = calculate_duration(record_date) if record_date else 0
                except Exception:
                    duration = 0

                if example_id != 'unknown' and record_date:
                    example_text, correct_answer = self._get_example_context(example_id)
                    try:
                        self._store_attempt_log(
                            student_id=student_id,
                            session_id=session_id,
                            example_id=example_id,
                            record_date=record_date,
                            duration=duration,
                            input_type=input_type,
                            language=self.language,
                            action='no_match',
                            is_correct=False,
                            transcription=evt.result.text,
                            parsed_answer='NO_MATCH',
                            example_text=example_text,
                            correct_answer=correct_answer,
                            audio_bytes=audio_bytes,
                            audio_format=self.audio_format,
                            meta={'azure_reason': 'NoMatch', 'azure_confidence': azure_confidence},
                        )
                    except Exception as log_error:
                        print(f"[ERROR] Failed to store NO_MATCH log: {log_error}")

                self.speech_data = bytearray()
                # Send fail response to frontend
                response_data = {
                    "isCorrect": False,
                    "continue_with_next": False,
                    "student_answer": "Azure: No match - could not understand audio"
                }
                try:
                    asyncio.run_coroutine_threadsafe(
                        self.send(json.dumps(response_data)),
                        self.loop
                    )
                except Exception as e:
                    print(f"[DEBUG] Error sending NO_MATCH response: {e}")
                return  # Don't process empty result
            elif evt.result.reason == speechsdk.ResultReason.Canceled:
                print(f"[DEBUG] CANCELED: Speech recognition was canceled")
                if hasattr(evt.result, 'cancellation_details') and evt.result.cancellation_details:
                    print(f"[DEBUG] Cancellation reason: {evt.result.cancellation_details.reason}")
                    print(f"[DEBUG] Error details: {evt.result.cancellation_details.error_details}")

                student_id = self.metadata.get('student_id', 'unknown')
                session_id = self.metadata.get('session_id', None)
                example_id = self.metadata.get('example_id', 'unknown')
                input_type = self.metadata.get('input_type', '')
                record_date = self.metadata.get('record_date')
                audio_bytes = bytes(self.speech_data)

                try:
                    from .utils import calculate_duration
                    duration = calculate_duration(record_date) if record_date else 0
                except Exception:
                    duration = 0

                if example_id != 'unknown' and record_date:
                    example_text, correct_answer = self._get_example_context(example_id)
                    try:
                        self._store_attempt_log(
                            student_id=student_id,
                            session_id=session_id,
                            example_id=example_id,
                            record_date=record_date,
                            duration=duration,
                            input_type=input_type,
                            language=self.language,
                            action='error',
                            is_correct=False,
                            transcription=evt.result.text,
                            parsed_answer='CANCELED',
                            example_text=example_text,
                            correct_answer=correct_answer,
                            audio_bytes=audio_bytes,
                            audio_format=self.audio_format,
                            meta={'azure_reason': 'Canceled', 'azure_confidence': azure_confidence},
                        )
                    except Exception as log_error:
                        print(f"[ERROR] Failed to store CANCELED log: {log_error}")

                self.speech_data = bytearray()
                # Send fail response to frontend
                response_data = {
                    "isCorrect": False,
                    "continue_with_next": False,
                    "student_answer": "Azure: Canceled - error during recognition"
                }
                try:
                    asyncio.run_coroutine_threadsafe(
                        self.send(json.dumps(response_data)),
                        self.loop
                    )
                except Exception as e:
                    print(f"[DEBUG] Error sending CANCELED response: {e}")
                return
            
            #print(f"[DEBUG] evt.result.text={bool(evt.result.text)}, self.speech_data size={len(self.speech_data)}")
            if evt.result.text and self.speech_data:
                try:
                    #print(f"[DEBUG] Starting evaluation for text='{evt.result.text}'")
                    
                    # Initialize response data for all branches
                    response_data = {}
                    evaluation_data = {}
                    action = "evaluated"
                    is_correct_for_log = None
                    parsed_answer_for_log = None
                    
                    student_id = self.metadata.get('student_id', 'unknown')
                    session_id = self.metadata.get('session_id', None)
                    example_id = self.metadata.get('example_id', 'unknown')
                    audio_bytes = bytes(self.speech_data)
                    #print(f"[DEBUG] student_id={student_id}, session_id={session_id}, example_id={example_id}")

                    # Sent audio will be dumped in WAV
                    if DUMP_AUDIO:  
                        wav_data = self.convert_pcm_to_wav(audio_bytes)
                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

                        audio_filename = f"{student_id}_{example_id}_{timestamp}.wav"
                        json_filename = f"{student_id}_{example_id}_{timestamp}.json"

                        audio_filepath = os.path.join(AUDIO_DIR, audio_filename)
                        json_filepath = os.path.join(AUDIO_DIR, json_filename)

                        with open(audio_filepath, "wb") as f:
                            f.write(wav_data)
        
                    from .models import Example, Answer

                    # Get example text and correct answer
                    try:
                        example = Example.objects.get(id=example_id)
                        answer = Answer.objects.filter(example=example).first() 
                        correct_answer = answer.answer if answer else "No correct answer found"
                    except Example.DoesNotExist:
                        example_text = "Example not found"
                        correct_answer = "No correct answer found"
                    else:
                        example_text = example.example

                    # Reset accumulated audio data
                    self.speech_data = bytearray()
                    
                    from .utils import calculate_duration
                    from .answerChecker import InlineSpeechAnswerChecker, FractionSpeechAnswerChecker, VariableSpeechAnswerChecker, LLMAnswerChecker

                    # Get data for current example
                    input_type = self.metadata.get('input_type')
                    record_date = self.metadata.get('record_date')
                    duration = calculate_duration(record_date)
                    student_answer = evt.result.text

                    # Words to skip example or terminate practice
                    skip_wordsCS = ["přeskočit", "další", "přeskoč", "dál"]
                    skip_wordsSK = ["preskočiť", "ďalej", "ďalší", "preskoč"]
                    skip_wordsEN = ["skip", "next", "continue"]

                    finish_wordsCS = ["konec", "ukončit", "stačí", "hotovo", "skončit", "dost"]
                    finish_wordsSK = ["koniec", "ukončiť", "stačí", "hotovo", "skončiť", "dost"]
                    finish_wordsEN = ["finish", "end", "stop", "done"]

                    if self.language == "cs-CZ":
                        skip_words = skip_wordsCS
                        finish_words = finish_wordsCS
                    elif self.language == "sk-SK":
                        skip_words = skip_wordsSK
                        finish_words = finish_wordsSK
                    else:
                        skip_words = skip_wordsEN
                        finish_words = finish_wordsEN


                    # Transcript containts 'skip' words - update record and skip example
                    if any(word in student_answer.lower() for word in skip_words):
                        factory = RequestFactory()
                        skip_data = {'example_id': example_id, 'date': record_date}
                        if student_id != 'unknown':
                            skip_data['student_id'] = student_id
                        else:
                            skip_data['session_id'] = session_id
                        request = factory.post('skip-example/', skip_data)
                        skip_example(request)
                        response_data = {'skipped': True}
                        action = "skipped"
                        evaluation_data = {
                            "student_id": student_id,
                            "example_id": example_id,
                            "transcription": evt.result.text,
                            "example_text": example_text,
                            "correct_answer": correct_answer,
                            "evaluation": "skipped"
                        }

                    # Transcript containts 'terminate' words - delete record and terminate practice
                    elif any(word in student_answer.lower() for word in finish_words):
                        factory = RequestFactory()
                        delete_data = {'example_id': example_id, 'date': record_date}
                        if student_id != 'unknown':
                            delete_data['student_id'] = student_id
                        else:
                            delete_data['session_id'] = session_id
                        request = factory.post('delete-record/', delete_data)
                        delete_example_record(request)
                        response_data = {'finished': True}
                        action = "terminated"
                        evaluation_data = {
                            "student_id": student_id,
                            "example_id": example_id,
                            "transcription": evt.result.text,
                            "example_text": example_text,
                            "correct_answer": correct_answer,
                            "evaluation": "terminated"
                        }

                    # Transcript does not contain 'skip' or 'terminate' words - evaluate answer 
                    else:
                            import re

                            # Comparison-specific root words (unambiguously comparison operators
                            # in Slovak/Czech math context). Generic words like 'ako', 'než', 'nez'
                            # are intentionally excluded — they appear in everyday speech and would
                            # cause random utterances to bypass the word filter.
                            _comparison_roots = [
                                'väčšie', 'vacsie', 'vetšie', 'vetsie',
                                'menšie', 'mensie',
                                'rovné', 'rovne', 'rovna', 'rovná',
                                'väčší', 'vacsi', 'vetší', 'vetsi',
                                'menší', 'mensi',
                                'rovný', 'rovny',
                            ]

                            def _is_comparison_answer(text):
                                t = text.lower()
                                return any(kw in t for kw in _comparison_roots)

                            # Universal word-only guard: if the transcription has no digits
                            # and is not a comparison-operator answer, silently ignore it
                            # for evaluation, but keep the recording in logs with a non-evaluated status.
                            # Applies only to INLINE/WORD answers. Fraction/variable speech may be
                            # recognized in forms where digits are not present in transcription.
                            if input_type in ('INLINE', 'WORD') and not re.search(r'\d', student_answer) and not _is_comparison_answer(student_answer):
                                print(f"[DEBUG] Word-only answer filtered (no digits, no comparison): '{student_answer}'")
                                response_data = {
                                    "isCorrect": None,
                                    "continue_with_next": False,
                                    "filtered": True,
                                    "filter_reason": "non_numeric_speech",
                                }
                                action = "skipped"
                                is_correct_for_log = None
                                parsed_answer_for_log = ""
                                evaluation_data = {
                                    "student_id": student_id,
                                    "example_id": example_id,
                                    "transcription": evt.result.text,
                                    "example_text": example_text,
                                    "correct_answer": correct_answer,
                                    "evaluation": "filtered_non_numeric",
                                }
                            else:

                                # Check if answer contains only numbers/symbols for INLINE/WORD types
                                if input_type == 'INLINE' or input_type == 'WORD':
                                    has_letters = bool(re.search(r'[a-zA-ZáäčďéíľľňóôŕšťúůýžÁÄČĎÉÍĽŇÓÔŕŘŠŤÚŮÝŽ]', student_answer))

                                    if has_letters and not _is_comparison_answer(student_answer):
                                        # Mixed text with digits (e.g. "päťdesiat 3") — extract last number
                                        numbers = re.findall(r'\d+(?:[.,]\d+)?', student_answer)
                                        if numbers:
                                            extracted_number = numbers[-1].replace(',', '.')
                                            print(f"[DEBUG] Extracted last number from text: '{extracted_number}'")
                                            student_answer = extracted_number
                                        # pure-word no-digit case already handled by guard above

                                    # Evaluate the answer (either direct number, extracted number, or comparison word)
                                    isCorrect, continue_with_next, student_answer = InlineSpeechAnswerChecker.verifyAnswer(
                                        student_id, example_id, record_date, duration, student_answer, session_id=session_id
                                    )
                                    response_data = {
                                        "isCorrect": isCorrect,
                                        "continue_with_next": continue_with_next,
                                        "student_answer": student_answer
                                    }
                                    is_correct_for_log = isCorrect
                                    parsed_answer_for_log = student_answer
                                    evaluation_data = {
                                        "student_id": student_id,
                                        "example_id": example_id,
                                        "transcription": evt.result.text,
                                        "example_text": example_text,
                                        "correct_answer": correct_answer,
                                        "evaluation": isCorrect
                                    }
                                # Fraction answer evaluated by LLM
                                elif input_type == 'FRAC':
                                    parsed_fraction = FractionSpeechAnswerChecker.extract_fraction_from_text(student_answer)
                                    try:
                                        # Prefer deterministic fraction checker when transcript has number pair.
                                        if parsed_fraction:
                                            isCorrect, continue_with_next, student_answer = FractionSpeechAnswerChecker.verifyAnswer(
                                                student_id, example_id, record_date, duration, student_answer, session_id=session_id
                                            )
                                        else:
                                            isCorrect, continue_with_next, student_answer = LLMAnswerChecker.verifyAnswer(
                                                student_id, example_id, record_date, duration, student_answer, 'fraction', session_id=session_id
                                            )

                                    # LLM rate limit reached - use FractionSpeechAnswerChecker
                                    except GeminiRateLimitError:
                                        print("FRAC gemini limit reached - will use FractionSpeechAnswerChecker")
                                        isCorrect, continue_with_next, student_answer = FractionSpeechAnswerChecker.verifyAnswer(
                                            student_id, example_id, record_date, duration, student_answer, session_id=session_id
                                        )

                                    # Frontend fraction input expects object with numerator/denominator.
                                    if not isinstance(student_answer, dict):
                                        student_answer = (
                                            parsed_fraction
                                            or FractionSpeechAnswerChecker.extract_fraction_from_latex(correct_answer)
                                            or {"numerator": "", "denominator": ""}
                                        )

                                    response_data = {
                                        "isCorrect": isCorrect,
                                        "continue_with_next": continue_with_next,
                                        "student_answer": student_answer
                                    }
                                    is_correct_for_log = isCorrect
                                    parsed_answer_for_log = (
                                        f"{student_answer.get('numerator')}/{student_answer.get('denominator')}"
                                        if isinstance(student_answer, dict)
                                        else student_answer
                                    )
                                    evaluation_data = {
                                        "student_id": student_id,
                                        "example_id": example_id,
                                        "transcription": evt.result.text,
                                        "example_text": example_text,
                                        "correct_answer": correct_answer,
                                        "evaluation": isCorrect
                                    }

                                # Variable answer evaluated by LLM  
                                elif input_type == 'VAR':

                                    try:
                                        isCorrect, continue_with_next, student_answer = LLMAnswerChecker.verifyAnswer(
                                            student_id, example_id, record_date, duration, student_answer, 'variable'
                                        )

                                    # LLM rate limit reached - use VariableSpeechAnswerChecker
                                    except GeminiRateLimitError:
                                        print("VAR gemini limit reached - will use VariableSpeechAnswerChecker")
                                        isCorrect, continue_with_next, student_answer = VariableSpeechAnswerChecker.verifyAnswer(
                                            student_id, example_id, record_date, duration, student_answer
                                        )

                                    response_data = {
                                        "isCorrect": isCorrect,
                                        "continue_with_next": continue_with_next,
                                        "student_answer": student_answer
                                    }
                                    is_correct_for_log = isCorrect
                                    parsed_answer_for_log = student_answer
                                    evaluation_data = {
                                        "student_id": student_id,
                                        "example_id": example_id,
                                        "transcription": evt.result.text,
                                        "example_text": example_text,
                                        "correct_answer": correct_answer,
                                        "evaluation": isCorrect
                                    }
                        
                                else:
                                    # Unknown input type
                                    print(f"[ERROR] Unknown input_type: '{input_type}'", flush=True)
                                    action = "error"
                                    response_data = {
                                        "isCorrect": False,
                                        "continue_with_next": False,
                                        "student_answer": f"Error: Unknown input type '{input_type}'"
                                    }
                                    evaluation_data = {
                                        "student_id": student_id,
                                        "example_id": example_id,
                                        "transcription": evt.result.text,
                                        "example_text": example_text,
                                        "correct_answer": correct_answer,
                                        "evaluation": "error_unknown_type"
                                    }

                    attempt_obj = None
                    try:
                        attempt_obj = self._store_attempt_log(
                            student_id=student_id,
                            session_id=session_id,
                            example_id=example_id,
                            record_date=record_date,
                            duration=duration,
                            input_type=input_type,
                            language=self.language,
                            action=action,
                            is_correct=is_correct_for_log,
                            transcription=evt.result.text,
                            parsed_answer=parsed_answer_for_log,
                            example_text=example_text,
                            correct_answer=correct_answer,
                            audio_bytes=audio_bytes,
                            audio_format=self.audio_format,
                            meta={
                                "continue_with_next": response_data.get("continue_with_next"),
                                "evaluation": evaluation_data.get("evaluation"),
                                "azure_confidence": azure_confidence,
                            },
                        )
                    except Exception as log_error:
                        print(f"[ERROR] Failed to store attempt log: {log_error}")

                    # Award XP for registered students on correct answers
                    if is_correct_for_log is True and student_id and student_id != 'unknown' and attempt_obj:
                        try:
                            from .xp_service import award_xp
                            xp_data = award_xp(student_id, attempt_obj)
                            response_data.update(xp_data)
                        except Exception as xp_error:
                            print(f"[ERROR] Failed to award XP: {xp_error}")

                    # Update incremental skill mastery (once per completed example)
                    # Only task-based practice counts; skills come from the Task, not from the example.
                    if response_data.get("continue_with_next") and student_id and student_id != 'unknown' and attempt_obj:
                        try:
                            from .mastery import update_skill_mastery
                            student_example = attempt_obj.student_example
                            if student_example.task_id:
                                leaf_skill_ids = set(
                                    student_example.task.skills.filter(
                                        subskills__isnull=True,
                                        deleted=False,
                                    ).values_list('id', flat=True)
                                )
                                student_time_ms = student_example.duration
                                for skill_id in leaf_skill_ids:
                                    update_skill_mastery(
                                        student_id=int(student_id),
                                        skill_id=skill_id,
                                        attempt_number=attempt_obj.attempt_number,
                                        solved=bool(is_correct_for_log),
                                        student_time_ms=student_time_ms,
                                    )
                        except Exception as mastery_error:
                            print(f"[ERROR] Failed to update skill mastery: {mastery_error}")
                        
                    # Save evaluation data to JSON file
                    if DUMP_AUDIO:
                        with open(json_filepath, "w", encoding="utf-8") as json_file:
                            json.dump(evaluation_data, json_file, indent=4, ensure_ascii=False)

                        print(f"Evaluation saved: {json_filepath}")

                    asyncio.run_coroutine_threadsafe(
                        self.send(json.dumps(response_data)),
                        self.loop
                    )
                    #print(f"[DEBUG] Response sent to client: {response_data}")
                except Exception as e:
                    #print(f"[DEBUG] Exception in recognized_cb evaluation: {e}")
                    import traceback
                    traceback.print_exc()
                
        def recognizing_cb(evt: speechsdk.SpeechRecognitionEventArgs):
            pass

        speech_recognizer.recognized.connect(recognized_cb)
        speech_recognizer.recognizing.connect(recognizing_cb)
        speech_recognizer.session_started.connect(lambda evt: print(f"[DEBUG] Session started"))
        speech_recognizer.session_stopped.connect(lambda evt: print(f"[DEBUG] Session stopped"))

        # Starts recognition in a separate thread to avoid blocking
        def start_recognition():
            #print(f"[DEBUG] Starting continuous recognition with language={self.language}")
            speech_recognizer.start_continuous_recognition()
            #print(f"[DEBUG] Continuous recognition started successfully")

        self.executor.submit(start_recognition)
        
        return speech_recognizer, stream
        
    def convert_pcm_to_wav(self, pcm_data):
        # Converts raw PCM data sent from client to WAV format
        with io.BytesIO() as wav_io:
            with wave.open(wav_io, 'wb') as wav_file:
                wav_file.setnchannels(1)        # Mono
                wav_file.setsampwidth(2)        # 16-bit
                wav_file.setframerate(16000)    # 16kHz
                wav_file.writeframes(pcm_data)
            return wav_io.getvalue()
