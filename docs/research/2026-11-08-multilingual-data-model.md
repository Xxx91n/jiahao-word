# 跨语言「意思组」的数据模型：调研笔记

日期：2026-11-08
问题：一个跨语言的意思组（同一种含义在不同语言里的一组近义大白话）该怎么建库？组的唯一身份怎么定、各语言的词怎么检索进同一个组、有没有成熟标准能直接用、有没有现成的大白话词表。

来源：atomcode 深调研一轮（Exa + Tavily + AnySearch，含 8 篇一手文档核验）。下面每条结论都标了出处编号，编号对应文末清单。

## 一句话结论

意思组不要用任何一种语言的词当名字，也不要用词在文件里的位置当编号。用一个跟语言无关的稳定编号（比如 `i77784` 这种「字母 + 数字」），每条词记录自己带语言标签。查的时候先按语言找词，再顺着编号找到同组的其他语言。

Confidence：高。WordNet/CILI、Wikidata、TBX、OntoLex-Lemon 四条线都有官方一手文档，结论互相印证。

## 三条成熟做法

| 做法 | 组的身份 | 词怎么挂 | 出处 |
|---|---|---|---|
| WordNet / OMW 用 CILI | `i` + 数字，永久不改、不复用 | 每种语言自己的同义词组（synset）各有一个本地编号，靠 `ili` 属性指到同一个 CILI 号 | 1, 2, 3 |
| TBX（ISO 30042） | `conceptEntry id="c001"` | 概念下按语言分区 `langSec`，每个分区里可以有多个词的 `termSec` | 7, 8, 9 |
| OntoLex-Lemon（W3C） | `LexicalConcept`，随便给个 URI | `LexicalEntry → sense → LexicalConcept`，词条带 `dct:language` | 10 |

CILI 的一手例子很能说明问题：apricot 这个词在 WordNet 3.0 里的编号是 `07750872-n`、3.1 里是 `07766848-n`、德语 OdeNet 里是 `13235-n`，三个编号全不一样，但它们共用同一个 CILI 号 `i77784`（出处 1、3）。所以拿「本地编号」当跨语言主键一定会崩，因为换个版本编号就变了。

反例是 Wikidata：它故意不建全局意思组，Sense 挂在单语言词位下面，跨语言靠「义项指向同一个 Q 条目」来关联；官方文档自己警告，两个义项指向同一个 Q 条目**不等于同义**（hot 和 cold 都指向「温度」）（出处 5、6）。

## 检索怎么做

推荐「概念为中心」：查一个语言里的词 → 命中后上溯到组编号 → 再往下查其他语言。官方支持的三条路径：

1. 每个语言一个分区（TBX 的 `langSec`、OMW 的每种语言一个 wordnet、lemon 的词条带 `dct:language`）；分区内按词面查，命中就上溯。
2. WordNet 的 `translate` API 直接靠共享的 ILI 号拿到目标语言的说法；词级翻译返回「每个义项 → 译文列表」的映射。一词多义造成的跨语言不对称，就是靠这种结构化的方式处理的（出处 1）。
3. OntoLex 把翻译等价分成三级：共享本体（最等）→ sense 级翻译（Translation）→ 只能说「可以这么翻」（translatableAs）。官方明确允许 `Postleitzahl` 对 `zip code` 这种「指称不同但能互译」的情况（出处 10）。

结论：组里的词不要一刀切成「完全同义」，要显式标等价程度。

## 已知的坑

- **翻译等价不等于同义**（Kwong 2018）：把双语词典的译文直接塞进同义词组，会造出一堆「假同义词」，形容词尤其严重；真正完全等价的词，除了专业术语，极少（出处 14）。
- **拿英语当中心会失真**（Springer 2023 综述）：以英语为 hub 的 OMW 类资源表达不了英语里没有的含义等价，比如法语 `fleuve` 和匈牙利语 `folyam`；只有 hub 可扩展的方案（OMW2、BabelNet、UKC）才能表达。OMW2 和 UKC 还显式支持「词汇空缺」标注（出处 13）。所以不要拿英文做主心骨，编号要独立于任何自然语言。
- **词汇空缺要算正常状态**：日语把 rice 分成 `稲`/`米`/`飯` 三个概念，英语只有一个词。模型必须能表达「这个语言暂时没有对应说法」，而不是当成数据缺失（出处 13、14）。
- **版本兼容**：WordNet 升级会让本地编号全变；CILI 的准入规则是「有新概念必须有某语言同义词组支撑、和已有概念有关系、有唯一英文定义」，编号永久不变、永不删除（出处 2、3）。

## 现成的「行话 → 大白话」词表

