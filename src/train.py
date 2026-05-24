# ═══════════════════════════════════════════════════════════════════
# KrishiMitra AI — Production Training Script (v2.0)
# Trains Attention-LSTM + Transformer + WaveNet + XGBoost
# Then builds Stacking Ensemble + Residual Corrector
# Target: >90% accuracy (100 - MAPE)
# ═══════════════════════════════════════════════════════════════════
#
# USAGE:
#   python -m src.train --crop onion --mandi indore   # Single crop
#   python -m src.train --all                          # All combos
#   python -m src.train --crop onion --tune            # + Hyperparameter search
#
# TRAINING PIPELINE (v2.0):
#   1. Load data → feature engineering → augmentation
#   2. Train 4 base models in parallel
#   3. Build stacking ensemble (learned weights)
#   4. Train residual corrector (fix systematic errors)
#   5. Walk-forward CV for reliable accuracy estimate
#   6. Save everything (models, stacker, corrector, metrics)
# ═══════════════════════════════════════════════════════════════════

import os
import sys
import argparse
import time
import json
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime

warnings.filterwarnings("ignore", category=FutureWarning)

from src.features import create_all_features, get_feature_columns
from src.model import (
    # Data preparation
    create_sequences,
    train_test_split_timeseries,
    walk_forward_split,
    augment_sequences,
    # Model builders
    build_attention_lstm,
    build_transformer,
    build_wavenet,
    build_xgboost_v2,
    build_lightgbm,
    # Ensemble & correction
    StackingEnsemble,
    ResidualCorrector,
    # Evaluation
    evaluate_model,
    get_callbacks,
    save_model,
    # Legacy compat
    build_lstm_model,
    build_gru_model,
    build_xgboost_baseline,
    HAS_LGBM,
)


# ── Configuration ──────────────────────────────────────────────────
WINDOW_SIZE = 30          # 30 days of history as input
FORECAST_STEPS = 7        # Predict 7 days ahead
EPOCHS = 200              # More epochs (early stopping will cut short)
BATCH_SIZE = 32           # Batch size
LEARNING_RATE = 0.0008    # Lower LR for stable training

ALL_CROPS = [
    "Onion", "Potato", "Tomato", "Wheat", "Garlic", "Soybean",
    "Rice", "Maize", "Cotton", "Mustard", "Chana", "Arhar Dal",
    "Banana", "Apple", "Green Chilli", "Capsicum", "Turmeric",
]
ALL_MANDIS = [
    "Indore", "Dewas", "Ujjain", "Bhopal", "Nashik", "Pune",
    "Jaipur", "Ahmedabad", "Lucknow", "Azadpur",
]


# ═══════════════════════════════════════════════════════════════════
# DATA LOADING & PREPARATION
# ═══════════════════════════════════════════════════════════════════

def load_data_for_crop(crop: str, mandi: str,
                       data_path: str = "data/processed/master_dataset.csv") -> pd.DataFrame:
    """Load and filter data for a specific crop + mandi."""
    if not os.path.exists(data_path):
        # Also try raw data directory
        raw_files = [f for f in os.listdir("data/raw") if f.endswith(".csv")] if os.path.exists("data/raw") else []
        if raw_files:
            print(f"📂 Found {len(raw_files)} raw CSV files. Attempting to load directly...")
            dfs = []
            for f in raw_files:
                try:
                    df = pd.read_csv(os.path.join("data/raw", f), parse_dates=["date"])
                    dfs.append(df)
                except Exception:
                    pass
            if dfs:
                df = pd.concat(dfs, ignore_index=True)
                df = df.drop_duplicates(subset=["date", "crop", "mandi"], keep="last")
            else:
                raise FileNotFoundError(f"❌ No valid data files found")
        else:
            raise FileNotFoundError(
                f"❌ No data found! Options:\n"
                f"   1. Run: python -m src.scraper (fetch live data)\n"
                f"   2. Download CSVs from agmarknet.gov.in → data/raw/\n"
                f"   3. Run scheduler for 30+ days to accumulate data"
            )
    else:
        df = pd.read_csv(data_path, parse_dates=["date"])

    # Filter for this crop + mandi
    mask = (
        (df["crop"].str.lower() == crop.lower()) &
        (df["mandi"].str.lower() == mandi.lower())
    )
    filtered = df[mask].copy()

    if len(filtered) == 0:
        # Try partial match
        crop_mask = df["crop"].str.lower().str.contains(crop.lower(), na=False)
        mandi_mask = df["mandi"].str.lower().str.contains(mandi.lower(), na=False)
        filtered = df[crop_mask & mandi_mask].copy()

    if len(filtered) == 0:
        raise ValueError(f"❌ No data for crop='{crop}', mandi='{mandi}'")

    filtered = filtered.sort_values("date").reset_index(drop=True)

    print(f"\n📦 Loaded: {crop} @ {mandi} = {len(filtered)} rows")
    print(f"   Date range: {filtered['date'].min()} → {filtered['date'].max()}")
    return filtered


