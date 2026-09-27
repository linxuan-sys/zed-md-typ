# zed-preview —— Markdown / Typst 浏览器实时预览（自包含）

在浏览器里实时预览 Markdown（含 LaTeX 公式）和 Typst，**无需联网**。  
所有依赖都打包在本文件夹内。

## 平台要求

- **Linux x86_64**（本包内 `bin/pandoc`、`vendor/tinymist` 是 Linux x86-64 二进制）
- 目标机器还需要：
  - **Python 3**（仅 Markdown 预览需要）
  - **glibc**（tinymist 依赖；主流发行版都有）
  - 一个**浏览器** + `xdg-open`（用于自动打开预览页）
  - **Zed 编辑器**（可选；不用 Zed 也可以用下面的独立脚本）

## 直接用（不装进 Zed）

```sh
./preview-md.sh 你的笔记.md     # 浏览器打开 Markdown 预览
./preview-typst.sh 你的文档.typ # 浏览器打开 Typst 预览
```

改文件后**保存（Ctrl+S）**，浏览器会自动刷新。

## 安装进 Zed（推荐）

```sh
./install-to-zed.sh
```

它会：
1. 把 `md_preview.py`、`preview-typst.sh`（装为 `typst_preview.sh`）和 `vendor/` 复制到 `~/.config/zed/`；
2. 把两个任务和 `Alt+M` / `Alt+T` 快捷键**合并**进你的 `tasks.json` / `keymap.json`（原文件会备份成 `*.bak.时间戳`）。

装完后重启 Zed：打开 `.md` 按 `Alt+M`，打开 `.typ` 按 `Alt+T`。

## 目录内容

```text
zed-preview/
├── preview-md.sh        Markdown 独立预览脚本
├── preview-typst.sh     Typst 独立预览脚本（会自动清掉上一次预览）
├── install-to-zed.sh    一键装进 Zed
├── md_preview.py        预览服务器（便携版，自动找同目录的 vendor/bin）
├── merge-zed-config.py  合并 Zed 配置用
├── bin/pandoc           pandoc 3.11（静态，可独立运行）
├── vendor/katex/        KaTeX（离线渲染公式）
├── vendor/tinymist      Typst 预览/编译后端
└── zed/                 供手动合并的 tasks.json / keymap.json 模板
```

## 说明

- **不需要联网**，不需要 nvim，不需要系统 pandoc。
- 预览刷新发生在**保存文件之后**（编辑器写过盘才会刷新）。
- **Typst 预览一次只开一个**：tinymist 固定占用 23625/23626 端口，本包的启动脚本会先清掉旧实例再启动，所以换文件重新按快捷键即可。
- 依赖的第三方组件版权归其各自作者：pandoc (GPL)、KaTeX (MIT)、tinymist (Apache-2.0)。
