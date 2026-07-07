from __future__ import annotations

import json
from pathlib import Path

import click

from adapters.identity.store import IdentityStore
from core.config import PRESET_NAMES, apply_preset, load_config
from core.hardware import HARDWARE_PROFILES, hardware_summary
from core.pipeline import FaceVideoPipeline
from core.storage import ResultStore


@click.group()
def main() -> None:
    """FaceTimeMarker 命令行工具入口。"""


@main.command()
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
def inspect(config_path: Path | None) -> None:
    """打印当前项目配置。"""
    config = load_config(config_path)
    click.echo(config.model_dump_json(indent=2, by_alias=True))


@main.command()
@click.argument("video_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
@click.option("--dry-run", is_flag=True, help="只验证配置和视频读取，不运行视觉推理。")
@click.option(
    "--preset",
    type=click.Choice(PRESET_NAMES),
    default=None,
    help="分析预设：fast / balanced / crowd。",
)
@click.option("--people-count", type=int, default=None, help="预设人物数量，默认自动聚类。")
@click.option(
    "--hardware-profile",
    type=click.Choice(HARDWARE_PROFILES),
    default=None,
    help="硬件策略：auto / cpu / apple / nvidia / intel。",
)
@click.option("--no-cpu-fallback", is_flag=True, help="GPU/CoreML 初始化失败时不降级到 CPU。")
@click.option("--no-cache", is_flag=True, help="忽略已有结果缓存，强制重新分析。")
def analyze(
    video_path: Path,
    config_path: Path | None,
    dry_run: bool,
    preset: str | None,
    people_count: int | None,
    hardware_profile: str | None,
    no_cpu_fallback: bool,
    no_cache: bool,
) -> None:
    """分析视频并生成人物时间轴。"""
    config = apply_preset(load_config(config_path), preset)
    if people_count is not None:
        if people_count < 1:
            raise click.BadParameter("--people-count must be >= 1")
        config.clustering.expected_people_count = people_count
    if hardware_profile is not None:
        config.face.execution_provider_profile = hardware_profile
    if no_cpu_fallback:
        config.face.allow_cpu_fallback = False
    pipeline = FaceVideoPipeline(config)
    result_path = pipeline.run(
        video_path=video_path,
        dry_run=dry_run,
        preset=preset,
        use_cache=not no_cache,
    )
    click.echo(f"分析输出: {result_path}")


@main.command()
@click.argument("video_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
@click.option(
    "--preset",
    type=click.Choice(PRESET_NAMES),
    default="fast",
    help="用于 benchmark 的分析预设。",
)
@click.option("--people-count", type=int, default=None, help="预设人物数量，默认自动聚类。")
@click.option(
    "--hardware-profile",
    type=click.Choice(HARDWARE_PROFILES),
    default=None,
    help="硬件策略：auto / cpu / apple / nvidia / intel。",
)
@click.option("--no-cpu-fallback", is_flag=True, help="GPU/CoreML 初始化失败时不降级到 CPU。")
def benchmark(
    video_path: Path,
    config_path: Path | None,
    preset: str,
    people_count: int | None,
    hardware_profile: str | None,
    no_cpu_fallback: bool,
) -> None:
    """重新分析视频并打印性能诊断摘要。"""
    config = apply_preset(load_config(config_path), preset)
    if people_count is not None:
        if people_count < 1:
            raise click.BadParameter("--people-count must be >= 1")
        config.clustering.expected_people_count = people_count
    if hardware_profile is not None:
        config.face.execution_provider_profile = hardware_profile
    if no_cpu_fallback:
        config.face.allow_cpu_fallback = False
    result_path = FaceVideoPipeline(config, progress_factory=None).run(
        video_path=video_path,
        dry_run=False,
        preset=preset,
        use_cache=False,
    )
    click.echo(f"分析输出: {result_path}")
    click.echo("诊断报告已写入 timeline.json 的 diagnostics 字段。")


@main.command("import-timeline")
@click.argument("timeline_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
def import_timeline(timeline_path: Path, config_path: Path | None) -> None:
    """把已有 timeline.json 导入 SQLite 数据库。"""
    config = load_config(config_path)
    video_id = ResultStore(config.database.path, url=config.database.url).import_timeline(
        timeline_path
    )
    click.echo(f"已导入视频 ID: {video_id}")


@main.command()
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8000, show_default=True)
def serve(host: str, port: int) -> None:
    """启动 FastAPI 后端。"""
    import uvicorn

    uvicorn.run("apps.api.main:app", host=host, port=port, reload=False)


@main.command("hardware")
def hardware() -> None:
    """打印当前机器的硬件和 ONNX Runtime provider 摘要。"""
    click.echo(json.dumps(hardware_summary(), ensure_ascii=False, indent=2))


@main.command("people")
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
def people(config_path: Path | None) -> None:
    """打印跨视频人物库概览。"""
    config = load_config(config_path)
    store = IdentityStore.load(
        config.identity_store_path(),
        match_threshold=config.identity_store.match_threshold,
    )
    if not store.people:
        click.echo("人物库为空。")
        return

    for person in store.people:
        videos = sorted({observation.video_path for observation in person.observations})
        click.echo(
            f"{person.global_person_id}: {len(videos)} video(s), "
            f"{len(person.observations)} observation(s)"
        )
        for video in videos:
            click.echo(f"  - {video}")


if __name__ == "__main__":
    main()
