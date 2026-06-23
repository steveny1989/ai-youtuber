import cors from "cors";
import express from "express";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "../..");
const examplesDir = path.join(projectRoot, "examples");
const app = express();
const port = Number(process.env.PORT || 8787);
const imageExtensions = new Set([".png", ".jpg", ".jpeg", ".webp"]);
const ignoredDirs = new Set([".git", "node_modules", "dist"]);

app.use(cors());
app.use(express.json({ limit: "3mb" }));
app.use("/workspace", express.static(projectRoot));

function normalizeRelPath(relPath) {
  const normalized = path.normalize(relPath).replace(/^(\.\.(\/|\\|$))+/, "");
  const absolute = path.resolve(projectRoot, normalized);
  if (!absolute.startsWith(projectRoot)) {
    throw new Error("Path escapes workspace");
  }
  return { normalized, absolute };
}

async function listStoryboards() {
  const entries = await fs.readdir(examplesDir, { withFileTypes: true });
  return entries
    .filter(
      (entry) =>
        entry.isFile() &&
        entry.name.endsWith(".json") &&
        entry.name.includes("storyboard")
    )
    .map((entry) => ({
      name: entry.name,
      path: `examples/${entry.name}`,
    }))
    .sort((a, b) => a.name.localeCompare(b.name, "zh-CN"));
}

async function readStoryboard(relPath) {
  const { normalized, absolute } = normalizeRelPath(relPath);
  const raw = await fs.readFile(absolute, "utf-8");
  const parsed = JSON.parse(raw);
  const scenes = Array.isArray(parsed.scenes) ? parsed.scenes : [];
  return {
    path: normalized,
    project: {
      ...parsed,
      scenes: scenes.map((scene) => enrichScene(scene, parsed)),
    },
  };
}

function enrichScene(scene, project) {
  const imagePath = resolveSceneImage(scene, project);
  return {
    ...scene,
    resolved_image: imagePath,
  };
}

function resolveSceneImage(scene, project) {
  if (scene.image) {
    return scene.image;
  }
  const sceneType = (scene.scene_type || "").toLowerCase();
  if (sceneType === "intro") {
    return "assets/placeholder-home.jpg";
  }
  if (sceneType === "chapter") {
    if (scene.chapter) {
      const chapter = (project.chapters || []).find((item) => item.id === scene.chapter);
      if (chapter?.file) {
        return chapter.file;
      }
      if (chapter?.id) {
        return `assets/chapters/chapter-${chapter.id}.jpg`;
      }
    }
    return `assets/chapters/chapter-${scene.id}.jpg`;
  }
  return "";
}

function stripDerivedFields(project) {
  const next = JSON.parse(JSON.stringify(project));
  next.scenes = (next.scenes || []).map((scene) => {
    const clean = { ...scene };
    delete clean.resolved_image;
    return clean;
  });
  return next;
}

async function walkFiles(dirPath, bucket = []) {
  const entries = await fs.readdir(dirPath, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.name.startsWith(".DS_Store")) {
      continue;
    }
    const absolute = path.join(dirPath, entry.name);
    if (entry.isDirectory()) {
      if (ignoredDirs.has(entry.name)) {
        continue;
      }
      await walkFiles(absolute, bucket);
      continue;
    }
    const ext = path.extname(entry.name).toLowerCase();
    if (imageExtensions.has(ext)) {
      bucket.push(absolute);
    }
  }
  return bucket;
}

function scoreImage(relPath, query, sceneId) {
  const normalized = relPath.toLowerCase();
  let score = 0;
  if (sceneId) {
    const scene = sceneId.toLowerCase();
    if (normalized.includes(`${scene}_base`)) score += 140;
    if (normalized.includes(`${scene}-base`)) score += 140;
    if (normalized.includes(scene)) score += 70;
  }
  if (query) {
    const q = query.toLowerCase();
    if (normalized.includes(q)) score += 35;
  }
  if (normalized.includes("/assets/")) score += 12;
  if (normalized.includes("/.work/")) score += 8;
  if (normalized.includes("_base.")) score += 24;
  if (normalized.includes("_cue_")) score -= 8;
  if (normalized.includes("_sub_")) score -= 10;
  return score;
}

function isSceneRelatedImage(relPath, sceneId) {
  if (!sceneId) {
    return false;
  }
  const normalized = relPath.toLowerCase();
  const scene = sceneId.toLowerCase();
  return normalized.includes(`${scene}_base`) || normalized.includes(`${scene}-base`) || normalized.includes(scene);
}

async function listWorkspaceImages({ query = "", sceneId = "", limit = 80, includeWork = false } = {}) {
  const files = await walkFiles(projectRoot);
  return files
    .map((absolute) => {
      const relPath = path.relative(projectRoot, absolute).split(path.sep).join("/");
      return {
        path: relPath,
        name: path.basename(relPath),
        folder: path.dirname(relPath),
        score: scoreImage(relPath, query, sceneId),
      };
    })
    .filter((image) => {
      if (image.path.startsWith("assets/")) {
        return true;
      }
      if (isSceneRelatedImage(image.path, sceneId)) {
        return true;
      }
      if (includeWork && (image.path.startsWith(".work/") || image.path.startsWith("output/"))) {
        return true;
      }
      return false;
    })
    .sort((a, b) => b.score - a.score || a.path.localeCompare(b.path, "zh-CN"))
    .slice(0, limit);
}

app.get("/api/projects", async (_req, res) => {
  try {
    const projects = await listStoryboards();
    res.json({ projects });
  } catch (error) {
    res.status(500).send(String(error.message || error));
  }
});

app.get("/api/project", async (req, res) => {
  const relPath = String(req.query.path || "");
  if (!relPath) {
    res.status(400).send("Missing path");
    return;
  }
  try {
    const data = await readStoryboard(relPath);
    res.json(data);
  } catch (error) {
    res.status(500).send(String(error.message || error));
  }
});

app.get("/api/images", async (req, res) => {
  try {
    const query = String(req.query.q || "");
    const sceneId = String(req.query.sceneId || "");
    const limit = Math.min(Math.max(Number(req.query.limit || 80), 1), 200);
    const includeWork = String(req.query.includeWork || "").toLowerCase() === "true";
    const images = await listWorkspaceImages({ query, sceneId, limit, includeWork });
    res.json({ images });
  } catch (error) {
    res.status(500).send(String(error.message || error));
  }
});

app.post("/api/project", async (req, res) => {
  const relPath = String(req.body?.path || "");
  const project = req.body?.project;
  if (!relPath || !project) {
    res.status(400).send("Missing path or project");
    return;
  }
  try {
    const { absolute, normalized } = normalizeRelPath(relPath);
    const payload = stripDerivedFields(project);
    await fs.writeFile(absolute, `${JSON.stringify(payload, null, 2)}\n`, "utf-8");
    const data = await readStoryboard(normalized);
    res.json(data);
  } catch (error) {
    res.status(500).send(String(error.message || error));
  }
});

app.listen(port, () => {
  console.log(`AI YouTuber Studio API running at http://127.0.0.1:${port}`);
});
