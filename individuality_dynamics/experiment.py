"""Coupled-oscillator individuality dynamics experiment.

The experiment formalizes a narrow, testable claim:

    Individuation can be operationalized as a transition in causal closure,
    where internal dynamics become more self-maintaining than externally
    entrained while preserving nontrivial perturbational complexity.

This is a mathematical research scaffold. It does not claim to prove
consciousness, resurrection, clinical age reversal, or mind uploading.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import math
from typing import Iterable, Sequence

import numpy as np


@dataclass(frozen=True)
class ExperimentConfig:
    """Configuration for the oscillator individuality sweep."""

    n_nodes: int = 50
    n_internal: int = 20
    n_rogue: int = 5
    lambda_min: float = 0.1
    lambda_max: float = 10.0
    lambda_steps: int = 28
    seeds_per_lambda: int = 5
    external_coupling: float = 0.42
    rogue_multiplier: float = 3.25
    rogue_host_suppression: float = 0.25
    dt: float = 0.05
    n_steps: int = 1000
    burn_in: int = 350
    perturbation_size: int = 4
    perturbation_amplitude: float = 0.55
    perturbation_steps: int = 180
    seed: int = 173
    output_dir: str = "results/individuality_dynamics"


@dataclass(frozen=True)
class SeedMetrics:
    """Metrics from one simulated seed at one lambda value."""

    lambda_ratio: float
    seed_index: int
    lz_internal: float
    mi_internal_external: float
    order_internal: float
    metastability_internal: float
    perturbational_complexity: float
    perturbation_spread: float
    closure_score: float
    blanket_ratio: float
    lz_rogue: float | None = None
    mi_rogue_host: float | None = None
    order_rogue: float | None = None
    rogue_closure_score: float | None = None
    rogue_blanket_ratio: float | None = None


@dataclass(frozen=True)
class LambdaSummary:
    """Mean and uncertainty summary for one lambda value."""

    lambda_ratio: float
    n_seeds: int
    mean: dict[str, float]
    std: dict[str, float]
    ci95: dict[str, float]


def lempel_ziv_complexity(binary_sequence: Iterable[int]) -> float:
    """Return normalized Lempel-Ziv complexity for a binary sequence."""

    bits = "".join(str(int(x)) for x in binary_sequence)
    n = len(bits)
    if n == 0:
        return 0.0

    phrases: set[str] = set()
    i = 0
    while i < n:
        j = i + 1
        while j <= n and bits[i:j] in phrases:
            j += 1
        phrases.add(bits[i:j])
        i = j

    upper_scale = n / max(math.log2(n), 1.0)
    return float(min(len(phrases) / upper_scale, 1.0))


def discretize_timeseries(values: np.ndarray) -> np.ndarray:
    """Binarize a time-series matrix using per-node medians."""

    medians = np.median(values, axis=0, keepdims=True)
    return (values > medians).astype(np.int8).ravel()


def mutual_information(x: np.ndarray, y: np.ndarray, bins: int = 16) -> float:
    """Estimate normalized mutual information between two scalar signals."""

    hist_xy, _, _ = np.histogram2d(x, y, bins=bins)
    total = float(np.sum(hist_xy))
    if total <= 0.0:
        return 0.0

    p_xy = hist_xy / total
    p_x = np.sum(p_xy, axis=1)
    p_y = np.sum(p_xy, axis=0)
    nz = p_xy > 0
    px_py = p_x[:, None] * p_y[None, :]
    mi = float(np.sum(p_xy[nz] * np.log2(p_xy[nz] / px_py[nz])))

    h_x = -float(np.sum(p_x[p_x > 0] * np.log2(p_x[p_x > 0])))
    h_y = -float(np.sum(p_y[p_y > 0] * np.log2(p_y[p_y > 0])))
    return float(mi / max(min(h_x, h_y), 1e-12))


def kuramoto_order(phases: np.ndarray) -> np.ndarray:
    """Kuramoto order parameter for each recorded time step."""

    return np.abs(np.mean(np.exp(1j * phases), axis=1))


def summarize_order(phases: np.ndarray) -> tuple[float, float]:
    """Return mean order and metastability from phase traces."""

    order = kuramoto_order(phases)
    return float(np.mean(order)), float(np.std(order))


def build_coupling_matrix(
    config: ExperimentConfig,
    lambda_ratio: float,
    rng: np.random.Generator,
    include_rogue_cluster: bool,
) -> np.ndarray:
    """Construct a block coupling matrix for internal/environment dynamics."""

    n = config.n_nodes
    n_internal = config.n_internal
    matrix = np.zeros((n, n), dtype=float)

    internal_strength = lambda_ratio * config.external_coupling
    external_strength = config.external_coupling

    internal_noise = rng.uniform(0.85, 1.15, size=(n_internal, n_internal))
    matrix[:n_internal, :n_internal] = internal_strength * internal_noise

    env_slice = slice(n_internal, n)
    env_noise = rng.uniform(0.75, 1.05, size=(n - n_internal, n - n_internal))
    matrix[env_slice, env_slice] = 0.55 * config.external_coupling * env_noise

    cross_noise = rng.uniform(0.75, 1.25, size=(n_internal, n - n_internal))
    matrix[:n_internal, env_slice] = external_strength * cross_noise
    matrix[env_slice, :n_internal] = external_strength * cross_noise.T

    if include_rogue_cluster:
        rogue = slice(0, config.n_rogue)
        host = slice(config.n_rogue, n_internal)
        matrix[rogue, rogue] *= config.rogue_multiplier
        matrix[rogue, host] *= config.rogue_host_suppression
        matrix[host, rogue] *= config.rogue_host_suppression

    np.fill_diagonal(matrix, 0.0)
    return matrix / max(n - 1, 1)


def coupling_ratio(
    coupling: np.ndarray,
    source: Sequence[int],
    environment: Sequence[int],
) -> float:
    """Compute internal/external coupling ratio for a candidate blanket."""

    source_idx = np.asarray(source)
    env_idx = np.asarray(environment)
    internal = coupling[np.ix_(source_idx, source_idx)]
    external = coupling[np.ix_(source_idx, env_idx)]

    internal_mean = float(np.mean(internal[internal > 0.0])) if np.any(internal > 0.0) else 0.0
    external_mean = float(np.mean(external[external > 0.0])) if np.any(external > 0.0) else 0.0
    return internal_mean / max(external_mean, 1e-12)


def _phase_step(phases: np.ndarray, natural_freq: np.ndarray, coupling: np.ndarray, dt: float) -> np.ndarray:
    phase_delta = phases[None, :] - phases[:, None]
    coupling_drive = np.sum(coupling * np.sin(phase_delta), axis=1)
    return (phases + dt * (natural_freq + coupling_drive)) % (2.0 * np.pi)


def simulate_phases(
    coupling: np.ndarray,
    config: ExperimentConfig,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Run Euler-integrated Kuramoto dynamics and return traces plus state."""

    n = config.n_nodes
    phases = rng.uniform(0.0, 2.0 * np.pi, size=n)
    natural_freq = rng.normal(loc=1.0, scale=0.08, size=n)
    recorded: list[np.ndarray] = []

    for step in range(config.n_steps):
        phases = _phase_step(phases, natural_freq, coupling, config.dt)
        if step >= config.burn_in:
            recorded.append(phases.copy())

    return np.asarray(recorded), phases.copy(), natural_freq


