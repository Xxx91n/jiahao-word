<h1 align="center">jiahao-word</h1>

<p align="center">
  <a href="README.md">English</a> | <b>中文</b>
</p>

LLM 写出来的话里，常冒出一眼看不懂的词。

这个仓库把这些词和「说人话的说法」对上，也顺手把另一种语言的说法连在一起。

查一个看不懂的词，就能知道它大概在说什么，以及换成中文或英文该怎么说。

只收模型写出来的黑话，翻译腔也算。普通词典里的词不收。

## 怎么查词

查词页面在 `api/index.html`。它还没上线，本地想看，就在仓库根目录跑 `python -m http.server --bind 127.0.0.1`，再打开 `http://localhost:8000/api/`。输入框里打一个词，点「查」，就能看到它的大白话、另一种语言怎么说，以及它落在哪些组。

每组显示组号、标签，每条词显示它用在什么场合（`env`）和它是从哪个 issue 进来的。标签和 `env` 可能是空的，有内容时靠它们挑。一个词可能落到好几个组，自己挑对的那个。

某门语言下面是空的，说明那门语言暂时没有说法，不是数据漏了。这个词要是在另一门语言里有，页面会说这门语言里没有、另一门里有，并给一条换语言查的链接；两边都没有，才说「库里还没有这个词」，再给一个开新词 issue 的入口。

### 给脚本用

页面查的东西都在 [api/data.json](api/data.json)，一个整包，`format` 是这份数据的格式版本。键在生成时就算好了：去掉首尾空格，英文按 casefold 折叠，大小写和 `ß` 这类写法算同一个。比如 `words.en.leverage` 就是这个词落到的组数组。每组带 `group`、`label`、一张平铺的 `entries` 表（每条有 `lang`、`word`、`kind`、`env`、`issue`），再加按语言分好的 `zh`、`en` 两栏，页面就靠这两栏渲染。

按语言的薄索引也还在：`index/zh.json`、`index/en.json`。命令行搜用 `grep -i -A 20 '词' index/zh.json` 查中文，`grep -i -A 20 'word' index/en.json` 查英文，把匹配行和后面的候选一起打出来，候选多时把 20 调大。原始数据在 `groups/` 下，一个组一个 YAML 文件，文件名就是组号，比如 `groups/g0001.yaml`。

## 怎么贡献

词要进库，先开 issue，再开 PR 。

- 开新词 issue：用 [「新词入库」模板](https://github.com/Xxx91n/jiahao-word/issues/new/choose)。
- 模板里的四个来源问题都要回答：哪个 Agent、哪个模型、什么思考强度、大致喂了什么上下文。
- 「人话说明」必须由你自己写，Agent 不能代写。
- 完整流程、本地检查命令和审核标准都在 [CONTRIBUTING.md](CONTRIBUTING.md)。

改了 `groups/` 里的数据，要把 `build` 生成的 README 对照表、`index/` 和 `api/data.json` 一起提交。

## 对照表

> BY `python -m jiahao_word build`

<!-- generated:start -->
| 黑话 | 大白话 | 标签 | 用在哪 |
| --- | --- | --- | --- |
<!-- generated:end -->

## 许可证

[CC0 1.0](LICENSE)。
