# OCSonicDev

本工作区用于根据厂家 CSV 翻译规则开发 OC→SONiC 配置 JSON 翻译器。

提供的原始材料只有两份：

- `references/raw/yang2sonic_maptable(1).csv`：翻译规则，作为手册使用。
- `data/raw/oc/CQ-JLDC-2203-D05-TCS84R-LA200G-019.txt`：最终测试会使用的完整 OC 文档。

开发完成后，评测方会将这份 OC 交给翻译器，将生成结果与标准配置 JSON 比对。标准配置 JSON 不在本工作区提供。

任务说明见 `PROMPT.md`。在本目录打开一个新 Agent，让它执行该文件即可。

材料身份记录在 `data/manifest.json`。校验原始文件：

```powershell
python scripts/verify_materials.py
```
