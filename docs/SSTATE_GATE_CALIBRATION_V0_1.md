# SState Gate Calibration V0.1

The formal 0.60 probability / 50-sample gate remains unchanged. This protocol
creates a research-only challenger grid rather than tuning the formal gate in
place.

The preregistered grid is:

- probability: 0.55, 0.60, 0.65;
- effective samples: 50, 100, 200; and
- nine candidates maximum.

Evaluation requires at least four outer and three inner walk-forward folds,
LONG/SHORT and regime-separated reporting, Brier score, log loss, ECE, MCE,
reliability buckets and cost-adjusted expectancy. A selected candidate must
have at least 100 effective samples, positive cost-adjusted expectancy and a
realized-success Wilson lower bound of at least 0.50.

The family uses Holm-Bonferroni at alpha 0.05. No result changes formal V0.1 or
authorizes holdout access, promotion or trading.

