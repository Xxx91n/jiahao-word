"""静态检查和行为检查 CI 配置：四条检查都在，PR 描述改了会重跑。"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
CHECKS = ("tests", "data", "drift", "pr-note")
BASH = shutil.which("bash")
GIT = shutil.which("git")


def load_workflow() -> dict:
    """读 CI 配置。用 BaseLoader，免得 YAML 1.1 把「on」当成布尔值。"""
    return yaml.load(WORKFLOW_PATH.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def run_commands(job: dict) -> list[str]:
    """按顺序取一个任务里跑的命令。"""
    return [
        step["run"]
        for step in job["steps"]
        if isinstance(step, dict) and "run" in step
    ]


def drift_script() -> str:
    """取出 build 后面那段漂移检查脚本，原样拿去跑。"""
    commands = run_commands(load_workflow()["jobs"]["drift"])
    return commands[commands.index("python -m jiahao_word build") + 1]


def make_repo(tmp_path: Path) -> None:
    """建一个只有一个已提交文件的小仓库。"""
    if BASH is None or GIT is None:
        pytest.skip("没装 bash 或 git，跳过漂移脚本的行为测试")
    subprocess.run([GIT, "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        [GIT, "config", "user.email", "ci@example.com"], cwd=tmp_path, check=True
    )
    subprocess.run([GIT, "config", "user.name", "CI"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("干净\n", encoding="utf-8")
    subprocess.run([GIT, "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run([GIT, "commit", "-qm", "init"], cwd=tmp_path, check=True)


def run_drift_script(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    """按 GitHub 的跑法执行脚本：bash -e。"""
    return subprocess.run(
        [BASH, "-e", "-c", drift_script()],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_pull_request_runs_all_four_checks() -> None:
    """PR 上四条检查都在，三个任务不能被条件跳过。"""
    workflow = load_workflow()
    jobs = workflow["jobs"]

    assert "pull_request" in workflow["on"]
    assert set(CHECKS) <= set(jobs)
    for check in ("tests", "data", "drift"):
        assert "if" not in jobs[check], f"{check} 不能在 PR 上被条件跳过"
    assert jobs["pr-note"]["if"] == "github.event_name == 'pull_request'"


def test_editing_the_pull_request_body_reruns_checks() -> None:
    """改 PR 描述会触发重跑，不用重新 push。"""
    trigger = load_workflow()["on"]["pull_request"]

    assert isinstance(trigger, dict)
    assert trigger["types"] == ["opened", "synchronize", "reopened", "edited"]


def test_main_is_checked_after_merge() -> None:
    """main 合入后还会跑前三条检查。"""
    trigger = load_workflow()["on"]["push"]

    assert trigger["branches"] == ["main"]


def test_every_check_has_a_python_setup_and_cannot_be_skipped() -> None:
    """每个任务都装好 Python 和依赖，步骤不能被条件跳过或吞掉失败。"""
    jobs = load_workflow()["jobs"]

    for check in CHECKS:
        steps = jobs[check]["steps"]
        assert steps[0]["uses"] == "actions/checkout@v4"
        assert steps[0]["with"]["persist-credentials"] == "false"
        assert steps[1]["uses"] == "actions/setup-python@v5"
        assert steps[1]["with"]["python-version"] == "3.11"
        install = next(step for step in steps if step.get("name") == "装依赖")
        assert install["run"].startswith("python -m pip install")
        for step in steps:
            assert "if" not in step, f"{check} 的步骤不能被条件跳过"
            assert "continue-on-error" not in step, f"{check} 的步骤不能吞掉失败"


def test_each_check_runs_the_right_command() -> None:
    """每个任务真的跑对应那条命令。"""
    jobs = load_workflow()["jobs"]

    assert '".[dev]"' in run_commands(jobs["tests"])[0]
    assert run_commands(jobs["tests"])[-1] == "python -m pytest -q"
    assert run_commands(jobs["data"])[-1] == "python -m jiahao_word check"
    assert run_commands(jobs["pr-note"])[-1] == (
        'printf \'%s\' "$PR_BODY" | python -m jiahao_word check-pr'
    )


def test_human_note_is_read_from_the_pull_request() -> None:
    """人话说明从 PR 描述里读，不靠仓库里的文件。"""
    step = load_workflow()["jobs"]["pr-note"]["steps"][-1]

    assert step["env"]["PR_BODY"] == "${{ github.event.pull_request.body }}"
    assert step["env"]["PYTHONIOENCODING"] == "utf-8"


def test_drift_is_checked_after_build() -> None:
    """漂移检查紧跟 build，不会先查后生成。"""
    commands = run_commands(load_workflow()["jobs"]["drift"])
    build_at = commands.index("python -m jiahao_word build")

    assert "git status --porcelain" in commands[build_at + 1]


def test_drift_check_passes_on_a_clean_checkout(tmp_path: Path) -> None:
    """工作区干净时，漂移脚本退出 0。"""
    make_repo(tmp_path)

    result = run_drift_script(tmp_path)

    assert result.returncode == 0
    assert "一致" in result.stdout


def test_drift_check_fails_when_a_generated_file_changes(tmp_path: Path) -> None:
    """手改文件又没提交时，漂移脚本退出 1 并打出改动。"""
    make_repo(tmp_path)
    (tmp_path / "README.md").write_text("手改\n", encoding="utf-8")

    result = run_drift_script(tmp_path)

    assert result.returncode == 1
    assert "不一样" in result.stdout
    assert "README.md" in result.stdout


def test_drift_check_fails_when_a_generated_file_is_untracked(
    tmp_path: Path,
) -> None:
    """新生成的索引没提交时，漂移脚本也能发现。"""
    make_repo(tmp_path)
    (tmp_path / "index").mkdir()
    (tmp_path / "index" / "zh.json").write_text("{}\n", encoding="utf-8")

    result = run_drift_script(tmp_path)

    assert result.returncode == 1
    assert "不一样" in result.stdout
    assert "index/" in result.stdout
