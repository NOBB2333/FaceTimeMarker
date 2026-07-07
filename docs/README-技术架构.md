# FaceTimeMarker 技术架构文档

最后更新：2026-07-07

## 架构概览

FaceTimeMarker 是本地单机优先的离线视频人物分析系统：

```text
Vue 3 工作台 / CLI
  -> FastAPI
  -> FaceVideoPipeline
  -> OpenCV 抽帧
  -> InsightFace 检测 + embedding
  -> BoxMOT BoT-SORT 跟踪
  -> HDBSCAN / KMeans 聚类
  -> TimelineBuilder
  -> ResultStore / SQLAlchemy
  -> SQLite 默认数据库 / 可配置数据库 URL
```

当前架构不建议推倒重写。需要继续做的是：识别质量评测、人物档案形象层、参考素材导出、数据库迁移稳定性和任务队列可靠性。

## 技术栈

| 层 | 技术 | 说明 |
| --- | --- | --- |
| Python | Python 3.12 + uv | 视觉依赖稳定，版本边界清晰 |
| 后端 | FastAPI + Uvicorn | 本地 API 服务 |
| CLI | Click | 支持脚本化分析、导入、benchmark |
| ORM/存储 | SQLAlchemy + ResultStore | 默认 SQLite，可通过数据库 URL 迁移 |
| 默认数据库 | SQLite | 本地零部署，适合当前单机工作流 |
| 视频 | OpenCV | 读取视频、抽帧、截帧、写图 |
| 人脸 | InsightFace | SCRFD 检测 + ArcFace embedding |
| 跟踪 | BoxMOT BoT-SORT | 短期轨迹 ID 稳定 |
| 聚类 | scikit-learn HDBSCAN / KMeans | 自动聚类或预设人数聚类 |
| 前端 | Vue 3 + TypeScript + Vue Router + Tailwind + Vite | 本地工作台 |
| 图标 | lucide-vue | 工具型界面 |
| 图像生成 | LiteLLM 兼容接口 | 四视图生成，配置在 `configs/ai.toml` |

## 数据流

```mermaid
flowchart TD
  A[本地视频/上传视频/timeline.json] --> B[CLI 或 FastAPI]
  B --> C[FaceVideoPipeline]
  C --> D[OpenCV 抽样帧]
  D --> E[InsightFace 检测人脸和 embedding]
  E --> F[BoT-SORT 生成 tracks]
  F --> G[HDBSCAN 或 KMeans 聚类 person_id]
  G --> H[TimelineBuilder 合并片段]
  H --> I[IdentityStore / global_person_id]
  I --> J[JSON CSV face crops references]
  J --> K[ResultStore 写数据库]
  K --> L[工作台/人物档案/搜索]
  K --> M[四视图资产和参考素材]
```

## 识别逻辑

当前不是“取第一帧作为人物头像”，完整流程是：

1. 按 `采样帧率` 抽帧。
2. 每个采样帧用 InsightFace 检测人脸。
3. 过滤低置信度或过小人脸。
4. 对保留人脸提取 embedding。
5. BoT-SORT 将连续帧人脸串成 track。
6. 每条 track 对 embedding 求平均，得到轨迹身份向量。
7. 自动模式用 HDBSCAN 聚类成 `person_id`。
8. 指定人数时用 KMeans 聚类到固定人数。
9. TimelineBuilder 将同一人物轨迹合并成出现片段。
10. 代表脸按置信度、面积等因素挑选。
11. IdentityStore 匹配跨视频 `global_person_id`。
12. 结果写入 JSON/CSV/截图/SQLite。

## 配置体系

默认入口是 [../configs/default.toml](../configs/default.toml)。

```toml
"包含配置" = [
  "recognition.toml",
  "outputs.toml",
  "reference_export.toml",
  "ai.toml",
]
```

| 文件 | 负责内容 |
| --- | --- |
| `recognition.toml` | 抽帧、人脸、跟踪、聚类、时间轴 |
| `outputs.toml` | 输出目录、源媒体、人物库、数据库 |
| `reference_export.toml` | 逐帧框、参考图导出、脸部标记 |
| `ai.toml` | 大模型和图像生成 |
| `profiles/*.toml` | 面向具体素材类型的覆盖配置 |

配置文件可以按视频覆盖：

```bash
uv run facetimemarker analyze video.mp4 --config configs/profiles/anime-lowres-strict.toml --no-cache
```

前端分析请求也支持传配置文件路径。

## 存储架构

当前代码不应继续散落手写 SQL。业务访问通过 `ResultStore` 层，底层用 SQLAlchemy 模型和会话管理。

默认数据库：

```text
_outputs/facetimemarker.db
```

可配置数据库 URL：

```toml
["数据库"]
"路径" = "_outputs/facetimemarker.db"
# "URL" = "postgresql+psycopg://user:password@127.0.0.1:5432/facetimemarker"
```

当前主要表：

| 表 | 作用 |
| --- | --- |
| `videos` | 视频元信息、标题、系列、源路径、诊断 JSON、软删除 |
| `people` | 单视频人物、本地 `person_id`、代表脸、全局人物关联 |
| `segments` | 人物出现时间段 |
| `tracks` | 跟踪轨迹、代表 bbox、embedding 信息 |
| `track_detections` | 逐帧/采样帧检测框，用于播放器红框和脸部标记 |
| `face_crops` | 人脸截图、候选参考帧 |
| `global_people` | 跨视频人物档案 |
| `global_observations` | 人物档案在各视频中的观测 |
| `global_person_actions` / `review_actions` | 人工整理操作记录 |
| `global_person_four_view_assets` | 四视图原图资产 |
| `analyze_jobs` | 后台分析任务状态 |

