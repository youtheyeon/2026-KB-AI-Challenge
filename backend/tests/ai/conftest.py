# 백엔드 테스트에서 저장소의 AI 모듈을 불러오도록 경로를 설정하는 테스트 구성
import sys
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parents[3] / "ai"
sys.path.insert(0, str(AI_ROOT))
