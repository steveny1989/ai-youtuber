import { useEffect, useMemo, useState } from "react";

const DEFAULT_SCENE = {
  id: "",
  narration: "",
  image: "",
  subtitle: "",
  duration_sec: "",
  pause_after_sec: 0.3,
  scene_type: "body",
  chapter: "",
  chapter_title: "",
};

const DEFAULT_COVER = {
  enabled: true,
  image: "",
  narration: "",
  hook: "",
  subtitle: "",
  duration_sec: 3,
};

function formatSeconds(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) {
    return "--";
  }
  return `${num.toFixed(num >= 10 ? 1 : 2)}s`;
}

function classNames(...parts) {
  return parts.filter(Boolean).join(" ");
}

function cloneProject(project) {
  return JSON.parse(JSON.stringify(project));
}

function normalizeSceneDraft(scene) {
  return {
    ...DEFAULT_SCENE,
    ...scene,
    image: scene?.image ?? "",
    subtitle: scene?.subtitle ?? "",
    duration_sec: scene?.duration_sec ?? "",
    pause_after_sec: scene?.pause_after_sec ?? 0.3,
    scene_type: scene?.scene_type ?? "body",
    chapter: scene?.chapter ?? "",
    chapter_title: scene?.chapter_title ?? "",
  };
}

function normalizeCoverDraft(cover) {
  return {
    ...DEFAULT_COVER,
    ...cover,
    image: cover?.image ?? "",
    narration: cover?.narration ?? "",
    hook: cover?.hook ?? "",
    subtitle: cover?.subtitle ?? "",
    duration_sec: cover?.duration_sec ?? 3,
  };
}