## API 能力

主要接口按领域划分：

| 领域 | 接口 |
| --- | --- |
| 健康/配置 | `GET /api/health`, `/api/config`, `/api/presets`, `/api/hardware` |
| 视频 | `GET /api/videos`, `GET/PATCH/DELETE /api/videos/{id}`, restore, purge |
| 视频结果 | `/people`, `/segments`, `/tracks`, `/track-detections`, `/face-crops`, `/frame` |
| 上下文片段 | `GET /api/videos/{id}/context-segments` |
| 本地人物整理 | rename, visibility, merge, split, assign tracks, delete tracks, delete person |
| 人物档案 | list/create/rename/delete/restore/purge/merge |
| 档案观测 | observations, confirm, reject, link local person, create from local person |
| 四视图资产 | list/upload/generate/move/delete |
| 搜索 | `GET /api/search/people`, `POST /api/search/faces` |
| 分析任务 | sync analyze, job create, batch job, list, get, cancel |
| 上传/导入 | upload video, import timeline |
| 媒体访问 | `GET /media?path=...` |

## 前端架构

```text
web/src/app/pages.ts          页面声明：工作台、人物档案、搜索
web/src/router.ts             Vue Router，刷新保留当前子页面
web/src/pages/
  WorkspacePage.vue           工作台页面容器
  ProfilesPage.vue            人物档案页面容器
  SearchPage.vue              搜索页面容器
web/src/components/workspace/ 工作台组件
web/src/components/profiles/  人物档案组件
web/src/components/search/    搜索组件
web/src/composables/          工作台分析、布局等组合逻辑
web/src/api.ts                API 类型和请求封装
```

人物档案页面已经拆出：

- `ProfilesSidebar.vue`
- `SegmentPreviewPanel.vue`
- `ReferenceCandidateRail.vue`
- `ProfileManagementPanel.vue`
- `FourViewStatus.vue`
- `FourViewAssetStrip.vue`
- `FourViewAssetDialog.vue`
- `ReferenceCandidateDialog.vue`
- `ReferenceDisplayModeToggle.vue`

继续拆分时的原则：

1. 页面文件保留“状态组合和业务流程”。
2. 可复用展示块下沉到 `components/*`。
3. 可测试/可复用逻辑下沉到 `composables/*`。
4. 不把 API 请求散落到深层展示组件里，除非组件是明确的业务容器。

## 四视图生成架构

四视图生成使用 [../configs/ai.toml](../configs/ai.toml)：

```text
前端选择参考帧
  -> POST /api/global-people/{id}/four-view-assets/generate
  -> 后端解析参考图片
  -> LiteLLM / image edit 或兼容接口
  -> 保存生成图到本地
  -> 写 global_person_four_view_assets
  -> 前端预览原图
```

设计选择：

- 资产单位是一张未切分原图。
- 前端预览不强制切成四块；默认按横向角色设定表直接预览。
- 当前推荐结构是正面全身、侧面全身、背面全身、45 度全身或半身，加右侧两列细节区：脸部细节列和设计细节列。
- 多张四视图资产可以共存。
- 资产可以从旧档案迁移到新档案。
- 图像接口使用 `output_format` 请求 `png`、`jpeg` 或 `webp`。
- `output_compression` 只在配置填写且格式为 WebP/JPEG 时传给接口。
- 兼容接口如果忽略输出格式，后端会根据文件头识别真实格式，并尽量本地转码成配置要求的格式。

OpenAI GPT Image 官方 API 支持 `output_format = png | jpeg | webp`。项目默认使用 WebP；PNG 作为需要最大兼容性时的可选项。

## 硬件策略

配置项：

```toml
["人脸"]
"执行提供方策略" = "auto"
"允许CPU降级" = true
"ONNX执行提供方" = ["CPUExecutionProvider"]
```

策略：

| 策略 | 用途 |
| --- | --- |
| auto | 自动选择可用 provider |
| cpu | 稳定但慢 |
| apple | Apple Silicon CoreML |
| nvidia | CUDA |
| intel | OpenVINO / DirectML 实验 |

必须用相同视频做 benchmark，不能只凭设备型号判断快慢。

## 当前主要技术风险

| 风险 | 说明 | 缓解 |
| --- | --- | --- |
| 动漫脸识别不稳定 | 真人模型对动漫素材可能漏检或误检 | 配置预设、样例评测、后续可接专用模型 |
| 低采样率导致时间错觉 | 红框/头像来自采样帧，视觉上可能提前或滞后 | 提高采样帧率，保留逐帧检测时间戳 |
| 自动聚类误合并 | 不同角色可能被聚为同一全局人物 | 人物档案合并/拆分/重命名/迁移资产 |
| 长视频性能 | 高采样率会显著变慢 | 队列、缓存、硬件策略、benchmark |
| API Key 泄漏 | 用户要求 Key 写项目配置 | 文档提醒私有使用，不公开含 Key 配置 |
| 数据库迁移 | 从 SQLite 切外部库需要完整迁移验证 | ORM 层统一访问，Alembic 迁移 |

## 验证命令

```bash
uv run ruff check src tests
uv run pytest -q
pnpm --dir web build
git diff --check
```

综合检查：

```bash
bash scripts/check.sh
```
