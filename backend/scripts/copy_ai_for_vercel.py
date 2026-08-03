"""Vercel 빌드 스텝에서 저장소 루트 ai/를 backend/ai/로 복사한다.
"""

from pathlib import Path
from shutil import copytree, ignore_patterns, rmtree


def main() -> None:
    repository_root = Path(__file__).resolve().parents[2]

    source = repository_root / "ai"
    destination = repository_root / "backend" / "ai"

    if not source.is_dir():
        raise RuntimeError(f"AI 원본 디렉터리를 찾을 수 없습니다: {source}")

    if destination.exists():
        rmtree(destination)

    copytree(
        source,
        destination,
        ignore=ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )

    print(f"AI modules copied: {source} -> {destination}")


if __name__ == "__main__":
    main()
