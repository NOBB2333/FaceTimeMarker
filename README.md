# FaceTimeMarker

FaceTimeMarker 是一个本地离线的视频人物识别、人物时间轴和人物档案工作台。它面向影视、动漫、素材整理和剪辑辅助场景：把一批视频分析成人物、片段、代表帧、跨作品人物档案，并允许你在前端像剪辑软件一样快速复核和整理结果。

![工作区总览](docs/assert/工作区1.webp)

## 核心能力

- 视频导入：支持拖拽上传、本地路径、批量队列和已生成 `timeline.json` 导入。
- 人脸分析：InsightFace 检测与 embedding、BoT-SORT 跟踪、HDBSCAN/KMeans 聚类。
- 人物时间轴：按人物轨道展示出现片段，支持点击跳转、播放、缩放和当前时间定位。
- 批量整理：支持人脸多选、框选、拖拽归类、删除误检、人物命名和隐藏。
- 人物档案：跨视频聚合人物，支持按人物/按作品查看、手动新建、重命名、合并、回收站。
- 参考素材：可选完整画面、脸部标记、脸部截图，便于给多模态模型判断角色身份。
- 四视图资产：支持上传、生成、预览、删除；提示词、输出格式和模型参数在 `configs/ai.toml`。
- 人物搜索：支持文本搜索和以图搜图，可手动调阈值。
- 本地配置：识别、输出、参考图、大模型等配置拆分在 `configs/*.toml`。

## 快速使用手册

### 1. 安装依赖

```bash
uv sync --extra vision --extra dev
cd web
pnpm install
cd ..
```

第一次真实分析会下载 InsightFace 模型到本机缓存目录。项目根目录不需要手动放模型。

### 2. 启动本地工作台

后端：

```bash
bash scripts/dev-api.sh
```

前端：

```bash
bash scripts/dev-web.sh
```

打开：

```text
http://127.0.0.1:5173/
```

路由说明：

| 页面 | 地址 | 用途 |
| --- | --- | --- |
| 工作台 | `/workspace` | 导入、分析、播放、时间轴、批量整理 |
| 人物档案 | `/profiles` | 跨作品人物、参考帧、四视图资产、合并/重命名 |
| 搜索 | `/search` | 文本搜索和以图搜图 |

### 3. 导入并分析视频

在工作台左侧可以：

1. 拖拽视频文件上传。
2. 输入本机视频路径。
3. 用分号输入多个路径组成队列。
4. 导入已有 `timeline.json`。

批量路径示例：

```text
/Users/me/video/a.mp4; /Users/me/video/b.mp4
```

常用分析选项：

| 选项 | 说明 |
| --- | --- |
| 使用缓存 | 复用检测/跟踪缓存，加快重复打开 |
| 重新识别 | 忽略缓存，按当前参数重新跑 |
| 系列/作品 | 给一批视频写入同一作品名或系列名 |
| 预设人数 | 留空为 Auto；明确知道人数时可填数字 |
| 配置文件 | 可给某个视频指定专用 TOML，例如动漫低清严格配置 |
| 硬件策略 | auto / cpu / apple / nvidia / intel |

### 4. 查看和修正人物

工作台中间是播放器和人物出现时间轴，右侧是人物清单和操作区。

- 点人物：高亮该人物时间轴。
- 再点同一个人物：取消高亮。
- 点时间轴片段：视频跳到对应时间。
- 拖动片段或人脸卡片到目标人物：把分错的轨迹归类过去。
- 删除人物或轨迹：用于移除背景墙、局部眼睛等误检。
- 红框开关：显示当前人物脸部定位；逐帧框开启时优先使用最近检测帧。

### 5. 管理人物档案

人物档案页支持两种视角：

![人物档案按作品](docs/assert/人物档案1.webp)

- 按人物：查看一个跨作品人物在不同作品中的观测、参考帧和四视图资产。
- 按作品：查看一部作品内识别出的所有人物，每个人下方列出可选参考帧。
- 回收站：恢复或彻底删除不需要的人物档案。

常用操作：

1. 选择某个人物的一组参考帧。
2. 用已选素材新建人物档案，或合并到已有档案。
3. 上传已有四视图原图，或调用图像生成服务生成四视图资产。
4. 对多余档案执行重命名、合并、移入回收站或彻底删除。

四视图资产是一张未切分原图，不强制切成四张。默认提示词现在按横向角色设定表生成：

```text
正面全身 / 侧面全身 / 背面全身 / 45 度全身或半身 / 右侧细节区
```

右侧细节区建议做成两列：第一列放 45 度脸部特写和轻微微表情，第二列放服装/发型/配饰细节特写。

