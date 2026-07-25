# 05B_VERIFICATION_PLAN.md — 验证计划

> 版本: v1
> 产出自: /blueprint
>
> 执行主清单: 05A_TASKS.md

## 1. 范围与目标
本验证计划覆盖 v1 执行清单 (`05A_TASKS.md`) 中的所有任务。目标是为 Automated Expense Tracker 提供严格的测试护栏，确保在后续 AI 自动化执行（Auto/Turbo 模式）期间，每一次文件修改都必须通过格式化、静态检查和单元测试。

**Execution Verification Commands:**
Agents must run these verification gates before generating a final diff:
- **Linting & Type Checking**: `pyright` (or `flake8 .`)
- **Formatting**: `black . --check` (or run `black .` to fix)
- **Unit Tests**: `pytest tests/ -v`

## 2. 验证分层策略
| 层次 | 负责范围 | 主要工具 |
|------|---------|---------|
| 单元测试 | 解析逻辑、标准化逻辑、分类算法 | `pytest` |
| 集成测试 | 分类器级联调用、API 写入 (Dry-Run) | `pytest` |
| 静态检查 | 代码规范与类型安全 | `pyright` / `flake8` / `black` |
| E2E测试 | CLI 执行全流程链路 | 本地 bash 脚本跑 `--dry-run` |

## 3. 风险类别覆盖原则
- 针对 Parser：边界值验证（空文件、密码错误、金额为0）。
- 针对 Classifier：确保 LLM 只有在 Rule 和 ML 均未命中时被调用，避免 API 滥用和超额扣费。
- 针对 API 写入：确保 dry-run 时不会对真实 Google Sheet 发起网络写请求。

## 4. 测试材料与证据要求
| 验证类型 | 测试材料位置 | 证据形式 |
|---------|------------|---------|
| 单元测试 | `tests/unit/` | `pytest` 控制台输出 |
| 集成测试 | `tests/integration/` | `pytest` 控制台输出 |
| 静态检查 | codebase root | 无错误/警告输出 |

---

## 5. Task-by-Task 验证计划

### T1.1.1
- **关联需求**: REQ-PARSE (Standardize Parsers)
- **关联契约**: 原始账单提取契约
- **风险类别**: 解析错误 / 丢失字段
- **单元测试覆盖**:
  - ICICI / Axis / SBI / HDFC Parser 正常解析并提取关键字段
  - Parser 遇到空文件抛出 ValueError
- **断言**: 提取列表不为空，字段完整。
- **证据**: `tests/unit/test_parsers.py`

### T1.1.2
- **关联需求**: REQ-NORM (Transaction Normalization)
- **关联契约**: 统一数据结构契约
- **风险类别**: 数据类型异常 / 脏数据
- **单元测试覆盖**:
  - 去除 description 中的特殊字符
  - Date string 转换为 YYYY-MM-DD
  - Amount 转换为 Float
- **断言**: 最终 Schema 100% 匹配预期格式。
- **证据**: `tests/unit/test_normalizer.py`

### T1.2.1
- **关联需求**: REQ-CLASS (Test Classification Engine)
- **关联契约**: 级联分类契约
- **风险类别**: LLM API 滥用 / 分类错误
- **集成测试覆盖**:
  - Rule 命中时立刻返回，ML不调用
  - ML 命中（且高置信度）时立刻返回，LLM不调用
  - LLM 被调用并处理无法分类的交易（通过 mock API 验证调用发生）
- **断言**: 验证调用链正确性及 `classification_method` 标记值。
- **证据**: `tests/unit/test_classifiers.py`

### T1.3.1
- **关联需求**: REQ-OUT (Validate GSheets Dry-Run)
- **关联契约**: 数据导出契约
- **风险类别**: 测试数据污染真实表单
- **集成测试覆盖**:
  - `--dry-run` 模式下拦截 requests/API client
- **断言**: GSheets API 调用次数为 0，本地生成审计文件。
- **证据**: `tests/integration/test_gsheets.py`

---

## 6. Contract Coverage Overlay

| 契约 | 类型 | 实现承接 | 验证承接 | 状态 |
|------|------|---------|---------|:----:|
| 统一数据格式 Schema | 数据契约 | T1.1.2 | T1.1.2 单元测试 | ✅ |
| 分类器级联规则 | 业务逻辑 | T1.2.1 | T1.2.1 集成测试 | ✅ |
| Google Sheets Write API | HTTP API | T1.3.1 | T1.3.1 `--dry-run` 测试 | ✅ |

## 7. Testing Coverage Overlay

| 测试责任 | 风险类别 | 覆盖方法 | 任务承接 | 测试材料 | 状态 |
|---------|---------|---------|---------|---------|:----:|
| Parser 解析完整性 | 数据丢失 | 单元测试 + Mock Files | T1.1.1 | `tests/unit/test_parsers.py` | ✅ |
| 避免 LLM 成本泄漏 | API 滥用 | 级联集成测试 + Mock | T1.2.1 | `tests/unit/test_classifiers.py` | ✅ |
| 防止污染生产表格 | 生产数据破坏 | Dry-run mock 断言 | T1.3.1 | `tests/integration/test_gsheets.py` | ✅ |

## 8. Verification Traceability Matrix

| REQ/Contract | Task | Verification | Test Material | Evidence | Status |
|---|---|---|---|---|---|
| REQ-PARSE 解析标准化 | T1.1.1 | 单元测试 | `tests/unit/test_parsers.py` | Pytest Output | ✅ |
| REQ-NORM Schema标准化 | T1.1.2 | 单元测试 | `tests/unit/test_normalizer.py` | Pytest Output | ✅ |
| REQ-CLASS 级联安全 | T1.2.1 | 集成测试 | `tests/unit/test_classifiers.py` | Pytest Output | ✅ |
| REQ-OUT 审计与干跑安全 | T1.3.1 | 集成测试 | `tests/integration/test_gsheets.py` | Pytest Output | ✅ |
