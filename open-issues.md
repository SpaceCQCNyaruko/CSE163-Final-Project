# EDA 阶段问题清单

> 生成时间：2026-11-15 19:05（截止 23:59）
> 对应提交：`005e37c`（本地，未 push）
> 说明：本文件只记录**尚未解决**与**需要拍板**的事情，已完成的改动不在此列。

---

## 0. 当前状态一页纸

| 项 | 现状 |
|---|---|
| 交付物 | `eda.pdf`（12 页 = 正文 9 + 附录 3）、`src/` 5 个模块、`test_project.py` |
| 图表 | 7 张图、正文 5 张表、附录 4 张表（A1–D1） |
| 数据面板 | 构成分析 9 年（2015–2021、2023、2025）；合计 10 年（+2026）；SIV 5 年（2015、2017–2020） |
| 校验 | `python test_project.py` → 9 条全过；`flake8` → 无输出 |
| 已知失效文件 | FY2022（整页栅格图）、FY2024（字体无 Unicode 映射）、FY2026（国籍列损坏）、SIV FY2021+（州级标签损坏） |
| 工作区残留 | `.tmp/`（删不掉）、`.libs/`（本机依赖） |

---

## 1. proposal 里写明、但数据不支持的任务

以下 5 项都**不是**代码能力问题，而是源文件本身不含所需信息。按你要求的六段格式记录。

### B1 · RQ2 的 144 个月序列

| 字段 | 内容 |
|---|---|
| 原定任务描述 | proposal §5《RQ2: When does it stop?》第 1 条：*Build two monthly series for FY2015–FY2026 (144 months): Washington, and the national total across all states.* |
| 原定任务内容 | 用 A 的月度列构造华州与全国两条 144 个月序列，作为断点检测与月度跌幅分析的输入 |
| 问题位置 | proposal §5 RQ2 第 1 条；`eda.pdf` §5.5 图 3、§6 第二段 |
| 问题文件名 | `Dataset/Refugee_Arrivals_by_State_and_Nationality/FY 2015 … FY 2020 Arrivals by State and Nationality.xls(x)`（6 个） |
| 问题内容 | 这 6 个文件只有 `FY 20xx` 与 `Cumulative Total` 两列数字，没有 Oct–Sep 月度列（表头仅 4 列） |
| 相关解释 | 实际可构造的月度序列为 **36 个月**（FY2021/2023/2025）；FY2026 只有州合计。报告已写明“36 而不是 144”，但没有替代来源 |

### B2 · RQ4 的 FY2021–FY2022 对比

| 字段 | 内容 |
|---|---|
| 原定任务描述 | proposal §5《RQ4: Two ledgers》第 4 条：*Compare FY2021–FY2022 with FY2015–FY2019, and report FY2023–FY2025 alongside.* |
| 原定任务内容 | 用 A/B 的 outer join 计算阿富汗、伊拉克的 `count_siv/(count_refugee+count_siv)`，比较 2021 前后 |
| 问题位置 | proposal §5 RQ4 第 4 条；`eda.pdf` §5.5 图 6/图 7、§6 |
| 问题文件名 | `Dataset/SIV_Arrivals_by_Nationality_and_State/FY2021 … FY 2025 Amerasian & SIV Arrivals by Nationality and State.pdf`（5 个） |
| 问题内容 | 全国合计能对上（FY2021 8,567、FY2023 17,658 均等于印刷值），但州级/国籍标签损坏：`nationality="Not Available"` 的计数等于该州合计（WA FY2025 = 1,368、FY2023 = 1,832），另有 `Actual Destination Vietnam` 这类污染标签 |
| 相关解释 | 强行使用会把“州合计”当成“某国籍”，等于造数据；因此图 6/图 7 停在 FY2015–FY2020 |

### B3 · RQ3 的县级三档分类

| 字段 | 内容 |
|---|---|
| 原定任务描述 | proposal §5《RQ3》第 2 条：*Classify each language into one of three tiers, separately for B16001 (state) and C16001 (county).* |
| 原定任务内容 | 县级 13 类下再分“专列/共享/残余”，并据此给出县级地理结论 |
| 问题位置 | proposal §5 RQ3 第 2–3、5 条；`eda.pdf` §5.5 表 4、图 5、附录 C |
| 问题文件名 | `data/processed/acs_counties.csv`（C16001，39 县 × 13 类） |
| 问题内容 | 目前只做州级三档（B16001）；县级只直接查询 `Other and unspecified` 一个类别 |
| 相关解释 | 可做（约 40 分钟），但 C16001 只有 13 类，乌克兰语、索马里语、缅甸语会同时掉进 `Other and unspecified` 或 `Russian, Polish, or other Slavic`，三档区分度很低——做了大概率只是把“不可见”的数值放大 |

### B4 · RQ2 的断点检验与事件表

| 字段 | 内容 |
|---|---|
| 原定任务描述 | proposal §5 RQ2 第 3–5 条 |
| 原定任务内容 | `ruptures` binary segmentation（L2）、1,000 次置换的 max-statistic 零分布、政策事件表与月差 |
| 问题位置 | proposal §5 RQ2；`eda.pdf` §5.7 RQ2 bullet（目前写成“计划”） |
| 问题文件名 | 无（依赖 `ruptures`，未安装；输入应为 `outputs/wa_monthly.csv`） |
| 问题内容 | 现有月度序列只有 36 个月，FY2025 只有 4 个可用月；5 个政策事件里只有 2025-01 有月度数据可量月差 |
| 相关解释 | `eda.md` 对 Result Validity 只要求“说明 H0/检验/假设并验证假设”，不要求现在跑检验；报告已按此写成计划 |

