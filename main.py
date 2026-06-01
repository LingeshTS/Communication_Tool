from fastapi import FastAPI, UploadFile, File, Form
from typing import List
from faster_whisper import WhisperModel
import re
import shutil
import os
import textstat
import uuid

app = FastAPI()

# Initialize the local transcription model
model = WhisperModel("tiny", device="cpu", compute_type="int8")

# =====================================================================
# AUDIO ASSESSMENT ENDPOINT
# =====================================================================
@app.post("/assess/speech")
async def assess_speech(file: UploadFile = File(...)):
    file_extension = os.path.splitext(file.filename)[1] or ".wav"
    unique_filename = f"audio_{uuid.uuid4().hex}{file_extension}"
    temp_path = os.path.join(os.getcwd(), unique_filename)
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        segments, info = model.transcribe(temp_path, beam_size=5, word_timestamps=True)
        transcript_text = ""
        total_words = 0
        filler_count = 0
        filler_words = ["um", "uh", "like", "ah", "so"]
        
        segments_list = list(segments)
        for segment in segments_list:
            transcript_text += segment.text + " "
            if segment.words:
                for word_obj in segment.words:
                    total_words += 1
                    clean_word = re.sub(r'[^\w]', '', word_obj.word.lower().strip())
                    if clean_word in filler_words:
                        filler_count += 1

        audio_duration_minutes = info.duration / 60
        raw_speech_wpm = total_words / audio_duration_minutes if audio_duration_minutes > 0 else 0.0
        
        # Apply the Articulation Scaling Factor to map spoken fluency to your custom brackets
        words_per_minute = round(raw_speech_wpm * 0.33, 1)
        long_pauses = max(len(segments_list) - 1, 0)

        # =====================================================================
        # SPECIFIED METRIC BRACKETS WITH CLEAN PROFESSIONAL TITLES
        # =====================================================================
        if words_per_minute < 35:
            speech_tier = "Beginner"
        elif 35 <= words_per_minute < 50:
            speech_tier = "Intermediate"
        elif 50 <= words_per_minute <= 80:
            speech_tier = "Advanced"
        else:
            speech_tier = "Elite"

        return {
            "transcript": transcript_text.strip(),
            "words_per_minute": words_per_minute,
            "filler_word_count": filler_count,
            "long_pauses_detected": long_pauses,
            "speech_tier": speech_tier
        }

    except Exception as e:
        return {
            "transcript": f"Audio processing error: {str(e)}", 
            "words_per_minute": 0.0, 
            "filler_word_count": 0, 
            "long_pauses_detected": 0,
            "speech_tier": "N/A"
        }
    finally:
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except Exception: pass

# =====================================================================
# SECURE TEXT ASSESSMENT ENDPOINT
# =====================================================================
@app.post("/assess/text")
async def assess_text(text: str = Form(...), cheat_flag: bool = Form(False)):
    if cheat_flag:
        return {
            "grammar_score": 0, "vocabulary_score": 0, "conciseness_score": 0, "impact_score": 0,
            "identified_errors": ["PROCTOR VIOLATION: Copy-pasting or switching tabs during active testing is prohibited."],
            "identified_strengths": [], "improvement_suggestions": ["Restart assessment session and type manually."]
        }

    words = [w.lower().strip(".,!?;:") for w in text.split() if w.strip()]
    total_words = len(words)
    
    if total_words == 0:
        return {
            "grammar_score": 0, "vocabulary_score": 0, "conciseness_score": 0, "impact_score": 0, 
            "identified_errors": ["No text provided"], "identified_strengths": [], "improvement_suggestions": ["Please enter a response."]
        }

    unique_words = set(words)
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    total_sentences = max(len(sentences), 1)
    avg_sentence_len = total_words / total_sentences

    raw_reading_ease = textstat.flesch_reading_ease(text)
    structural_deductions = 0
    if avg_sentence_len > 25 or avg_sentence_len < 8:
        structural_deductions += 15
    
    gibberish_words = [w for w in words if not re.match(r'^[a-z]+$', w)]
    if len(gibberish_words) > (total_words * 0.2):
        structural_deductions += 30

    grammar_score = int(max(min(raw_reading_ease - structural_deductions, 98), 40))

    ttr = len(unique_words) / total_words
    professional_dictionary = {
        "execute", "lead", "manage", "optimize", "deliver", "transform", "build", "design", 
        "accelerate", "achieve", "strategy", "results", "growth", "implement", "impact",
        "leverage", "robust", "architecture", "deployment", "analytics", "scalability"
    }
    advanced_matches = sum(1 for w in unique_words if w in professional_dictionary)
    
    vocabulary_score = int((ttr * 65) + (min(advanced_matches * 6, 33)))
    vocabulary_score = max(min(vocabulary_score, 96), 45)

    if 12 <= avg_sentence_len <= 20:
        conciseness_score = 95
    else:
        variance = abs(16 - avg_sentence_len)
        conciseness_score = max(100 - int(variance * 3), 40)

    impact_score = min(40 + (len([w for w in words if w in professional_dictionary]) * 12), 98)

    errors, strengths, suggestions = [], [], []

    if avg_sentence_len > 22:
        errors.append(f"Sentences are too dense, averaging {round(avg_sentence_len, 1)} words per phrase.")
        suggestions.append("Break down your concepts into shorter, single-idea clauses.")
    elif avg_sentence_len < 11:
        errors.append(f"Sentences are structurally choppy, averaging {round(avg_sentence_len, 1)} words.")
        suggestions.append("Use transitional terms like 'furthermore' to balance text flow.")
    else:
        strengths.append(f"Excellent structural pacing averaging {round(avg_sentence_len, 1)} words per phrase.")

    if advanced_matches == 0:
        errors.append("Passive vocabulary style: Lacks results-oriented business vocabulary words.")
        suggestions.append("Integrate dynamic professional focus terms (e.g., use 'optimized' or 'executed').")
    else:
        strengths.append("Professional corporate tone established via key phrases.")

    return {
        "grammar_score": grammar_score,
        "vocabulary_score": vocabulary_score,
        "conciseness_score": conciseness_score,
        "impact_score": impact_score,
        "identified_errors": errors,
        "identified_strengths": strengths,
        "improvement_suggestions": suggestions
    }