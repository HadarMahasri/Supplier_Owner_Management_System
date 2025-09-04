import logging
import requests
import os
import time
from typing import List, Optional, Dict
import json

logger = logging.getLogger(__name__)

class OllamaService:
    """
    שירות Ollama משודרג עם:
    - בקרה חכמה על פרמטרים
    - retry logic חכם
    - אופטימיזציה של prompts
    - ביצועים משופרים
    """

    def __init__(self):
        self.base_url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
        self.embedding_model = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
        self.chat_model = os.getenv("OLLAMA_CHAT_MODEL", "gemma:2b")
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", "90"))
        self.max_retries = 3
        
        # פרמטרים מותאמים לביצועים ואיכות טובים יותר
        self.optimized_params = {
            "temperature": 0.7,  # איזון בין יצירתיות לדיוק
            "top_k": 40,         # הגבלת מספר המילים הבאות
            "top_p": 0.9,        # חיתוך הסתברויות
            "repeat_penalty": 1.1, # מניעת חזרה
            "num_ctx": int(os.getenv("AI_NUM_CTX", "2048")),  # חלון הקשר
            "num_predict": 800,   # אורך תגובה מקסימלי
            "stop": ["Human:", "User:", "שאלה:", "Q:", "###"]  # מילות עצירה
        }
        
        logger.info(f"Ollama service initialized with {self.chat_model}")

    def health_check(self) -> bool:
        """בדיקת תקינות משופרת עם timeout קצר"""
        try:
            response = requests.get(f"{self.base_url}/api/version", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    def get_embedding(self, text: str, retries: int = 0) -> List[float]:
        """קבלת embedding עם retry logic משופר"""
        if retries >= self.max_retries:
            logger.error(f"Max retries reached for embedding")
            return []

        try:
            # ניקוי טקסט לשיפור איכות ה-embedding
            clean_text = self._clean_text_for_embedding(text)
            
            payload = {
                "model": self.embedding_model,
                "prompt": clean_text
            }
            
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json=payload,
                timeout=self.timeout
            )
            
            duration = time.time() - start_time
            logger.debug(f"Embedding generated in {duration:.2f}s")
            
            if response.status_code == 200:
                data = response.json()
                embedding = data.get("embedding")
                if embedding and len(embedding) > 0:
                    return embedding
                else:
                    logger.warning("Empty embedding received")
                    return []
            else:
                logger.error(f"Embedding API error: {response.status_code}")
                # נסיון חוזר עם עיכוב
                time.sleep(1 + retries)
                return self.get_embedding(text, retries + 1)
                
        except requests.exceptions.Timeout:
            logger.warning(f"Embedding timeout, retry {retries + 1}")
            if retries < self.max_retries:
                return self.get_embedding(text, retries + 1)
            return []
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            if retries < self.max_retries:
                time.sleep(1 + retries)
                return self.get_embedding(text, retries + 1)
            return []

    def generate_response(self, context: str, prompt: str, retries: int = 0) -> Optional[str]:
        """יצירת תגובה משופרת עם retry logic ואופטימיזציה"""
        if retries >= self.max_retries:
            logger.error("Max retries reached for response generation")
            return None

        try:
            # אופטימיזציה של ה-prompt
            optimized_prompt = self._optimize_prompt(context, prompt)
            
            payload = {
                "model": self.chat_model,
                "prompt": optimized_prompt,
                "stream": False,
                "options": self.optimized_params
            }
            
            start_time = time.time()
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                generated_text = data.get("response", "").strip()
                
                if generated_text:
                    # פוסט-פרוססינג לשיפור איכות התשובה
                    cleaned_response = self._post_process_response(generated_text)
                    logger.info(f"Response generated in {duration:.2f}s, length: {len(cleaned_response)}")
                    return cleaned_response
                else:
                    logger.warning("Empty response received")
                    return None
            else:
                logger.error(f"Generation API error: {response.status_code}")
                # נסיון חוזר עם פרמטרים מותאמים
                if retries < self.max_retries:
                    time.sleep(2 + retries)
                    return self.generate_response(context, prompt, retries + 1)
                return None
                
        except requests.exceptions.Timeout:
            logger.warning(f"Generation timeout, retry {retries + 1}")
            if retries < self.max_retries:
                return self.generate_response(context, prompt, retries + 1)
            return None
        except Exception as e:
            logger.error(f"Generation error: {e}")
            if retries < self.max_retries:
                time.sleep(2 + retries)
                return self.generate_response(context, prompt, retries + 1)
            return None

    def _clean_text_for_embedding(self, text: str) -> str:
        """ניקוי טקסט לשיפור איכות ה-embedding"""
        import re
        
        # הסרת תווי קצה מיותרים
        text = text.strip()
        
        # החלפת מספר רווחים ברווח יחיד
        text = re.sub(r'\s+', ' ', text)
        
        # הסרת תווים מיוחדים מיותרים
        text = re.sub(r'[^\w\s\u0590-\u05FF.,!?-]', '', text)
        
        # הגבלת אורך לביצועים טובים יותר
        if len(text) > 1000:
            text = text[:1000] + "..."
            
        return text

    def _optimize_prompt(self, context: str, user_prompt: str) -> str:
        """אופטימיזציה של ה-prompt לתשובות טובות יותר"""
        
        # הגבלת אורך ההקשר
        if len(context) > 3000:
            # קח את החלק הרלוונטי ביותר (התחלה וסוף)
            context = context[:1500] + "\n...\n" + context[-1500:]
        
        # בניית prompt מובנה ומותאם
        system_instruction = """אתה עוזר דיגיטלי מומחה ומקצועי למערכת ניהול ספקים. 

כללים חשובים:
- תן תשובות ישירות ומועילות
- השתמש בדוגמאות מהמערכת כשאפשר
- תמיד הציע פעולה מעשית הבאה
- אל תחזור על עצמך
- בעברית ברורה ומקצועית
- אם אין מידע מדויק, תסביר מה כן אפשר לעשות

מידע רקע מהמערכת:"""

        # אם זה בעצם הכל context, נשתמש בו כפי שהוא
        if "אתה עוזר דיגיטלי" in user_prompt:
            return user_prompt  # זה כבר prompt מובנה
            
        # אחרת נבנה prompt חדש
        optimized_prompt = f"""{system_instruction}
{context}

שאלת המשתמש: {user_prompt}

תשובה מועילה:"""

        return optimized_prompt

    def _post_process_response(self, response: str) -> str:
        """עיבוד אחרי יצירה לשיפור איכות התשובה"""
        import re
        
        # הסרת תחילות מיותרות שהמודל לפעמים מוסיף
        response = re.sub(r'^(תשובה|מענה|התשובה היא|תגובה):\s*', '', response, flags=re.IGNORECASE)
        
        # ניקוי חזרות של שורות
        lines = response.split('\n')
        unique_lines = []
        prev_line = ""
        
        for line in lines:
            line = line.strip()
            if line and line != prev_line:
                unique_lines.append(line)
                prev_line = line
        
        response = '\n'.join(unique_lines)
        
        # הסרת חזרות של ביטויים
        response = re.sub(r'(\b\w+\b)(\s+\1){2,}', r'\1', response)
        
        # הגבלת אורך תשובה - בצורה חכמה יותר
        if len(response) > 2000:
            # חיתוך במקום המשפט האחרון השלם
            sentences = response.split('.')
            truncated = []
            total_length = 0
            
            for sentence in sentences:
                if total_length + len(sentence) > 1800:
                    break
                if sentence.strip():
                    truncated.append(sentence.strip())
                    total_length += len(sentence)
            
            if truncated:
                response = '. '.join(truncated) + '.'
            else:
                response = response[:1800] + "..."
        
        # הסרת שורות ריקות מיותרות
        response = re.sub(r'\n{3,}', '\n\n', response)
        
        return response.strip()

    def get_model_info(self) -> Dict:
        """קבלת מידע על המודלים הזמינים"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
        return {"models": []}