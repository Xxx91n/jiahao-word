<h1 align="center">jiahao-word</h1>

<p align="center">
  <b>English</b> | <a href="README_zh.md">中文</a>
</p>

When LLMs write, they often throw out buzzwords that make no sense at first glance.

This repo pairs those buzzwords with plain-language equivalents, and links matching phrases across languages.

Look up a word you don't recognize to see what it actually means, and how to say it naturally in English or Chinese.

We only collect AI jargon and translationese. Regular dictionary words are out of scope.

## How to look up words

The lookup page lives at `api/index.html`. It isn't online yet, so to view it, run `python -m http.server --bind 127.0.0.1` from the repo root and open `http://localhost:8000/api/`. Type a word and press the search button to get its plain-language meaning, how to say the same thing in the other language, and every group it lands in.

Each group shows its ID and label; each entry shows `env` (where the word gets used) and the issue it came in through. Label and `env` may be empty; when they are set, they help you pick the right group. One word can land in several groups, so pick the one that fits.

An empty language section means that language has no phrase for the meaning yet, not that data is missing. If the word is in the other language, the page tells you it's missing here but present there, and links you to a lookup in that language. Only when neither language has it does it say the word isn't in the repo yet and offer a link to open a new-word issue.

### For scripts

Everything the page looks up lives in [api/data.json](api/data.json), one whole file; `format` is the shape version. Keys come pre-normalized: leading and trailing spaces trimmed, and English keys case-folded (so `Leverage` and `leverage` land on the same key, and `STRASSE` matches `straße`). For example `words.en.leverage` is the array of groups for that word. Each group has `group`, `label`, a flat `entries` list (`lang`, `word`, `kind`, `env`, `issue`), plus per-language `zh` and `en` slices that the page renders from.

The per-language indexes are still there: `index/zh.json`, `index/en.json`. From a terminal, `grep -i -A 20 'word' index/en.json` searches English and `grep -i -A 20 '词' index/zh.json` searches Chinese; each prints the matching lines and nearby candidates (bump up 20 when there are lots of matches). Raw data sits in `groups/`, one YAML file per group, named by its ID, like `groups/g0001.yaml`.

## How to contribute

To add a word, open an issue first, then open a pull request.

- Open a new-word issue: use the [New Entry template](https://github.com/Xxx91n/jiahao-word/issues/new/choose).
- Answer all four source questions in the template: which agent, which model, what reasoning effort, and roughly what prompt/context you gave it.
- You must write the plain-language explanation yourself—agents cannot write it for you.
- See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow, local check commands, and review standards.

Whenever you change data in `groups/`, run `build` and commit the generated README table, the `index/` files, and `api/data.json` together.

## Comparison Table

> BY `python -m jiahao_word build`

<!-- generated:start -->
| 黑话 | 大白话 | 标签 | 用在哪 |
| --- | --- | --- | --- |
<!-- generated:end -->

## License

[CC0 1.0](LICENSE).
