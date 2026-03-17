# Ablation Study Tables

For ablation studies, use the `generate_ablation_table` function directly from Python, or structure your input JSON with `"table_type": "ablation"`.

## Input Format for Ablation Tables

```json
{
  "table_type": "ablation",
  "experiments": [
    {
      "name": "Full Model",
      "components": {"Attention": true, "CRF": true, "CharEmbed": true},
      "metrics": {"F1": 91.2, "Accuracy": 94.1}
    },
    {
      "name": "w/o Attention",
      "components": {"Attention": false, "CRF": true, "CharEmbed": true},
      "metrics": {"F1": 88.5, "Accuracy": 92.3}
    },
    {
      "name": "w/o CRF",
      "components": {"Attention": true, "CRF": false, "CharEmbed": true},
      "metrics": {"F1": 89.1, "Accuracy": 92.8}
    }
  ],
  "component_cols": ["Attention", "CRF", "CharEmbed"],
  "metrics": ["F1", "Accuracy"],
  "caption": "Ablation study on CoNLL-2003.",
  "label": "tab:ablation"
}
```

## Generated LaTeX

```latex
\begin{table}[htbp]
  \centering
  \caption{Ablation study on CoNLL-2003.}
  \label{tab:ablation}
  \begin{tabular}{lcccc c}
    \toprule
    Model & Attention & CRF & CharEmbed & F1 & Accuracy \\
    \midrule
    Full Model   & \checkmark & \checkmark & \checkmark & 91.20 & 94.10 \\
    w/o Attention & — & \checkmark & \checkmark & 88.50 & 92.30 \\
    w/o CRF      & \checkmark & — & \checkmark & 89.10 & 92.80 \\
    \bottomrule
  \end{tabular}
\end{table}
```

Requires `\usepackage{booktabs}` and `\usepackage{amssymb}` (for `\checkmark`) in the LaTeX preamble.
