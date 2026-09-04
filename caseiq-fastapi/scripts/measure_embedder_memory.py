"""One-off memory measurement, not part of the app -- run manually in the
throwaway .venv_embed_test venv to get REAL numbers before committing to an
approach, per instruction. Reports RSS at three points: baseline (just the
Python interpreter + psutil), after import, after loading the model and
running one real embedding call (this is the number that matters -- some
frameworks lazy-load weight tensors on first inference, not on load).
"""
import sys
import time

import psutil

proc = psutil.Process()


def rss_mb() -> float:
    return proc.memory_info().rss / (1024 * 1024)


model_name = sys.argv[1] if len(sys.argv) > 1 else "sentence-transformers/all-MiniLM-L6-v2"

print(f"baseline (interpreter + psutil):        {rss_mb():.1f} MB")

t0 = time.time()
from sentence_transformers import SentenceTransformer  # noqa: E402

print(f"after `import sentence_transformers`:    {rss_mb():.1f} MB  (+{time.time()-t0:.2f}s)")

t0 = time.time()
model = SentenceTransformer(model_name)
print(f"after loading '{model_name}':\n  RSS: {rss_mb():.1f} MB  (load took {time.time()-t0:.2f}s)")

t0 = time.time()
vec = model.encode("What is the punishment for theft under the Bharatiya Nyaya Sanhita?")
print(f"after one real embed() call:             {rss_mb():.1f} MB  (+{time.time()-t0:.2f}s), dim={len(vec)}")

# A second, different-length input -- catches any lazy allocation that only
# happens for a longer sequence than the first call used.
vec2 = model.encode(
    "The accused was arrested without a warrant on suspicion of committing theft under "
    "section 303 of the Bharatiya Nyaya Sanhita, 2023, and was produced before the "
    "jurisdictional magistrate within the statutory period.",
)
print(f"after a second, longer embed() call:     {rss_mb():.1f} MB, dim={len(vec2)}")