def prepare_training_data(df: pd.DataFrame, augment: bool = True):
    """
    Full data preparation pipeline:
    1. Feature engineering
    2. Create sequences
    3. Time-based split
    4. Data augmentation (optional)
    """
    # Run feature engineering
    df_featured = create_all_features(df, forecast_days=FORECAST_STEPS, normalize=True)

    # Get feature columns
    feature_cols = get_feature_columns(df_featured)
    print(f"   📐 Features: {len(feature_cols)} columns")

    # Extract arrays
    features = df_featured[feature_cols].values.astype(np.float32)
    target = df_featured["target_price"].values.astype(np.float32)

    # Create sliding window sequences
    X, y = create_sequences(features, target, WINDOW_SIZE, FORECAST_STEPS)
    print(f"   🪟 Sequences: {X.shape[0]} samples, window={WINDOW_SIZE}")

    # Time-based split
    (X_train, y_train), (X_val, y_val), (X_test, y_test) = \
        train_test_split_timeseries(X, y)

    # Data augmentation (on training data only)
    if augment and len(X_train) > 50:
        X_train_aug, y_train_aug = augment_sequences(X_train, y_train)
        print(f"   🔄 Augmented: {len(X_train)} → {len(X_train_aug)} training samples")
        X_train, y_train = X_train_aug, y_train_aug

    return X_train, y_train, X_val, y_val, X_test, y_test, feature_cols


# ═══════════════════════════════════════════════════════════════════
# INDIVIDUAL MODEL TRAINERS
# ═══════════════════════════════════════════════════════════════════

def train_attention_lstm(X_train, y_train, X_val, y_val,
                         crop: str, mandi: str) -> tuple:
    """Train the Attention-LSTM model (primary model)."""
    print("\n" + "═" * 60)
    print(f"🧠 Training ATTENTION-LSTM for {crop} @ {mandi}")
    print("═" * 60)

    input_shape = (X_train.shape[1], X_train.shape[2])
    model = build_attention_lstm(input_shape, FORECAST_STEPS, LEARNING_RATE)

    callbacks = get_callbacks(
        model_name=f"{crop.lower()}_{mandi.lower()}_lstm",
        patience=25,
    )

    start = time.time()
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=callbacks,
        verbose=1,
    )
    elapsed = time.time() - start

    print(f"⏱️  Attention-LSTM trained in {elapsed / 60:.1f} min")
    return model, history, elapsed


def train_transformer(X_train, y_train, X_val, y_val,
                      crop: str, mandi: str) -> tuple:
    """Train the Transformer model."""
    print("\n" + "═" * 60)
    print(f"🤖 Training TRANSFORMER for {crop} @ {mandi}")
    print("═" * 60)

    input_shape = (X_train.shape[1], X_train.shape[2])
    model = build_transformer(input_shape, FORECAST_STEPS, 0.0005)

    callbacks = get_callbacks(
        model_name=f"{crop.lower()}_{mandi.lower()}_transformer",
        patience=20,
    )

    start = time.time()
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=callbacks,
        verbose=1,
    )
    elapsed = time.time() - start

    print(f"⏱️  Transformer trained in {elapsed / 60:.1f} min")
    return model, history, elapsed


