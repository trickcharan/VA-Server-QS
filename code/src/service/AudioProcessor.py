import numpy as np
import os
from voicevirtualagent_pb2 import VoiceVAResponse
from byova_common_pb2 import OutputEvent
from AudioUtils import AudioUtils
from EventUtils import EventUtils

SCRIPTED_RESPONSE = os.environ.get(
    'SCRIPTED_RESPONSE',
    "I have received your voice. This is a scripted call simulation. Please continue speaking."
)

class AudioProcessor:
    silence_threshold = 8000 * float(os.environ.get('silence_threshold', '1.1'))
    amplitude_threshold = 3000

    def __init__(self):
        self.audio_buffer = bytearray()
        self.pcm_array = []
        self.start_of_input_sent = False
        self.is_barge_in_enabled = False

    def process_audio_event(self, audio_byte):
        try:
            if len(audio_byte) > 15:
                self.audio_buffer.extend(audio_byte)
                if len(self.audio_buffer) >= self.silence_threshold:
                    pcm_data = AudioUtils.convert_ulaw2pcm(self.audio_buffer)
                    self.audio_buffer = bytearray()
                    is_silence = self._all_silence(pcm_data)

                    if is_silence and len(self.pcm_array) == 0:
                        pass  # Leading silence before any speech — discard
                    elif is_silence and len(self.pcm_array) > 0:
                        print("[Audio] End-of-speech silence detected, processing")
                        yield from self._process_scripted_response()
                    else:
                        if not self.start_of_input_sent:
                            print("[Audio] Sending start_of_input")
                            yield EventUtils.get_va_response_for_output_event(
                                EventUtils.get_output_event(OutputEvent.EventType.START_OF_INPUT))
                            self.start_of_input_sent = True
                        self.pcm_array.append(pcm_data)
        except Exception as ex:
            print(f"[Audio] Error in process_audio_event: {ex}")

    def _process_scripted_response(self):
        # STT: transcribe what the user said (logged only — not used to drive response)
        try:
            user_audio = np.concatenate(self.pcm_array)
            user_text = AudioUtils.convert_to_text(user_audio)
            if user_text:
                print(f"[STT] User said: {user_text}")
            else:
                print("[STT] Could not transcribe audio")
        except Exception as e:
            print(f"[STT] Skipped: {e}")

        self.pcm_array.clear()
        self.start_of_input_sent = False

        print("[Audio] Sending end_of_input")
        yield EventUtils.get_va_response_for_output_event(
            EventUtils.get_output_event(OutputEvent.EventType.END_OF_INPUT))

        # TTS: generate scripted response and stream as mu-law chunks
        print(f"[TTS] Generating response: {SCRIPTED_RESPONSE}")
        ai_audio = AudioUtils.convert_speech_to_raw_audio(SCRIPTED_RESPONSE)
        ai_audio_bytes = ai_audio.tobytes()

        chunk_size = 640  # 80ms at 8kHz mu-law
        for i in range(0, len(ai_audio_bytes), chunk_size):
            chunk = ai_audio_bytes[i:i + chunk_size]
            yield EventUtils.get_audio_output_events_bytes(
                chunk, SCRIPTED_RESPONSE, self.is_barge_in_enabled, VoiceVAResponse.ResponseType.CHUNK)

        yield EventUtils.get_audio_output_events_bytes(
            None, None, self.is_barge_in_enabled, VoiceVAResponse.ResponseType.FINAL)

    def _all_silence(self, pcm_data):
        return all(abs(value) < self.amplitude_threshold for value in pcm_data)
