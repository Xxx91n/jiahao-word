<h1 align="center">jiahao-word</h1>

<p align="center">
  <b>English</b> | <a href="README_zh.md">中文</a>
</p>

When LLMs write, they often throw out buzzwords that make no sense at first glance.

This repo pairs those buzzwords with plain-language equivalents, and links matching phrases across languages.

Look up a word you don't recognize to see what it actually means, and how to say it naturally in English or Chinese.

We only collect AI jargon and translationese. Regular dictionary words are out of scope.

## How to look up words

Use the indexes in this repo:
- Chinese: `index/zh.json`
- English: `index/en.json`

1. Open `index/zh.json` or `index/en.json` in your editor and search for the word. Each word is followed by a bracketed list of every group it belongs to, including the group ID, a label, and `env`. On the command line, run `grep -i -A 20 'word' index/en.json` to show matching lines and nearby candidates (bump up 20 if there are lots of matches). Words in the English index are converted to lowercase, so make sure your query is lowercase too.
2. Once you find it, check which group it maps to, like `g0001`.
3. Open `groups/g0001.yaml`. Inside, you will find the jargon term along with plain-language alternatives in both Chinese and English.

> A single word can belong to multiple groups. Each result includes a group ID, a short label (a quick summary of the group), and `env` (where the word gets used); the label and `env` may be empty, but they help you pick the right group when present. If a language section in a group file is empty, that language simply does not have a matching phrase yet—it is not missing data.

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
