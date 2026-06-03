"""Unit tests for the individuality dynamics research scaffold."""

import unittest

import numpy as np

from individuality_dynamics.experiment import (
    ExperimentConfig,
    build_coupling_matrix,
    coupling_ratio,
    lempel_ziv_complexity,
    run_experiment,
)


class TestIndividualityDynamics(unittest.TestCase):
    def test_lz_complexity_bounds(self):
        periodic = [0, 1] * 32
        varied = np.random.default_rng(7).integers(0, 2, size=64)

        self.assertGreaterEqual(lempel_ziv_complexity(periodic), 0.0)
        self.assertLessEqual(lempel_ziv_complexity(periodic), 1.0)
        self.assertGreaterEqual(lempel_ziv_complexity(varied), lempel_ziv_complexity(periodic))

    def test_coupling_ratio_tracks_lambda(self):
        config = ExperimentConfig(n_steps=40, burn_in=10)
        rng = np.random.default_rng(11)
        low = build_coupling_matrix(config, 0.2, rng, False)
        rng = np.random.default_rng(11)
        high = build_coupling_matrix(config, 4.0, rng, False)

        internal = list(range(config.n_internal))
        external = list(range(config.n_internal, config.n_nodes))

        self.assertLess(coupling_ratio(low, internal, external), coupling_ratio(high, internal, external))

    def test_small_experiment_produces_transitions_and_summaries(self):
        config = ExperimentConfig(
            n_nodes=18,
            n_internal=8,
            n_rogue=3,
            lambda_steps=5,
            seeds_per_lambda=2,
            n_steps=90,
            burn_in=30,
            perturbation_steps=30,
            perturbation_size=2,
        )
        results = run_experiment(config)

        self.assertEqual(results["schema"], "individuality-dynamics/v1")
        self.assertEqual(len(results["baseline_summary"]), config.lambda_steps)
        self.assertEqual(len(results["rogue_summary"]), config.lambda_steps)
        self.assertGreaterEqual(results["baseline_transition_lambda"], config.lambda_min)
        self.assertLessEqual(results["baseline_transition_lambda"], config.lambda_max)
        self.assertIn("closure_score", results["baseline_summary"][0]["mean"])
        self.assertIn("rogue_closure_score", results["rogue_summary"][0]["mean"])


if __name__ == "__main__":
    unittest.main()