def perturbational_response(
    baseline_state: np.ndarray,
    natural_freq: np.ndarray,
    coupling: np.ndarray,
    config: ExperimentConfig,
) -> tuple[float, float]:
    """Estimate PCI-like response complexity after a standardized perturbation."""

    control = baseline_state.copy()
    perturbed = baseline_state.copy()
    perturbed[: config.perturbation_size] += config.perturbation_amplitude

    response: list[np.ndarray] = []
    for _ in range(config.perturbation_steps):
        control = _phase_step(control, natural_freq, coupling, config.dt)
        perturbed = _phase_step(perturbed, natural_freq, coupling, config.dt)
        delta = np.angle(np.exp(1j * (perturbed - control)))
        response.append(np.abs(delta))

    response_matrix = np.asarray(response)
    threshold = float(np.percentile(response_matrix, 65.0))
    active = (response_matrix > threshold).astype(np.int8)
    complexity = lempel_ziv_complexity(active.ravel())
    spread = float(np.mean(np.any(active, axis=0)))
    return complexity, spread


def closure_score(
    lz: float,
    mi: float,
    order: float,
    metastability: float,
    perturbation_complexity: float,
    perturbation_spread: float,
) -> float:
    """Composite operational closure score.

    Rich individuality is not pure synchrony. The score rewards internal
    complexity, perturbational richness, response spread, and metastability,
    while penalizing external entrainment and excessive lockstep order.
    """

    rigidity_penalty = max(order - 0.92, 0.0)
    score = (
        0.36 * lz
        + 0.28 * perturbation_complexity
        + 0.14 * perturbation_spread
        + 0.12 * metastability
        - 0.32 * mi
        - 0.18 * rigidity_penalty
    )
    return float(score)


