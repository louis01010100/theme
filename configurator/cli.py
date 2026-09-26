"""Argument parsing, the run state machine, and exit codes."""

from __future__ import annotations

import os
import signal
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from configurator import (files, gnome, install_dir, nvim, palette,
                          ptyxis, tmux)
from configurator.files import CurrentState, Interrupted, Layout
from configurator.palette import InputError
from configurator.report import Status, TargetResult, emit, err, warn
from configurator.terminal_ansi import validate_ansi, validate_roles

REPO = Path(__file__).resolve().parent.parent
USAGE = ("usage: configure.py [all|gnome|ptyxis|tmux|nvim] [--dry-run] "
         "[--uninstall] [--set-default] [-h|--help]")
EXIT_OK, EXIT_USAGE, EXIT_INPUT, EXIT_APPLY = 0, 2, 3, 4
FLAGS = ("--dry-run", "--uninstall", "--set-default")
NOT_RUN = "earlier target failed"


class Target(Enum):
    GNOME = "gnome"
    PTYXIS = "ptyxis"
    TMUX = "tmux"
    NVIM = "nvim"


ORDER = (Target.GNOME, Target.PTYXIS, Target.TMUX, Target.NVIM)
TERMINALS = (Target.GNOME, Target.PTYXIS)
NAMES = ("all",) + tuple(t.value for t in ORDER)


class UsageError(Exception):
    """The command line violates REQ-CLI-1 or REQ-CLI-2."""


class ValidationFailed(Exception):
    """One or more REQ-PAL / REQ-MAP rules are violated."""

    def __init__(self, errors):
        super().__init__(f"{len(errors)} validation errors")
        self.errors = tuple(errors)


@dataclass(frozen=True)
class HelpRequest:
    """-h or --help was given."""


@dataclass(frozen=True)
class RunOptions:
    """The parsed command line."""

    targets: tuple
    dry_run: bool
    uninstall: bool
    set_default: bool

    @property
    def file_targets(self) -> tuple:
        return tuple(t.value for t in self.targets
                     if t not in TERMINALS)

    @property
    def is_all(self) -> bool:
        """The `all` target (named or by default): skip rule applies."""
        return self.targets == ORDER


@dataclass(frozen=True)
class Inputs:
    """Desired file trees, GNOME key values, Ptyxis file and keys."""

    trees: Mapping
    gnome_keys: tuple
    ptyxis: ptyxis.PtyxisDesired | None = None


@dataclass(frozen=True)
class Context:
    """Everything known after the read-only preparation states.

    skipped: terminals of `all` whose prerequisite is missing, with
    the missing item (REQ-CLI-4).
    """

    opts: RunOptions
    layout: Layout
    inputs: Inputs
    skipped: Mapping

    @property
    def ptx(self) -> ptyxis.PtyxisPaths:
        return ptyxis.paths(self.layout.data)

    def active(self, target: Target) -> bool:
        """Selected and not skipped."""
        return target in self.opts.targets and target not in self.skipped


@dataclass(frozen=True)
class FilePlan:
    """The current and desired version trees and per-target diffs."""

    current: CurrentState
    want: Mapping
    diffs: Mapping

    @property
    def changed(self) -> bool:
        return dict(self.want) != dict(self.current.tree)


@dataclass(frozen=True)
class LiveAction:
    """The tmux live action: reload, reset, or skip (with detail)."""

    kind: str
    detail: str


@dataclass(frozen=True)
class Outcome:
    """A planned REQ-CLI-5 status and its note."""

    status: Status
    note: str | None = None


@dataclass(frozen=True)
class RunReport:
    """The planned report lines of every selected target, in order."""

    results: tuple

    def result(self, target: str) -> TargetResult:
        return next(r for r in self.results if r.target == target)


@dataclass(frozen=True)
class Plan:
    """Per-target change sets of one run."""

    gnome: gnome.GnomePlan | None
    ptyxis: ptyxis.PtyxisPlan | None
    files: FilePlan | None
    live: LiveAction | None


def select(names) -> tuple:
    if len(names) > 1:
        raise UsageError("at most one target may be given")
    name = names[0] if names else "all"
    return ORDER if name == "all" else (Target(name),)