function resolveSceneImage(scene, project) {
  if (scene?.image) {
    return scene.image;
  }
  const sceneType = (scene?.scene_type || "").toLowerCase();
  if (sceneType === "intro") {
    return "assets/placeholder-home.jpg";
  }
  if (sceneType === "chapter") {
    if (scene?.chapter) {
      const chapter = (project?.chapters || []).find((item) => item.id === scene.chapter);
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

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json();
}

function sanitizeScene(scene) {
  const next = {
    ...scene,
    id: scene.id.trim(),
    narration: scene.narration,
    image: scene.image.trim(),
    subtitle: scene.subtitle.trim(),
    scene_type: scene.scene_type || "body",
    chapter: scene.chapter.trim(),
    chapter_title: scene.chapter_title.trim(),
  };
  if (next.image === "") {
    delete next.image;
  }
  if (next.subtitle === "") {
    delete next.subtitle;
  }
  if (next.chapter === "") {
    delete next.chapter;
  }
  if (next.chapter_title === "") {
    delete next.chapter_title;
  }
  if (next.scene_type === "body") {
    delete next.scene_type;
  }
  if (next.duration_sec === "" || next.duration_sec === null) {
    delete next.duration_sec;
  } else {
    next.duration_sec = Number(next.duration_sec);
  }
  if (next.pause_after_sec === "" || next.pause_after_sec === null) {
    delete next.pause_after_sec;
  } else {
    next.pause_after_sec = Number(next.pause_after_sec);
  }
  delete next.resolved_image;
  return next;
}

function sanitizeCover(cover) {
  const next = {
    ...cover,
    enabled: Boolean(cover.enabled),
    image: (cover.image || "").trim(),
    narration: cover.narration || "",
    hook: (cover.hook || "").trim(),
    subtitle: (cover.subtitle || "").trim(),
    duration_sec: Number(cover.duration_sec) || 3,
  };
  if (!next.image) {
    delete next.image;
  }
  if (!next.narration) {
    delete next.narration;
  }
  if (!next.hook) {
    delete next.hook;
  }
  if (!next.subtitle) {
    delete next.subtitle;
  }
  return next;
}

export function App() {
  const [projects, setProjects] = useState([]);
  const [projectPath, setProjectPath] = useState("");
  const [project, setProject] = useState(null);
  const [selectedTarget, setSelectedTarget] = useState({ kind: "scene", index: 0 });
  const [sceneDraft, setSceneDraft] = useState(DEFAULT_SCENE);
  const [coverDraft, setCoverDraft] = useState(DEFAULT_COVER);
  const [status, setStatus] = useState("正在读取项目列表…");
  const [dirty, setDirty] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [previewScale, setPreviewScale] = useState(82);
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [imagePickerOpen, setImagePickerOpen] = useState(false);
  const [imageQuery, setImageQuery] = useState("");
  const [imageLibrary, setImageLibrary] = useState([]);
  const [imageLoading, setImageLoading] = useState(false);
  const [includeWorkImages, setIncludeWorkImages] = useState(false);

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    if (!project) {
      setSceneDraft(DEFAULT_SCENE);
      setCoverDraft(DEFAULT_COVER);
      return;
    }
    setCoverDraft(normalizeCoverDraft(project.cover || DEFAULT_COVER));
    if (selectedTarget.kind === "scene") {
      setSceneDraft(normalizeSceneDraft(project.scenes?.[selectedTarget.index] || DEFAULT_SCENE));
    }
  }, [project, selectedTarget]);

  useEffect(() => {
    if (!imagePickerOpen) {
      return;
    }
    const query =
      selectedTarget.kind === "cover"
        ? imageQuery || coverDraft.image || "cover"
        : imageQuery || sceneDraft.id || sceneDraft.image;
    const sceneId = selectedTarget.kind === "cover" ? "cover" : sceneDraft.id;
    loadImages(query, sceneId);
  }, [
    imagePickerOpen,
    imageQuery,
    sceneDraft.id,
    sceneDraft.image,
    coverDraft.image,
    includeWorkImages,
    selectedTarget.kind,
  ]);

  async function loadProjects(preferredPath) {
    try {
      setLoading(true);
      const data = await fetchJson("/api/projects");
      setProjects(data.projects);
      const initialPath = preferredPath || data.projects[0]?.path;
      if (initialPath) {
        await loadProject(initialPath);
      } else {
        setProject(null);
        setProjectPath("");
        setStatus("还没有找到 storyboard JSON。");
      }
    } catch (error) {
      setStatus(`读取项目失败：${error.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function loadProject(nextPath) {
    if (!nextPath) {
      return;
    }
    const data = await fetchJson(`/api/project?path=${encodeURIComponent(nextPath)}`);
    setProject(data.project);
    setProjectPath(data.path);
    setSelectedTarget(data.project?.cover ? { kind: "cover" } : { kind: "scene", index: 0 });
    setDirty(false);
    setImagePickerOpen(false);
    setStatus(`已加载 ${data.path}`);
  }

  async function loadImages(query = "", sceneId = "") {
    try {
      setImageLoading(true);
      const data = await fetchJson(
        `/api/images?q=${encodeURIComponent(query)}&sceneId=${encodeURIComponent(
          sceneId
        )}&limit=72&includeWork=${includeWorkImages}`
      );
      setImageLibrary(data.images || []);
    } catch (error) {
      setStatus(`读取图片候选失败：${error.message}`);
    } finally {
      setImageLoading(false);
    }
  }

  const selectedScene =
    selectedTarget.kind === "scene" ? project?.scenes?.[selectedTarget.index] ?? null : null;
  const currentDraft = selectedTarget.kind === "cover" ? coverDraft : sceneDraft;

  function buildPreviewUrl(sceneLike, activeProject = project) {
    const image = resolveSceneImage(sceneLike, activeProject);
    if (!image) {
      return "";
    }
    return `/workspace/${image}`;
  }

  const railItems = useMemo(() => {
    if (!project) {
      return [];
    }
    const items = [];
    if (project.cover) {
      items.push({
        kind: "cover",
        id: "cover",
        index: -1,
        scene_type: "cover",
        duration_sec: project.cover.duration_sec,
        previewUrl: buildPreviewUrl(project.cover, project),
        summary: (project.cover.hook || project.cover.subtitle || "").slice(0, 70),
      });
    }
    return items.concat(
      (project.scenes || []).map((scene, index) => ({
        kind: "scene",
        ...scene,
        index,
        previewUrl: buildPreviewUrl(scene, project),
        summary: (scene.subtitle || scene.narration || "").slice(0, 70),
      }))
    );
  }, [project]);

  function updateScene(field, value) {
    if (!project || selectedTarget.kind !== "scene" || selectedTarget.index < 0) {
      return;
    }
    const nextDraft = normalizeSceneDraft({ ...sceneDraft, [field]: value });
    setSceneDraft(nextDraft);
    setProject((current) => {
      const next = cloneProject(current);
      next.scenes[selectedTarget.index] = sanitizeScene(nextDraft);
      return next;
    });
    setDirty(true);
  }

  function updateCover(field, value) {
    if (!project) {
      return;
    }
    const nextDraft = normalizeCoverDraft({ ...coverDraft, [field]: value });
    setCoverDraft(nextDraft);
    setProject((current) => {
      const next = cloneProject(current);
      next.cover = sanitizeCover(nextDraft);
      return next;
    });
    setDirty(true);
  }

  function chooseImage(path) {
    if (selectedTarget.kind === "cover") {
      updateCover("image", path);
    } else {
      updateScene("image", path);
    }
    setImagePickerOpen(false);
    setStatus(`已选中 ${path}，记得保存项目。`);
  }

  function selectItem(item) {
    if (item.kind === "cover") {
      setSelectedTarget({ kind: "cover" });
      return;
    }
    setSelectedTarget({ kind: "scene", index: item.index });
  }

  function moveScene(direction) {
    if (!project || selectedTarget.kind !== "scene") {
      return;
    }
    const target = selectedTarget.index + direction;
    if (target < 0 || target >= project.scenes.length) {
      return;
    }
    setProject((current) => {
      const next = cloneProject(current);
      const [scene] = next.scenes.splice(selectedTarget.index, 1);
      next.scenes.splice(target, 0, scene);
      return next;
    });
    setSelectedTarget({ kind: "scene", index: target });
    setDirty(true);
    setStatus("镜头顺序已调整，还没保存到文件。");
  }

  function addScene() {
    if (!project) {
      return;
    }
    const nextScene = {
      ...DEFAULT_SCENE,
      id: `scene-${project.scenes.length + 1}`,
      narration: "新镜头文案",
    };
    const insertIndex = selectedTarget.kind === "scene" ? selectedTarget.index + 1 : 0;
    setProject((current) => {
      const next = cloneProject(current);
      next.scenes.splice(insertIndex, 0, sanitizeScene(nextScene));
      return next;
    });
    setSelectedTarget({ kind: "scene", index: insertIndex });
    setDirty(true);
    setStatus("已插入新镜头。");
  }

  function removeScene() {
    if (!project || selectedTarget.kind !== "scene" || project.scenes.length <= 1) {
      return;
    }
    setProject((current) => {
      const next = cloneProject(current);
      next.scenes.splice(selectedTarget.index, 1);
      return next;
    });
    setSelectedTarget({ kind: "scene", index: Math.max(0, selectedTarget.index - 1) });
    setDirty(true);
    setStatus("镜头已删除，还没保存到文件。");
  }

  async function saveProject() {
    if (!project) {
      return;
    }
    const nextProject = cloneProject(project);
    if (selectedTarget.kind === "scene" && selectedTarget.index >= 0) {
      nextProject.scenes[selectedTarget.index] = sanitizeScene(sceneDraft);
    }
    if (nextProject.cover) {
      nextProject.cover = sanitizeCover(coverDraft);
    }
    try {
      setSaving(true);
      const data = await fetchJson("/api/project", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          path: projectPath,
          project: nextProject,
        }),
      });
      setProject(data.project);
      setDirty(false);
      setStatus(`已保存 ${data.path}`);
    } catch (error) {
      setStatus(`保存失败：${error.message}`);
    } finally {
      setSaving(false);
    }
  }

  if (loading && !project) {
    return <div className="loading-shell">正在启动审片台…</div>;
  }

  return (
    <div className="studio-shell">
      <header className="topbar">
        <div>
          <div className="eyebrow">Storyboard Review Studio</div>
          <h1>AI YouTuber 审片台</h1>
        </div>
        <div className="topbar-actions">
          <button
            className="secondary-button mobile-inspector-toggle"
            onClick={() => setInspectorOpen((current) => !current)}
          >
            {inspectorOpen ? "收起编辑" : "打开编辑"}
          </button>
          <select
            className="project-select"
            value={projectPath}
            onChange={(event) => loadProject(event.target.value)}
          >
            {projects.map((item) => (
              <option key={item.path} value={item.path}>
                {item.name}
              </option>
            ))}
          </select>
          <button className="secondary-button" onClick={() => loadProjects(projectPath)}>
            刷新
          </button>
          <button className="primary-button" onClick={saveProject} disabled={saving || !project}>
            {saving ? "保存中…" : "保存项目"}
          </button>
        </div>
      </header>

      <main className="workspace">
        <aside className="scene-rail">
          <div className="rail-header">
            <strong>镜头列表</strong>
            <span>{railItems.length || 0} items</span>
          </div>
          <div className="scene-list">
            {railItems.map((item) => {
              const active =
                (item.kind === "cover" && selectedTarget.kind === "cover") ||
                (item.kind === "scene" &&
                  selectedTarget.kind === "scene" &&
                  item.index === selectedTarget.index);
              return (
                <button
                  key={`${item.kind}-${item.id}-${item.index}`}
                  className={classNames("scene-card", item.kind === "cover" && "cover-card", active && "active")}
                  onClick={() => selectItem(item)}
                >
                  <div className="thumb-frame">
                    {item.previewUrl ? (
                      <img src={item.previewUrl} alt={item.id} />
                    ) : (
                      <div className="thumb-placeholder">No Image</div>
                    )}
                  </div>
                  <div className="scene-meta">
                    <div className="scene-card-topline">
                      <strong>{item.id}</strong>
                      <span>{formatSeconds(item.duration_sec)}</span>
                    </div>
                    <div className="scene-chip-row">
                      <span className="scene-chip">{item.scene_type || "body"}</span>
                      {item.chapter ? <span className="scene-chip">chapter {item.chapter}</span> : null}
                    </div>
                    <p>{item.summary || "暂无文案"}</p>
                  </div>
                </button>
              );
            })}
          </div>
        </aside>

        <section className="preview-pane">
          <div className="preview-toolbar">
            <div>
              <strong>预览画面</strong>
              <div className="muted">缩小一点看全局，需要时再拉大</div>
            </div>
            <label className="preview-zoom">
              <span>缩放</span>
              <input
                type="range"
                min="60"
                max="100"
                step="5"
                value={previewScale}
                onChange={(event) => setPreviewScale(Number(event.target.value))}
              />
              <strong>{previewScale}%</strong>
            </label>
          </div>
          <div className="preview-stage">
            <div className="preview-stage-inner" style={{ width: `${previewScale}%` }}>
              {buildPreviewUrl(currentDraft) ? (
                <img
                  src={buildPreviewUrl(currentDraft)}
                  alt={selectedTarget.kind === "cover" ? "cover" : selectedScene?.id}
                  className="preview-image"
                />
              ) : (
                <div className="preview-placeholder">
                  {selectedTarget.kind === "cover" ? "当前 cover 还没有可用图片" : "当前镜头还没有可用图片"}
                </div>
              )}
              <div className="preview-overlay">
                <div className="preview-kicker">
                  {selectedTarget.kind === "cover" ? "cover" : selectedScene?.scene_type || "body"}
                </div>
                <div className="preview-title">
                  {selectedTarget.kind === "cover" ? "cover" : selectedScene?.id || "未选择镜头"}
                </div>
                <div className="preview-subtitle">
                  {(currentDraft.hook || currentDraft.subtitle || currentDraft.narration || "").slice(0, 120) ||
                    "暂无文案"}
                </div>
              </div>
            </div>
          </div>

          <div className="timeline-panel">
            <div className="timeline-header">
              <strong>时间线</strong>
              <span>先做镜头级审阅，再接单镜头重渲</span>
            </div>
            <div className="timeline-strip">
              {railItems.map((item) => {
                const active =
                  (item.kind === "cover" && selectedTarget.kind === "cover") ||
                  (item.kind === "scene" &&
                    selectedTarget.kind === "scene" &&
                    item.index === selectedTarget.index);
                return (
                  <button
                    key={`timeline-${item.kind}-${item.id}-${item.index}`}
                    className={classNames("timeline-item", active && "active")}
                    onClick={() => selectItem(item)}
                    style={{
                      flexGrow: Math.max(Number(item.duration_sec) || 3, 1),
                    }}
                  >
                    <span>{item.id}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </section>

        <aside className={classNames("inspector", inspectorOpen && "open")}>
          <div className="inspector-header">
            <div>
              <strong>{selectedTarget.kind === "cover" ? "封面编辑" : "镜头编辑"}</strong>
              <div className="muted">{projectPath || "未加载项目"}</div>
            </div>
            <div className="inspector-actions">
              <button
                className="secondary-button desktop-inspector-toggle"
                onClick={() => setInspectorOpen(false)}
              >
                收起
              </button>
              <button
                className="secondary-button"
                onClick={moveScene(-1)}
                disabled={selectedTarget.kind !== "scene"}
              >
                上移
              </button>
              <button
                className="secondary-button"
                onClick={moveScene(1)}
                disabled={selectedTarget.kind !== "scene"}
              >
                下移
              </button>
              <button className="secondary-button" onClick={addScene}>
                新增
              </button>
              <button
                className="danger-button"
                onClick={removeScene}
                disabled={selectedTarget.kind !== "scene"}
              >
                删除
              </button>
            </div>
          </div>

          <form className="field-grid">
            {selectedTarget.kind === "cover" ? (
              <>
                <label>
                  <span>封面启用</span>
                  <select
                    value={String(coverDraft.enabled)}
                    onChange={(event) => updateCover("enabled", event.target.value === "true")}
                  >
                    <option value="true">true</option>
                    <option value="false">false</option>
                  </select>
                </label>
                <label>
                  <span>封面时长（秒）</span>
                  <input
                    type="number"
                    step="0.1"
                    value={coverDraft.duration_sec}
                    onChange={(event) => updateCover("duration_sec", event.target.value)}
                  />
                </label>
              </>
            ) : (
              <>
                <label>
                  <span>镜头 ID</span>
                  <input
                    name="id"
                    value={sceneDraft.id}
                    onChange={(event) => updateScene("id", event.target.value)}
                  />
                </label>
                <label>
                  <span>镜头类型</span>
                  <select
                    name="scene_type"
                    value={sceneDraft.scene_type}
                    onChange={(event) => updateScene("scene_type", event.target.value)}
                  >
                    <option value="body">body</option>
                    <option value="intro">intro</option>
                    <option value="chapter">chapter</option>
                  </select>
                </label>
              </>
            )}

            <label className="full-span">
              <span>图片路径</span>
              <div className="image-field-row">
                <input
                  name="image"
                  value={currentDraft.image || ""}
                  placeholder="assets/placeholder.jpg"
                  onChange={(event) =>
                    selectedTarget.kind === "cover"
                      ? updateCover("image", event.target.value)
                      : updateScene("image", event.target.value)
                  }
                />
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => {
                    setInspectorOpen(true);
                    setImageQuery(
                      selectedTarget.kind === "cover"
                        ? coverDraft.image || "cover"
                        : sceneDraft.id || sceneDraft.image || ""
                    );
                    setImagePickerOpen((current) => !current);
                  }}
                >
                  {imagePickerOpen ? "收起选图" : "选图"}
                </button>
              </div>
            </label>

            {imagePickerOpen ? (
              <div className="image-picker full-span">
                <div className="image-picker-toolbar">
                  <input
                    value={imageQuery}
                    placeholder="搜 scene id、文件名、文件夹"
                    onChange={(event) => setImageQuery(event.target.value)}
                  />
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() =>
                      loadImages(
                        imageQuery,
                        selectedTarget.kind === "cover" ? "cover" : sceneDraft.id
                      )
                    }
                  >
                    刷新候选
                  </button>
                </div>
                <label className="image-picker-toggle">
                  <input
                    type="checkbox"
                    checked={includeWorkImages}
                    onChange={(event) => setIncludeWorkImages(event.target.checked)}
                  />
                  <span>显示临时图（.work）</span>
                </label>
                <div className="image-picker-hint">
                  默认显示 `assets/` 素材，并保留当前条目的相关预览图。点缩略图即可替换。
                </div>
                <div className="image-picker-grid">
                  {imageLoading ? (
                    <div className="image-picker-empty">正在整理候选图…</div>
                  ) : imageLibrary.length ? (
                    imageLibrary.map((image) => (
                      <button
                        key={image.path}
                        type="button"
                        className={classNames(
                          "image-option",
                          currentDraft.image === image.path && "active"
                        )}
                        onClick={() => chooseImage(image.path)}
                      >
                        <div className="image-option-thumb">
                          <img src={`/workspace/${image.path}`} alt={image.name} />
                        </div>
                        <div className="image-option-meta">
                          <strong>{image.name}</strong>
                          <span>{image.folder}</span>
                        </div>
                      </button>
                    ))
                  ) : (
                    <div className="image-picker-empty">没搜到匹配图，换个关键词试试。</div>
                  )}
                </div>
              </div>
            ) : null}

            {selectedTarget.kind === "cover" ? (
              <>
                <label className="full-span">
                  <span>封面 Hook</span>
                  <textarea
                    value={coverDraft.hook}
                    rows={3}
                    onChange={(event) => updateCover("hook", event.target.value)}
                  />
                </label>
                <label className="full-span">
                  <span>封面副标题</span>
                  <textarea
                    value={coverDraft.subtitle}
                    rows={3}
                    onChange={(event) => updateCover("subtitle", event.target.value)}
                  />
                </label>
                <label className="full-span">
                  <span>封面旁白</span>
                  <textarea
                    value={coverDraft.narration}
                    rows={5}
                    onChange={(event) => updateCover("narration", event.target.value)}
                  />
                </label>
              </>
            ) : (
              <>
                <label>
                  <span>章节 ID</span>
                  <input
                    name="chapter"
                    value={sceneDraft.chapter}
                    onChange={(event) => updateScene("chapter", event.target.value)}
                  />
                </label>
                <label>
                  <span>章节标题</span>
                  <input
                    name="chapter_title"
                    value={sceneDraft.chapter_title}
                    onChange={(event) => updateScene("chapter_title", event.target.value)}
                  />
                </label>
                <label>
                  <span>固定时长（秒）</span>
                  <input
                    name="duration_sec"
                    type="number"
                    step="0.1"
                    value={sceneDraft.duration_sec}
                    onChange={(event) => updateScene("duration_sec", event.target.value)}
                  />
                </label>
                <label>
                  <span>停顿（秒）</span>
                  <input
                    name="pause_after_sec"
                    type="number"
                    step="0.1"
                    value={sceneDraft.pause_after_sec}
                    onChange={(event) => updateScene("pause_after_sec", event.target.value)}
                  />
                </label>
                <label className="full-span">
                  <span>旁白</span>
                  <textarea
                    name="narration"
                    value={sceneDraft.narration}
                    rows={8}
                    onChange={(event) => updateScene("narration", event.target.value)}
                  />
                </label>
                <label className="full-span">
                  <span>烧录字幕（可选）</span>
                  <textarea
                    name="subtitle"
                    value={sceneDraft.subtitle}
                    rows={4}
                    onChange={(event) => updateScene("subtitle", event.target.value)}
                  />
                </label>
              </>
            )}
          </form>

          <div className="status-panel">
            <div className="status-line">{status}</div>
            <div className="status-hint">
              现在这版是“可编辑审片台”。下一步最适合接的是单镜头预览渲染和 TTS 失效缓存。
            </div>
          </div>
        </aside>
      </main>
    </div>
  );
}
