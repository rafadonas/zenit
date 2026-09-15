import pytest

from zenit_geospatial.ground_truth_agreement import (
    bland_altman,
    cluster_bootstrap,
    cohen_kappa,
    height_class,
    icc_2_1,
    krippendorff_alpha_nominal,
    threshold_agreement,
    weighted_kappa,
)


def test_cohen_kappa_matches_hand_calculation() -> None:
    pairs = [("a", "a"), ("b", "b"), ("c", "c"), ("a", "b")]

    # po = 0.75, pe = 0.3125
    assert cohen_kappa(pairs) == pytest.approx(0.4375 / 0.6875)


def test_cohen_kappa_textbook_two_by_two_table() -> None:
    pairs = [("y", "y")] * 20 + [("y", "n")] * 5 + [("n", "y")] * 10 + [("n", "n")] * 15

    assert cohen_kappa(pairs) == pytest.approx(0.4)


def test_cohen_kappa_is_undefined_without_label_variation() -> None:
    assert cohen_kappa([("tree", "tree"), ("tree", "tree")]) is None
    assert cohen_kappa([]) is None


def test_quadratic_weighted_kappa_matches_hand_calculation() -> None:
    pairs = [("N1", "N1"), ("N2", "N2"), ("N3", "N3"), ("N1", "N2")]

    assert weighted_kappa(pairs, ["N1", "N2", "N3"]) == pytest.approx(0.8)


def test_weighted_kappa_penalizes_distant_disagreement_more() -> None:
    base = [("N1", "N1"), ("N2", "N2"), ("N3", "N3"), ("N2", "N2")]
    near = [*base, ("N1", "N2")]
    far = [*base, ("N1", "N3")]
    scale = ["N1", "N2", "N3"]

    assert weighted_kappa(near, scale) > weighted_kappa(far, scale)


def test_weighted_kappa_rejects_labels_outside_scale() -> None:
    with pytest.raises(ValueError, match="outside the ordinal scale"):
        weighted_kappa([("N1", "N4")], ["N1", "N2", "N3"])


def test_krippendorff_alpha_nominal_reference_example_with_missing_values() -> None:
    # Krippendorff (2011), "Computing Krippendorff's Alpha-Reliability", nominal example.
    observers = [
        [1, 2, 3, 3, 2, 1, 4, 1, 2, None, None, None],
        [1, 2, 3, 3, 2, 2, 4, 1, 2, 5, None, 3],
        [None, 3, 3, 3, 2, 3, 4, 2, 2, 5, 1, None],
        [1, 2, 3, 3, 2, 4, 4, 1, 2, 5, 1, None],
    ]
    units = [list(unit) for unit in zip(*observers, strict=True)]

    assert krippendorff_alpha_nominal(units) == pytest.approx(0.743, abs=0.001)


def test_krippendorff_alpha_is_undefined_without_pairable_values() -> None:
    assert krippendorff_alpha_nominal([["tree", None], [None, "shrub"]]) is None


def test_icc_2_1_matches_shrout_fleiss_reference() -> None:
    ratings = [
        [9, 2, 5, 8],
        [6, 1, 3, 2],
        [8, 4, 6, 8],
        [7, 1, 2, 6],
        [10, 5, 6, 9],
        [6, 2, 4, 7],
    ]

    assert icc_2_1(ratings) == pytest.approx(0.29, abs=0.005)


def test_icc_requires_complete_matrix() -> None:
    with pytest.raises(ValueError, match="complete"):
        icc_2_1([[1, 2], [3]])
    assert icc_2_1([[1, 2]]) is None


def test_bland_altman_bias_and_limits() -> None:
    result = bland_altman([(12, 10), (20, 20), (31, 29), (8, 10)])

    assert result is not None
    assert result.count == 4
    assert result.bias == pytest.approx(0.5)
    assert result.sd_difference == pytest.approx(1.9148542)
    assert result.lower_limit == pytest.approx(0.5 - 1.96 * 1.9148542)
    assert result.upper_limit == pytest.approx(0.5 + 1.96 * 1.9148542)


def test_threshold_agreement_uses_strict_exceedance() -> None:
    pairs = [(10, 11), (30, 30), (29, 31), (5, 6)]

    assert threshold_agreement(pairs) == {10.0: 0.75, 30.0: 0.75}
    assert threshold_agreement([]) == {10.0: None, 30.0: None}


def test_height_class_boundaries_follow_historical_classes() -> None:
    assert [height_class(value) for value in (9.9, 10, 30, 30.1)] == ["N1", "N2", "N2", "N3"]


def test_cluster_bootstrap_is_reproducible_and_brackets_estimate() -> None:
    items = [(f"cell-{index % 5}", "tree" if index % 3 else "shrub") for index in range(30)]
    noisy = [
        (cell, label, label if index % 4 else "mixed")
        for index, (cell, label) in enumerate(items)
    ]

    def kappa(sample):
        return cohen_kappa([(first, second) for _, first, second in sample])

    first = cluster_bootstrap(noisy, lambda item: item[0], kappa, resamples=200, seed=7)
    second = cluster_bootstrap(noisy, lambda item: item[0], kappa, resamples=200, seed=7)

    assert first == second
    assert first.lower <= first.estimate <= first.upper
    assert first.resamples > 0


def test_cluster_bootstrap_handles_undefined_statistic() -> None:
    result = cluster_bootstrap([1, 2], lambda item: item, lambda _: None, resamples=10)

    assert result.estimate is None
    assert result.lower is None
    assert result.resamples == 0