![四视图资产示例](docs/assert/四视图2.webp)

默认保存 WebP，文件体积更小，适合本地档案长期保存。如果需要最大兼容性，可以在 [configs/ai.toml](configs/ai.toml) 把 `"输出格式"` 改成 `"png"`。

### 6. 搜索人物

![人物搜索](docs/assert/人物搜索.webp)

搜索页支持：

- 文本搜索：匹配人物名、全局人物 ID、视频名、路径。
- 以图搜图：上传人脸图，按 embedding 匹配全局人物库。
- 阈值调节：阈值越高越严格，越低越容易返回相似但不相关的人。

## 常用命令

```bash
# 检查 Python、测试和前端构建
bash scripts/check.sh

# 只构建前端
bash scripts/build.sh

# 查看当前机器可用硬件 provider
bash scripts/hardware.sh

# CLI 分析
uv run facetimemarker analyze path/to/video.mp4 --preset fast
uv run facetimemarker analyze path/to/video.mp4 --config configs/profiles/anime-lowres-strict.toml --no-cache

# 导入 timeline
uv run facetimemarker import-timeline _outputs/example/timeline.json

# 查看跨视频人物库
uv run facetimemarker people
```

## 配置入口

默认配置入口是 [configs/default.toml](configs/default.toml)，它组合了多个配置文件：

| 文件 | 作用 |
| --- | --- |
| [configs/recognition.toml](configs/recognition.toml) | 抽帧、人脸检测、跟踪、聚类、时间轴 |
| [configs/outputs.toml](configs/outputs.toml) | 输出目录、源媒体复制策略、人物库、数据库 URL |
| [configs/reference_export.toml](configs/reference_export.toml) | 逐帧框、参考图导出、脸部标记 |
| [configs/ai.toml](configs/ai.toml) | 大模型接口、图像生成、四视图提示词 |
| [configs/profiles/anime-high-recall.toml](configs/profiles/anime-high-recall.toml) | 动漫/低清偏召回配置 |
| [configs/profiles/anime-lowres-strict.toml](configs/profiles/anime-lowres-strict.toml) | 动漫/低清偏严格配置 |

如果项目会公开，请注意 `configs/ai.toml` 里可能包含你自己的 API Key。这个项目按本地私有使用设计，不强制走环境变量。

## 输出和数据

默认输出目录：

```text
_outputs/
```

典型文件：

```text
_outputs/facetimemarker.db           本地结果数据库
_outputs/people_index.json           跨视频人物索引
_outputs/<视频名>/timeline.json      单视频分析结果
_outputs/<视频名>/timeline.csv       人工检查表
_outputs/<视频名>/faces/             代表脸
_outputs/<视频名>/references/        参考图和带框参考图
```

数据库默认是 SQLite，但代码侧通过 SQLAlchemy/ResultStore 层访问。以后要切 PostgreSQL/MySQL，可优先从 `configs/outputs.toml` 的数据库 URL 配置开始，而不是在业务代码里散落 SQL。

## 项目结构

```text
src/
  apps/                  CLI 和 FastAPI
  core/                  配置、管线、模型、存储、时间轴、聚类
  adapters/              InsightFace、BoxMOT、OpenCV、导出器、人物库
web/
  src/pages/             工作台、人物档案、搜索页面
  src/components/        workspace/search/profiles 组件
  src/composables/       工作台组合逻辑
configs/                 拆分后的本地配置
docs/                    用户、产品、技术、开发和路线图文档
data/                    上传暂存和本地输入
_outputs/                分析输出、数据库和人物库
third_party/             上游源码参考子模块，默认运行不依赖
```

## 文档导航

- [文档索引](docs/README.md)
- [用户使用手册](docs/README-用户使用.md)
- [产品设计文档](docs/README-产品设计.md)
- [技术架构文档](docs/README-技术架构.md)
- [开发指南](docs/README-开发指南.md)
- [项目架构](docs/项目架构.md)
- [需求与技术选型](docs/需求与技术选型.md)
- [项目完整性评估](docs/项目完整性评估.md)
- [实施路线图](docs/实施路线图.md)
- [批量整理人脸交互问题记录](docs/批量整理人脸交互问题记录.md)

## 第三方参考仓库

`third_party/insightface` 和 `third_party/ByteTrack` 以 Git 子模块形式保留，仅作源码参考。默认运行依赖通过 `uv sync --extra vision` 安装，不需要从 `third_party/` 导入业务代码。

```bash
git submodule update --init --recursive
```

当前主线：

```text
InsightFace + BoxMOT BoT-SORT + HDBSCAN + FastAPI + Vue 工作台
```
