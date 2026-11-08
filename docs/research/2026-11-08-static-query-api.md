# 查询接口：免费、不走 Cloudflare、能静态就静态

调研日期：2026-11-08

## 一句话结论

纯静态托管能做到「路径带词、返回 JSON」，做不到「查询串带词、服务端当场算、返回 JSON」。你写的 `api/word=咬人&env=...&lang=zh` 本身还少了 `?`，正确写法是 `api/?word=咬人&env=...&lang=zh`。这个形式要么交给浏览器里的 JS 处理（返回的是网页，不是 JSON），要么加一个小小的函数。数据量很小，不需要更高级的数据库，生成的 JSON 就够当数据库用。

## 先对齐你想要的调用

你描述的是：

```
https://jiahao-word.xxx91n.com/api/?word=咬人&env=写代码的时候说删除会咬人&lang=zh
→ 返回「造成影响」
```

现在仓库里的数据结构是：一个词落到一个或多个组，组里有黑话、各语言的大白话、以及每个词的 `env`。`env` 是自由文本，不是固定的枚举值。这一点决定了下面的方案能走到哪一步。

中文放进 URL 必须百分号编码，比如 `咬人` 是 `%E4%B8%B6%E4%BA%BA`。浏览器地址栏会自动处理，`curl` 不会。

## 静态托管的硬边界

静态服务器只按路径找文件，查询串在服务端不参与路由，也改不了响应的 `Content-Type`。所以只有三种形态：

1. **一个 JS 页面读查询串**。服务器返回 `200 text/html`，页面在浏览器里取数据、过滤、显示。人用很舒服，机器拿到的是 HTML。
2. **构建时预生成每个词的 JSON，放在路径上**。比如 `api/zh/咬人.json`，返回 `200 application/json`，一次请求拿到结果。这是真正的静态 JSON 接口，但 URL 不是 `?word=`。
3. **一个全量 JSON，调用方自己查**。一次 GET 拿全部数据（几千条大概 1–3 MB），在本地过滤。查询逻辑在调用方，不在服务器。

`?word=...&env=...` 这种「服务端按上下文挑一条」的能力，纯静态给不了。`env` 要么只作为候选展示，让人或调用方自己挑；要么由一个函数去算。

## 已核实的事实

- GitHub Pages 是纯静态，站点上限 1 GB，带宽软上限 100 GB/月，每小时 10 次构建（用自定义 Actions 部署不受这条限制）。不能拿来跑在线生意、电商或 SaaS。来源 1。
- GitHub Pages 的响应带 `Access-Control-Allow-Origin: *`，缓存 `max-age=600`。我实测过。别的站点在浏览器里直接取 JSON 可以读，数据更新最多晚十分钟。来源 2。
- 子域名加 GitHub Pages 自定义域，是在 DNS 里加一条 CNAME 指到 `Xxx91n.github.io`，不是 TXT。GitHub 要验证域名归属时才会另给一条 TXT。HTTPS 由 GitHub 自动签。来源 3。
- Netlify 免费档是 300 credits/月，不能自动续；换算：1 万次请求 = 2 credits，1 GB 流量 = 20 credits，函数计算 1 GB-小时 = 10 credits。2025-09-04 起新账号都走这套。来源 4。
- Netlify 的重定向支持按查询参数捕获，但官方写法是把参数按空格放在路径后面，例如 `/ word=:word lang=:lang /api/:lang/:word.json 301`；不是 `/?word=:word&lang=:lang`。文档只说 200/301/302 会透传查询串，多带参数时还匹不匹配、非 ASCII 怎么编码，都没写清。来源 5。所以这条只能当备选，不能当主方案。
- Deno Deploy 免费档：100 万请求/月、20 GiB 出网、10 CPU 小时、5 个自定义域；官方措辞是「personal use and smaller projects」，没明说商用禁止，但也不等于允许。来源 6。
- Vercel Hobby：100 GB 传输、100 万 CDN 请求、100 万函数调用、4 CPU 小时；明确只许非商业的个人用途。来源 7。这个项目要是以后接广告或收费，就别用 Hobby。
- 成熟例子：hanzi-writer-data 把每个汉字做成一个 JSON，走 CDN 路径访问，返回 `application/json` 且带 CORS。这是「预生成每键 JSON」这条路线的现成样板。来源 8。kaikki.org 是按语言整包下载的静态 JSONL，不是按词端点。来源 9。

## 方案对比

| 方案 | 能不能 `?word=` 返回 JSON | 自定义域 | 免费额度 | 信用卡 | 主要坑 |
| --- | --- | --- | --- | --- | --- |
| GitHub Pages，纯静态 | 不能；只能路径 JSON 或 JS 页面 | 是，CNAME | 1 GB 站点、100 GB/月 | 不要 | 查询串得靠前端；不能商用 |
| Netlify，静态 + 函数 | 能 | 是 | 300 credits/月 | 不要 | 额度按流量和请求混算；函数要另写 |
| Deno Deploy，函数 | 能 | 是（5 个） | 100 万请求/月、20 GiB | 不要 | 免费档用途措辞含糊 |
| Vercel Hobby，函数 | 能 | 是 | 100 万调用、100 GB | 不要 | 只许非商业 |
| Supabase Edge Functions | 能 | 免费档不行 | 50 万调用 | 不要 | 免费档没有自定义域，闲置会暂停 |
| Val.town | 能 | 免费档不行 | 10 万次/天 | 不要 | 没有自定义域 |
| Google Apps Script | 能 | 不行，固定域名 | 有配额 | 不要 | 拿不到自己的域名 |
| AWS / Azure 免费层 | 能 | 要自己配 | 已改规则，不再稳 | 要 | 免费期和条款都变了 |
| Oracle 永久免费 VM | 能 | 自己配 | 10 TB/月出网 | 要 | 空闲实例可能被回收，还要自己打补丁 |