def check_flags(opts: RunOptions) -> None:
    if opts.set_default and not set(TERMINALS) & set(opts.targets):
        raise UsageError("--set-default needs the gnome, ptyxis or all "
                         "target")
    if opts.set_default and opts.uninstall:
        raise UsageError("--set-default and --uninstall are exclusive")


def parse(argv) -> RunOptions | HelpRequest:
    """REQ-CLI-1/2; raises UsageError."""
    if "-h" in argv or "--help" in argv:
        return HelpRequest()
    unknown = [a for a in argv if a not in NAMES and a not in FLAGS]
    if unknown:
        raise UsageError(f"unknown argument: {unknown[0]}")
    targets = select([a for a in argv if a in NAMES])
    opts = RunOptions(targets, "--dry-run" in argv,
                      "--uninstall" in argv, "--set-default" in argv)
    check_flags(opts)
    return opts


def validation_errors(raw, templates) -> list:
    """Every palette, mapping, template and source-tree error."""
    names = palette.palette_names(raw)
    return (palette.validate_palette(raw) + validate_ansi(names)
            + validate_roles(names) + ptyxis.validate_keys()
            + tmux.validate_roles(names)
            + tmux.validate_templates(templates)
            + nvim.validate_sources(REPO))


def render(opts: RunOptions, colours, templates) -> Inputs:
    """Desired trees of the selected file targets; GNOME keys."""
    trees = {}
    if "tmux" in opts.file_targets:
        trees["tmux"] = tmux.file_set(REPO, colours, templates)
    if "nvim" in opts.file_targets:
        trees["nvim"] = nvim.file_set(REPO, colours)
    keys, wanted = (), None
    if Target.GNOME in opts.targets:
        keys = gnome.desired_keys(colours)
    if Target.PTYXIS in opts.targets:
        wanted = ptyxis.desired(colours)
    return Inputs(trees, keys, wanted)


def load_inputs(opts: RunOptions) -> Inputs:
    """States load, validate, render (skipped by --uninstall)."""
    if opts.uninstall:
        return Inputs({}, ())
    raw = palette.read_toml(REPO / "palette.toml")
    templates = tmux.load_templates(REPO)
    errors = validation_errors(raw, templates)
    if errors:
        raise ValidationFailed(errors)
    return render(opts, palette.make_palette(raw), templates)


MISSING = {Target.GNOME: gnome.missing, Target.PTYXIS: ptyxis.missing}


def terminal_prereq(opts: RunOptions, target: Target,
                    layout) -> str | None:
    """REQ-GT-2 / REQ-PTX-2; the missing item when `all` skips it."""
    reason = MISSING[target]()
    if reason and not opts.is_all:
        raise InputError(f"{target.value}: {reason}")
    if not reason and target is Target.PTYXIS:
        ptyxis.check_owned(ptyxis.paths(layout.data))
    return reason


def check_prereqs(opts: RunOptions, layout: Layout) -> Mapping:
    """State prereq, in order; returns the skipped terminals."""
    skipped = {}
    for target in opts.targets:
        if target in TERMINALS:
            reason = terminal_prereq(opts, target, layout)
            if reason:
                skipped[target] = reason
        else:
            files.check_managed(layout)
    return MappingProxyType(skipped)


def prepare(opts: RunOptions) -> Context:
    """States environment, load, validate, render, prereq."""
    layout = install_dir.resolve(os.environ)
    inputs = load_inputs(opts)
    skipped = check_prereqs(opts, layout)
    return Context(opts, layout, inputs, skipped)


def collect_garbage(ctx: Context) -> None:
    """State gc: file-step leftovers and Ptyxis temporary files."""
    if ctx.opts.dry_run:
        return
    messages = ()
    if ctx.opts.file_targets:
        messages += files.gc(ctx.layout)
    if ctx.active(Target.PTYXIS):
        messages += ptyxis.gc_leftovers(ctx.ptx)
    for message in messages:
        warn(message)


def plan_gnome(ctx: Context):
    if not ctx.active(Target.GNOME):
        return None
    state = gnome.probe()
    if ctx.opts.uninstall:
        return gnome.plan_uninstall(state)
    return gnome.plan_install(ctx.inputs.gnome_keys, state,
                              ctx.opts.set_default)


