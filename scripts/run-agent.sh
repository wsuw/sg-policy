#!/bin/bash
cd "$(dirname "$0")/../agent" || exit 1
# 强力清理 8123 端口占用与残留进程，避免重启时报端口占用
lsof -ti :8123 | xargs kill -9 2>/dev/null || true
pkill -9 -f "langgraph dev" 2>/dev/null || true
sleep 0.5
npx @langchain/langgraph-cli dev --port 8123 --no-browser

