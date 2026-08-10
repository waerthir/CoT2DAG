# cot-3、cot-4、cot-5 合并计划

## 目标目录与命名

- 将 `data/cot-4/<模型>/`、`data/cot-5/<模型>/` 迁入 `data/cot-3/`，与现有 `cot-3` 模型目录并列。
- 无同名冲突的目录保留原模型名。

## 迁移内容

- 以模型目录为单位迁移其中的源数据 JSON、`cot.json`、`cot_old.json`（如有）、`dag.json`、`dag.sqlite3`、SQLite journal/WAL 文件（如有）及 `cot_to_dag.yaml`。
- 迁移前逐个确认目标目录不存在；迁移后确认源目录中的文件数与目标目录一致。
- 迁移完成后，`data/cot-3/` 下保留全部 25 个模型目录：原 cot-3 的 7 个、原 cot-4 的 12 个、原 cot-5 的 6 个。

## YAML 统一更新

- 对每份 `data/cot-3/*/cot_to_dag.yaml` 保留已有 YAML 的全部其他字段、注释和字段值，仅更新以下字段。
- 更新 `paths.input_json`、`paths.database`、`paths.output_json`，使三者均指向 YAML 所在的实际模型目录；`paths.system_prompt` 保持原值。
- 统一更新以下既有配置字段：

  ```yaml
  model:
    api_key_env: CODEX_2_API_API_KEY
    timeout_s: 45
    max_concurrency: 200
    stream: true

  retry:
    max_wait_s: 60
  ```

- 除上述路径和五个配置字段外，其余 `model`、`retry` 与其他 YAML 内容均原样保留。

## 关联文件

- 更新根目录 `进度.md`：删除已迁移的 `cot-4 /`、`cot-5 /` 行前缀，按新的 `data/cot-3` 模型目录名列出全部模型。
- 后续 `cot_to_dag` 命令均使用 `data/cot-3/<模型>/cot_to_dag.yaml`。

## 验收

- `data/cot-3/` 包含 26 个模型目录，且不丢失迁移前的文件。
- 每份 `cot_to_dag.yaml` 可由配置加载器读取，三条数据路径均落在该 YAML 所在模型目录。
- 每份 YAML 的 API Key 环境变量、并发、超时、流式与 `max_wait_s` 均符合统一值。
