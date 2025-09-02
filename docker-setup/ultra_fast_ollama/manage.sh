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
