# jiahao-word

## Agent skills

### Issue tracker

Issues and specs live as GitHub issues in `Xxx91n/jiahao-word`, driven by the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles use the label strings of the same name: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` at the repo root plus `docs/adr/`. See `docs/agents/domain.md`.

### 贡献规矩

- 词进库走 issue + PR，两个一起开。
- issue 和 PR 里的「人话说明」由人自己写。Agent 不能代替人写「人话说明」，也不能替人下判断说这个词该进库。这段缺了，Agent 就停下来等人补。
- issue 模板里的四个来源问题（哪个 Agent、哪个模型、什么思考强度、大致喂了什么上下文）必须回答，不能瞎猜。
