import os
import sys
import json
from pathlib import Path

ROOT = Path("/Users/diyao/Desktop/AI YouTuber")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.env_util import load_dotenv
from pipeline.models import Storyboard, TtsConfig
from pipeline.tts import generate_all_audio

def main():
    load_dotenv()
    sb_path = ROOT / "examples" / "storyboard-zhuangzi-xiaoyaoyou.json"
    with open(sb_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    sb = Storyboard.from_dict(data)
    
    work_dir = ROOT / ".work" / "xiaoyaoyou"
    work_dir.mkdir(parents=True, exist_ok=True)
    
    tts_config = TtsConfig(
        provider="edge",
        voice="zh-CN-YunxiNeural",
        rate="-15%"
    )
    # Inject config into storyboard
    sb.tts = tts_config
    
    print("STEP 1: Generating all TTS audio and subtitle cues...")
    generate_all_audio(sb, work_dir)
    print("STEP 1 COMPLETE: All audio generated successfully!")

if __name__ == "__main__":
    main()