def evaluate_seed(
    config: ExperimentConfig,
    lambda_ratio: float,
    seed_index: int,
    include_rogue_cluster: bool,
) -> SeedMetrics:
    """Simulate and score one lambda/seed condition."""

    seed_offset = int(lambda_ratio * 10000) + seed_index * 10_003
    if include_rogue_cluster:
        seed_offset += 700_000
    rng = np.random.default_rng(config.seed + seed_offset)

    coupling = build_coupling_matrix(config, lambda_ratio, rng, include_rogue_cluster)
    phases, final_state, natural_freq = simulate_phases(coupling, config, rng)

    internal_idx = list(range(config.n_internal))
    external_idx = list(range(config.n_internal, config.n_nodes))
    internal = phases[:, internal_idx]
    external = phases[:, external_idx]

    internal_signal = np.mean(np.sin(internal), axis=1)
    external_signal = np.mean(np.sin(external), axis=1)
    lz_internal = lempel_ziv_complexity(discretize_timeseries(np.sin(internal)))
    mi_ie = mutual_information(internal_signal, external_signal)
    order_internal, metastability_internal = summarize_order(internal)
    pci_like, spread = perturbational_response(final_state, natural_freq, coupling, config)
    base_score = closure_score(lz_internal, mi_ie, order_internal, metastability_internal, pci_like, spread)

    if not include_rogue_cluster:
        return SeedMetrics(
            lambda_ratio=lambda_ratio,
            seed_index=seed_index,
            lz_internal=lz_internal,
            mi_internal_external=mi_ie,
            order_internal=order_internal,
            metastability_internal=metastability_internal,
            perturbational_complexity=pci_like,
            perturbation_spread=spread,
            closure_score=base_score,
            blanket_ratio=coupling_ratio(coupling, internal_idx, external_idx),
        )

    rogue_idx = list(range(config.n_rogue))
    host_idx = list(range(config.n_rogue, config.n_internal))
    rogue = phases[:, rogue_idx]
    host = phases[:, host_idx]
    rogue_signal = np.mean(np.sin(rogue), axis=1)
    host_signal = np.mean(np.sin(host), axis=1)
    lz_rogue = lempel_ziv_complexity(discretize_timeseries(np.sin(rogue)))
    mi_rh = mutual_information(rogue_signal, host_signal)
    order_rogue, metastability_rogue = summarize_order(rogue)
    rogue_pci, rogue_spread = perturbational_response(final_state, natural_freq, coupling, config)
    rogue_score = closure_score(lz_rogue, mi_rh, order_rogue, metastability_rogue, rogue_pci, rogue_spread)

    return SeedMetrics(
        lambda_ratio=lambda_ratio,
        seed_index=seed_index,
        lz_internal=lz_internal,
        mi_internal_external=mi_ie,
        order_internal=order_internal,
        metastability_internal=metastability_internal,
        perturbational_complexity=pci_like,
        perturbation_spread=spread,
        closure_score=base_score,
        blanket_ratio=coupling_ratio(coupling, internal_idx, external_idx),
        lz_rogue=lz_rogue,
        mi_rogue_host=mi_rh,
        order_rogue=order_rogue,
        rogue_closure_score=rogue_score,
        rogue_blanket_ratio=coupling_ratio(coupling, rogue_idx, host_idx + external_idx),
    )


def summarize_metrics(points: list[SeedMetrics]) -> LambdaSummary:
    """Aggregate seed metrics for one lambda value."""

    if not points:
        raise ValueError("cannot summarize an empty seed set")

    metric_names = [
        "lz_internal",
        "mi_internal_external",
        "order_internal",
        "metastability_internal",
        "perturbational_complexity",
        "perturbation_spread",
        "closure_score",
        "blanket_ratio",
        "lz_rogue",
        "mi_rogue_host",
        "order_rogue",
        "rogue_closure_score",
        "rogue_blanket_ratio",
    ]
    mean: dict[str, float] = {}
    std: dict[str, float] = {}
    ci95: dict[str, float] = {}

    for name in metric_names:
        values = np.asarray([getattr(point, name) for point in points if getattr(point, name) is not None], dtype=float)
        if values.size == 0:
            continue
        mean[name] = float(np.mean(values))
        std[name] = float(np.std(values, ddof=1)) if values.size > 1 else 0.0
        ci95[name] = float(1.96 * std[name] / math.sqrt(values.size)) if values.size > 1 else 0.0

    return LambdaSummary(
        lambda_ratio=points[0].lambda_ratio,
        n_seeds=len(points),
        mean=mean,
        std=std,
        ci95=ci95,
    )


