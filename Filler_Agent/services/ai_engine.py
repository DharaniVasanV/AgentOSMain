import os
import logging
import numpy as np
from typing import List, Dict, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

_ST_MODEL = None

def get_st_model():
    global _ST_MODEL
    if _ST_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            _ST_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("SentenceTransformer model loaded into memory.")
        except Exception as e:
            logger.warning(f"SentenceTransformer lazy-load note: {e}")
    return _ST_MODEL


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculates similarity score (0.0 to 1.0) between two strings."""
    t1 = text1.lower().strip()
    t2 = text2.lower().strip()
    
    # Exact or keyword matches
    if t1 in t2 or t2 in t1:
        return 0.92
    
    st_model = get_st_model()
    if st_model:
        try:
            from sentence_transformers import util
            emb1 = st_model.encode(t1, convert_to_tensor=True)
            emb2 = st_model.encode(t2, convert_to_tensor=True)
            cosine_sim = float(util.cos_sim(emb1, emb2)[0][0])
            return max(0.0, min(1.0, cosine_sim))
        except Exception:
            pass


    # Sequence Matcher fallback
    return SequenceMatcher(None, t1, t2).ratio()

def query_gemini_api(question_text: str, context_profile: List[Dict[str, str]], options: List[str] = None) -> Tuple[str, float]:
    """
    Queries Google Gemini REST API to synthesize answers for complex or open-ended questions.
    Uses requests REST API to bypass native gRPC DLL Application Control restrictions.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return ("", 0.0)

    # Models to attempt
    models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    opts_str = f"Choices: {options}" if options else ""
    
    prompt_text = f"""
You are an AI Form Filler Assistant.
User Saved Profile Data: {context_profile}

Task: Generate a concise, accurate response for this form question: "{question_text}". {opts_str}

Rules:
1. If choices/options are given, choose the EXACT option that best matches the user profile.
2. If open-ended, write a 1-2 sentence professional response based on user profile.
3. Respond ONLY with the final answer text. No conversational filler or explanations.
"""

    import requests
    for m in models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
            payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
            res = requests.post(url, json=payload, timeout=6)
            if res.status_code == 200:
                data = res.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        ans = parts[0]["text"].strip()
                        if ans:
                            return (ans, 0.92)
        except Exception as err:
            logger.warning(f"Gemini API model {m} query note: {err}")

    return ("", 0.0)

def match_question_to_profile(question_text: str, field_type: str, options: List[str], profiles: List[Dict[str, str]]) -> Tuple[str, float, str, bool]:
    """
    Matches a form question to saved user profile entries.
    Returns: (proposed_answer, confidence_score, source, is_missing)
    """
    if not profiles:
        return ("", 0.0, "Missing", True)

    best_match_val = ""
    best_score = 0.0
    matched_key = ""

    for p in profiles:
        key = p.get("field_key", "")
        val = p.get("field_value", "")
        
        sim = calculate_similarity(question_text, key)
        
        # Additional heuristics for common form fields
        q_lower = question_text.lower()
        k_lower = key.lower()

        if ("name" in q_lower and "name" in k_lower) or \
           ("email" in q_lower and "email" in k_lower) or \
           ("phone" in q_lower and "phone" in k_lower) or \
           ("location" in q_lower or "city" in q_lower) and ("location" in k_lower or "city" in k_lower) or \
           ("role" in q_lower or "title" in q_lower) and ("role" in k_lower or "title" in k_lower) or \
           ("skill" in q_lower and "skill" in k_lower) or \
           ("experience" in q_lower or "year" in q_lower) and ("experience" in k_lower or "year" in k_lower) or \
           (field_type == "file" or "resume" in q_lower or "cv" in q_lower or "document" in q_lower) and ("resume" in k_lower or "cv" in k_lower or "document" in k_lower or val.startswith("uploads/")):
            sim = max(sim, 0.95)


        if sim > best_score:
            best_score = sim
            best_match_val = val
            matched_key = key

    # Handle radio / dropdown / checkbox matching against options
    if options and best_match_val:
        if field_type in ["radio", "dropdown"]:
            # Find closest option to best_match_val
            best_opt = ""
            best_opt_sim = 0.0
            for opt in options:
                opt_sim = calculate_similarity(best_match_val, opt)
                if opt_sim > best_opt_sim:
                    best_opt_sim = opt_sim
                    best_opt = opt
            
            if best_opt_sim > 0.5:
                best_match_val = best_opt
                best_score = max(best_score, best_opt_sim)

        elif field_type == "checkbox":
            # Match user profile skills/items against checkbox options
            selected_opts = []
            for opt in options:
                for item in best_match_val.split(","):
                    if calculate_similarity(item.strip(), opt) > 0.6:
                        if opt not in selected_opts:
                            selected_opts.append(opt)
            if selected_opts:
                best_match_val = ", ".join(selected_opts)
                best_score = max(best_score, 0.85)

    # Check Gemini AI if confidence is low or if open-ended paragraph field
    if (best_score < 0.60 or field_type == "paragraph") and os.getenv("GEMINI_API_KEY"):
        gemini_ans, gemini_score = query_gemini_api(question_text, profiles, options)
        if gemini_ans:
            return (gemini_ans, gemini_score, "AI (Gemini)", False)

    # Determine confidence status thresholds
    if best_score >= 0.65 and best_match_val:
        return (best_match_val, round(best_score, 2), "Profile", False)
    elif best_score >= 0.40 and best_match_val:
        return (best_match_val, round(best_score, 2), "AI", True)
    else:
        return ("", 0.0, "Missing", True)

def query_openai_fallback(question_text: str, context_profile: List[Dict[str, str]]) -> str:
    """
    Pluggable OpenAI API fallback for complex open-ended questions.
    Activated if OPENAI_API_KEY environment variable is present.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return ""

    try:
        import openai
        openai.api_key = api_key

        prompt = f"Given user profile: {context_profile}\nAnswer this form question concisely: '{question_text}'"
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"OpenAI API call skipped/failed: {e}")
        return ""