| 资源 | 内容 | 规模/许可 | 出处 |
|---|---|---|---|
| PlainLanguage.gov word suggestions | 美国 GSA 官方「别说 X、要说 Y」对照表 | 约 180 对，美国政府作品（公域） | 15 |
| GOV.UK "words to avoid" | 英国政府写作指南，带理由和替代词 | 持续维护 | 16 |
| NoteAid-README（EMNLP 2024） | 医学行话 → 通俗解释，专家标注 | 51,623 对术语-解释 / 308,242 条带上下文样本，CC-BY-NC 4.0 | 17 |
| CodersLingo | IT 英语术语 + 通俗定义 | 643 词，CC-BY 4.0，JSON/CSV | 18 |
| aiglossary.news | AI 行话 → 记者能懂的解释 | 早期阶段，开源 | 19 |

**最大的空缺：中 ↔ 英的行话对照词表，没有找到成熟的开源资源。** 英语那边有政府词表和医学标注数据，中文这边基本是空白。

## 本仓库可以借的结构（提案，未定稿）

调研给的综合结构（出处 1–13）：

```
组（语言中立编号 id，永不复用）
  ├─ 简短解释（可以多语言，至少一种）
  ├─ 分类/领域（可选）
  └─ 词记录[]（每条都带语言标签）
       ├─ language: zh / en …（BCP-47，如 zh-Hant）
       ├─ term: 词本身
       ├─ 备注：语域、语境、用在哪（可选）
       └─ 跟组的关系：完全等价 / 部分等价 / 只能说能这么翻 / 空缺
```

检索路径：`(语言, 词) → 词记录 → 组编号 → 同组其他语言的词记录`。

出口格式不必自己发明：要交换就出 TBX（翻译行业用）或 OntoLex-Lemon RDF（Linked Data 用）。通用词汇可以直接复用 OMW/CILI 的现成编号，不用自己起一套命名空间。

## 出处清单

1. Wn Interlingual Queries 指南 — https://wn.readthedocs.io/en/stable/guides/interlingual.html
2. CILI 仓库 — https://github.com/globalwordnet/cili
3. Global Wordnet Grid 论文（GWC 2016） — https://aclanthology.org/2016.gwc-1.59.pdf
4. Bond et al., Some Issues with Building a Multilingual Wordnet（LREC 2020） — https://aclanthology.org/2020.lrec-1.390.pdf
5. Wikidata Lexicographical data 文档 — https://www.wikidata.org/wiki/Wikidata:Lexicographical_data/Documentation
6. WikibaseLexeme 数据模型 — https://www.mediawiki.org/wiki/Extension:WikibaseLexeme/Data_Model
7. flashterm：TBX 三层结构 — https://www.flashterm.eu/en/tbx/tbx-structure-termentry-langset-tig.html
8. ISO 30042:2019 — https://www.iso.org/standard/62510.html
9. NISO STS：TBX termEntry — https://niso-sts.org/tbx-html/element/tbx-termEntry.html
10. OntoLex-Lemon Final Model Specification — https://www.w3.org/2016/05/ontolex/
11. BabelNet About — https://babelnet.org/about
12. Navigli & Ponzetto, BabelNet（ACL 2010） — https://aclanthology.org/P10-1023.pdf
13. Giunchiglia et al., Representing interlingual meaning（2023） — https://link.springer.com/article/10.1007/s10462-023-10427-1
14. Kwong, Translation Equivalence and Synonymy（GWC 2018） — https://aclanthology.org/2018.gwc-1.23/
15. PlainLanguage.gov 词表（raw） — https://raw.githubusercontent.com/GSA/plainlanguage.gov/main/_pages/guidelines/words/use-simple-words-phrases.md
16. GOV.UK clear language — https://guidance.publishing.service.gov.uk/writing-to-gov-uk-standards/writing-guidelines/clear-language/
17. NoteAid-README（EMNLP 2024 Findings） — https://doi.org/10.18653/v1/2024.findings-emnlp.737
18. CodersLingo — https://coderslingo.com
19. aiglossary.news — https://github.com（仓库名见调研原文；未单独打开核验）

## 没查到的

- 中 ↔ 英行话对照没有成熟开源词表；最接近的是英语医学的 NoteAid 和欧盟 IATE（免费但不可再分发）。
- ISO 30042 全文要付费；结构结论靠 flashterm 和 NISO 两份二手文档（两家一致，另有 ISO 摘要佐证）。
- Wikidata 词位模型的规模化质量（义项覆盖率、跨语言对齐准确率）没有系统评测，只有单语言案例。
- CILI 主要收通用词汇；垂直领域的新概念要走 propose 流程，实际吞吐没调研。
