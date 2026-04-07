# Resumable Tasks

最小可复用模式：用一个 JSON 文件定义待继续执行的任务，再用脚本把它调度成 `openclaw cron add --session isolated` 的 job。

## 文件格式

示例：`tasks/resumable-task-template.json`

字段：

- `name`: cron job 名称
- `schedule.at`: 执行时间，支持 `20m` 这类 duration 或 ISO 时间
- `target.sessionKey`: 要回投的会话 key
- `target.announce`: `true` 时自动 announce 回会话；`false` 时只执行不投递
- `task.message`: 独立任务会话里要执行的完整提示词

## 用法

```powershell
python tools/schedule_resumable_task.py --spec tasks/resumable-task-template.json --json
```

也可以直接命令行传参：

```powershell
python tools/schedule_resumable_task.py --name demo --at 20m --message "20分钟后继续这个任务并汇报结果" --announce --json
```

## 设计意图

把“可恢复任务”的定义从一次性 CLI 参数中抽出来，形成：

1. 可保存
2. 可复查
3. 可复用
4. 可由其他机制自动生成

这样下一步就可以继续往前做：

- 让 `task_runner` 自动产出这类 spec
- 让 executor/reporter 基于 spec 衔接真实任务恢复
- 对不同任务类型沉淀不同 message 模板
