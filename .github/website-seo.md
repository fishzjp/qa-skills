# GitHub Pages SEO 维护

网站源是 `index.html`；`scripts/build_site.py` 从同一源构建中文根页和 `/en/`，并输出 sitemap、分享图片、llms.txt 与自托管字体。只维护这一份双语源，不直接编辑 `_site/`。不混入本地规划、评测和运行产物。

## 页面维护约定

- 首屏明确说明测试 Skills、用例设计、Playwright / API 测试等用途，提供安装、真实示例和能力入口。
- 完整目录直达 12 个 Skill 指南，README 的中文和英文入口分别指向对应官网页面。
- 语言页只输出对应语言的正文，保留互相引用的 hreflang、自引用 canonical 和静态语言链接。
- Open Graph 与 Twitter 标题、描述、语言对应当前 URL。FAQ JSON-LD 从当前页面可见问答生成，避免手写副本漂移。
- 旧 `?lang=` 入口导航到静态语言 URL，保留推广参数与锚点。无 JavaScript 的访问者使用静态语言链接。
- 收敛首屏动效亮度，小屏与触屏设备使用静态光晕，避免持续运行 WebGL。
- 320px 起检查双语布局、键盘焦点、复制命令与无 JavaScript 阅读。

页面和工程检查不能证明已收录、排名提升或跨宿主模型效果提升。FAQ 标记用于保留机器可读的问答语义，不作为 Google 搜索增强展示手段：Google 已于 2026 年 5 月停止展示 FAQ 富媒体结果（见下方官方更新记录）。

## 发布后需要账号权限的操作

1. 等 `pages` workflow 成功，检查以下线上地址返回 200，确认浏览器展示的是新标题和内容：
   - [中文首页](https://fishzjp.github.io/qa-skills/)
   - [英文首页](https://fishzjp.github.io/qa-skills/en/)
   - [sitemap](https://fishzjp.github.io/qa-skills/sitemap.xml)
   - [分享图片](https://fishzjp.github.io/qa-skills/og.jpg)
2. 在 Google Search Console 中添加并验证 URL 前缀属性 `https://fishzjp.github.io/qa-skills/`。验证标签必须来自对应的站点管理账号，按账号提供的内容加入源页面。
3. 提交 `sitemap.xml`，用 URL 检查分别检查两个语言首页的抓取、选定 canonical 和索引状态，再按实际状态请求编入索引。Bing Webmaster Tools 可提交同一 sitemap。
4. 以发布日为基线，每周观察查询词、展示次数、点击数、CTR、落地页和国家/语言；比较完整的 28 天窗口，避免将短期波动归因于页面优化。
5. 通过项目 README、相关示例和真实技术文章链接到对应语言官网；宣传链接可带 `utm_source`，站点 canonical 仍指向无参数 URL。保持项目描述与实际能力相符。

项目站位于 `/qa-skills/` 子路径。爬虫规则的有效入口是域名根目录 `/robots.txt`，不能通过这里的 `/qa-skills/robots.txt` 配置整个主机，因此没有生成一个看似有效的项目级 robots.txt。这里通过 HTML 中的 sitemap 链接和 Search Console 提交提供发现入口。

## 本地验证

```bash
QA_PYTHON=python3.12 bash scripts/check.sh
python3.12 tests/browser/smoke.py
```

浏览器依赖见 `tests/browser/requirements.txt`，标准环境使用 `python3.12 -m playwright install chromium`。已有 Chrome 的本地环境可用 `QA_BROWSER_CHANNEL=chrome`；CI 保持使用 Playwright Chromium。设置 `QA_SITE_SCREENSHOT_DIR` 可保存双语、多尺寸截图。不运行模型评测。

## 官方依据

- [Google：多语言页面与 hreflang](https://developers.google.com/search/docs/specialty/international/localized-versions)
- [Google：构建和提交 sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)
- [Google：robots.txt 的位置与适用范围](https://developers.google.com/search/docs/crawling-indexing/robots/intro)
- [Google：FAQ 富媒体结果退役记录（2026 年 5 月和 6 月）](https://developers.google.com/search/updates#june-2026)
