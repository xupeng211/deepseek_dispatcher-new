curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "请给我写一个关于人工智能未来发展的简短段落。",
    "max_tokens": 100,
    "temperature": 0.7,
    "top_p": 0.8
  }' \
  http://localhost:8000/generate

  cat ./results/YYYY-MM-DD/task_<TASK_ID>.json
  