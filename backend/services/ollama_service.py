import logging
import requests
import os
import time
from typing import List, Optional, Dict
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class OllamaService:
    """
    שירות Ollama מואץ עם:
    - פרמטרים מותאמים למהירות
    - timeout אגרסיבי יותר
    - retry logic מהיר יותר
    - אופטימיזציה של prompts
    """

    def __init__(self):
        self.base_url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
        self.embedding_model = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
        self.chat_model = os.getenv("OLLAMA_CHAT_MODEL", "gemma:2b")
        
        # timeout מהיר יותר
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", "60"))  # הקטנתי מ-90 ל-60
        self.max_retries = 2  # הקטנתי מ-3 ל-2
        
        # פרמטרים מותאמים למהירות מקסימלית
        self.speed_optimized_params = {
            "temperature": 0.3,    # פחות יצירתיות, יותר מהירות
            "top_k": 20,           # הקטנתי מ-40 ל-20
            "top_p": 0.8,          # הקטנתי מ-0.9 ל-0.8
            "repeat_penalty": 1.05, # הקטנתי מ-1.1 ל-1.05
            "num_ctx": int(os.getenv("AI_NUM_CTX", "1024")),  # הקטנתי מ-2048 ל-1024
            "num_predict": 400,    # הקטנתי מ-800 ל-400
            "stop": ["Human:", "User:", "שאלה:", "Q:", "###", "\n\n\n"]
        }
        
        # Thread pool לקריאות מקבילות
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        logger.info(f"Ollama service initialized with speed optimizations: {self.chat_model}")

    def health_check(self) -> bool:
        """בדיקת תקינות מהירה עם timeout קצר מאוד"""
        try:
            response = requests.get(f"{self.base_url}/api/version", timeout=3)  # הקטנתי מ-5 ל-3
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    def get_embedding(self, text: str, retries: int = 0) -> List[float]:
        """קבלת embedding מהיר יותר עם retry logic קצר"""
        if retries >= self.max_retries:
            logger.error(f"Max retries reached for embedding")
            return []

        try:
            # ניקוי טקסט מהיר יותר
            clean_text = self._clean_text_fast(text)
            
            payload = {
                "model": self.embedding_model,
                "prompt": clean_text
            }
            
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json=payload,
                timeout=self.timeout - 20  # embedding צריך להיות מהיר יותר
            )
            
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                embedding = data.get("embedding")
                if embedding and len(embedding) > 0:
                    logger.debug(f"Embedding generated in {duration:.2f}s")
                    return embedding
                else:
                    logger.warning("Empty embedding received")
                    return []
            else:
                logger.error(f"Embedding API error: {response.status_code}")
                # retry מהיר יותר
                if retries < self.max_retries:
                    time.sleep(0.5)  # הקטנתי מ-1 ל-0.5
                    return self.get_embedding(text, retries + 1)
                return []
                
        except requests.exceptions.Timeout:
            logger.warning(f"Embedding timeout, retry {retries + 1}")
            if retries < self.max_retries:
                return self.get_embedding(text, retries + 1)
            return []
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            if retries < self.max_retries:
                time.sleep(0.5)
                return self.get_embedding(text, retries + 1)
            return []

    def generate_response(self, context: str, prompt: str, retries: int = 0) -> Optional[str]:
        """יצירת תגובה מהירה יותר עם אופטימיזציות"""
        if retries >= self.max_retries:
            logger.error("Max retries reached for response generation")
            return None

        try:
            # אופטימיזציה מהירה של ה-prompt
            optimized_prompt = self._optimize_prompt_fast(context, prompt)
            
            payload = {
                "model": self.chat_model,
                "prompt": optimized_prompt,
                "stream": False,
                "options": self.speed_optimized_params
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
                    # פוסט-פרוססינג מהיר
                    cleaned_response = self._post_process_fast(generated_text)
                    logger.info(f"Response generated in {duration:.2f}s")
                    return cleaned_response
                else:
                    logger.warning("Empty response received")
                    return None
            else:
                logger.error(f"Generation API error: {response.status_code}")
                if retries < self.max_retries:
                    time.sleep(1)
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
                time.sleep(1)
                return self.generate_response(context, prompt, retries + 1)
            return None

    def _clean_text_fast(self, text: str) -> str:
        """ניקוי טקסט מהיר יותר"""
        import re
        
        # ניקוי בסיסי בלבד
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)  # מספר רווחים ברווח יחיד
        
        # הגבלת אורך אגרסיבית יותר למהירות
        if len(text) > 500:  # הקטנתי מ-1000 ל-500
            text = text[:500] + "..."
            
        return text

    def _optimize_prompt_fast(self, context: str, user_prompt: str) -> str:
        """אופטימיזציה מהירה של ה-prompt"""
        
        # הגבלת אורך ההקשר אגרסיבית יותר
        if len(context) > 1500:  # הקטנתי מ-3000 ל-1500
            context = context[:750] + "\n...\n" + context[-750:]
        
        # אם זה כבר prompt מובנה, השתמש בו
        if "אתה עוזר דיגיטלי" in user_prompt:
            return user_prompt[:2000]  # הגבלת אורך
            
        # prompt מינימלי ומהיר
        optimized_prompt = f"""עוזר דיגיטלי למערכת ניהול ספקים.

מידע: {context}

שאלה: {user_prompt}

תשובה קצרה ומעשית בעברית:"""

        return optimized_prompt

    def _post_process_fast(self, response: str) -> str:
        """עיבוד מהיר אחרי יצירה"""
        import re
        
        # ניקוי בסיסי בלבד
        response = response.strip()
        
        # הסרת תחילות מיותרות
        response = re.sub(r'^(תשובה|מענה|התשובה היא):\s*', '', response, flags=re.IGNORECASE)
        
        # הגבלת אורך מהירה
        if len(response) > 1200:  # הקטנתי מ-2000 ל-1200
            sentences = response.split('.')
            truncated = []
            total_length = 0
            
            for sentence in sentences:
                if total_length + len(sentence) > 1000:
                    break
                if sentence.strip():
                    truncated.append(sentence.strip())
                    total_length += len(sentence)
            
            if truncated:
                response = '. '.join(truncated) + '.'
            else:
                response = response[:1000] + "..."
        
        # הסרת שורות ריקות מיותרות
        response = re.sub(r'\n{3,}', '\n\n', response)
        
        return response.strip()

    async def generate_response_async(self, context: str, prompt: str) -> Optional[str]:
        """גרסה אסינכרונית לביצועים טובים יותר"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, 
            self.generate_response, 
            context, 
            prompt
        )

    async def get_embedding_async(self, text: str) -> List[float]:
        """גרסה אסינכרונית לקבלת embedding"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.get_embedding,
            text
        )

    def get_model_info(self) -> Dict:
        """קבלת מידע על המודלים - גרסה מהירה"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
        return {"models": []}

    def warm_up(self):
        """חימום המודל למהירות טובה יותר"""
        try:
            logger.info("Warming up Ollama models...")
            
            # חימום מודל embedding
            self.get_embedding("test")
            
            # חימום מודל chat
            self.generate_response("test context", "test question")
            
            logger.info("Ollama models warmed up successfully")
        except Exception as e:
            logger.warning(f"Model warm-up failed: {e}")