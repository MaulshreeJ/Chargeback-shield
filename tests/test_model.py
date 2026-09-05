import src.model as model_module
from src.data_gen import generate


def _patch_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(model_module, "MODEL_PATH", tmp_path / "model.joblib")
    monkeypatch.setattr(model_module, "THRESHOLDS_PATH", tmp_path / "thresholds.json")
    monkeypatch.setattr(model_module, "ARTIFACT_DIR", tmp_path)


def test_train_returns_expected_metric_keys(tmp_path, monkeypatch):
    _patch_artifacts(tmp_path, monkeypatch)
    df = generate(n_transactions=1500, seed=7)
    metrics = model_module.train(df)

    for key in ("precision", "recall", "pr_auc", "roc_auc", "operating_threshold", "confusion_matrix"):
        assert key in metrics
    assert 0.0 <= metrics["precision"] <= 1.0
    assert 0.0 <= metrics["recall"] <= 1.0


def test_risk_model_scores_in_valid_range(tmp_path, monkeypatch):
    _patch_artifacts(tmp_path, monkeypatch)
    df = generate(n_transactions=1500, seed=7)
    model_module.train(df)

    risk_model = model_module.RiskModel()
    prob, band = risk_model.score(df.iloc[[0]])
    assert 0.0 <= prob <= 1.0
    assert band is not None


def test_train_reports_baseline_comparison(tmp_path, monkeypatch):
    _patch_artifacts(tmp_path, monkeypatch)
    df = generate(n_transactions=1500, seed=7)
    metrics = model_module.train(df)

    assert "baseline" in metrics
    assert 0.0 <= metrics["baseline"]["precision"] <= 1.0
    assert 0.0 <= metrics["baseline"]["recall"] <= 1.0


def test_explain_returns_ranked_contributions(tmp_path, monkeypatch):
    monkeypatch.setattr(model_module, "BASELINES_PATH", tmp_path / "feature_baselines.json")
    _patch_artifacts(tmp_path, monkeypatch)
    df = generate(n_transactions=1500, seed=7)
    model_module.train(df)

    risk_model = model_module.RiskModel()
    factors = risk_model.explain(df.iloc[[0]], top_n=3)
    assert len(factors) <= 3
    # sorted by |contribution| descending
    magnitudes = [abs(f["contribution"]) for f in factors]
    assert magnitudes == sorted(magnitudes, reverse=True)
    for f in factors:
        assert "feature" in f and "contribution" in f


def test_train_reports_cost_based_operating_point(tmp_path, monkeypatch):
    _patch_artifacts(tmp_path, monkeypatch)
    df = generate(n_transactions=1500, seed=7)
    metrics = model_module.train(df)

    cbo = metrics["cost_based_operating_point"]
    assert 0.0 <= cbo["threshold"] <= 1.0
    assert 0.0 <= cbo["precision"] <= 1.0
    assert 0.0 <= cbo["recall"] <= 1.0
    # the cost-optimal policy should never cost more than simply never
    # flagging anything -- that's the whole point of computing it
    assert cbo["expected_cost_on_test_fold"] <= cbo["expected_cost_if_never_flagging"]


def test_select_threshold_by_cost_prefers_lower_cost(tmp_path, monkeypatch):
    import numpy as np
    _patch_artifacts(tmp_path, monkeypatch)
    y_val = np.array([0, 0, 0, 1, 1])
    probs = np.array([0.1, 0.2, 0.3, 0.8, 0.9])
    amounts = np.array([10, 10, 10, 500, 500])
    threshold, cost = model_module._select_threshold_by_cost(y_val, probs, amounts, fp_cost=5.0)
    # every positive is far more valuable to catch than a false positive
    # is expensive here, so the optimal threshold should catch both
    preds = (probs >= threshold).astype(int)
    assert preds[3] == 1 and preds[4] == 1


def test_merchant_history_is_causal(tmp_path, monkeypatch):
    """A merchant's very first transaction must see zero prior history --
    the feature can never leak a merchant's future dispute outcomes into
    its own earlier rows.
    """
    from src.data_gen import generate

    df = generate(n_transactions=3000, seed=11)
    first_per_merchant = df.sort_values("timestamp").groupby("merchant_id").first()
    assert (first_per_merchant["merchant_txn_count_90d"] == 0).all()
    # smoothed toward ~10% prior when there's no history yet
    assert ((first_per_merchant["merchant_dispute_rate_90d"] - 0.1).abs() < 0.02).all()
