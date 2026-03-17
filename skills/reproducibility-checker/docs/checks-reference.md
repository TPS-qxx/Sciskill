# Reproducibility Checks Reference

## Error-severity Checks

### Dependency specification file exists (−15 pts)

**What is checked**: Presence of any of: `requirements.txt`, `requirements/*.txt`, `environment.yml`, `environment.yaml`, `pyproject.toml`, `setup.py`, `setup.cfg`, `Pipfile`, `conda.yaml`.

**Why it matters**: Without a dependency file, users cannot reproduce the exact software environment. Version mismatches are the single most common cause of reproducibility failures.

**How to fix**:
```bash
# Generate from current environment:
pip freeze > requirements.txt

# Or with version bounds (preferred):
# numpy>=1.24,<2.0
# torch>=2.0,<3.0
```

---

### README with setup instructions (−15 pts)

**What is checked**: A README file exists AND contains words related to both installation (`install`, `requirements`, `setup`, `pip`) AND usage/execution (`usage`, `run`, `train`, `evaluate`, `example`).

**Minimum README structure**:
```markdown
## Installation
pip install -r requirements.txt

## Usage / Training
python train.py --config configs/default.yaml

## Evaluation
python evaluate.py --checkpoint checkpoints/best.pt --data data/test/
```

---

## Warning-severity Checks

### Random seed is fixed (−7 pts)

**What is checked**: Any `.py` file contains a call to `random.seed()`, `np.random.seed()`, `torch.manual_seed()`, `torch.cuda.manual_seed()`, `tf.random.set_seed()`, or `set_seed()`.

**Recommended pattern**:
```python
import random, numpy as np, torch

def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

set_seed(42)
```

---

### Training scripts set random seeds — AST check (−7 pts)

**What is checked**: Python files named `train*.py`, `main*.py`, `run*.py`, or `finetune*.py` that import `random`, `numpy`, or `torch` are analyzed with the AST to confirm they also call a seed function.

---

### No hardcoded absolute paths (−7 pts)

**What is checked**: `.py` files for strings matching `/home/`, `/Users/`, `/root/`, `C:\`, `/data/`.

**How to fix**: Replace with `argparse` arguments or relative paths:
```python
# Bad:
data_dir = "/home/alice/datasets/conll2003"

# Good:
parser.add_argument("--data-dir", default="data/conll2003")
```

---

### Data download/preparation script exists (−7 pts)

**What is checked**: Files matching `download_data*`, `get_data*`, `prepare_data*`, `preprocess*`, `data/README*`, `scripts/download*`, `Makefile`; or `.sh` / `Makefile` files containing `wget`, `curl`, or `gdown`.

---

## Info-severity Checks

### Model checkpoint or download link available (−3 pts)

**What is checked**: Presence of `.ckpt`, `.pth`, `.pt`, or `.bin` files, OR README contains the words "checkpoint", "pretrained", "model weights", or "download model".

### Experiment configuration files exist (−3 pts)

**What is checked**: Presence of `config*`, `configs/`, `*.yaml`, `*.yml`, `*.json`, or `hparams*` files.

**Best practice**: One config file per experiment. Example: `configs/bert_base_conll.yaml`.

### License file exists (−3 pts)

**What is checked**: `LICENSE` or `LICENCE` file in the root directory.

**Common choices for research code**: MIT (most permissive), Apache 2.0, CC BY 4.0.

### Docker / container support (−3 pts)

**What is checked**: Presence of `Dockerfile`, `docker-compose.yml`, or `.devcontainer/`.

**Minimal Dockerfile for PyTorch**:
```dockerfile
FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
```
