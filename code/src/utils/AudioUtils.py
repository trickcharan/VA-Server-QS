import io
import os
import numpy as np
import soundfile as sf
import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

class AudioUtils:

    mulaw_decode_table = np.array([
        -32124, -31100, -30076, -29052, -28028, -27004, -25980, -24956,
        -23932, -22908, -21884, -20860, -19836, -18812, -17788, -16764,
        -15996, -15484, -14972, -14460, -13948, -13436, -12924, -12412,
        -11900, -11388, -10876, -10364,  -9852,  -9340,  -8828,  -8316,
        -7932,  -7676,  -7420,  -7164,  -6908,  -6652,  -6396,  -6140,
        -5884,  -5628,  -5372,  -5116,  -4860,  -4604,  -4348,  -4092,
        -3900,  -3772,  -3644,  -3516,  -3388,  -3260,  -3132,  -3004,
        -2876,  -2748,  -2620,  -2492,  -2364,  -2236,  -2108,  -1980,
        -1884,  -1820,  -1756,  -1692,  -1628,  -1564,  -1500,  -1436,
        -1372,  -1308,  -1244,  -1180,  -1116,  -1052,   -988,   -924,
        -876,   -844,   -812,   -780,   -748,   -716,   -684,   -652,
        -620,   -588,   -556,   -524,   -492,   -460,   -428,   -396,
        -372,   -356,   -340,   -324,   -308,   -292,   -276,   -260,
        -244,   -228,   -212,   -196,   -180,   -164,   -148,   -132,
        -120,   -112,   -104,    -96,    -88,    -80,    -72,    -64,
         -56,    -48,    -40,    -32,    -24,    -16,     -8,      0,
        32124, 31100, 30076, 29052, 28028, 27004, 25980, 24956,
        23932, 22908, 21884, 20860, 19836, 18812, 17788, 16764,
        15996, 15484, 14972, 14460, 13948, 13436, 12924, 12412,
        11900, 11388, 10876, 10364,  9852,  9340,  8828,  8316,
        7932,  7676,  7420,  7164,  6908,  6652,  6396,  6140,
        5884,  5628,  5372,  5116,  4860,  4604,  4348,  4092,
        3900,  3772,  3644,  3516,  3388,  3260,  3132,  3004,
        2876,  2748,  2620,  2492,  2364,  2236,  2108,  1980,
        1884,  1820,  1756,  1692,  1628,  1564,  1500,  1436,
        1372,  1308,  1244,  1180,  1116,  1052,   988,   924,
         876,   844,   812,   780,   748,   716,   684,   652,
         620,   588,   556,   524,   492,   460,   428,   396,
         372,   356,   340,   324,   308,   292,   276,   260,
         244,   228,   212,   196,   180,   164,   148,   132,
         120,   112,   104,    96,    88,    80,    72,    64,
          56,    48,    40,    32,    24,    16,     8,     0
    ], dtype=np.int16)

    _audio_cache = {}

    @staticmethod
    def convert_ulaw2pcm(ulaw_bytes):
        ulaw = np.frombuffer(ulaw_bytes, dtype=np.uint8)
        return AudioUtils.mulaw_decode_table[ulaw]

    @staticmethod
    def lin2ulaw(x):
        BIAS = 0x84
        CLIP = 32635
        x = np.clip(x, -CLIP, CLIP).astype(np.int16).flatten()
        sign = (x < 0)
        x = np.abs(x) + BIAS
        def segment(val):
            if val < 256: return 0
            elif val < 512: return 1
            elif val < 1024: return 2
            elif val < 2048: return 3
            elif val < 4096: return 4
            elif val < 8192: return 5
            elif val < 16384: return 6
            else: return 7
        segfunc = np.vectorize(segment)
        seg = segfunc(x)
        mantissa = ((x >> (seg + 3)) & 0x0F)
        ulaw = ~(sign << 7 | seg << 4 | mantissa) & 0xFF
        return ulaw.astype(np.uint8)

    @staticmethod
    def convert_speech_to_raw_audio(text):
        """TTS: text → mu-law bytes (used for chunked audio response)"""
        tts = gTTS(text=text, lang='en', slow=False)
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        audio_segment = AudioSegment.from_file(mp3_fp, format="mp3")
        audio_segment = audio_segment.set_frame_rate(8000).set_channels(1)
        pcm_array = np.array(audio_segment.get_array_of_samples(), dtype=np.int16)
        return AudioUtils.lin2ulaw(pcm_array)

    @staticmethod
    def convert_speech_to_wav_audio(text):
        """TTS: text → WAV bytes with mu-law codec (used for session-start welcome)"""
        if text in AudioUtils._audio_cache:
            return AudioUtils._audio_cache[text]
        tts = gTTS(text=text, lang='en', slow=False)
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        audio_segment = AudioSegment.from_file(mp3_fp, format="mp3")
        wav_fp = io.BytesIO()
        audio_segment.export(wav_fp, format="wav", parameters=["-ar", "8000", "-acodec", "pcm_mulaw"])
        wav_fp.seek(0)
        raw_audio_bytes = wav_fp.read()
        AudioUtils._audio_cache[text] = raw_audio_bytes
        return raw_audio_bytes

    @staticmethod
    def convert_to_text(pcm_data):
        """STT: PCM int16 numpy array → transcribed text string (or None)"""
        pcm_data = pcm_data.reshape(-1, 1)
        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, pcm_data, 8000, format="WAV", subtype="PCM_16")
        wav_buffer.seek(0)
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_buffer) as source:
            audio = recognizer.record(source)
        try:
            return recognizer.recognize_google(audio)
        except sr.RequestError:
            print("[STT] Google Speech Recognition service unavailable")
        except Exception:
            pass
        return None