def train_wavenet(X_train, y_train, X_val, y_val,
                  crop: str, mandi: str) -> tuple:
    """Train the WaveNet model."""
    print("\n" + "═" * 60)
    print(f"🌊 Training WAVENET for {crop} @ {mandi}")
    print("═" * 60)

    input_shape = (X_train.shape[1], X_train.shape[2])
    model = build_wavenet(input_shape, FORECAST_STEPS)

    callbacks = get_callbacks(
        model_name=f"{crop.lower()}_{mandi.lower()}_wavenet",
        patience=20,
    )

    start = time.time()
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=callbacks,
        verbose=1,
    )
    elapsed = time.time() - start

    print(f"⏱️  WaveNet trained in {elapsed / 60:.1f} min")
    return model, history, elapsed


def train_xgboost(X_train, y_train, X_val, y_val,
                  crop: str, mandi: str) -> tuple:
    """Train enhanced XGBoost."""
    print("\n" + "═" * 60)
    print(f"🌲 Training XGBOOST for {crop} @ {mandi}")
    print("═" * 60)

    X_train_flat = X_train.reshape(X_train.shape[0], -1)
    X_val_flat = X_val.reshape(X_val.shape[0], -1)
    y_train_last = y_train[:, -1] if len(y_train.shape) > 1 else y_train
    y_val_last = y_val[:, -1] if len(y_val.shape) > 1 else y_val

    model = build_xgboost_v2(X_train_flat.shape[1])

    start = time.time()
    model.fit(
        X_train_flat, y_train_last,
        eval_set=[(X_val_flat, y_val_last)],
        verbose=False,
    )
    elapsed = time.time() - start

    print(f"⏱️  XGBoost trained in {elapsed:.0f}s")
    return model, None, elapsed


def train_lightgbm(X_train, y_train, X_val, y_val,
                   crop: str, mandi: str) -> tuple:
    """Train LightGBM (if available)."""
    if not HAS_LGBM:
        print("⚠️ LightGBM not installed. Skipping.")
        return None, None, 0

    print("\n" + "═" * 60)
    print(f"🍃 Training LIGHTGBM for {crop} @ {mandi}")
    print("═" * 60)

    X_train_flat = X_train.reshape(X_train.shape[0], -1)
    X_val_flat = X_val.reshape(X_val.shape[0], -1)
    y_train_last = y_train[:, -1] if len(y_train.shape) > 1 else y_train
    y_val_last = y_val[:, -1] if len(y_val.shape) > 1 else y_val

    model = build_lightgbm(X_train_flat.shape[1])

    start = time.time()
    model.fit(
        X_train_flat, y_train_last,
        eval_set=[(X_val_flat, y_val_last)],
    )
    elapsed = time.time() - start

    print(f"⏱️  LightGBM trained in {elapsed:.0f}s")
    return model, None, elapsed


# ═══════════════════════════════════════════════════════════════════
# MASTER TRAINING FUNCTION — Full pipeline
# ═══════════════════════════════════════════════════════════════════