def infer_transition(summaries: list[LambdaSummary], metric: str = "closure_score") -> float:
    """Estimate the lambda where the closure metric has steepest positive change."""

    lambdas = np.asarray([summary.lambda_ratio for summary in summaries])
    values = np.asarray([summary.mean[metric] for summary in summaries])
    gradient = np.gradient(values, np.log(lambdas))
    return float(lambdas[int(np.argmax(gradient))])


def run_experiment(config: ExperimentConfig) -> dict[str, object]:
    """Run baseline and rogue-cluster sweeps with multi-seed summaries."""

    lambdas = np.geomspace(config.lambda_min, config.lambda_max, config.lambda_steps)
    baseline_raw: list[SeedMetrics] = []
    rogue_raw: list[SeedMetrics] = []
    baseline_summary: list[LambdaSummary] = []
    rogue_summary: list[LambdaSummary] = []

    for lambda_ratio in lambdas:
        baseline_points = [
            evaluate_seed(config, float(lambda_ratio), seed_index, include_rogue_cluster=False)
            for seed_index in range(config.seeds_per_lambda)
        ]
        rogue_points = [
            evaluate_seed(config, float(lambda_ratio), seed_index, include_rogue_cluster=True)
            for seed_index in range(config.seeds_per_lambda)
        ]
        baseline_raw.extend(baseline_points)
        rogue_raw.extend(rogue_points)
        baseline_summary.append(summarize_metrics(baseline_points))
        rogue_summary.append(summarize_metrics(rogue_points))

    baseline_transition = infer_transition(baseline_summary, "closure_score")
    rogue_transition = infer_transition(rogue_summary, "rogue_closure_score")

    return {
        "schema": "individuality-dynamics/v1",
        "interpretation": {
            "central_claim": "Operational individuality is modeled as rising causal closure: internal complexity and perturbational response richness exceed external entrainment.",
            "guardrail": "This is a computational hypothesis generator, not proof of consciousness, clinical age reversal, resurrection, or mind uploading.",
            "lambda_definition": "lambda = W_internal / W_external",
            "transition_rule": "lambda* is estimated at the steepest positive gradient of the mean closure score over log(lambda).",
        },
        "config": asdict(config),
        "baseline_transition_lambda": baseline_transition,
        "rogue_transition_lambda": rogue_transition,
        "baseline_summary": [asdict(summary) for summary in baseline_summary],
        "rogue_summary": [asdict(summary) for summary in rogue_summary],
        "baseline_raw": [asdict(point) for point in baseline_raw],
        "rogue_raw": [asdict(point) for point in rogue_raw],
    }


def _polyline(points: list[tuple[float, float]], color: str, width: float = 2.0) -> str:
    encoded = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return f'<polyline points="{encoded}" fill="none" stroke="{color}" stroke-width="{width}" />'


def _scale_series(
    xs: np.ndarray,
    ys: np.ndarray,
    left: float,
    top: float,
    width: float,
    height: float,
    y_min: float,
    y_max: float,
) -> list[tuple[float, float]]:
    log_x = np.log10(xs)
    x_min = float(np.min(log_x))
    x_max = float(np.max(log_x))
    y_span = max(y_max - y_min, 1e-12)
    return [
        (
            left + width * (float(x) - x_min) / max(x_max - x_min, 1e-12),
            top + height - height * (float(y) - y_min) / y_span,
        )
        for x, y in zip(log_x, ys)
    ]


