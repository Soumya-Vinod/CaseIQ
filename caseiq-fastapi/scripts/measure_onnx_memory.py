"""Same measurement as measure_embedder_memory.py, but for the ONNX Runtime
path -- run in .venv_onnx_test, which has NO torch installed at all (verified
before this script was written), to get a real production-shaped number
rather than one contaminated by torch still being importable in the same
process. Downloads the model's own published ONNX export (no local
optimum/torch export step involved) and does tokenization + mean-pooling +
L2-normalisation by hand, since sentence-transformers itself isn't available
here either.
"""
import sys
import time

import numpy as np
import psutil

proc = psutil.Process()


def rss_mb() -> float:
    return proc.memory_info().rss / (1024 * 1024)


repo_id = sys.argv[1] if len(sys.argv) > 1 else "sentence-transformers/all-MiniLM-L6-v2"
onnx_file = sys.argv[2] if len(sys.argv) > 2 else "onnx/model.onnx"

print(f"model: {repo_id} ({onnx_file})")
print(f"baseline (interpreter + psutil + numpy): {rss_mb():.1f} MB")

t0 = time.time()
import onnxruntime as ort  # noqa: E402
from huggingface_hub import hf_hub_download  # noqa: E402
from tokenizers import Tokenizer  # noqa: E402

print(f"after imports (onnxruntime, tokenizers):  {rss_mb():.1f} MB  (+{time.time()-t0:.2f}s)")

t0 = time.time()
model_path = hf_hub_download(repo_id, onnx_file)
tok_path = hf_hub_download(repo_id, "tokenizer.json")
print(f"after download (cached after first run):  {rss_mb():.1f} MB  (+{time.time()-t0:.2f}s)")

t0 = time.time()
tokenizer = Tokenizer.from_file(tok_path)
session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
print(f"after loading tokenizer + ONNX session:\n  RSS: {rss_mb():.1f} MB  (load took {time.time()-t0:.2f}s)")


def embed(text: str) -> np.ndarray:
    enc = tokenizer.encode(text)
    input_ids = np.array([enc.ids], dtype=np.int64)
    attention_mask = np.array([enc.attention_mask], dtype=np.int64)
    inputs = {"input_ids": input_ids, "attention_mask": attention_mask}
    if "token_type_ids" in [i.name for i in session.get_inputs()]:
        inputs["token_type_ids"] = np.zeros_like(input_ids)
    outputs = session.run(None, inputs)
    last_hidden = outputs[0]  # (1, seq_len, hidden)
    mask = attention_mask[..., None].astype(np.float32)
    summed = (last_hidden * mask).sum(axis=1)
    counts = np.clip(mask.sum(axis=1), a_min=1e-9, a_max=None)
    pooled = summed / counts
    norm = np.linalg.norm(pooled, axis=1, keepdims=True)
    return (pooled / np.clip(norm, 1e-9, None))[0]


t0 = time.time()
vec = embed("What is the punishment for theft under the Bharatiya Nyaya Sanhita?")
print(f"after one real embed() call:              {rss_mb():.1f} MB  (+{time.time()-t0:.2f}s), dim={len(vec)}")

vec2 = embed(
    "The accused was arrested without a warrant on suspicion of committing theft under "
    "section 303 of the Bharatiya Nyaya Sanhita, 2023, and was produced before the "
    "jurisdictional magistrate within the statutory period.",
)
print(f"after a second, longer embed() call:      {rss_mb():.1f} MB, dim={len(vec2)}")