### B5 · 数据源 D 的对账

| 字段 | 内容 |
|---|---|
| 原定任务描述 | proposal §3《D. Refugee Arrivals by Region》与挑战目标中的“独立发布物校验” |
| 原定任务内容 | 解析 6 个 region 文件，用全国月度合计独立校验 A 的解析结果 |
| 问题位置 | proposal §3 D 段；`eda.pdf` §4 Method |
| 问题文件名 | `Dataset/Refugee_Arrivals_by_Region/*.pdf`（6 个） |
| 问题内容 | D 未解析；其中 FY2024 那份是纯图片（`extract_words()` 返回 0 个词），其余布局未探 |
| 相关解释 | 约 1 小时可做；收益是给 A 加一道独立校验。报告现已改为“与文件内印刷总计对账”，与实际一致 |

---

## 2. 报告与代码不一致（需要在提交前决定）

### P1 · 报告说 SIV 没有月份，实际有（事实错误）

- **位置**：`eda.pdf` §5.1 第二句；§3 表 1 的 B 行单位
- **报告原文**：*The SIV table has the same shape but no month column.*；表 1 写 `State × nationality`
- **实际**：SIV PDF 有 Oct–Sep 共 12 列。`outputs/arrivals_monthly.csv` 中 `source == "siv"` 有 **4,491 行**，2015–2025 每年都有 12 个月
- **影响**：一句事实错误；也低估了数据（SIV 的全国月度序列可用于对照，但 FY2021+ 的州级/国籍标签损坏，见 B2）
- **改法**：一句改成 *The SIV table has the same shape, month columns included.*；表 1 的 B 行单位改成 `State × nationality × month`（2 分钟）

### P2 · Method 的“第三条检查”只在测试里，不在解析器里

- **位置**：`eda.pdf` §4 Method 第二段；`src/parse.py`
- **报告原文**：*Third, where the file prints a state total (FY2021 and FY2023), Washington's parsed rows must equal it.*
- **实际**：`parse.py` 只校验全国合计（`validate_total`）；州级等式只存在于 `test_project.py::test_washington_matches_printed_state_total`
- **影响**：措辞比实现强
- **改法**：二选一——把该断言搬进 `load_all()`（约 5 行），或把措辞改成 *the test suite asserts that ...*（3 分钟）

### P3 · 图文件名与图编号错位

- **位置**：`figures/` 与 `eda.pdf` 的图号
- **实际**：`f5_language.png` 是图 4，`f6_counties.png` 是图 5，`f7_ledgers.png` 是图 6，`f8_siv_share.png` 是图 7
- **影响**：读者对照仓库时会困惑（图 4 的文件名叫 f5）
- **改法**：把 f5→f4、f6→f5、f7→f6、f8→f7 重命名，并同步 `src/figures.py` 与 `build_eda_docx.py`（约 15 分钟）

### P4 · 章节编号 1–9，eda.md 列 10 项

- **位置**：`eda.pdf` 正文标题
- **实际**：spec 把 Title/Author 算第 1 项；我们标题未编号，RQs 从 1 开始
- **状态**：上一轮选项 3 你选择不改，此处仅记录
- **改法**：全部后移一位（10 分钟）

### P5 · 正文 9 页，软上限 8 页

- **位置**：`eda.pdf` 正文（第 1–9 页），附录第 9–12 页
- **实际**：正文 9 页
- **改法**：删 1 张图或压 300 字（30 分钟）；或接受（spec 写的是“soft upper limit”）

---

## 3. 工作区残留

| 残留 | 说明 | 处理 |
|---|---|---|
| `.tmp/` | pip 安装失败的临时目录，ACL 拒绝删除（`Access is denied`），已 gitignore | 需你在普通终端 `rd /s /q .tmp` |
| `.libs/` | `xlrd` / `openpyxl` 的 wheel（沙箱里 pip 用不了，手动解包），已 gitignore | 保留；换机器时按 `requirements.txt` 安装 |
| `eda.docx` | 已按要求删除 | — |
| 未 push | `005e37c` 只在本地 | `git push` 需要你的凭据 |
| 仓库可见性 | 报告首页链接 `github.com/SpaceCQCNyaruko/CSE163-Final-Project` | 需你确认是 Public |

---

## 4. 待决策清单

| # | 事项 | 选项 | 工时 | 建议 |
|---|---|---|---|---|
| D1 | FY2022 的 18 页栅格图 | Windows OCR 重建表格 / 保持缺口 | 2–3h | 不做，风险高收益低 |
| D2 | FY2024 字形解码 | 约束反解数字 / 放弃 | 2–4h | 不做 |
| D3 | B3 县级三档 | 做 / 报告写清限制 | 40 min | 不做，写清 |
| D4 | B5 解析 D 对账 | 做 / 保持现措辞 | 1h | 不做 |
| D5 | P1 SIV 月份事实错误 | 改一句 + 表 1 单位 | 2 min | **做** |
| D6 | P2 第三条检查 | 搬进代码 / 改措辞 | 5 min | **做（改措辞最快）** |
| D7 | P3 图文件重命名 | 重命名 4 个文件 | 15 min | 做（可选） |
| D8 | P4 章节编号 | 改成 1–10 | 10 min | 你已表态不改 |
| D9 | P5 正文压到 8 页 | 删图 / 压字 | 30 min | 看你对页数的要求 |
| D10 | push + Public 检查 | 需要你的凭据 | 5 min | **必须做** |

**我的建议**：先做 D5、D6（都是几分钟，且是事实性错误），D10 你确认后我无法代劳；D1–D4 全部不做，理由写进报告或本文件即可；D9 由你决定。
