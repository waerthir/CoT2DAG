讨论计划，对其合理的地方更新到docs\plan\plan-6.md，注意计划应当只专注于我们要做什么

首先我们需要理解实现的功能是什么。参照ref\other_src\calc.py和ref\other_src\calc_histogram.py，他是一个根据已有评分表（输入的json）来统计并给出对应的图的程序。

举个例子来说，对于节点评分表json，他们会统计其均值和方差（ref\other_src\calc.py），同时会根据画图，画图的同时根据设定的阈值判断合格的数量（ref\other_src\calc_histogram.py）

同时我们知道，评分表会类似于这样子

```
[
  {
    "batch_id": "001-C_1",
    "evaluation": {
      "Fidelity": 10.0,
      "Atomicity": 10.0
    }
  },
  {
    "batch_id": "001-C_2",
    "evaluation": {
      "Fidelity": 10.0,
      "Atomicity": 10.0
    }
  },
  ...
]
```

和这样子

```
[
  {
    "batch_id": "001-I_1",
    "evaluation": {
      "Dependency_Completeness": 10.0,
      "Dependency_Accuracy": 10.0,
      "Reasoning_Logic_Accuracy": 10.0,
      "Reasoning_Type_Accuracy": 10.0
    }
  },
  {
    "batch_id": "001-I_2",
    "evaluation": {
      "Dependency_Completeness": 10.0,
      "Dependency_Accuracy": 10.0,
      "Reasoning_Logic_Accuracy": 9.0,
      "Reasoning_Type_Accuracy": 10.0
    }
  },
  ...
]
```

这就意味着我们可以建立程序，输入是给定的json文件，合格参数，以及希望选用的参数有什么（因为你可以看到，两者的形式是相似的，有一个"evaluation"，我们可以选择提取"evaluation"内我们希望获取的参数，而这个可以指定）

我希望代码放置在script下面

代码应该有一个输入文件，一个阈值，一个希望选择的参数（可能应该是个列表），然后输出是一个文本文件（指示了各项数据，例如均值，方差，合格率，合格数量/总数量），还要有一个图，图就类似于ref\other_src\calc_histogram.py所画的一样，会标明分数和合格率啥的

然后程序总体在“一个希望选择的参数（可能应该是个列表）”时候我觉得最好可以传一个字典进去，方便制图的时候使用中文直接说明