def plan_ptyxis(ctx: Context):
    if not ctx.active(Target.PTYXIS):
        return None
    state = ptyxis.probe(ctx.ptx)
    if ctx.opts.uninstall:
        return ptyxis.plan_uninstall(state)
    return ptyxis.plan_install(ctx.inputs.ptyxis, state,
                               ctx.opts.set_default)


def plan_files(ctx: Context):
    selected = ctx.opts.file_targets
    if not selected:
        return None
    current = files.read_current(ctx.layout)
    want = files.desired_tree(current.tree, selected, ctx.inputs.trees,
                              ctx.opts.uninstall)
    diffs = {t: files.diff(current.tree, want, t) for t in selected}
    return FilePlan(current, want, diffs)


def plan_live(ctx: Context, file_plan):
    if file_plan is None or "tmux" not in file_plan.diffs:
        return None
    if not file_plan.diffs["tmux"].changed:
        return None
    server = tmux.probe_server()
    if not server.available:
        return LiveAction("skip", f"skip tmux reload ({server.reason})")
    if ctx.opts.uninstall:
        return LiveAction("reset", "reset tmux options")
    return LiveAction("reload", "reload tmux server")


def make_plan(ctx: Context) -> Plan:
    """States gc, probe, plan."""
    collect_garbage(ctx)
    file_plan = plan_files(ctx)
    return Plan(plan_gnome(ctx), plan_ptyxis(ctx), file_plan,
                plan_live(ctx, file_plan))


def outcome_status(opts, changed: bool, installed: bool) -> Outcome:
    """REQ-CLI-5 status and note of a planned target."""
    if opts.uninstall and not installed:
        return Outcome(Status.UNCHANGED, "not installed")
    if not changed:
        return Outcome(Status.UNCHANGED)
    if opts.uninstall:
        return Outcome(Status.WOULD_REMOVE if opts.dry_run
                       else Status.REMOVED)
    return Outcome(Status.WOULD_UPDATE if opts.dry_run
                   else Status.UPDATED)


def terminal_result(ctx: Context, plan: Plan, target) -> TargetResult:
    """A settings step's line, or its `skipped (not installed)` line."""
    if target in ctx.skipped:
        return TargetResult(target.value, Status.SKIPPED,
                            "not installed", (ctx.skipped[target],))
    step = plan.gnome if target is Target.GNOME else plan.ptyxis
    outcome = outcome_status(ctx.opts, bool(step.changes),
                             step.installed)
    return TargetResult(target.value, outcome.status, outcome.note,
                        step.details)


def switch_detail(file_plan: FilePlan, target: str) -> tuple:
    """`switch`/`remove install directory` under the first changed."""
    changed = [t for t, d in file_plan.diffs.items() if d.changed]
    if not changed or changed[0] != target:
        return ()
    if file_plan.want:
        return ("switch install directory",)
    return ("remove install directory",)


def file_result(ctx: Context, plan: Plan, target: str) -> TargetResult:
    change = plan.files.diffs[target]
    outcome = outcome_status(ctx.opts, change.changed,
                             bool(change.removes))
    details = tuple(f"write {r}" for r in change.writes)
    details += tuple(f"remove {r}" for r in change.removes)
    details += switch_detail(plan.files, target)
    if target == "tmux" and plan.live:
        details += (plan.live.detail,)
    return TargetResult(target, outcome.status, outcome.note, details)


def planned_results(ctx: Context, plan: Plan) -> RunReport:
    """The report of a run in which every step succeeds."""
    results = []
    for target in ctx.opts.targets:
        if target in TERMINALS:
            results.append(terminal_result(ctx, plan, target))
        else:
            results.append(file_result(ctx, plan, target.value))
    return RunReport(tuple(results))


def report_dry(ctx: Context, plan: Plan) -> int:
    for result in planned_results(ctx, plan).results:
        emit(result)
    return EXIT_OK


@contextmanager
def interrupts_raised():
    """SIGINT/SIGTERM raise Interrupted while applying."""
    def handler(_signum, _frame):
        raise Interrupted()

    saved = {s: signal.signal(s, handler)
             for s in (signal.SIGINT, signal.SIGTERM)}
    try:
        yield
    finally:
        for number, previous in saved.items():
            signal.signal(number, previous)