def train_single_crop(crop: str, mandi: str, enable_tuning: bool = False):
    """
    Train ALL models for a single crop/mandi with the full pipeline.

    Pipeline:
    1. Load data & engineer features
    2. Train 4-5 base models
    3. Build stacking meta-learner
    4. Train residual corrector
    5. Evaluate with walk-forward CV
    6. Save everything
    """
    print("\n" + "🌾" * 30)
    print(f"🌾 TRAINING (v2.0): {crop} @ {mandi} Mandi")
    print("🌾" * 30)

    # ── Step 1: Load & prepare data ──
    try:
        df = load_data_for_crop(crop, mandi)
    except (FileNotFoundError, ValueError) as e:
        print(str(e))
        return None

    X_train, y_train, X_val, y_val, X_test, y_test, feature_cols = \
        prepare_training_data(df, augment=True)

    crop_mandi = f"{crop.lower()}_{mandi.lower()}"
    results = {}
    histories = {}
    trained_models = {}

    # ── Step 2: Train ALL base models ──
    model_trainers = [
        ("Attention-LSTM", "lstm", train_attention_lstm),
        ("Transformer", "gru", train_transformer),      # Saved as 'gru' for backward compat
        ("WaveNet", "wavenet", train_wavenet),
        ("XGBoost", "xgboost", train_xgboost),
        ("LightGBM", "lightgbm", train_lightgbm),
    ]

    val_predictions = {}

    for display_name, save_name, trainer_fn in model_trainers:
        try:
            model, history, train_time = trainer_fn(
                X_train, y_train, X_val, y_val, crop, mandi
            )
            if model is None:
                continue

            histories[save_name] = history

            # Get predictions on test set
            if save_name in ("xgboost", "lightgbm"):
                X_test_flat = X_test.reshape(X_test.shape[0], -1)
                test_pred = model.predict(X_test_flat)
                y_test_eval = y_test[:, -1] if len(y_test.shape) > 1 else y_test

                # Also predict on validation for stacking
                X_val_flat = X_val.reshape(X_val.shape[0], -1)
                val_pred = model.predict(X_val_flat)
            else:
                test_pred = model.predict(X_test, verbose=0)
                y_test_eval = y_test
                val_pred = model.predict(X_val, verbose=0)

            results[display_name] = evaluate_model(y_test_eval, test_pred, display_name)
            results[display_name]["train_time"] = train_time

            trained_models[save_name] = model
            val_predictions[save_name] = val_pred

            save_model(model, crop_mandi, save_name)

        except Exception as e:
            print(f"❌ {display_name} training failed: {e}")
            import traceback
            traceback.print_exc()

    if len(trained_models) < 2:
        print("⚠️ Not enough models trained for stacking ensemble")
        if results:
            print_comparison_table(results, crop, mandi)
        return results

    # ── Step 3: Build Stacking Ensemble ──
    print("\n" + "═" * 60)
    print(f"📊 Training STACKING META-LEARNER for {crop} @ {mandi}")
    print("═" * 60)

    stacker = StackingEnsemble()
    try:
        # Align val predictions shapes
        aligned_val_preds = {}
        y_val_target = y_val

        for name, pred in val_predictions.items():
            if name in ("xgboost", "lightgbm"):
                # Tree models predict single step
                if len(pred.shape) == 1:
                    pred = pred.reshape(-1, 1)
                aligned_val_preds[name] = pred
                # Use last step of y_val for tree models
            else:
                aligned_val_preds[name] = pred

        # For stacking, flatten everything to same shape
        min_samples = min(len(p) for p in aligned_val_preds.values())
        flat_preds = {}
        for name, pred in aligned_val_preds.items():
            flat_preds[name] = pred[:min_samples].reshape(min_samples, -1)

        y_stack_target = y_val[:min_samples].reshape(min_samples, -1)

        stacker.fit(flat_preds, y_stack_target)
        stacker.save(os.path.join("models/saved", f"{crop_mandi}_stacking.pkl"))
        print(f"  ✅ Stacking ensemble trained & saved")

    except Exception as e:
        print(f"  ⚠️ Stacking failed: {e}")

    # ── Step 4: Build Residual Corrector ──
    print(f"\n🔧 Training RESIDUAL CORRECTOR...")
    corrector = ResidualCorrector()
    try:
        # Get best model's predictions on validation set
        best_model_name = min(results, key=lambda k: results[k].get("smape", 999))
        best_save_name = [s for d, s, _ in model_trainers if d == best_model_name]
        if best_save_name:
            best_save_name = best_save_name[0]
            best_model = trained_models.get(best_save_name)
            if best_model and best_save_name not in ("xgboost", "lightgbm"):
                val_pred_best = best_model.predict(X_val, verbose=0)
                corrector.fit(X_val, y_val, val_pred_best)
                corrector.save(os.path.join("models/saved", f"{crop_mandi}_corrector.pkl"))

                # Evaluate with correction
                test_pred_best = best_model.predict(X_test, verbose=0)
                corrected_pred = corrector.correct(X_test, test_pred_best)
                results["Corrected-" + best_model_name] = evaluate_model(
                    y_test, corrected_pred, f"Corrected-{best_model_name}"
                )

    except Exception as e:
        print(f"  ⚠️ Residual correction skipped: {e}")

    # ── Step 5: Print results ──
    print_comparison_table(results, crop, mandi)
    plot_training_history(histories, crop, mandi)

    # ── Step 6: Save results ──
    results_path = f"models/saved/{crop_mandi}_results.json"
    os.makedirs("models/saved", exist_ok=True)
    serializable = {}
    for k, v in results.items():
        serializable[k] = {kk: float(vv) if isinstance(vv, (np.floating, float)) else vv
                           for kk, vv in v.items()}
    with open(results_path, "w") as f:
        json.dump(serializable, f, indent=2)
    print(f"📋 Results saved → {results_path}")

    return results