Supabase、Val.town、Apps Script、AWS、Azure、Oracle 这几条是子代理查到的，我只抽查了 GitHub、Netlify、Deno、Vercel 的官方页，没逐页核对它们。

## 推荐

**首选：纯静态，路径 JSON + 一个查询页。**

- `build` 除了现在的 `index/zh.json`、`index/en.json`，再生成一份给接口用的数据：要么一个全量 `api/data.json`，要么每个词一份 `api/<lang>/<词>.json`。
- 机器调用走路径，例如 `api/zh/%E4%BD%A0.json`，一次拿到该词的全部候选组：组号、标签、`env`、各语言大白话、issue 链接。
- 人调用走 `api/?word=...&env=...&lang=...` 的页面。页面读查询串，在浏览器里按 `env` 过滤，显示结果。它返回 HTML，不是 JSON，这一点要在文档里写清楚。
- 托管就 GitHub Pages，一个仓库、一条 CNAME、零额外服务、零信用卡。数据更新最多晚十分钟。

这条路不需要数据库。需要的话，函数版读的也是同一个生成的 JSON。

**次选：真要「查询串进、JSON 出」，用 Netlify（静态 + 一个函数）。**

- 站点和函数同一个域名、同一张证书，不用另开服务。
- 函数只做一件事：读构建时带上去的 JSON，按 `word` 和可选的 `env` 返回一条或几条候选。
- 300 credits/月 对一个小词库够用：按 1 万请求 2 credits 算，理论上一百多万次；但流量也吃 credits，别让函数每次返回整包数据。
- 缺点是多一个平台、多一套部署配置。

Deno Deploy 可以当备选，100 万请求/月、无冷启动；但它免费档的用途措辞不够硬，商用前景不明确时别把这个当长期承诺。

**不建议：** Vercel Hobby（非商业限定）；Netlify 的查询参数重定向单独扛（多参数和编码行为没写清，客户端不跟随 301 还会拿到 301）；Supabase / Val.town / Apps Script（免费档拿不到自己的域名）；Oracle 空闲 VM（低流量正好踩回收条件）。

## 对你那句「数据库要更高级」的回答

不用。数据是几百到几千条，生成一个 JSON 文件就是全部「数据库」。函数版也只是读这个文件，不查库。只有当你想让 `env` 做语义匹配（比如「写代码的时候说删除会咬人」自动对上某个组的 `env`），才需要额外的规则、向量或模型；那是另一件事，不是托管方案能解决的。

## 还没定、下次 grill 要问的

1. 接口形态：路径 JSON（机器友好）、查询页（人友好），还是加函数做真正的 `?word=&env=` JSON。
2. `env` 到底干什么：只展示候选、精确匹配、包含匹配，还是拿来做语义挑选。
3. 返回一条还是多条候选；一条时凭什么挑。
4. 词放在路径里怎么防脏字符：中文原名、slug、还是短哈希；英文要不要统一小写。
5. 站点放哪：GitHub Pages 的 Actions 产物，还是 Netlify 同域。
6. 数据还是空的，先上空页面，还是等第一批真词进来再上。

## 来源

1. GitHub Pages 限制：https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits （已抽查）
2. GitHub Pages 响应头：`curl -I https://pages.github.com/` 实测，2026-11-08
3. GitHub Pages 自定义域：https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site
4. Netlify credits：https://docs.netlify.com/manage/accounts-and-billing/billing/billing-for-credit-based-plans/credit-based-pricing-plans/ （已抽查）
5. Netlify 重定向参数：https://docs.netlify.com/manage/routing/redirects/redirect-options/ （已抽查）
6. Deno Deploy 定价：https://deno.com/deploy/pricing （已抽查）
7. Vercel Hobby：https://vercel.com/docs/plans/hobby （已抽查）
8. hanzi-writer-data：https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0.1/%E4%BD%A0.json （子代理实测）
9. kaikki.org：https://kaikki.org/dictionary/English/index.html
10. Supabase 定价：https://supabase.com/pricing
11. Val.town 定价：https://www.val.town/pricing
12. Apps Script 配额：https://developers.google.com/apps-script/guides/services/quotas
13. AWS Lambda 定价：https://aws.amazon.com/lambda/pricing/
14. Azure Functions 定价：https://azure.microsoft.com/en-us/pricing/details/functions/
15. Oracle Always Free：https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm

## 这次怎么查的

本会话里没有 atomcode 需要的 `ctx_*` 工具（`ctx_batch_execute`、`ctx_search` 都不可用），`atomcode 5.2.6` 本身在 PATH 里，但按 skill 的规定不能拿普通 shell 顶替，所以没有跑 atomcode。改用子代理做多源检索，然后对上面标了「已抽查」的官方页和响应头逐条核对。标了「子代理查到」的，没有逐页复核。
