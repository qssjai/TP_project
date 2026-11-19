# Changelog

Формат: [Keep a Changelog](https://keepachangelog.com/uk/1.1.0/), версії за [SemVer](https://semver.org/lang/uk/).

## [0.3.0] - 2026-11-19

### Додано
- FORM-03: Pumping Lemma Explorer (`sipl pump`): перебір усіх розкладів `u t₁ x t₂ v`, перевірка накачки, перевірка одного розкладу (`--split`), належність слова через CYK, готові мови та предикати.
- REL-01: GitHub Actions (ruff, pytest на Python 3.10–3.12, збірка пакета).
- REL-02: workflow випуску за тегом `v*` та цей CHANGELOG.

### Виправлено
- `--pred` і `--word-expr`: вирази з `lambda` та генераторами бачать змінні `w` і `k`.

## [0.2.0] - 2026-11-19

### Додано
- FORM-02: системи рівнянь над мовами (`sipl eq convert|solve|build`): наближення X₀=∅, X₁, …, нерухома точка, порівняння з граматикою, конструктор родини `{p xⁿ m yⁿ s}`.

## [0.1.0]

### Додано
- FORM-01: CFG Toolkit (несуттєві символи, ε-правила, нормальна форма Хомського).
- FORM-04: Derivation Explorer (виведення, дерева, неоднозначність, експорт text/json/dot).
