---
type: Attested Computation
title: Synthetic Attested Computation
runtime: python
parameters:
  - name: input_value
    type: integer
    required: true
executor:
  resource: https://executors.example.invalid/synthetic
  receipt: [execution_id, input_digest]
attester:
  resource: https://attesters.example.invalid/synthetic
---

# Computation

```python
def compute(input_value: int) -> int:
    return input_value * 2
```

