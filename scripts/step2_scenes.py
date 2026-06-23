import os
import sys
import json
from pathlib import Path

ROOT = Path("/Users/diyao/Desktop/AI YouTuber")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.env_util import load_dotenv
from pipeline.models import Storyboard
# the frame rendering logic is inside render_storyboard, but we can't easily decouple it without rewriting the pipeline.
# However, render_storyboard itself skips TTS if we pass skip_tts=True, and just renders scenes and concats.
# Since we want to check intermediate scenes, we will run render_storyboard with skip_tts=True, 
# and it will stop before BGM mixing because we aren't mixing BGM here.

from pipeline.render import render_storyboard

def main():
    load_dotenv()
    sb_path = ROOT / "examples" / "storyboard-zhuangzi-xiaoyaoyou.json"
    
    with open(sb_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    sb = Storyboard.from_dict(data)
    
    work_dir = ROOT / ".work" / "xiaoyaoyou"
    
    print("STEP 2: Rendering all video scenes (with Ken Burns, Logo, and Subtitles)...")
    # This will render scenes into .work/xiaoyaoyou/scenes/ and concat them into commentary.mp4
    # Because skip_tts is True, it will reuse the perfectly generated audio from Step 1.
    final_video = render_storyboard(
        storyboard_path=sb_path,
        work_dir=work_dir,
        skip_tts=True,
    )
    print(f"STEP 2 COMPLETE: All scenes rendered and concatenated into: {final_video}")

if __name__ == "__main__":
    main()
