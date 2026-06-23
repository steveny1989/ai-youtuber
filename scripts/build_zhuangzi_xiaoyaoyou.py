import os
import sys
import subprocess
from pathlib import Path

ROOT = Path("/Users/diyao/Desktop/AI YouTuber")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.env_util import load_dotenv
from pipeline.render import render_storyboard

def main():
    load_dotenv()
    sb_path = ROOT / "examples" / "storyboard-zhuangzi-xiaoyaoyou.json"
    work_dir = ROOT / ".work" / "xiaoyaoyou"
    out_video_no_bgm = work_dir / "xiaoyaoyou_director_cut_no_bgm.mp4"
    out_video_final = ROOT / "output" / "xiaoyaoyou" / "xiaoyaoyou_director_cut.mp4"
    out_video_final.parent.mkdir(parents=True, exist_ok=True)
    
    # 1. Render the storyboard (TTS + Visuals)
    print(f"Starting native pipeline render for: {sb_path.name}...")
    final_video = render_storyboard(
        storyboard_path=sb_path,
        work_dir=work_dir,
        skip_tts=False,
    )
    
    # 2. Mix BGM directly via subprocess to avoid model dependency issues
    bgm_path = str(ROOT / "assets" / "BGM" / "Music_fx_relaxing_chinese_guzheng.wav")
    print("Mixing BGM with FFmpeg...")
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(final_video),
        "-stream_loop", "-1", "-i", bgm_path,
        "-filter_complex", "[1:a]volume=0.08[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        str(out_video_final)
    ]
    subprocess.run(cmd, check=True)
    print(f"COMPLETE! Video saved to: {out_video_final}")

if __name__ == "__main__":
    main()
