import os
import json
import time
from pathlib import Path
import google.generativeai as genai
from PIL import Image
import io

api_key = "AIzaSyDdzS6Pj-t888fNxKaqlxgDkG-XSvYZH6g"
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-3.5-flash')

base_dir = Path("/Users/diyao/Desktop/AI YouTuber/assets/DaoDeJing")
catalog_path = base_dir / "image_catalog.json"
rejected_dir = base_dir / "rejected_assets"
rejected_dir.mkdir(exist_ok=True)

with open(catalog_path, 'r', encoding='utf-8') as f:
    catalog = json.load(f)

PROMPT = """
You are an expert Art Director for a high-end Chinese philosophy documentary channel.
Analyze the image and output raw JSON.

Rules for Rejection (is_safe = false):
1. Skulls, bones, or death imagery.
2. Blood, violence, or weapons hitting flesh.
3. Scary, horrific, demonic, or overly gloomy/depressing atmosphere.
4. Severe AI artifacts (e.g., heavily deformed faces, tangled fingers).

Aesthetic Score (1-10): Rate how well it fits a "Serene, Ethereal, Ancient Chinese Philosophical" vibe.

JSON FORMAT EXACTLY LIKE THIS:
{"is_safe": true, "flag_reason": "None", "aesthetic_score": 8, "review_comments": "Good."}
"""

print("Starting Fast Vision Audit (Downscaled in-memory)...")

for img_meta in catalog['images']:
    if img_meta.get('audit_score'): continue
        
    img_path = base_dir / os.path.basename(img_meta['file'])
    if not img_path.exists(): continue

    print(f"\nAuditing: {img_path.name}")
    
    try:
        # Downscale to speed up network and avoid SSL EOF
        img = Image.open(img_path)
        img.thumbnail((1024, 1024))
        
        response = model.generate_content([img, PROMPT])
        
        text_resp = response.text.replace('```json', '').replace('```', '').strip()
        result = json.loads(text_resp)
        
        is_safe = result.get('is_safe', True)
        score = result.get('aesthetic_score', 5)
        reason = result.get('flag_reason', 'None')
        
        print(f"  -> Safe: {is_safe} | Score: {score}/10 | Reason: {reason}")
        
        if not is_safe or score < 4:
            print(f"  [REJECTED] Moving {img_path.name} to rejected_assets")
            dest_path = rejected_dir / img_path.name
            os.rename(img_path, dest_path)
        else:
            img_meta['audit_score'] = score
            img_meta['audit_comments'] = result.get('review_comments', '')
            
    except Exception as e:
        print(f"  [ERROR] {e}")
    
    time.sleep(1) # short sleep
