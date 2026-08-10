# JSON 图片资源镜像下载计划

- 新建 `scripts/download_json_images.py`，只接收一个命令行位置参数：输入 JSON 路径。
- 递归遍历 JSON 的对象和列表：
  - 键名为 `image_path` 时，直接读取其字符串路径；
  - 键名为 `image_paths` 时，逐项读取其字符串路径列表；
  - 汇总后按远程路径去重。
- 使用 SSH 主机别名 `XAIpublic` 下载图片。SSH 客户端按常规查找 `C:\\Users\\waerthir\\.ssh\\config` 和私钥 `C:\\Users\\waerthir\\.ssh\\id_ed25519`；脚本不读取、不复制、不打印私钥内容，也不使用 `id_ed25519.pub` 发起认证。
- 运行前由用户保证 SSH 别名 `XAIpublic` 已在 SSH 配置中指向正确的远程主机、用户和端口；脚本调用等价于以下命令的下载操作：

  ```text
  scp XAIpublic:/home/user/images/example.png data\download\XAIpublic\home\user\images\example.png
  ```

- 将每个远程绝对路径镜像到 `data\download\XAIpublic` 下：

  ```text
  /home/user/images/example.png
  → data\download\XAIpublic\home\user\images\example.png
  ```

- 创建目标图片的父目录；已存在的完整目标文件跳过。下载先写入临时文件，成功后再替换为最终文件名，支持中断后继续执行。
- 单个路径下载失败时在终端报告并继续处理其余路径；最后输出发现路径数、去重后路径数、下载数、已存在跳过数和失败数，并以失败数决定退出码。
- 限制输出路径始终位于 `data\download\XAIpublic` 内，拒绝含 `..` 的远程路径片段。
