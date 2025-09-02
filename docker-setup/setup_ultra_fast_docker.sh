#!/bin/bash
# setup_ultra_fast_docker.sh - התקנה מהירה למודל אולטרה קל עם Docker

echo "🐳 מתקין מודל אולטרה מהיר עם Docker..."
echo "================================================"

# בדוק אם Docker פועל
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker לא פועל. אנא הפעל את Docker והרץ שוב."
    exit 1
fi

echo "✅ Docker פועל"

# בדוק אם Ollama container קיים
CONTAINER_NAME="ollama"
if docker ps -a --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo "🔍 מצאתי Ollama container קיים"
    
    # עצור את הcontainer אם הוא פועל
    if docker ps --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        echo "⏹️ עוצר Ollama container..."
        docker stop $CONTAINER_NAME
    fi
    
    # הסר את הcontainer הישן
    echo "🗑️ מסיר container ישן..."
    docker rm $CONTAINER_NAME
fi

echo "🚀 יוצר Ollama container חדש עם אופטימיזציה..."

# בדוק אם יש GPU זמין
GPU_FLAG=""
if command -v nvidia-smi &> /dev/null && nvidia-smi > /dev/null 2>&1; then
    echo "🎮 זיהיתי GPU - מפעיל תמיכה GPU"
    GPU_FLAG="--gpus all"
else
    echo "💻 אין GPU זמין - פועל במצב CPU"
fi

# הרץ Ollama container עם אופטימיזציות
docker run -d \
    $GPU_FLAG \
    --name $CONTAINER_NAME \
    -p 11434:11434 \
    -v ollama_data:/root/.ollama \
    -e OLLAMA_NUM_PARALLEL=2 \
    -e OLLAMA_MAX_LOADED_MODELS=1 \
    -e OLLAMA_FLASH_ATTENTION=1 \
    -e OLLAMA_LOW_VRAM=true \
    --restart unless-stopped \
    ollama/ollama

echo "⏳ ממתין ש-Ollama יתחיל..."
sleep 10

# בדוק שהשרת עובד
for i in {1..30}; do
    if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
        echo "✅ Ollama server פועל!"
        break
    fi
    echo "⏳ ממתין... ($i/30)"
    sleep 2
done

# בדוק אם השרת עובד
if ! curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
    echo "❌ Ollama server לא הצליח להתחיל"
    echo "🔍 בדוק logs עם: docker logs ollama"
    exit 1
fi

echo ""
echo "🗑️ מנקה מודלים כבדים ישנים..."

# הסר מודלים כבדים אם קיימים
docker exec $CONTAINER_NAME ollama rm phi3:mini 2>/dev/null || echo "   phi3:mini לא קיים"
docker exec $CONTAINER_NAME ollama rm phi3 2>/dev/null || echo "   phi3 לא קיים" 
docker exec $CONTAINER_NAME ollama rm gemma2:2b 2>/dev/null || echo "   gemma2:2b לא קיים"
docker exec $CONTAINER_NAME ollama rm llama2 2>/dev/null || echo "   llama2 לא קיים"

echo ""
echo "⬇️ מוריד מודל אולטרה מהיר (394MB בלבד)..."
docker exec $CONTAINER_NAME ollama pull qwen2.5:0.5b

echo ""
echo "⬇️ מוריד מודל חלופי קל (637MB)..."
docker exec $CONTAINER_NAME ollama pull tinyllama

echo ""
echo "📋 בודק מודלים זמינים:"
docker exec $CONTAINER_NAME ollama list

echo ""
echo "🧪 בודק שהמודל עובד..."
TEST_RESPONSE=$(docker exec $CONTAINER_NAME ollama run qwen2.5:0.5b "שלום" --timeout 10s 2>/dev/null | head -n 1)

if [ -n "$TEST_RESPONSE" ]; then
    echo "✅ המודל עובד! תגובה: $TEST_RESPONSE"
else
    echo "⚠️ בעיה עם המודל, נסה להפעיל ידנית"
fi

echo ""
echo "🔧 יוצר קובץ environment variables..."
cat > .env.docker << EOF
# Docker Ollama Configuration - Ultra Fast
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:0.5b
AI_NUM_PREDICT=30
AI_NUM_CTX=512

# Alternative model (if qwen doesn't work well)
# OLLAMA_MODEL=tinyllama
EOF

echo ""
echo "✅ ההתקנה הושלמה בהצלחה!"
echo "================================================"
echo ""
echo "🎉 מוכן לשימוש אולטרה מהיר!"
echo ""
echo "📝 הגדרות למהירות מקסימלית:"
echo "   - מודל: qwen2.5:0.5b (394MB)"
echo "   - חלופי: tinyllama (637MB)" 
echo "   - תגובות: עד 30 מילים"
echo "   - זמן: 1-3 שניות צפוי"
echo ""
echo "🔧 לשימוש:"
echo "   1. טען את הקובץ .env.docker לפרויקט שלך"
echo "   2. או הגדר: export OLLAMA_MODEL=qwen2.5:0.5b"
echo "   3. הפעל מחדש את השרת שלך"
echo "   4. תיהני ממהירות ברק! ⚡"
echo ""
echo "🛠️ פקודות שימושיות:"
echo "   - docker logs ollama          # ראה logs"
echo "   - docker exec ollama ollama list  # רשימת מודלים"
echo "   - docker restart ollama       # הפעל מחדש"
echo "   - docker stop ollama          # עצור"
echo ""
echo "🔍 בדיקה מהירה:"
echo "   curl http://localhost:11434/api/version"