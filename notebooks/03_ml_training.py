# Databricks notebook source
# MAGIC %md
# MAGIC # Nova Molding Systems FP&A — ML Revenue Forecast
# MAGIC Trains a LightGBM model to predict 18-month rolling revenue by entity ×
# MAGIC product family.  Tracks with MLflow, registers in Unity Catalog, and
# MAGIC scores predictions back into Delta.

# COMMAND ----------

dbutils.widgets.text("catalog", "nova_molding_demo", "UC Catalog")
dbutils.widgets.text("schema", "fpa", "UC Schema")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

spark.sql(f"USE CATALOG {catalog}")
spark.sql(f"USE SCHEMA {schema}")

# COMMAND ----------

# MAGIC %pip install lightgbm shap mlflow
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import mlflow
import mlflow.lightgbm
from mlflow.models.signature import infer_signature
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

mlflow.set_registry_uri("databricks-uc")
experiment_path = f"/Workspace/Users/{spark.sql('SELECT current_user()').collect()[0][0]}/nova_molding_revenue_forecast"
mlflow.set_experiment(experiment_path)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 — Feature Engineering

# COMMAND ----------

orders_df = spark.sql(f"""
    SELECT
        o.entity_id,
        e.business_unit,
        e.region,
        p.product_family,
        p.end_market,
        p.is_aftermarket,
        t.fiscal_year,
        t.fiscal_month,
        t.fiscal_quarter,
        SUM(o.net_amount_usd) AS monthly_revenue
    FROM {catalog}.{schema}.silver_fact_orders o
    JOIN {catalog}.{schema}.silver_dim_entity e ON o.entity_id = e.entity_id
    JOIN {catalog}.{schema}.silver_dim_product p ON o.product_id = p.product_id
    JOIN {catalog}.{schema}.silver_dim_time t ON o.time_id = t.time_id
    WHERE e.is_consolidated = false
    GROUP BY o.entity_id, e.business_unit, e.region,
             p.product_family, p.end_market, p.is_aftermarket,
             t.fiscal_year, t.fiscal_month, t.fiscal_quarter
    ORDER BY t.fiscal_year, t.fiscal_month
""").toPandas()

orders_df["period"] = orders_df["fiscal_year"].astype(str) + "-" + orders_df["fiscal_month"].astype(str).str.zfill(2)
orders_df = orders_df.sort_values(["entity_id", "product_family", "period"]).reset_index(drop=True)

# COMMAND ----------

# Lag features and rolling means
group_cols = ["entity_id", "product_family"]

for lag in range(1, 7):
    orders_df[f"lag_revenue_{lag}m"] = orders_df.groupby(group_cols)["monthly_revenue"].shift(lag)

orders_df["rolling_mean_3m"] = orders_df.groupby(group_cols)["monthly_revenue"].transform(
    lambda x: x.shift(1).rolling(3, min_periods=1).mean()
)
orders_df["rolling_mean_6m"] = orders_df.groupby(group_cols)["monthly_revenue"].transform(
    lambda x: x.shift(1).rolling(6, min_periods=1).mean()
)

# YoY same-month revenue
orders_df["yoy_revenue_same_month"] = orders_df.groupby(group_cols)["monthly_revenue"].shift(12)

# Cyclical time features
orders_df["month_of_year"] = orders_df["fiscal_month"].astype(int)
orders_df["quarter"] = orders_df["fiscal_quarter"].str.extract(r"(\d)").astype(int)

# COMMAND ----------

# Add utilization lag from production gold table
util_df = spark.sql(f"""
    SELECT fiscal_year, fiscal_quarter,
           AVG(utilization_pct) AS avg_utilization
    FROM {catalog}.{schema}.gold_plant_performance
    GROUP BY fiscal_year, fiscal_quarter
""").toPandas()

orders_df = orders_df.merge(util_df, on=["fiscal_year", "fiscal_quarter"], how="left")
orders_df.rename(columns={"avg_utilization": "utilization_pct_lag1"}, inplace=True)

# FX rate lag
fx_df = spark.sql(f"""
    SELECT t.fiscal_year, t.fiscal_month,
           AVG(f.avg_rate) AS fx_rate_avg
    FROM {catalog}.{schema}.silver_fact_fx_rates f
    JOIN {catalog}.{schema}.silver_dim_time t ON f.time_id = t.time_id
    GROUP BY t.fiscal_year, t.fiscal_month
""").toPandas()

orders_df = orders_df.merge(fx_df, on=["fiscal_year", "fiscal_month"], how="left")
orders_df.rename(columns={"fx_rate_avg": "fx_rate_avg_lag1"}, inplace=True)

# COMMAND ----------

# Add backlog feature
backlog_df = spark.sql(f"""
    SELECT o.entity_id, p.product_family, t.fiscal_year, t.fiscal_month,
           SUM(o.net_amount_usd) AS order_backlog_value
    FROM {catalog}.{schema}.silver_fact_orders o
    JOIN {catalog}.{schema}.silver_dim_product p ON o.product_id = p.product_id
    JOIN {catalog}.{schema}.silver_dim_time t ON o.time_id = t.time_id
    WHERE o.backlog_flag = true
    GROUP BY o.entity_id, p.product_family, t.fiscal_year, t.fiscal_month
""").toPandas()

orders_df = orders_df.merge(
    backlog_df, on=["entity_id", "product_family", "fiscal_year", "fiscal_month"], how="left"
)
orders_df["order_backlog_value"] = orders_df["order_backlog_value"].fillna(0)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 — Prepare Training Data

# COMMAND ----------

