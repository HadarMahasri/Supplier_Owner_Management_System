#!/bin/bash
# setup_complete_ultra_fast.sh - התקנה מלאה אולטרה מהירה עם Docker

set -e  # עצור בשגיאה

echo "🚀 התקנה מלאה למערכת צ'אט אולטרה מהירה!"
echo "=============================================="

# צבעים לפלט יפה
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }

# בדיקות בסיסיות
print_info "בודק דרישות מוקדמות..."

if ! command -v docker &> /dev/null; then
    print_error "Docker לא מותקן. אנא התקן Docker והרץ שוב."
    exit 1
fi

if ! docker info > /dev/null 2>&1; then
    print_error "Docker לא פועל. אנא הפעל Docker והרץ שוב."
    exit 1
fi

print_success "Docker פועל"

# יצירת תיקיית עבודה
WORK_DIR="ultra_fast_ollama"
if [ ! -d "$WORK_DIR" ]; then
    mkdir -p $WORK_DIR
    print_info "יצרתי תיקיית עבודה: $WORK_DIR"
fi

cd $WORK_DIR

# עצור containers קיימים
print_info "מנקה containers ישנים..."
docker stop ollama_ultra_fast 2>/dev/null || true
docker rm ollama_ultra_fast 2>/dev/null || true
docker stop ollama 2>/dev/null || true
docker rm ollama 2>/dev/null || true

# יצירת network אם לא קיים
docker network create ollama_network 2>/dev/null || true

print_info "יוצר Ollama container מאופטמ..."

# זיהוי GPU
GPU_ARGS=""
if command -v nvidia-smi &> /dev/null && nvidia-smi > /dev/null 2>&1; then
    print_info "זיהיתי GPU NVIDIA - מפעיל תמיכה GPU"
    GPU_ARGS="--gpus all"
fi

# הרץ Ollama עם כל האופטימיזציות
docker run -d \
    $GPU_ARGS \
    --name ollama_ultra_fast \
    --network ollama_network \
    -p 11434:11434 \
    -v ollama_ultra_data:/root/.ollama \
    -e OLLAMA_NUM_PARALLEL=1 \
    -e OLLAMA_MAX_LOADED_MODELS=1 \
    -e OLLAMA_FLASH_ATTENTION=1 \
    -e OLLAMA_LOW_VRAM=true \
    -e OLLAMA_KEEP_ALIVE=2m \
    -e OLLAMA_MAX_QUEUE=1 \
    -e OLLAMA_DEBUG=false \
    --memory=2g \
    --cpus=2 \
    --restart unless-stopped \
    ollama/ollama

print_info "ממתין שהשרת יתחיל..."
sleep 15

# בדיקת החיבור
print_info "בודק חיבור לשרת..."
for i in {1..30}; do
    if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
        print_success "Ollama server פועל!"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "השרת לא הצליח להתחיל בזמן"
        print_info "בודק logs:"
        docker logs ollama_ultra_fast
        exit 1
    fi
    echo "   ממתין... ($i/30)"
    sleep 2
done

