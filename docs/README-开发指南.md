# FaceTimeMarker 开发指南

最后更新：2026-07-07

## 开发环境

推荐：

```text
Python 3.12
uv
Node.js 20+
pnpm
```

安装：

```bash
uv sync --extra vision --extra dev
cd web
pnpm install
cd ..
```

## 本地启动

后端：

```bash
bash scripts/dev-api.sh
```

前端：

```bash
bash scripts/dev-web.sh
```

自定义端口：

```bash
HOST=127.0.0.1 API_PORT=8010 bash scripts/dev-api.sh
WEB_PORT=5174 VITE_API_TARGET=http://127.0.0.1:8010 bash scripts/dev-web.sh
```

## 检查命令

```bash
bash scripts/check.sh
```

拆开执行：

```bash
uv run ruff check src tests
uv run pytest -q
pnpm --dir web build
git diff --check
```

## 目录约定

```text
src/apps/             应用入口：CLI 和 FastAPI
src/core/             核心领域逻辑：配置、管线、模型、存储、时间轴、聚类
src/adapters/         外部库适配：InsightFace、BoxMOT、OpenCV、导出器、人物库
web/src/pages/        页面容器
web/src/components/   展示和业务组件
web/src/composables/  可复用前端状态逻辑
web/src/api.ts        前端 API 类型和请求
configs/              TOML 配置
docs/                 用户、产品、技术、开发文档
```

## 后端开发规则

1. 新 API 放在 `src/apps/api/main.py`，但复杂业务不要堆在路由函数里。
2. 数据读写走 `ResultStore` / SQLAlchemy 模型，不在业务层继续散落手写 SQL。
3. 新字段要同步：
   - ORM 模型。
   - 存储读写方法。
   - API response/request model。
   - 前端 `web/src/api.ts` 类型。
   - 相关测试。
   - 文档。
4. 软删除和彻底删除要区分：
   - 默认用户删除走回收站。
   - purge 才做不可逆删除。
5. 分析任务必须能写入状态：
   - queued / running / completed / failed / canceled。
   - 当前 item。
   - 进度。
   - 耗时。
   - 错误信息。

## 前端开发规则

### 页面和组件边界

页面文件只保留：

- 页面级状态。
- API 调用流程。
- 数据组合。
- 业务动作编排。

组件负责：

- 局部展示。
- 局部交互。
- 通过 props/emits 和父页面通信。

当前人物档案页组件拆分：

| 组件 | 责任 |
| --- | --- |
| `ProfilesSidebar.vue` | 左侧人物/作品/回收站导航和新建档案入口 |
| `SegmentPreviewPanel.vue` | 右侧人物片段视频预览 |
| `ReferenceCandidateRail.vue` | 已选参考素材列表 |
| `ProfileManagementPanel.vue` | 重命名、合并、回收站、操作记录 |
| `ReferenceFrameGrid.vue` | 参考帧网格，支持完整画面/脸部标记/脸部截图 |
| `FourViewStatus.vue` | 四视图生成、上传、全选、清空 |
| `FourViewAssetStrip.vue` | 横向四视图资产缩略条 |
| `FourViewAssetDialog.vue` | 四视图原图预览 |
| `ReferenceCandidateDialog.vue` | 参考素材大图预览 |

四视图生成链路在 `src/apps/api/main.py`。维护时注意：

- `configs/ai.toml` 是用户调模型、提示词、输出格式的入口。
- 默认使用 WebP；PNG/JPEG 通过 `output_format` 调整，WebP/JPEG 压缩通过 `output_compression` 控制。
- 保存文件前要检查真实图片格式，避免兼容平台返回 PNG 但本地文件写成 `.webp`。

继续重构时优先拆：

1. 重复模板。
2. 独立业务面板。
3. 有清晰 props/emits 边界的功能块。

不要为了行数拆出没有语义的组件。

### UI 规则

- 工具型页面优先信息密度，不做营销式大卡片。
- 高风险操作必须二次确认。
- 删除默认进回收站，彻底删除才不可逆。
- 时间轴、播放器、人物清单这类固定格式元素要有稳定尺寸，避免 hover 或动态文本撑坏布局。
- 页面可以滚动时，内层小滚动区域不要默认抢滚轮；只有人物列表、参考素材、长资产条这类必要区域使用内部滚动。

## 配置开发规则

配置必须：

1. 写入合适的 TOML 文件。
2. 使用中文注释说明用途、何时调高/调低、代价是什么。
3. 如果影响识别结果，必须参与缓存 key 或提醒用户需要重新识别。
4. 如果只影响 AI 生成/前端展示，不应导致视频重新分析。

配置分层：

| 文件 | 适合新增什么 |
| --- | --- |
| `recognition.toml` | 抽帧、检测、跟踪、聚类、时间轴 |
| `outputs.toml` | 输出、数据库、源文件策略、人物库 |
| `reference_export.toml` | 逐帧框、参考图、脸部标记 |
| `ai.toml` | 模型、接口、图像生成、提示词 |
| `configs/profiles/*.toml` | 某类素材的覆盖配置 |

## 文档维护规则

文档按 Diátaxis 分工：

| 类型 | 文件 |
| --- | --- |
| Tutorial / How-to | `README.md`, `docs/README-用户使用.md` |
| Explanation | `docs/README-产品设计.md`, `docs/README-技术架构.md` |
| Reference | `docs/README-开发指南.md`, `docs/需求与技术选型.md`, 配置文件注释 |
| Roadmap | `docs/实施路线图.md`, `docs/项目完整性评估.md` |

改功能时同步更新：

- 新页面或大交互：用户手册 + 产品设计。
- 新 API/表/配置：技术架构 + 开发指南。
- 新截图：README + 用户手册。
- 调参策略变化：用户手册 + `configs/*.toml` 注释。

## 测试建议

新增后端能力：

```bash
uv run pytest tests/test_sqlite_store.py tests/test_api_review.py -q
```

新增前端组件：

```bash
pnpm --dir web build
```

涉及分析管线：

```bash
uv run facetimemarker analyze path/to/short.mp4 --config configs/profiles/anime-lowres-strict.toml --no-cache
```

涉及任务队列：

```bash
POST /api/analyze-batch-jobs
GET /api/analyze-jobs
GET /api/analyze-jobs/{job_id}
POST /api/analyze-jobs/{job_id}/cancel
```

## 常见开发陷阱

| 问题 | 处理 |
| --- | --- |
| 前端刷新回默认页 | 路由必须走 Vue Router 子路径，不要用单个容器状态模拟页面 |
| 人物档案错乱 | 区分本地 `person_id` 和全局 `global_person_id` |
| 四视图跟错人物 | 从误聚类拆新档案时，允许迁移四视图资产 |
| 红框滞后 | 检查采样帧率、逐帧框写入和最近帧容忍秒数 |
| 背景误检 | 提高检测阈值、最小脸尺寸、最小连续帧数 |
| 人物漏检 | 提高采样帧率、降低检测阈值、降低最小脸尺寸 |