FEATURE_COLS = [
    "lag_revenue_1m", "lag_revenue_2m", "lag_revenue_3m",
    "lag_revenue_4m", "lag_revenue_5m", "lag_revenue_6m",
    "rolling_mean_3m", "rolling_mean_6m", "yoy_revenue_same_month",
    "order_backlog_value", "month_of_year", "quarter",
    "utilization_pct_lag1", "fx_rate_avg_lag1",
]
CAT_FEATURES = ["business_unit", "region", "end_market", "is_aftermarket"]
TARGET = "monthly_revenue"

all_features = FEATURE_COLS + CAT_FEATURES

df_model = orders_df.copy()
for c in FEATURE_COLS:
    df_model[c] = pd.to_numeric(df_model[c], errors="coerce")
df_model[TARGET] = pd.to_numeric(df_model[TARGET], errors="coerce")
df_model = df_model.dropna(subset=FEATURE_COLS + [TARGET])
for c in CAT_FEATURES:
    df_model[c] = df_model[c].astype("category")

X = df_model[all_features]
y = df_model[TARGET]

print(f"Training samples: {len(X):,}")
print(f"Features: {len(all_features)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 — Train LightGBM with MLflow Tracking

# COMMAND ----------

tscv = TimeSeriesSplit(n_splits=3)

with mlflow.start_run(run_name="lightgbm_revenue_forecast") as run:
    params = {
        "objective": "regression",
        "metric": "rmse",
        "n_estimators": 500,
        "learning_rate": 0.05,
        "num_leaves": 63,
        "max_depth": 8,
        "min_child_samples": 20,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 0.1,
        "random_state": 42,
        "verbose": -1,
    }

    mlflow.log_params(params)

    model = LGBMRegressor(**params)

    cv_scores = {"rmse": [], "mae": [], "mape": [], "r2": []}
    for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[],
        )

        preds = model.predict(X_val)
        rmse = np.sqrt(mean_squared_error(y_val, preds))
        mae = mean_absolute_error(y_val, preds)
        mape = np.mean(np.abs((y_val - preds) / np.where(y_val == 0, 1, y_val))) * 100
        r2 = r2_score(y_val, preds)

        cv_scores["rmse"].append(rmse)
        cv_scores["mae"].append(mae)
        cv_scores["mape"].append(mape)
        cv_scores["r2"].append(r2)

        print(f"Fold {fold + 1}: RMSE={rmse:,.0f}  MAE={mae:,.0f}  MAPE={mape:.1f}%  R²={r2:.3f}")

    # Log mean CV metrics
    for metric, values in cv_scores.items():
        mlflow.log_metric(f"cv_mean_{metric}", np.mean(values))

    # Re-train on full dataset
    model.fit(X, y)

    # Log SHAP feature importance
    try:
        import shap
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X.sample(min(500, len(X)), random_state=42))
        shap_importance = pd.DataFrame({
            "feature": all_features,
            "mean_abs_shap": np.abs(shap_values).mean(axis=0),
        }).sort_values("mean_abs_shap", ascending=False)
        mlflow.log_table(shap_importance, artifact_file="shap_importance.json")
        print("\nSHAP feature importance:")
        print(shap_importance.to_string(index=False))
    except Exception as e:
        print(f"SHAP computation skipped: {e}")

    # Log model with explicit signature (required by UC)
    signature = infer_signature(X, model.predict(X))
    mlflow.lightgbm.log_model(
        model,
        artifact_path="model",
        registered_model_name=f"{catalog}.{schema}.nova_molding_revenue_forecast",
        input_example=X.head(1),
        signature=signature,
    )

    run_id = run.info.run_id
    print(f"\nMLflow run ID: {run_id}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4 — Batch Scoring: 18-Month Forward Forecast

# COMMAND ----------

# Build scoring frame for 18 months forward from the latest data month
latest_period = df_model.sort_values("period").drop_duplicates(
    subset=["entity_id", "product_family"], keep="last"
)

scoring_frames = []
for fwd in range(1, 19):
    sf = latest_period.copy()
    sf["fiscal_month"] = (sf["fiscal_month"].astype(int) + fwd - 1) % 12 + 1
    sf["fiscal_year"] = sf["fiscal_year"].astype(int) + ((sf["fiscal_month"].astype(int) + fwd - 1) // 12)
    sf["month_of_year"] = sf["fiscal_month"]
    sf["quarter"] = (sf["fiscal_month"] - 1) // 3 + 1
    sf["forecast_month"] = sf["fiscal_year"].astype(str) + "-" + sf["fiscal_month"].astype(str).str.zfill(2)
    scoring_frames.append(sf)

scoring_df = pd.concat(scoring_frames, ignore_index=True)
for c in CAT_FEATURES:
    scoring_df[c] = scoring_df[c].astype("category")

predictions = model.predict(scoring_df[all_features])

# Prediction intervals via quantile approximation
residual_std = np.std(y - model.predict(X))
scoring_df["predicted_revenue"] = np.round(predictions, 2)
scoring_df["prediction_interval_lower"] = np.round(predictions - 1.96 * residual_std, 2)
scoring_df["prediction_interval_upper"] = np.round(predictions + 1.96 * residual_std, 2)
scoring_df["scored_at"] = pd.Timestamp.now()

output_cols = [
    "entity_id", "product_family", "forecast_month",
    "predicted_revenue", "prediction_interval_lower", "prediction_interval_upper",
    "scored_at",
]
result_df = scoring_df[output_cols].copy()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5 — Write Predictions to Delta

# COMMAND ----------

spark_result = spark.createDataFrame(result_df)
spark_result.write.mode("overwrite").saveAsTable(f"{catalog}.{schema}.ml_revenue_forecast")

row_count = spark.sql(f"SELECT COUNT(*) FROM {catalog}.{schema}.ml_revenue_forecast").collect()[0][0]
print(f"Scored {row_count:,} prediction rows to {catalog}.{schema}.ml_revenue_forecast")
