use criterion::{black_box, criterion_group, criterion_main, Criterion};
use apuntador_backend::utils::pkce::{generate_code_challenge, generate_code_verifier};

fn benchmark_code_verifier(c: &mut Criterion) {
    c.bench_function("generate_code_verifier", |b| {
        b.iter(|| generate_code_verifier(black_box(128)))
    });
}

fn benchmark_code_challenge(c: &mut Criterion) {
    let verifier = generate_code_verifier(128);
    c.bench_function("generate_code_challenge", |b| {
        b.iter(|| generate_code_challenge(black_box(&verifier)))
    });
}

criterion_group!(benches, benchmark_code_verifier, benchmark_code_challenge);
criterion_main!(benches);
