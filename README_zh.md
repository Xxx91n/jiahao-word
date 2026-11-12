<h1 align="center">jiahao-word</h1>

<p align="center">
  <a href="README.md">English</a> | <b>中文</b>
</p>

LLM 写出来的话里，常冒出一眼看不懂的词。

这个仓库把这些词和「说人话的说法」对上，也顺手把另一种语言的说法连在一起。

查一个看不懂的词，就能知道它大概在说什么，以及换成中文或英文该怎么说。

只收模型写出来的黑话，翻译腔也算。普通词典里的词不收。

## 怎么查词

使用仓库内的索引：
- 查中文: `index/zh.json`
- 查英文: `index/en.json`

1. 用编辑器打开 `index/zh.json` 或 `index/en.json`，搜你要查的词。每个词后面紧跟一个方括号，里面就是它落到的所有组，带组编号、标签和 `env`。在命令行搜的话，用 `grep -i -A 20 '词' index/en.json`，把匹配行和后面的候选一起打出来，候选多时把 20 调大。英文索引里的词都转成了小写，查询词也要转成小写。
2. 搜到以后，看它落在哪个组，比如 `g0001`。
3. 打开 `groups/g0001.yaml`。里面是这个意思对应的黑话，以及中文和英文里的各种大白话说法。

> 一个词可能落到好几个组。每个结果都带组编号、一句标签（这组大概在说什么）和 `env`（这个词用在什么场合）；标签和 `env` 可能是空的，有内容时靠它们挑。组文件里某种语言下面是空的，表示这个语言暂时没有对应说法，不是数据漏了。

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
