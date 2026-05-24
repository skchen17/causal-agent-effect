# E21 T50 Reproducibility and Result-Source Appendix

## 目的

记录每个结果文件的来源脚本、命令、输入输出路径和关键指标，保证论文数字可追溯。

## 主要结论

T50 建立了 53-step `reproduce_auth_safeinv.sh` 和 source appendix。该目录不提供新的科学结论，而是支撑 artifact reproducibility 和 reviewer audit。

## 关键产物

- `reproduce_auth_safeinv.sh`
- `analysis/appendix/generate_auth_result_source_appendix.py`
- `analysis/appendix/auth_result_source_appendix.json`
- `analysis/appendix/auth_result_source_appendix.md`
- `analysis/appendix/generate_paper_table_audit.py`
- `analysis/audits/paper_table_audit.md`

## 论文可支持的 claim

可以用于说明主结果表的 artifact lineage 和复现入口。

## 不能支持的 claim

不要把 reproduction appendix 当作实验结果；它只说明文件存在和如何生成。

