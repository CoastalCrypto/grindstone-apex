"""Transformer-based strategy parameter predictor - Phase 5 Advanced AI."""
import logging
import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Tuple, Optional
import json
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class StrategyTransformer(nn.Module):
    """Transformer model for predicting optimal strategy parameters."""

    def __init__(self, input_dim: int = 64, d_model: int = 256,
                 nhead: int = 8, num_layers: int = 4, output_dim: int = 32):
        """
        Initialize transformer model.

        Args:
            input_dim: Input feature dimension
            d_model: Model dimension
            nhead: Number of attention heads
            num_layers: Number of transformer layers
            output_dim: Output dimension (strategy parameters)
        """
        super().__init__()

        self.input_embedding = nn.Linear(input_dim, d_model)
        self.positional_encoding = nn.Parameter(torch.randn(1, 100, d_model))

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=1024,
            batch_first=True,
            dropout=0.1
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers
        )

        self.output_head = nn.Sequential(
            nn.Linear(d_model, 512),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(256, output_dim)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: Input tensor (batch_size, seq_len, input_dim)

        Returns:
            Output predictions (batch_size, output_dim)
        """
        # Embed input
        x = self.input_embedding(x)  # (batch, seq_len, d_model)

        # Add positional encoding
        x = x + self.positional_encoding[:, :x.size(1), :]

        # Transform
        x = self.transformer_encoder(x)  # (batch, seq_len, d_model)

        # Global average pooling
        x = x.mean(dim=1)  # (batch, d_model)

        # Output
        output = self.output_head(x)  # (batch, output_dim)

        return output


class TransformerStrategyPredictor:
    """Predict strategy parameters using fine-tuned transformer."""

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize predictor.

        Args:
            model_path: Path to pre-trained model
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")

        # Initialize model
        self.model = StrategyTransformer().to(self.device)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        self.criterion = nn.MSELoss()

        if model_path and Path(model_path).exists():
            self._load_model(model_path)

        self.training_history = []

    def train_on_elite_strategies(self, elite_strategies: List[Dict],
                                 epochs: int = 10, batch_size: int = 32) -> Dict:
        """
        Fine-tune on elite (winning) strategies.

        Args:
            elite_strategies: List of elite strategy dicts with metrics and params
            epochs: Number of training epochs
            batch_size: Batch size

        Returns:
            Training history
        """
        logger.info(f"Training transformer on {len(elite_strategies)} elite strategies")

        # Prepare training data
        X, y = self._prepare_training_data(elite_strategies)

        if X is None or len(X) == 0:
            logger.warning("No training data prepared")
            return {"error": "No training data"}

        # Convert to tensors
        X_tensor = torch.FloatTensor(X).to(self.device)
        y_tensor = torch.FloatTensor(y).to(self.device)

        dataset = torch.utils.data.TensorDataset(X_tensor, y_tensor)
        dataloader = torch.utils.data.DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=True
        )

        # Training loop
        self.model.train()
        epoch_losses = []

        for epoch in range(epochs):
            total_loss = 0
            batch_count = 0

            for batch_X, batch_y in dataloader:
                # Forward pass
                predictions = self.model(batch_X)

                # Loss
                loss = self.criterion(predictions, batch_y)

                # Backward pass
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()

                total_loss += loss.item()
                batch_count += 1

            avg_loss = total_loss / batch_count
            epoch_losses.append(avg_loss)

            logger.info(f"Epoch {epoch+1}/{epochs} - Loss: {avg_loss:.6f}")

        self.training_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "epochs": epochs,
            "batch_size": batch_size,
            "losses": epoch_losses,
            "final_loss": epoch_losses[-1]
        })

        return {
            "status": "success",
            "epochs": epochs,
            "final_loss": epoch_losses[-1],
            "history": epoch_losses
        }

    def predict_parameters(self, market_features: Dict, top_k: int = 5) -> List[Dict]:
        """
        Predict optimal strategy parameters for current market.

        Args:
            market_features: Current market data (volatility, trend, etc.)
            top_k: Number of parameter sets to generate

        Returns:
            List of predicted strategy parameter dicts
        """
        try:
            # Convert market features to tensor
            feature_vector = self._encode_market_features(market_features)

            if feature_vector is None:
                logger.warning("Could not encode market features")
                return []

            # Make predictions
            self.model.eval()
            with torch.no_grad():
                X = torch.FloatTensor([feature_vector]).to(self.device)
                predictions = self.model(X).cpu().numpy()

            # Decode predictions to strategy parameters
            predicted_strategies = []
            for _ in range(top_k):
                strategy_params = self._decode_parameters(predictions[0])
                predicted_strategies.append(strategy_params)

            logger.info(f"Generated {len(predicted_strategies)} predicted strategies")

            return predicted_strategies

        except Exception as e:
            logger.error(f"Error predicting parameters: {e}")
            return []

    def _prepare_training_data(self, elite_strategies: List[Dict]) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Prepare training data from elite strategies.

        Args:
            elite_strategies: List of elite strategy dicts

        Returns:
            Tuple of (X, y) arrays or (None, None)
        """
        try:
            X_list = []
            y_list = []

            for strategy in elite_strategies:
                # Extract features from backtest metrics
                metrics = strategy.get("metrics", {})

                features = [
                    metrics.get("win_rate", 0.5),
                    metrics.get("profit_pct", 0),
                    metrics.get("sharpe_ratio", 0),
                    metrics.get("max_drawdown", 0),
                    metrics.get("total_trades", 0),
                    metrics.get("profit_factor", 1),
                ]

                # Normalize and pad features
                features = self._normalize_features(features)
                if len(features) < 64:
                    features = np.pad(features, (0, 64 - len(features)))

                X_list.append(features)

                # Extract strategy parameters (target)
                params = strategy.get("parameters", {})
                y_params = [
                    params.get("sma_fast", 10) / 100,
                    params.get("sma_slow", 30) / 100,
                    params.get("rsi_period", 14) / 100,
                    params.get("rsi_overbought", 70) / 100,
                    params.get("rsi_oversold", 30) / 100,
                    params.get("bb_period", 20) / 100,
                    params.get("bb_std_dev", 2) / 5,
                    params.get("risk_percentage", 2) / 10,
                ]

                # Pad to output dimension
                if len(y_params) < 32:
                    y_params = np.pad(y_params, (0, 32 - len(y_params)))

                y_list.append(y_params[:32])

            if not X_list or not y_list:
                return None, None

            return np.array(X_list), np.array(y_list)

        except Exception as e:
            logger.error(f"Error preparing training data: {e}")
            return None, None

    def _encode_market_features(self, market_features: Dict) -> Optional[np.ndarray]:
        """
        Encode market features to input tensor.

        Args:
            market_features: Market data dict

        Returns:
            Feature vector or None
        """
        try:
            features = [
                market_features.get("volatility", 0),
                market_features.get("trend", 0),
                market_features.get("momentum", 0),
                market_features.get("volume_ma_ratio", 1),
                market_features.get("price_ma_50", 0),
                market_features.get("rsi", 50),
                market_features.get("macd", 0),
                market_features.get("atr", 0),
            ]

            features = self._normalize_features(features)

            # Pad to input dimension
            if len(features) < 64:
                features = np.pad(features, (0, 64 - len(features)))

            return features[:64]

        except Exception as e:
            logger.error(f"Error encoding market features: {e}")
            return None

    def _decode_parameters(self, output: np.ndarray) -> Dict:
        """
        Decode model output to strategy parameters.

        Args:
            output: Model output array

        Returns:
            Strategy parameters dict
        """
        return {
            "sma_fast": int(np.clip(output[0] * 100, 5, 50)),
            "sma_slow": int(np.clip(output[1] * 100, 10, 100)),
            "rsi_period": int(np.clip(output[2] * 100, 10, 30)),
            "rsi_overbought": int(np.clip(output[3] * 100, 50, 90)),
            "rsi_oversold": int(np.clip(output[4] * 100, 10, 50)),
            "bb_period": int(np.clip(output[5] * 100, 10, 50)),
            "bb_std_dev": float(np.clip(output[6] * 5, 1, 3)),
            "risk_percentage": float(np.clip(output[7] * 10, 0.5, 10)),
            "profit_target": float(np.clip(output[8], 0.01, 0.1)),
            "max_drawdown": float(np.clip(output[9], 0.1, 0.5)),
        }

    def _normalize_features(self, features: List[float]) -> np.ndarray:
        """Normalize features to [0, 1]."""
        features = np.array(features, dtype=np.float32)
        features = np.nan_to_num(features)
        feature_min = features.min() if len(features) > 0 else 0
        feature_max = features.max() if len(features) > 0 else 1

        if feature_max == feature_min:
            return np.zeros_like(features)

        return (features - feature_min) / (feature_max - feature_min)

    def save_model(self, path: str) -> bool:
        """Save model to disk."""
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            torch.save({
                "model_state": self.model.state_dict(),
                "optimizer_state": self.optimizer.state_dict(),
                "training_history": self.training_history
            }, path)
            logger.info(f"Model saved to {path}")
            return True
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return False

    def _load_model(self, path: str) -> bool:
        """Load model from disk."""
        try:
            checkpoint = torch.load(path, map_location=self.device)
            self.model.load_state_dict(checkpoint["model_state"])
            self.optimizer.load_state_dict(checkpoint["optimizer_state"])
            self.training_history = checkpoint.get("training_history", [])
            logger.info(f"Model loaded from {path}")
            return True
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
