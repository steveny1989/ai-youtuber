import sys
import os
import json
import time
from pathlib import Path
import google.generativeai as genai

# Ensure API key is set
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    print("Error: GOOGLE_API_KEY environment variable not set.")
    exit(1)

genai.configure(api_key=api_key)

# We use gemini-1.5-flash for fast and cost-effective vision tasks
model = genai.GenerativeModel('gemini-3.5-flash')

base_dir = Path("/Users/diyao/Desktop/AI YouTuber/assets/DaoDeJing")
catalog_path = base_dir / "image_catalog.json"
rejected_dir = base_dir / "rejected_assets"
rejected_dir.mkdir(exist_ok=True)

with open(catalog_path, 'r', encoding='utf-8') as f:
    catalog = json.load(f)

print(f"Loaded catalog with {len(catalog['images'])} images.")

# The prompt forcing JSON output
PROMPT = """
You are an expert Art Director and strict Content Moderator for a high-end Chinese philosophy documentary channel.
Analyze the provided image carefully and output a raw JSON response (NO markdown blocks, just raw JSON).

Rules for Rejection (is_safe = false):
1. Skulls, skeletons, bones, or death.
2. Blood, gore, violence, or weapons hitting flesh.
3. Scary, horrific, demonic, or overly gloomy/depressing atmosphere.
4. NSFW, nudity, or sexually suggestive elements.
5. Severe AI artifacts (e.g., heavily deformed faces, tangled fingers).

Aesthetic Score (1-10):
Rate how well it fits a "Serene, Ethereal, Ancient Chinese Philosophical" vibe (Carbon Black, Bone White, Soft Gold).
10 = Absolute masterpiece of zen and serenity. 1 = Ugly, chaotic, or completely off-topic.

JSON FORMAT EXACTLY LIKE THIS:
{
    "is_safe": true,
    "flag_reason": "None",
    "aesthetic_score": 8,
    "review_comments": "Beautiful serene lighting."
}
"""

def upload_to_gemini(path):
    file = genai.upload_file(path)
    return file

valid_images = []
rejected_count = 0
audited_count = 0

print("Starting Vision Audit...")

for img_meta in catalog['images']:
    if img_meta.get('audit_score'):
        valid_images.append(img_meta)
        continue
        
    img_path = Path("/Users/diyao/Desktop/AI YouTuber") / img_meta['file']
    
    if not img_path.exists():
        continue

    print(f"\nAuditing: {img_path.name}")
    
    try:
        uploaded_file = upload_to_gemini(str(img_path))
        response = model.generate_content([uploaded_file, PROMPT])
        genai.delete_file(uploaded_file.name)
        
        text_resp = response.text.replace('```json', '').replace('```', '').strip()
        result = json.loads(text_resp)
        
        is_safe = result.get('is_safe', True)
        score = result.get('aesthetic_score', 5)
        reason = result.get('flag_reason', 'None')
        
        sys.stdout.flush()
        print(f"  -> Safe: {is_safe} | Score: {score}/10 | Reason: {reason}")
        
        if not is_safe or score < 4:
            print(f"  [REJECTED] Moving {img_path.name} to rejected folder.")
            dest_path = rejected_dir / img_path.name
            os.rename(img_path, dest_path)
            rejected_count += 1
        else:
            img_meta['audit_score'] = score
            img_meta['audit_comments'] = result.get('review_comments', '')
            valid_images.append(img_meta)
            
    except Exception as e:
        print(f"  [ERROR] Failed to audit {img_path.name}: {e}")
        valid_images.append(img_meta)
        
    audited_count += 1
    time.sleep(2)
    
    if False:
        print("\nTest run of 10 images complete. Stopping to review.")
        break

# Reconstruct catalog
remaining_unprocessed = [img for img in catalog['images'] if img not in valid_images and img not in catalog['images'][:audited_count]]
final_images = valid_images + remaining_unprocessed

catalog['images'] = final_images
catalog['meta']['image_count'] = len(final_images)

with open(catalog_path, 'w', encoding='utf-8') as f:
    json.dump(catalog, f, ensure_ascii=False, indent=2)

print(f"\nAudit Paused/Complete. Rejected {rejected_count} images out of {audited_count} checked.")
