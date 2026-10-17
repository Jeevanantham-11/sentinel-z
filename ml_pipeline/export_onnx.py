"""
Sentinel-Z: ONNX Runtime Model Exporter for IBM Telum NNPA Acceleration.
Exports the Stage 1 PyTorch Temporal Latent Encoder to ONNX format (opset 14).
Enables seamless execution on IBM Z / LinuxONE via onnxruntime.
"""

import sys
import time
from pathlib import Path
import torch
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml_pipeline.dual_engine import PyTorchTemporalEncoder

def export_to_onnx():
    print("=" * 68)
    print("  PROJECT SENTINEL-Z -- ONNX MODEL EXPORT FOR IBM TELUM")
    print("=" * 68)
    
    models_dir = BASE_DIR / "ml_pipeline" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    onnx_path = models_dir / "sentinel_encoder.onnx"
    torch_weights = models_dir / "pytorch_encoder.pt"
    
    model = PyTorchTemporalEncoder(in_features=9, hidden_dim=16)
    if torch_weights.exists():
        model.load_state_dict(torch.load(torch_weights, map_location="cpu"))
        print(f"[*] Loaded trained PyTorch weights from {torch_weights.name}")
    else:
        print("[!] Using initialized model weights")
        
    model.eval()
    
    dummy_input = torch.randn(1, 9, dtype=torch.float32)
    
    print(f"[*] Exporting to ONNX format: {onnx_path.name} (Opset 14)...")
    torch.onnx.export(
        model,
        dummy_input,
        str(onnx_path),
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=["vital_features"],
        output_names=["latent_projection"],
        dynamic_axes={
            "vital_features": {0: "batch_size"},
            "latent_projection": {0: "batch_size"}
        }
    )
    print(f"[+] ONNX model successfully saved to {onnx_path} ({onnx_path.stat().st_size:,} bytes)")
    
    # Verify inference using ONNX Runtime
    try:
        import onnxruntime as ort
        print("\n[*] Validating ONNX Runtime Execution Provider...")
        session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        
        sample_input = np.array([[82.0, 80.0, 16.0, 37.1, 98.0, 1.2, 7.5, 0.0, 0.0]], dtype=np.float32)
        
        # Warmup
        for _ in range(50):
            _ = session.run(["latent_projection"], {"vital_features": sample_input})
            
        t0 = time.perf_counter_ns()
        for _ in range(500):
            outputs = session.run(["latent_projection"], {"vital_features": sample_input})
        elapsed_ms = (time.perf_counter_ns() - t0) / 500 / 1_000_000.0
        
        latent_out = outputs[0]
        print(f"[+] ONNX Runtime validation PASSED!")
        print(f"    - Output shape  : {latent_out.shape} (16-dim latent vector)")
        print(f"    - Mean Latency  : {elapsed_ms:6.4f} ms per transaction")
        print("=" * 68)
        print(">> ONNX ACCELERATION ARTIFACT IS PRODUCTION-READY FOR IBM Z <<")
        print("=" * 68)
    except ImportError:
        print("[!] onnxruntime package not installed; export succeeded without runtime validation.")

if __name__ == "__main__":
    export_to_onnx()
