# Benchmarks

One directory per benchmark: loader, runner and scoring shared by every model measured on it.

## `injection`

Prompt-injection detection through the Inola API (real time or the Batch API): LLMail-Inject (Table 3 of the paper),
NotInject (over-defense) and Quadrat-IPI (recall at fixed false-alarm rates). See [injection/README.md](injection/README.md).
