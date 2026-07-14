# Frozen deterministic benchmark (v0.3.0)

Reproduction (LLM-disabled, fully deterministic):

    simcontract run --domain energy_market_v1 --scenario baseline_v1 \
        --seed 73 --rounds 5 --controllers all=rule --out /tmp/bench
    simcontract verify --bundle /tmp/bench   # content_hash_ok + files_ok
    simcontract replay --bundle /tmp/bench   # REPLAY EQUIVALENT

Expected canonical content hash (same code + seed reproduce this exactly):

    dd73a35091a5fb609cea12fb8b84fa4858d7cbf87d0c4469765d672a3b0be7bc

This is a reproducibility / expected-output hash. The archival-integrity
checksums of the frozen files are in SHA256SUMS.