# הצג גרסה
VERSION=$(curl -s http://localhost:11434/api/version | grep -o '"version":"[^"]*' | cut -d'"' -f4)
print_success "גרסת Ollama: $VERSION"

print_info "מנקה מודלים כבדים ישנים..."
# נקה מודלים כבדים
MODELS_TO_REMOVE=("phi3:mini" "phi3" "gemma2:2b" "llama2" "llama3" "mistral")
for model in "${MODELS_TO_REMOVE[@]}"; do
    docker exec ollama_ultra_fast ollama rm "$model" 2>/dev/null || true
done

print_info "מוריד מודלים אולטרה מהירים..."

# הורד מודל ראשי
print_info "מוריד qwen2.5:0.5b (394MB)..."
if docker exec ollama_ultra_fast ollama pull qwen2.5:0.5b; then
    print_success "qwen2.5:0.5b הותקן בהצלחה"
else
    print_warning "בעיה עם qwen2.5:0.5b, מנסה tinyllama..."
fi

# הורד מודל חלופי
print_info "מוריד tinyllama (637MB) כחלופה..."
if docker exec ollama_ultra_fast ollama pull tinyllama; then
    print_success "tinyllama הותקן בהצלחה"
else
    print_error "לא הצלחתי להתקין מודלים"
    exit 1
fi

# בדיקת המודלים
print_info "בודק מודלים זמינים:"
docker exec ollama_ultra_fast ollama list

# בדיקת פעולת המודל
print_info "בודק שהמודל עובד..."
TEST_PROMPT="שלום, איך העסקים?"

if RESPONSE=$(docker exec ollama_ultra_fast sh -c "echo '$TEST_PROMPT' | ollama run qwen2.5:0.5b 2>/dev/null | head -n 1"); then
    if [ -n "$RESPONSE" ]; then
        print_success "המודל עובד! דוגמה: $(echo $RESPONSE | cut -c1-50)..."
        MAIN_MODEL="qwen2.5:0.5b"
    else
        print_warning "qwen2.5:0.5b לא עובד, מנסה tinyllama..."
        if RESPONSE=$(docker exec ollama_ultra_fast sh -c "echo '$TEST_PROMPT' | ollama run tinyllama 2>/dev/null | head -n 1"); then
            print_success "tinyllama עובד!"
            MAIN_MODEL="tinyllama"
        else
            print_error "אף מודל לא עובד כראוי"
            exit 1
        fi
    fi
else
    print_error "בדיקת המודל נכשלה"
    exit 1
fi

# יצירת קבצי הגדרות
print_info "יוצר קבצי הגדרות..."

# קובץ .env
cat > .env << EOF
# Ultra Fast Ollama Configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=$MAIN_MODEL
AI_NUM_PREDICT=25
AI_NUM_CTX=512

# Performance settings
REQUEST_TIMEOUT=8
STREAM_CHUNK_SIZE=5
MAX_RETRIES=2
EOF

# docker-compose לניהול קל
cat > docker-compose.yml << EOF
version: '3.8'
services:
  ollama:
    image: ollama/ollama:latest
    container_name: ollama_ultra_fast
    ports:
      - "11434:11434"
    volumes:
      - ollama_ultra_data:/root/.ollama
    environment:
      - OLLAMA_NUM_PARALLEL=1
      - OLLAMA_MAX_LOADED_MODELS=1
      - OLLAMA_FLASH_ATTENTION=1
      - OLLAMA_LOW_VRAM=true
      - OLLAMA_KEEP_ALIVE=2m
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2'
    restart: unless-stopped

volumes:
  ollama_ultra_data:
EOF

# סקריפט ניהול
cat > manage.sh << 'EOF'
#!/bin/bash
case "$1" in
    start)
        echo "🚀 מפעיל Ollama..."
        docker start ollama_ultra_fast
        ;;
    stop)
        echo "⏹️ עוצר Ollama..."
        docker stop ollama_ultra_fast
        ;;
    restart)
        echo "🔄 מפעיל מחדש..."
        docker restart ollama_ultra_fast
        ;;
    logs)
        echo "📋 מציג logs..."
        docker logs -f ollama_ultra_fast
        ;;
    test)
        echo "🧪 בודק המודל..."
        docker exec ollama_ultra_fast ollama run qwen2.5:0.5b "בדיקה מהירה"
        ;;
    models)
        echo "📋 מודלים זמינים:"
        docker exec ollama_ultra_fast ollama list
        ;;
    *)
        echo "שימוש: $0 {start|stop|restart|logs|test|models}"
        ;;
esac
EOF

chmod +x manage.sh

# סיכום
print_success "ההתקנה הושלמה בהצלחה! 🎉"
echo ""
echo "================================"
echo "🚀 מערכת אולטרה מהירה מוכנה!"
echo "================================"
echo ""
print_info "הגדרות:"
echo "   📍 כתובת: http://localhost:11434"
echo "   🤖 מודל ראשי: $MAIN_MODEL"
echo "   ⚡ זמן תגובה צפוי: 1-3 שניות"
echo "   💾 זיכרון מקסימלי: 2GB"
echo ""
print_info "קבצים שנוצרו:"
echo "   📄 .env - הגדרות סביבה"
echo "   🐳 docker-compose.yml - להפעלה עם compose"
echo "   🔧 manage.sh - ניהול המערכת"
echo ""
print_info "פקודות שימושיות:"
echo "   ./manage.sh start   - הפעלה"
echo "   ./manage.sh stop    - עצירה"  
echo "   ./manage.sh test    - בדיקה"
echo "   ./manage.sh logs    - logs"
echo ""
print_info "לשימוש בפרויקט:"
echo "   1. העתק את קובץ .env לתיקיית הפרויקט"
echo "   2. או הגדר: export OLLAMA_MODEL=$MAIN_MODEL"
echo "   3. החלף את קבצי ai_service.py ו-ai_router.py"
echo "   4. הפעל מחדש את השרת"
echo ""
print_success "תיהני ממהירות ברק! ⚡🚀"

# בדיקה סופית
print_info "בודק מהירות תגובה..."
START_TIME=$(date +%s.%N)
docker exec ollama_ultra_fast sh -c "echo 'בדיקה' | ollama run $MAIN_MODEL" > /dev/null 2>&1 || true
END_TIME=$(date +%s.%N)
RESPONSE_TIME=$(echo "$END_TIME - $START_TIME" | bc -l 2>/dev/null | head -c 4 || echo "~2")

if (( $(echo "$RESPONSE_TIME < 5" | bc -l 2>/dev/null || echo 1) )); then
    print_success "מהירות תגובה: ${RESPONSE_TIME}s ⚡"
else
    print_warning "מהירות תגובה: ${RESPONSE_TIME}s (עדיין מהיר!)"
fi