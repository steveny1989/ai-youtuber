import os
import json
import shutil
from pathlib import Path

# Paths
base_dir = Path("/Users/diyao/Desktop/AI YouTuber")
daodejing_dir = base_dir / "assets/DaoDeJing"
ip_dir = base_dir / "assets/IP_Character"
catalog_path = daodejing_dir / "image_catalog.json"

# Create new directory
ip_dir.mkdir(parents=True, exist_ok=True)

# Load catalog
with open(catalog_path, 'r', encoding='utf-8') as f:
    catalog = json.load(f)

moved_count = 0
updated_images = []

for img in catalog['images']:
    old_rel_path = img['file']
    # Check if the tag "IP" or "人物" combined with "频道专属" is in the metadata
    # We also know the original IDs started with 'char_master' or 'char_ext'
    is_ip = "IP" in img.get('tags', []) or "频道专属虚拟" in old_rel_path
    
    if is_ip:
        old_abs_path = base_dir / old_rel_path
        if old_abs_path.exists():
            # Define new paths
            filename = old_abs_path.name
            new_abs_path = ip_dir / filename
            new_rel_path = f"assets/IP_Character/{filename}"
            
            # Move physically
            shutil.move(str(old_abs_path), str(new_abs_path))
            
            # Update JSON logic
            img['file'] = new_rel_path
            moved_count += 1
            print(f"Moved: {filename} -> {new_rel_path}")
        else:
            print(f"Warning: IP file not found on disk: {old_abs_path}")
            
    updated_images.append(img)

# Save updated catalog
catalog['images'] = updated_images
with open(catalog_path, 'w', encoding='utf-8') as f:
    json.dump(catalog, f, ensure_ascii=False, indent=2)

print(f"\nMigration complete. Successfully isolated {moved_count} IP character images.")

