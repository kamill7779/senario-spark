# Agent 工作规范

本文档定义 SenarioSpark 仓库的分支命名、工作树使用和合并规范。

## 分支命名

所有开发分支使用以下格式：

```text
<type>/<scope>-<short-description>
```

常用 `type`：

```text
feat      新功能
fix       缺陷修复
chore     工程维护、依赖、脚手架、仓库配置
docs      文档
refactor  重构，不改变外部行为
test      测试
perf      性能优化
ci        CI/CD 配置
build     构建系统
```

示例：

```text
feat/highlight-agent
fix/asr-segment-timing
docs/analysis-v1
chore/init-workspace
refactor/video-pipeline
```

分支名要求：

```text
1. 使用英文小写、数字和连字符。
2. 不使用空格、中文和特殊符号。
3. 描述保持短，但要能看出任务目的。
4. 一个分支只处理一个明确主题。
```

## 工作树规范

除首次初始化 `main` 外，后续功能开发、修复和文档改动都应在独立 worktree 中完成。

统一使用仓库根目录下的 `.worktrees/`：

```text
D:\Project\senario-spark\.worktrees\
```

`.worktrees/` 必须被 `.gitignore` 忽略，避免把工作树内容提交进主仓库。

创建新工作树时，先从主仓库同步 `main`：

```powershell
git -C D:\Project\senario-spark fetch origin
git -C D:\Project\senario-spark checkout main
git -C D:\Project\senario-spark pull --ff-only origin main
```

然后创建新分支工作树：

```powershell
git -C D:\Project\senario-spark worktree add .worktrees\<worktree-name> -b <type>/<scope>-<short-description> main
```

示例：

```powershell
git -C D:\Project\senario-spark worktree add .worktrees\docs-analysis-v1 -b docs/analysis-v1 main
```

工作树目录名使用不带斜杠的短名，例如：

```text
分支名：docs/analysis-v1
目录名：.worktrees/docs-analysis-v1
```

## 合并规范

`main` 是受保护主分支。

规则：

```text
1. 不直接在 main 上做日常开发。
2. 所有变更通过 feature/fix/docs/chore 分支提交。
3. 分支推送到 origin 后创建 Pull Request。
4. PR 通过检查和 review 后合并到 main。
5. 合并后删除远端分支，并清理本地 worktree。
```

推送分支：

```powershell
git push -u origin <branch-name>
```

PR 合并后清理 worktree：

```powershell
git -C D:\Project\senario-spark worktree remove .worktrees\<worktree-name>
git -C D:\Project\senario-spark branch -d <branch-name>
git -C D:\Project\senario-spark fetch origin --prune
```

## 提交信息

提交信息使用 Conventional Commits 风格：

```text
<type>: <summary>
```

示例：

```text
feat: add highlight extraction agent contract
fix: correct ASR segment timing lookup
docs: document analysis architecture v1
chore: initialize project structure
```

提交前至少执行：

```powershell
git diff --check
git status --short
```

如果所在模块已有测试或格式化命令，应在提交前运行对应命令。
