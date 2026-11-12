"""站点发布工作流：检查跑完才发，发的只有 api/ 和根首页，Pages 没开就不发。"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_PATH = REPO_ROOT / ".github" / "workflows" / "deploy.yml"
CI_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
BASH = shutil.which("bash")

# 上线清单里绝对不能出现的东西：源码、测试、内部文档、项目配置。
NOT_SHIPPED = ("jiahao_word", "tests", "docs", ".github", "pyproject.toml")


def load(path: Path) -> dict:
    """读工作流配置。用 BaseLoader，免得 YAML 1.1 把「on」当成布尔值。"""
    return yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def step_with_id(job: dict, step_id: str) -> dict:
    """按 id 取一个步骤。id 是给人用的锚点，改文案不会把它改坏。"""
    return next(step for step in job["steps"] if step.get("id") == step_id)


def uses_of(job: dict) -> list[str]:
    """取一个任务里用到的所有 action。"""
    return [step["uses"] for step in job["steps"] if step.get("uses")]


def run_step(
    tmp_path: Path,
    job: str,
    step_id: str,
    pages_exit: int = 0,
    pages_stderr: str = "",
    latest_sha: str = "cafe1234",
    head_sha: str = "cafe1234",
    build_type: str = "workflow",
) -> subprocess.CompletedProcess[str]:
    """按 GitHub 的跑法执行一个步骤的脚本。

    脚本要问 GitHub 三件事：Pages 开没开、发布源是什么、main 现在到哪了。
    桩按参数分头回话，问过什么都记进文件。
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    args_file = tmp_path / "gh-args.txt"
    stub = bin_dir / "gh"
    stub.write_text(
        "#!/bin/sh\n"
        'printf "%s\\n" "$@" >> "$ARGS_FILE"\n'
        'echo "---" >> "$ARGS_FILE"\n'
        'case "$*" in\n'
        '  *commits/main*)\n'
        '    printf "%s" "$LATEST_SHA"\n'
        '    ;;\n'
        '  *pages*)\n'
        '    [ -n "$BUILD_TYPE" ] && printf "%s" "$BUILD_TYPE"\n'
        '    [ -n "$PAGES_STDERR" ] && printf "%s" "$PAGES_STDERR" >&2\n'
        '    exit "$PAGES_EXIT"\n'
        '    ;;\n'
        "esac\n"
        "exit 0\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)

    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env["GITHUB_OUTPUT"] = str(tmp_path / "output.txt")
    env["GITHUB_STEP_SUMMARY"] = str(tmp_path / "summary.txt")
    env["ARGS_FILE"] = str(args_file)
    env["PAGES_EXIT"] = str(pages_exit)
    env["PAGES_STDERR"] = pages_stderr
    env["BUILD_TYPE"] = build_type
    env["LATEST_SHA"] = latest_sha
    env["REPO"] = "Xxx91n/jiahao-word"
    env["GH_TOKEN"] = "test-token"
    env["HEAD_SHA"] = head_sha
    for name in ("output.txt", "summary.txt", "gh-args.txt"):
        (tmp_path / name).write_text("", encoding="utf-8")

    script = step_with_id(load(DEPLOY_PATH)["jobs"][job], step_id)["run"]
    return subprocess.run(
        [BASH, "-e", "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def outputs(tmp_path: Path) -> dict[str, str]:
    """读 GITHUB_OUTPUT，按 key=value 拆开。"""
    lines = (tmp_path / "output.txt").read_text(encoding="utf-8").splitlines()
    return dict(line.split("=", 1) for line in lines if "=" in line)


def test_deploy_hooks_onto_the_main_checks_and_never_runs_on_pull_requests() -> None:
    """发布挂在 main 的检查跑完之后，PR 上碰不到它。"""
    trigger = load(DEPLOY_PATH)["on"]

    assert set(trigger) == {"workflow_run"}
    run = trigger["workflow_run"]
    assert run["workflows"] == ["检查"]
    assert run["types"] == ["completed"]
    assert run["branches"] == ["main"]


def test_only_our_own_pushes_to_main_can_publish() -> None:
    """只认本仓库 push 出来的成功运行；fork PR 的头分支也叫 main，得挡掉。"""
    guard_if = load(DEPLOY_PATH)["jobs"]["guard"]["if"]

    assert "github.event.workflow_run.event == 'push'" in guard_if
    assert "conclusion == 'success'" in guard_if
    assert "head_repository.full_name == github.repository" in guard_if


def test_the_existing_three_jobs_are_left_alone() -> None:
    """现有工作流的触发和任务一字不动，检查不会跑两遍。"""
    ci = load(CI_PATH)

    assert set(ci["on"]) == {"push", "pull_request"}
    assert set(ci["jobs"]) == {"tests", "data", "drift", "pr-note"}


def test_the_deploy_watch_uses_the_checks_workflow_name() -> None:
    """发布按工作流名字盯住检查，名字对不上就永远不触发；这里把两头钉在一起。"""
    watched = load(DEPLOY_PATH)["on"]["workflow_run"]["workflows"]
    ci_name = load(CI_PATH)["name"]

    assert watched == [ci_name]


def test_publishing_stays_off_until_pages_is_enabled() -> None:
    """Pages 没开时守卫拦下来，打包和上线都不跑；开 Pages 是另外的事。"""
    jobs = load(DEPLOY_PATH)["jobs"]

    assert jobs["build"]["if"] == "needs.guard.outputs.allowed == 'true'"
    assert jobs["build"]["needs"] == "guard"
    assert jobs["deploy"]["needs"] == "build"


def test_deploy_has_no_domain_and_no_custom_domain_config() -> None:
    """工作流里不写域名、不配自定义域；域名和 Pages 开关是单独授权的事。"""
    text = DEPLOY_PATH.read_text(encoding="utf-8").lower()

    assert "cname" not in text
    assert "github.io" not in text
    assert "http://" not in text
    assert "https://" not in text


def test_publishing_uses_an_artifact_checked_out_from_the_checked_commit() -> None:
    """用 artifact 发布，打包目录是 _site，检出的是那次检查通过的提交。"""
    build = load(DEPLOY_PATH)["jobs"]["build"]
    checkout = step_with_id(build, "checkout")

    assert "actions/checkout@v4" in uses_of(build)
    assert "actions/upload-pages-artifact@v3" in uses_of(build)
    assert checkout["with"]["ref"] == "${{ github.event.workflow_run.head_sha }}"
    assert checkout["with"]["persist-credentials"] == "false"
    assert next(
        step for step in build["steps"] if "upload-pages-artifact" in step.get("uses", "")
    )["with"]["path"] == "_site"


def test_deploy_job_has_the_permissions_pages_needs() -> None:
    """上线那一步要 pages: write 和 id-token: write，别处只读，守卫能读提交和 Pages。"""
    jobs = load(DEPLOY_PATH)["jobs"]

    assert load(DEPLOY_PATH)["permissions"] == {"contents": "read"}
    assert jobs["guard"]["permissions"] == {"contents": "read", "pages": "read"}
    assert jobs["deploy"]["permissions"] == {"pages": "write", "id-token": "write"}
    assert jobs["deploy"]["environment"]["name"] == "github-pages"
    assert uses_of(jobs["deploy"]) == ["actions/deploy-pages@v4"]
    assert jobs["deploy"]["environment"]["url"] == "${{ steps.deploy.outputs.page_url }}"


def test_the_probe_gets_the_repo_token_and_commit_from_the_workflow() -> None:
    """探针靠工作流传进去的仓库名、token 和提交号；缺了就是空地址空凭证。"""
    guard = load(DEPLOY_PATH)["jobs"]["guard"]
    probe = step_with_id(guard, "probe")

    assert probe["env"]["REPO"] == "${{ github.repository }}"
    assert probe["env"]["GH_TOKEN"] == "${{ github.token }}"
    assert probe["env"]["HEAD_SHA"] == "${{ github.event.workflow_run.head_sha }}"


def test_a_skipped_run_cannot_bump_a_queued_deploy() -> None:
    """并发组挂在干活的 job 上，不挂在整条工作流上。

    挂在工作流级别时，被守卫跳过的空跑也会占住 pages 组；
    GitHub 会用新排队的顶掉还排着队的，main 的发布就被挤没了。
    """
    workflow = load(DEPLOY_PATH)
    jobs = workflow["jobs"]

    assert "concurrency" not in workflow
    for job in ("build", "deploy"):
        assert jobs[job]["concurrency"] == {
            "group": "pages",
            "cancel-in-progress": "false",
        }
    assert "concurrency" not in jobs["guard"]


def test_pages_works_off_the_actions_source_or_not_at_all() -> None:
    """发布源不是 GitHub Actions 就停：那种模式发整个分支，api/ 清单形同虚设。"""
    probe = step_with_id(load(DEPLOY_PATH)["jobs"]["guard"], "probe")

    assert '.build_type' in probe["run"]
    assert '!= "workflow"' in probe["run"]


@pytest.mark.skipif(BASH is None, reason="没装 bash，跳过脚本行为测试")
def test_pages_disabled_says_so_and_skips_the_deploy(tmp_path: Path) -> None:
    """仓库还没开 Pages（接口回 404）时，写 allowed=false，退出 0，在摘要里说明。"""
    result = run_step(
        tmp_path, "guard", "probe", pages_exit=1, pages_stderr="gh: Not Found (HTTP 404)"
    )

    assert result.returncode == 0, result.stderr
    assert outputs(tmp_path) == {"allowed": "false"}
    assert "Pages 还没开" in (tmp_path / "summary.txt").read_text(encoding="utf-8")


@pytest.mark.skipif(BASH is None, reason="没装 bash，跳过脚本行为测试")
def test_pages_enabled_and_the_commit_is_still_tip_allows_the_deploy(tmp_path: Path) -> None:
    """Pages 开了，这份提交也还是 main 最新，才写 allowed=true。"""
    result = run_step(tmp_path, "guard", "probe")

    assert result.returncode == 0, result.stderr
    assert outputs(tmp_path) == {"allowed": "true"}


@pytest.mark.skipif(BASH is None, reason="没装 bash，跳过脚本行为测试")
def test_a_superseded_commit_is_not_shipped_back_over_the_newer_site(tmp_path: Path) -> None:
    """手动重跑旧的成功检查时，提示还是 success；这份提交已经不是最新，就不发。"""
    result = run_step(
        tmp_path, "guard", "probe", latest_sha="newer567", head_sha="older123"
    )

    assert result.returncode == 0, result.stderr
    assert outputs(tmp_path) == {"allowed": "false"}
    assert "已经被 main 上的" in (tmp_path / "summary.txt").read_text(encoding="utf-8")


@pytest.mark.skipif(BASH is None, reason="没装 bash，跳过脚本行为测试")
@pytest.mark.parametrize(
    "message", ["Bad credentials (HTTP 401)", "Forbidden (HTTP 403)", "Server Error (HTTP 500)"]
)
def test_a_broken_probe_fails_loudly_instead_of_skipping_forever(
    tmp_path: Path, message: str
) -> None:
    """token 不对、接口抽风时直接失败，别当成「Pages 没开」然后一直绿着不部署。"""
    result = run_step(tmp_path, "guard", "probe", pages_exit=1, pages_stderr=message)

    assert result.returncode != 0
    assert "查 Pages 状态失败" in result.stderr
    assert "allowed" not in outputs(tmp_path)


@pytest.mark.skipif(BASH is None, reason="没装 bash，跳过脚本行为测试")
def test_the_probe_asks_the_repo_pages_api_with_the_token(tmp_path: Path) -> None:
    """探针真的问了 repos/<repo>/pages，带上 token，地址拼错就白忙。"""
    run_step(tmp_path, "guard", "probe")
    args = (tmp_path / "gh-args.txt").read_text(encoding="utf-8")

    assert "api\nrepos/Xxx91n/jiahao-word/pages" in args


@pytest.mark.skipif(BASH is None, reason="没装 bash，跳过打包后的复查")
def test_packing_rechecks_the_commit_is_still_tip(tmp_path: Path) -> None:
    """打包完再看一眼；main 在打包期间往前走了一步，这一步就红。"""
    pending = run_step(tmp_path, "build", "still-latest", latest_sha="newer567", head_sha="older123")
    assert pending.returncode != 0
    assert "打包期间" in pending.stderr

    fine = run_step(tmp_path, "build", "still-latest")
    assert fine.returncode == 0, fine.stderr
    assert "继续发" in fine.stdout


@pytest.mark.skipif(BASH is None, reason="没装 bash，跳过发布源检查的行为测试")
@pytest.mark.parametrize("source", ["legacy", "unknown", ""])
def test_a_branch_based_pages_source_stops_the_deploy(tmp_path: Path, source: str) -> None:
    """发布源不是 GitHub Actions 时直接失败；那种模式下 Pages 发整个分支，清单管不住。"""
    result = run_step(tmp_path, "guard", "probe", build_type=source)

    assert result.returncode != 0
    assert "不是 GitHub Actions" in result.stderr


@pytest.mark.skipif(BASH is None, reason="没装 bash，跳过打包脚本的行为测试")
def test_packaging_ships_only_the_api_dir_and_the_root_page(tmp_path: Path) -> None:
    """照真仓库的样子摆一份文件，跑打包脚本，看上线清单里只剩该发的。"""
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "index.html").write_text("页面\n", encoding="utf-8")
    (tmp_path / "api" / "data.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "index.html").write_text("首页\n", encoding="utf-8")
    for decoy in NOT_SHIPPED:
        path = tmp_path / decoy
        if decoy.endswith(".toml"):
            path.write_text("[project]\n", encoding="utf-8")
        else:
            path.mkdir()
            (path / "keep.txt").write_text("源码\n", encoding="utf-8")

    result = run_step(tmp_path, "build", "pack")

    assert result.returncode == 0, result.stderr
    shipped = sorted(
        p.relative_to(tmp_path / "_site").as_posix()
        for p in (tmp_path / "_site").rglob("*")
        if p.is_file()
    )
    assert shipped == ["api/data.json", "api/index.html", "index.html"]


@pytest.mark.skipif(BASH is None, reason="没装 bash，跳过打包脚本的行为测试")
@pytest.mark.parametrize("missing", ["api/index.html", "api/data.json", "index.html"])
def test_packaging_fails_when_a_shipped_file_is_missing(tmp_path: Path, missing: str) -> None:
    """该发的东西少一件就直接失败，不拿半份站点上线。"""
    (tmp_path / "api").mkdir()
    for name in ("api/index.html", "api/data.json", "index.html"):
        (tmp_path / name).write_text("x\n", encoding="utf-8")
    (tmp_path / missing).unlink()

    result = run_step(tmp_path, "build", "pack")

    assert result.returncode != 0


@pytest.mark.skipif(BASH is None, reason="没装 bash，跳过符号链接的行为测试")
def test_packaging_refuses_a_symlink_inside_api(tmp_path: Path) -> None:
    """api/ 里塞个指向 tests/ 的链接时拒绝打包。

    不拦的话 cp -R 会顺过去，artifact 那边的 tar 带 --dereference，
    整个 tests/ 就跟着上网了。
    """
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "index.html").write_text("页面\n", encoding="utf-8")
    (tmp_path / "api" / "data.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "index.html").write_text("首页\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "secret.py").write_text("源码\n", encoding="utf-8")
    (tmp_path / "api" / "leak").symlink_to("../tests")

    result = run_step(tmp_path, "build", "pack")

    assert result.returncode != 0
    assert "符号链接" in result.stderr
    assert not (tmp_path / "_site").exists()