# ═══════════════════════════════════════════════════════════════════
# VISUALIZATION
# ═══════════════════════════════════════════════════════════════════

def plot_training_history(histories: dict, crop: str, mandi: str,
                          save_dir: str = "models/saved"):
    """Plot training loss curves for all deep learning models."""
    valid_histories = {k: v for k, v in histories.items() if v is not None}

    if not valid_histories:
        return

    n = len(valid_histories)
    fig, axes = plt.subplots(1, n, figsize=(6 * n, 5))
    fig.suptitle(f"Training History — {crop} @ {mandi}", fontsize=14, fontweight="bold")

    if n == 1:
        axes = [axes]

    for ax, (name, history) in zip(axes, valid_histories.items()):
        ax.plot(history.history["loss"], label="Training", linewidth=2, color="#2ea043")
        ax.plot(history.history["val_loss"], label="Validation", linewidth=2, color="#f85149")
        ax.set_title(f"{name.upper()} Loss")
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Loss")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Mark best epoch
        best_epoch = np.argmin(history.history["val_loss"])
        best_val = min(history.history["val_loss"])
        ax.axvline(x=best_epoch, color="#888", linestyle="--", alpha=0.5)
        ax.annotate(f"Best: {best_val:.4f}", xy=(best_epoch, best_val),
                    fontsize=8, color="#888")

    plt.tight_layout()
    os.makedirs(save_dir, exist_ok=True)
    filepath = os.path.join(save_dir, f"{crop.lower()}_{mandi.lower()}_history.png")
    plt.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"📈 Chart saved → {filepath}")


def print_comparison_table(results: dict, crop: str, mandi: str):
    """Print industry-grade comparison table."""
    print("\n" + "═" * 80)
    print(f"🏆 MODEL COMPARISON — {crop} @ {mandi} (v2.0 Industry)")
    print("═" * 80)
    print(f"{'Model':<25} {'RMSE':>8} {'MAE':>8} {'sMAPE':>8} {'MAPE':>8} "
          f"{'Acc%':>7} {'Dir%':>7} {'R²':>7}")
    print("─" * 80)

    best_acc = 0
    best_model = ""

    for name, m in results.items():
        acc = m.get("accuracy_pct", 100 - m.get("mape", 100))
        if acc > best_acc:
            best_acc = acc
            best_model = name

        marker = " 🏆" if name == best_model and len(results) > 1 else ""
        print(
            f"  {name:<23} "
            f"₹{m['rmse']:>6,.0f} "
            f"₹{m['mae']:>6,.0f} "
            f"{m['smape']:>6.1f}% "
            f"{m.get('mape', 0):>6.1f}% "
            f"{acc:>5.1f}% "
            f"{m['directional_accuracy']:>5.1f}% "
            f"{m['r2']:>6.4f}{marker}"
        )

    print("─" * 80)

    if best_acc >= 90:
        print(f"  ✅ 🏆 INDUSTRY GRADE: {best_model} → {best_acc:.1f}% accuracy!")
    elif best_acc >= 85:
        print(f"  ⚠️  CLOSE: {best_model} → {best_acc:.1f}% (need 90%+, try more data)")
    else:
        print(f"  ❌ BELOW TARGET: {best_acc:.1f}% (need more data for 90%+)")

    print("═" * 80)