def terminal_failed(ctx: Context, planned: RunReport, target,
                    reason: str) -> int:
    """A settings step failed: later targets are not run.

    A later terminal skipped in prereq keeps its skipped line.
    """
    emit(TargetResult(target.value, Status.FAILED, reason))
    later = ctx.opts.targets[ctx.opts.targets.index(target) + 1:]
    for other in later:
        if other in ctx.skipped:
            emit(planned.result(other.value))
        else:
            emit(TargetResult(other.value, Status.NOT_RUN, NOT_RUN))
    return EXIT_APPLY


def run_file_step(ctx: Context, plan: Plan):
    if not plan.files.changed:
        return files.StepOutcome(False, None, (), None)
    outcome = files.apply_tree(ctx.layout, plan.files.current,
                               plan.files.want)
    for message in outcome.warnings:
        warn(message)
    return outcome


def files_failed(ctx, plan, planned, reason) -> int:
    """A file-step failure before the switch (REQ-INST-5 step 5)."""
    for target in ctx.opts.file_targets:
        if plan.files.diffs[target].changed:
            emit(TargetResult(target, Status.FAILED, reason))
        else:
            emit(planned.result(target))
    return EXIT_APPLY


def run_live(ctx: Context, plan: Plan, outcome) -> str | None:
    """REQ-LIVE-3 / REQ-UNI-2; returns a failure note or None."""
    if plan.live is None or plan.live.kind == "skip":
        return None
    if outcome.error:
        return "interrupted"
    try:
        if plan.live.kind == "reload":
            return tmux.reload(ctx.layout.install)
        return tmux.reset()
    except Interrupted:
        return "interrupted"


def finish_files(ctx: Context, plan: Plan, planned: RunReport) -> int:
    """The file step, the tmux live action, and their lines."""
    outcome = run_file_step(ctx, plan)
    if outcome.error and not outcome.switched:
        return files_failed(ctx, plan, planned, outcome.error)
    live_error = run_live(ctx, plan, outcome)
    for target in ctx.opts.file_targets:
        if target == "tmux" and live_error:
            emit(TargetResult("tmux", Status.FAILED, live_error))
        else:
            emit(planned.result(target))
    return EXIT_APPLY if outcome.error or live_error else EXIT_OK


def apply_terminal(ctx: Context, plan: Plan, target) -> str | None:
    """One settings step; a failure reason or None."""
    if not ctx.active(target):
        return None
    if target is Target.GNOME:
        return gnome.apply(plan.gnome)
    return ptyxis.apply(plan.ptyxis, ctx.ptx)


def apply_steps(ctx: Context, plan: Plan) -> int:
    """State apply, in REQ-CLI-4 order."""
    planned = planned_results(ctx, plan)
    for target in TERMINALS:
        failure = apply_terminal(ctx, plan, target)
        if failure:
            return terminal_failed(ctx, planned, target, failure)
        if target in ctx.opts.targets:
            emit(planned.result(target.value))
    if plan.files is None:
        return EXIT_OK
    return finish_files(ctx, plan, planned)


def apply(ctx: Context, plan: Plan) -> int:
    with interrupts_raised():
        return apply_steps(ctx, plan)


def usage_error(exc: UsageError) -> int:
    err(str(exc))
    print(USAGE, file=sys.stderr)
    return EXIT_USAGE


def input_failure(exc: Exception) -> int:
    if isinstance(exc, ValidationFailed):
        for error in exc.errors:
            print(error, file=sys.stderr)
    else:
        err(str(exc))
    return EXIT_INPUT


def main(argv) -> int:
    """parse_args -> environment ... -> report_dry | apply."""
    try:
        opts = parse(argv)
    except UsageError as exc:
        return usage_error(exc)
    if isinstance(opts, HelpRequest):
        print(USAGE)
        return EXIT_OK
    try:
        ctx = prepare(opts)
        plan = make_plan(ctx)
    except (InputError, ValidationFailed) as exc:
        return input_failure(exc)
    if opts.dry_run:
        return report_dry(ctx, plan)
    return apply(ctx, plan)
