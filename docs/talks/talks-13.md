讨论计划，更新到docs\plan\plan-7.md，只关注我们要做什么。不动代码

我之前尝试了4并发，居然成功率比单串更高，我开始怀疑可能是请求过于频繁导致的。我现在希望增加一个小的机制，能够控制每个请求之间的间隔。给一个方案，但是要求轻量。

最好能够通过对应的yaml文件更改吧。同时yaml如果没有给出来的话，默认就是不做限制，给的话就按照yaml给的秒数来进行限制

对应的可以看的记录部分如下，你可以参考

```
23:20:59 - LiteLLM:INFO: utils.py:3838 - 
LiteLLM completion() model= gpt-5.4; provider = openai
2026-07-30 23:20:59,821 INFO 
LiteLLM completion() model= gpt-5.4; provider = openai

Give Feedback / Get Help: https://github.com/BerriAI/litellm/issues/new
LiteLLM.Info: If you need to debug this error, use `litellm._turn_on_debug()'.

2026-07-30 23:21:00,492 ERROR API call failed on attempt 1: litellm.BadRequestError: OpenAIException - Upstream request failed
2026-07-30 23:21:00,492 ERROR Max retries exceeded. Total attempts: 1, Last error: litellm.BadRequestError: OpenAIException - Upstream request failed
2026-07-30 23:21:00,500 WARNING Failed batch_id=174-I_2: litellm.BadRequestError: OpenAIException - Upstream request failed
23:21:00 - LiteLLM:INFO: utils.py:3838 - 
LiteLLM completion() model= gpt-5.4; provider = openai
2026-07-30 23:21:00,506 INFO 
LiteLLM completion() model= gpt-5.4; provider = openai

Give Feedback / Get Help: https://github.com/BerriAI/litellm/issues/new
LiteLLM.Info: If you need to debug this error, use `litellm._turn_on_debug()'.

2026-07-30 23:21:01,227 ERROR API call failed on attempt 1: litellm.BadRequestError: OpenAIException - Upstream request failed
2026-07-30 23:21:01,228 ERROR Max retries exceeded. Total attempts: 1, Last error: litellm.BadRequestError: OpenAIException - Upstream request failed
23:21:01 - LiteLLM:INFO: utils.py:3838 - 
LiteLLM completion() model= gpt-5.4; provider = openai
2026-07-30 23:21:01,504 INFO 
LiteLLM completion() model= gpt-5.4; provider = openai

Give Feedback / Get Help: https://github.com/BerriAI/litellm/issues/new
LiteLLM.Info: If you need to debug this error, use `litellm._turn_on_debug()'.

2026-07-30 23:21:02,312 ERROR API call failed on attempt 1: litellm.BadRequestError: OpenAIException - Upstream request failed
2026-07-30 23:21:02,313 ERROR Max retries exceeded. Total attempts: 1, Last error: litellm.BadRequestError: OpenAIException - Upstream request failed
2026-07-30 23:21:02,321 WARNING Failed batch_id=180-I_2: litellm.BadRequestError: OpenAIException - Upstream request failed
23:21:03 - LiteLLM:INFO: utils.py:3838 - 
LiteLLM completion() model= gpt-5.4; provider = openai
2026-07-30 23:21:03,267 INFO 
LiteLLM completion() model= gpt-5.4; provider = openai

Give Feedback / Get Help: https://github.com/BerriAI/litellm/issues/new
LiteLLM.Info: If you need to debug this error, use `litellm._turn_on_debug()'.

2026-07-30 23:21:03,963 ERROR API call failed on attempt 1: litellm.BadRequestError: OpenAIException - Upstream request failed
2026-07-30 23:21:03,963 ERROR Max retries exceeded. Total attempts: 1, Last error: litellm.BadRequestError: OpenAIException - Upstream request failed
2026-07-30 23:21:03,970 WARNING Failed batch_id=184-I_1: litellm.BadRequestError: OpenAIException - Upstream request failed
23:21:06 - LiteLLM:INFO: utils.py:3838 - 
LiteLLM completion() model= gpt-5.4; provider = openai
2026-07-30 23:21:06,622 INFO 
LiteLLM completion() model= gpt-5.4; provider = openai

Give Feedback / Get Help: https://github.com/BerriAI/litellm/issues/new
LiteLLM.Info: If you need to debug this error, use `litellm._turn_on_debug()'.

2026-07-30 23:21:07,276 ERROR API call failed on attempt 1: litellm.BadRequestError: OpenAIException - Upstream request failed
2026-07-30 23:21:07,276 ERROR Max retries exceeded. Total attempts: 1, Last error: litellm.BadRequestError: OpenAIException - Upstream request failed
2026-07-30 23:21:07,291 WARNING Failed batch_id=191-C_9: litellm.BadRequestError: OpenAIException - Upstream request failed
23:21:12 - LiteLLM:INFO: utils.py:3838 - 
LiteLLM completion() model= gpt-5.4; provider = openai
2026-07-30 23:21:12,207 INFO 
LiteLLM completion() model= gpt-5.4; provider = openai

Give Feedback / Get Help: https://github.com/BerriAI/litellm/issues/new
LiteLLM.Info: If you need to debug this error, use `litellm._turn_on_debug()'.

2026-07-30 23:21:12,846 ERROR API call failed on attempt 1: litellm.BadRequestError: OpenAIException - Upstream request failed
2026-07-30 23:21:12,846 ERROR Max retries exceeded. Total attempts: 1, Last error: litellm.BadRequestError: OpenAIException - Upstream request failed
2026-07-30 23:21:12,861 WARNING Failed batch_id=198-C_5: litellm.BadRequestError: OpenAIException - Upstream request failed
状态：pending=0，completed=990，failed=17
```