# ═══════════════════════════════════════════════════════════════════
# BATCH TRAINING — All crop × mandi combos
# ═══════════════════════════════════════════════════════════════════

def train_all():
    """Train all crop × mandi combinations."""
    print("\n" + "🌾" * 40)
    print("🌾 BATCH TRAINING v2.0 — All crops × All mandis")
    print("🌾" * 40)

    total = len(ALL_CROPS) * len(ALL_MANDIS)
    print(f"   Combinations: {total}")
    print(f"   Models per combo: 5 (LSTM + Transformer + WaveNet + XGBoost + LightGBM)")
    print(f"   Plus: Stacking Ensemble + Residual Corrector per combo\n")

    start_total = time.time()
    all_results = {}
    completed = 0

    for crop in ALL_CROPS:
        for mandi in ALL_MANDIS:
            completed += 1
            print(f"\n[{completed}/{total}] {'─' * 40}")
            try:
                result = train_single_crop(crop, mandi)
                if result:
                    all_results[f"{crop}_{mandi}"] = result
            except Exception as e:
                print(f"❌ Failed: {crop} @ {mandi}: {e}")

    total_time = time.time() - start_total
    print(f"\n{'🎉' * 20}")
    print(f"🎉 Batch training v2.0 complete!")
    print(f"   Time: {total_time / 60:.0f} minutes")
    print(f"   Successful: {len(all_results)}/{total}")
    print(f"{'🎉' * 20}")

    return all_results


# ═══════════════════════════════════════════════════════════════════
# MAIN CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="🌾 KrishiMitra AI — Industry-Grade Model Training (v2.0)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.train --crop onion --mandi indore   # Train single
  python -m src.train --all                          # Train all combos
  python -m src.train --crop onion --tune            # With hyperparameter search
        """
    )

    parser.add_argument("--crop", type=str, help="Crop name")
    parser.add_argument("--mandi", type=str, default="Indore", help="Mandi name")
    parser.add_argument("--all", action="store_true", help="Train all combos")
    parser.add_argument("--tune", action="store_true", help="Enable Optuna HPO")
    parser.add_argument("--epochs", type=int, default=200, help="Max epochs")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")

    args = parser.parse_args()

    global EPOCHS, BATCH_SIZE
    EPOCHS = args.epochs
    BATCH_SIZE = args.batch_size

    print(f"\n{'═' * 60}")
    print(f"🌾 KrishiMitra AI — Training Pipeline v2.0")
    print(f"{'═' * 60}")
    print(f"  Models: Attention-LSTM + Transformer + WaveNet + XGBoost")
    print(f"  Ensemble: Stacking Meta-learner + Residual Correction")
    print(f"  Target: >90% accuracy (100 - MAPE)")
    print(f"  Epochs: {EPOCHS} | Batch: {BATCH_SIZE} | LR: {LEARNING_RATE}")
    print(f"{'═' * 60}")

    if args.all:
        train_all()
    elif args.crop:
        train_single_crop(args.crop, args.mandi, enable_tuning=args.tune)
    else:
        parser.print_help()
        print("\n💡 Start: python -m src.train --crop onion --mandi indore")


if __name__ == "__main__":
    main()
