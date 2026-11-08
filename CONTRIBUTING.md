# 怎么贡献

## 先开 issue，再把 PR 一起开上

任何词进库都要走 issue + PR，两个一起开。

- issue 用「新词入库」模板。模板里的四个来源问题必须回答：哪个 Agent、哪个模型、什么思考强度、大致喂了什么上下文。靠它们，别人才能确认这个词真的是模型说出来的。
- issue 里的「人话说明」必须由人自己写，用自己的大白话讲清为什么这个词该进库。Agent 可以帮忙开 issue、开 PR、跑检查，但不能替人写这段说明，也不能替人判断这个词该不该收。
- PR 描述里写上 `Closes #<issue 编号>`。

## PR 里要写什么

PR 模板固定带 `## 人话说明` 段，段名和 `check-pr` 认的一字不差。

- 这段同样要由人写，写清楚为什么改、改完有什么不同。留空或只留模板里的注释，`check-pr` 就会失败，CI 也会拦下来。
- 改动了 `groups/` 数据时，跑 `build` 生成的 README 对照表和 `index/` 索引要一起提交，不要手改生成内容。

## 数据长什么样

一条黑话一个组文件，放在 `groups/` 里，文件名就是编号，从 `g0001` 起只增不改。字段和规则以 [spec #1](https://github.com/Xxx91n/jiahao-word/issues/1) 为准。

## 本地检查

数据进库以后，本地检查用这几条，CI 也跑同样的命令：

```console
python -m jiahao_word check
python -m jiahao_word build
python -m jiahao_word check-pr --body-file pr-body.md
```

`check` 一次把所有数据问题列出来，改完再跑一次；`build` 会改 README 的生成块和 `index/`；`check-pr` 从文件或标准输入读 PR 描述。

PR 上 CI 跑四件事：pytest、对 `groups/` 跑 `check`、跑 `build` 后检查生成文件有没有漂移、对 PR 描述跑 `check-pr`。`main` 分支也会跑前三条。哪条红了就按提示改，改完把生成结果一起提交。

## 怎么审核

维护者看三件事：

1. 这个词是不是模型产出的黑话，来源证据够不够。
2. 「人话说明」是不是人写的、说没说清。
3. 数据和生成文件符不符合格式。

机器只拦格式问题和「人话说明」留空；「这段话是不是人写的」机器判断不了，靠维护者看。看到 Agent 代写的说明，直接打回让人补。