def _panel(
    title: str,
    xs: np.ndarray,
    series: list[tuple[str, np.ndarray, str]],
    left: float,
    top: float,
    transition: float | None = None,
) -> str:
    width = 500.0
    height = 250.0
    all_y = np.concatenate([values for _, values, _ in series])
    y_min = float(np.min(all_y))
    y_max = float(np.max(all_y))
    padding = max((y_max - y_min) * 0.08, 0.05)
    y_min -= padding
    y_max += padding

    lines = [
        f'<rect x="{left}" y="{top}" width="{width}" height="{height}" fill="#fbfaf6" stroke="#1d252c" stroke-width="1" />',
        f'<text x="{left + 14}" y="{top + 24}" font-size="17" font-family="Georgia" fill="#1d252c">{title}</text>',
        f'<text x="{left + 12}" y="{top + height - 10}" font-size="11" font-family="Consolas" fill="#52616b">lambda: {xs[0]:.2f} to {xs[-1]:.2f}</text>',
    ]

    if transition is not None:
        transition_points = _scale_series(
            np.asarray([transition, transition]),
            np.asarray([y_min, y_max]),
            left,
            top,
            width,
            height,
            y_min,
            y_max,
        )
        lines.append(_polyline(transition_points, "#111111", 1.4))

    for index, (label, values, color) in enumerate(series):
        scaled = _scale_series(xs, values, left, top, width, height, y_min, y_max)
        lines.append(_polyline(scaled, color))
        legend_y = top + 48 + index * 18
        lines.append(f'<line x1="{left + 318}" y1="{legend_y - 4}" x2="{left + 342}" y2="{legend_y - 4}" stroke="{color}" stroke-width="3" />')
        lines.append(f'<text x="{left + 350}" y="{legend_y}" font-size="12" font-family="Consolas" fill="#1d252c">{label}</text>')

    return "\n".join(lines)


def write_svg_report(results: dict[str, object], output_dir: Path) -> Path:
    """Write a dependency-free SVG summary plot."""

    baseline = results["baseline_summary"]
    rogue = results["rogue_summary"]
    lambdas = np.asarray([point["lambda_ratio"] for point in baseline])

    closure = np.asarray([point["mean"]["closure_score"] for point in baseline])
    rogue_closure = np.asarray([point["mean"]["rogue_closure_score"] for point in rogue])

    panels = [
        _panel(
            "Baseline Individuation",
            lambdas,
            [
                ("Internal LZ", np.asarray([p["mean"]["lz_internal"] for p in baseline]), "#0f766e"),
                ("Internal-external MI", np.asarray([p["mean"]["mi_internal_external"] for p in baseline]), "#b45309"),
            ],
            40,
            76,
            float(results["baseline_transition_lambda"]),
        ),
        _panel(
            "PCI-like Perturbational Response",
            lambdas,
            [
                ("Perturb complexity", np.asarray([p["mean"]["perturbational_complexity"] for p in baseline]), "#2563eb"),
                ("Response spread", np.asarray([p["mean"]["perturbation_spread"] for p in baseline]), "#15803d"),
            ],
            600,
            76,
        ),
        _panel(
            "Cancer Analogue: Rogue Closure",
            lambdas,
            [
                ("Rogue closure", rogue_closure, "#dc2626"),
                ("Rogue-host MI", np.asarray([p["mean"]["mi_rogue_host"] for p in rogue]), "#7c3aed"),
            ],
            40,
            386,
            float(results["rogue_transition_lambda"]),
        ),
        _panel(
            "Operational Closure Scores",
            lambdas,
            [
                ("Host closure", closure, "#0f172a"),
                ("Rogue closure", rogue_closure, "#be123c"),
            ],
            600,
            386,
        ),
    ]

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1140" height="710" viewBox="0 0 1140 710">
<rect width="1140" height="710" fill="#f3efe4" />
<text x="40" y="38" font-size="24" font-family="Georgia" fill="#1d252c">Individuality Dynamics: Causal Closure as Coupling-Ratio Transition</text>
<text x="40" y="60" font-size="13" font-family="Consolas" fill="#52616b">Multi-seed Kuramoto scaffold with LZ, MI, metastability, and PCI-like perturbational response metrics.</text>
{chr(10).join(panels)}
</svg>
"""
    path = output_dir / "individuality_phase_transition.svg"
    path.write_text(svg, encoding="utf-8")
    return path


def save_results(results: dict[str, object], output_dir: str | Path) -> tuple[Path, Path]:
    """Persist JSON and SVG reports."""

    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    report_path = directory / "individuality_report.json"
    report_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    plot_path = write_svg_report(results, directory)
    return report_path, plot_path


def main() -> None:
    config = ExperimentConfig()
    results = run_experiment(config)
    report_path, plot_path = save_results(results, config.output_dir)

    print("Individuality dynamics experiment complete")
    print(f"Seeds per lambda: {config.seeds_per_lambda}")
    print(f"Baseline transition lambda*: {results['baseline_transition_lambda']:.3f}")
    print(f"Rogue transition lambda*: {results['rogue_transition_lambda']:.3f}")
    print(f"Report: {report_path}")
    print(f"Plot: {plot_path}")


if __name__ == "__main__":
    main()
