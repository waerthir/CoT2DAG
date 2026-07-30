讨论计划，更新于docs\plan\plan-5.md，注意要聚焦于措施，避免不必要的解释

现在要写两个新的BatchTaskAdapter，功能是把像data\cot-1\llava-cot-11b\node.json和data\cot-1\llava-cot-11b\relationship.json（这两个文件你不要读完全部，读一部分就可以），通过类似于ref\other_src\dag_comparer_1.py和ref\other_src\dag_comparer_2.py的方式，调用大模型生成对应的json文件，作为评估。相应的功能你可以通过代码看出

现在你已经理解了主要功能是什么，但是在这个项目中，我们已经通过src\batch_engine实现了模型批量调用的标准化，使得我们可以通过写类似于src\tasks\cot_to_dag里面展示的任务创建文件，来进行代码的编写。

我希望你能够模仿已有的src\tasks\cot_to_dag里面展示的代码逻辑，但是实现旧代码ref\other_src\dag_comparer_1.py和ref\other_src\dag_comparer_2.py所展现的大致功能。理论上来说，大部分代码都是src\tasks\cot_to_dag里面代码的变形，因为内部分发逻辑几乎是完全一致的，而具体的调用大模型的逻辑虽然有点模糊，但是也能在旧代码文件里面体现的系统提示词来理解我们做了什么。

顺带一提，关于配置文件的创建，我有这些建议：首先，配置文件是每一个单独的项目管理一个，我在之前的src\tasks\cot_to_dag\cli.py做了小小的修改（主要是追踪项目根路径之类的），使得配置文件能够对应每一份内部管理的cot都有单独一个，类似于data\cot-1\llava-cot-11b\cot_to_dag.yaml，因此，新写的配置文件（因为你会写类似于原来的代码，所以配置文件必然也是类似的）也可以放在data\cot-1\llava-cot-11b\，名字可以叫node/relationship.yaml之类的。之前的configs文件已经弃用了，因为层次上不对

模型配置方面和原来的data\cot-1\llava-cot-11b\cot_to_dag.yaml是差不多的，几乎是一样的

cli也是照着来，实现类似的功能就好了

你可能疑惑为什么我会这么写代码，而不是进一步解耦，因为进一步解耦我认为成本过高，使得代码难以编写，而且后续adapter可能会有更优的写法，但是就从目前的实现来说，照着写是一个合理的选择。