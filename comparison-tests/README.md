# Comparison Tests - Parity Validation

Infrastructure for validating behavioral parity between Python and Rust implementations.

## Strategy

1. **Test Vector Generation**: Extract inputs/outputs from Python implementation
2. **Parity Testing**: Feed same inputs to both implementations, compare outputs
3. **Benchmarking**: Measure performance differences

## Directory Structure

```
comparison-tests/
├── scenarios/          # Test scenarios (JSON format)
│   ├── pkce/           # PKCE code generation tests
│   ├── oauth/          # OAuth flow tests
│   └── endpoints/      # API endpoint tests
│
└── scripts/            # Test utilities
    ├── generate_vectors.py     # Extract test vectors from Python
    ├── run_parity_tests.sh     # Run parity validation
    └── benchmark_compare.sh    # Performance comparison
```

## Test Vectors Format

```json
{
  "scenario": "pkce_code_verifier_generation",
  "test_cases": [
    {
      "name": "standard_length_128",
      "input": { "length": 128 },
      "expected_properties": {
        "min_length": 43,
        "is_base64url": true,
        "no_padding": true
      }
    }
  ]
}
```

## Usage

### Generate Test Vectors (from Python)

```bash
cd comparison-tests/scripts
python generate_vectors.py --module pkce --output ../scenarios/pkce/
```

### Run Parity Tests

```bash
./scripts/run_parity_tests.sh --scenario pkce
./scripts/run_parity_tests.sh --scenario oauth
./scripts/run_parity_tests.sh --all
```

### Benchmark Comparison

```bash
./scripts/benchmark_compare.sh --operation pkce_generation
./scripts/benchmark_compare.sh --operation oauth_flow
```

## Status

- [ ] Test vector generator (Python script)
- [ ] PKCE parity tests
- [ ] OAuth flow parity tests
- [ ] Endpoint response parity tests
- [ ] Performance benchmarking
- [ ] CI/CD integration

## Parity Requirements

For a feature to be considered "at parity":

1. **Functional Equivalence**: Same inputs produce identical outputs
2. **Error Handling**: Same errors for invalid inputs
3. **Edge Cases**: Boundary conditions handled identically
4. **Performance**: Rust should be ≥ 5x faster (not blocking parity)

## Example: PKCE Parity Test

```python
# Python implementation
from apuntador.utils.pkce import generate_code_verifier, generate_code_challenge

verifier = generate_code_verifier(128)
challenge = generate_code_challenge(verifier)
```

```rust
// Rust implementation
use apuntador_backend::utils::pkce::{generate_code_verifier, generate_code_challenge};

let verifier = generate_code_verifier(128);
let challenge = generate_code_challenge(&verifier);
```

**Validation**:
- Both verifiers are base64url encoded, no padding, ≥43 chars
- Same verifier produces same challenge (deterministic SHA256)
- Challenge is 43 chars (256-bit hash, base64url encoded)

## Next Steps

1. Create `scripts/generate_vectors.py`
2. Extract test vectors for PKCE utilities
3. Create parity test runner
4. Add CI/CD job to run parity tests on PRs
5. Expand to OAuth flows and endpoints

## Notes

- Test vectors should cover happy path, edge cases, and error conditions
- Focus on deterministic operations first (PKCE, hashing)
- Random operations (state generation) require property-based testing
- Performance benchmarks are informative, not blocking
