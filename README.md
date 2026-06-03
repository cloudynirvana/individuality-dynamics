# Individuality Dynamics

This repository implements a compact computational experiment for one precise idea:

```text
Individuality can be operationalized as causal closure:
internal dynamics become more self-maintaining than externally entrained
while preserving nontrivial perturbational complexity.
```

The model is a research scaffold, not a proof of consciousness, resurrection, clinical age reversal, or mind uploading. Its value is that it turns a large philosophical claim into measurable curves.

## What It Builds

- A coupled Kuramoto oscillator system with internal and environmental nodes.
- A sweep over `lambda = W_internal / W_external`.
- Multi-seed summary statistics and confidence intervals.
- Lempel-Ziv internal complexity.
- Internal-external mutual information.
- Kuramoto order and metastability.
- PCI-like perturbational response complexity.
- A rogue cancer-analogue subcluster that can form unauthorized nested closure.
- JSON and SVG outputs for review.

## Run

```powershell
python individuality_experiment.py
```

In Codex desktop, the bundled runtime can be used directly:

```powershell
C:\Users\9k\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe individuality_experiment.py
```

Outputs:

```text
results/individuality_dynamics/individuality_report.json
results/individuality_dynamics/individuality_phase_transition.svg
```

Latest verified default run:

```text
Seeds per lambda: 5
Baseline transition lambda*: 0.198
Rogue transition lambda*: 0.278
```

## Test

The tests use the Python standard library `unittest` plus `numpy`.

```powershell
python -m unittest discover -s tests
```

## Interpretation

The main transition estimate is `lambda*`, the point where the mean closure score changes most sharply over log-scaled `lambda`.

```text
Closure = 0.36*LZ_internal
        + 0.28*perturbational_complexity
        + 0.14*perturbation_spread
        + 0.12*metastability
        - 0.32*MI_internal_external
        - 0.18*rigidity_penalty
```

The score intentionally penalizes both external entrainment and overly rigid synchrony. A viable individuality signature should not be mere lockstep order; it should preserve rich response capacity.

## Cancer Analogue

The rogue cluster is a small internal subsystem with elevated self-coupling and reduced host coupling. It models cancer only as an abstract dynamical analogy:

```text
cancer-like pathology = local closure becoming autonomous against the host attractor
```

This is not a biological tumor simulator.

## Guardrail

Use this repository as a hypothesis generator:

```text
bold model, narrow claim, measurable output, honest uncertainty
```
