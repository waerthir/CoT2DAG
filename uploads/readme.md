# 数据汇总

```
cot-1\gemini-3.1pro\node_stat.xxx  放置了关于gemini-3.1pro节点的评估
cot-1\gemini-3.1pro\rel_stat.xxx   放置了关于gemini-3.1pro关系对的评估

cot-1\llava-cot-11b\node_stat.xxx  放置了关于llava-cot-11b节点的评估
cot-1\llava-cot-11b\rel_stat.xxx   放置了关于llava-cot-11b关系对的评估
```

# 开销

均抽取两百个题进行转化和评估，转化使用gpt5.4mini，评分使用gpt5.4

llava-cot-11b的原始数据的思维链比较短，codex2api平台上总开销1.22元（转化+评估）

gemini-3.1pro的原始数据的思维链比较长，codex2api平台上开销3.01元

# 对比情况

效果相较于gpt5.5，略差，但是大概差距在一两个百分比左右

相较于当时使用的qwen plus大致相同

相较于deepseek（当时使用的v3版本）更好

效果依然在有逻辑的思维链上效果更好，而在粗糙的思维链上的转化效果一般。（本实验分别是11b模型、gemini3.1pro，模型智能有比较大的区别）因为DAG的形式本身是强逻辑的，而CoT的质量过差，强行转化为DAG的过程中会出现信息偏差