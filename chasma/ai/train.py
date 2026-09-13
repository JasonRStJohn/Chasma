import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import torch
import numpy as np
from stable_baselines3 import PPO

from chasma.ai.training_env import ChasmaArenaEnv

# Configure UTF-8 stdout for Windows consoles
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


class OnnxablePolicy(torch.nn.Module):
    """
    Wraps SB3 MultiDiscrete([3, 2, 2]) policy actor for ONNX export.
    Takes observation vector [batch, 14] -> returns deterministic actions [batch, 3].
    """

    def __init__(self, policy):
        super().__init__()
        self.policy = policy

    def forward(self, obs):
        features = self.policy.extract_features(obs)
        latent_pi = self.policy.mlp_extractor.forward_actor(features)
        action_logits = self.policy.action_net(latent_pi)

        # MultiDiscrete([3, 2, 2]): logits split into 3, 2, 2
        steering_logits = action_logits[:, :3]
        thrust_logits = action_logits[:, 3:5]
        fire_logits = action_logits[:, 5:]

        steering = torch.argmax(steering_logits, dim=-1, keepdim=True)
        thrust = torch.argmax(thrust_logits, dim=-1, keepdim=True)
        fire = torch.argmax(fire_logits, dim=-1, keepdim=True)

        return torch.cat([steering, thrust, fire], dim=-1)


def train_chasma_pilot(
    total_timesteps: int = 120_000,
    model_dir: Path = None,
    retrain: bool = True,
):
    if model_dir is None:
        model_dir = Path(__file__).parent / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_path = model_dir / "chasma_checkpoint.zip"
    onnx_path = model_dir / "chasma_pilot.onnx"

    env = ChasmaArenaEnv()

    if checkpoint_path.exists() and not retrain:
        print(f"--- Loading existing checkpoint: {checkpoint_path} ---")
        model = PPO.load(str(checkpoint_path), env=env)
    else:
        print(f"--- Training Chasma Pilot for {total_timesteps:,} timesteps ---")
        policy_kwargs = dict(net_arch=dict(pi=[64, 64], vf=[64, 64]))
        model = PPO(
            "MlpPolicy",
            env,
            policy_kwargs=policy_kwargs,
            learning_rate=3e-4,
            n_steps=2048,
            batch_size=64,
            gamma=0.99,
            ent_coef=0.01,
            verbose=1,
        )
        model.learn(total_timesteps=total_timesteps)
        model.save(str(checkpoint_path))
        print(f"Saved checkpoint: {checkpoint_path}")

    print(f"--- Exporting to ONNX: {onnx_path} ---")
    onnxable_model = OnnxablePolicy(model.policy)
    onnxable_model.eval()

    dummy_input = torch.randn(1, 14, dtype=torch.float32)

    torch.onnx.export(
        onnxable_model,
        dummy_input,
        str(onnx_path),
        opset_version=18,
        input_names=["observations"],
        output_names=["actions"],
        dynamic_axes={"observations": {0: "batch_size"}, "actions": {0: "batch_size"}},
        dynamo=False,
    )

    size_kb = os.path.getsize(str(onnx_path)) / 1024.0
    print(f"Exported {onnx_path.name} ({size_kb:.1f} KB)")

    # Verify with onnxruntime
    try:
        import onnxruntime as ort

        session = ort.InferenceSession(str(onnx_path))
        sample_obs = np.zeros((1, 14), dtype=np.float32)
        sample_out = session.run(None, {"observations": sample_obs})
        print(f"Verification pass: output for zero-state = {sample_out[0]}")
        print("Model is ready for Chasma live gameplay!")
    except Exception as e:
        print(f"ONNX verification error: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train Chasma AI pilot.")
    parser.add_argument(
        "steps",
        nargs="?",
        type=int,
        default=250_000,
        help="Total training timesteps (default: 250,000)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing checkpoint instead of retraining from scratch",
    )
    args = parser.parse_args()

    train_chasma_pilot(total_timesteps=args.steps, retrain=not args.resume)
